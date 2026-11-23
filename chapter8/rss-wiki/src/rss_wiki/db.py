"""SQLite 연결과 스키마 (PRD §6). 마이그레이션 도구 없이 앱 시작 시 IF NOT EXISTS로 생성한다."""
from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS feeds (
  id                   INTEGER PRIMARY KEY AUTOINCREMENT,
  url                  TEXT NOT NULL UNIQUE,
  title                TEXT,
  is_active            INTEGER NOT NULL DEFAULT 1,
  last_fetched_at      TEXT,
  consecutive_failures INTEGER NOT NULL DEFAULT 0,
  created_at           TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS categories (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  name            TEXT NOT NULL UNIQUE,
  parent_id       INTEGER REFERENCES categories(id) ON DELETE SET NULL,
  description     TEXT,
  is_user_edited  INTEGER NOT NULL DEFAULT 0,
  merged_into_id  INTEGER REFERENCES categories(id) ON DELETE SET NULL,
  created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_categories_parent ON categories(parent_id);

CREATE TABLE IF NOT EXISTS articles (
  id                  INTEGER PRIMARY KEY AUTOINCREMENT,
  feed_id             INTEGER NOT NULL REFERENCES feeds(id) ON DELETE CASCADE,
  url                 TEXT NOT NULL UNIQUE,
  title               TEXT NOT NULL,
  author              TEXT,
  published_at        TEXT,
  raw_summary         TEXT,
  extracted_content   TEXT,
  llm_summary         TEXT,
  primary_category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
  language            TEXT,
  status              TEXT NOT NULL DEFAULT 'ok',
  fetched_at          TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_articles_feed ON articles(feed_id);
CREATE INDEX IF NOT EXISTS idx_articles_cat  ON articles(primary_category_id);
CREATE INDEX IF NOT EXISTS idx_articles_pub  ON articles(published_at DESC);

CREATE TABLE IF NOT EXISTS wiki_pages (
  id                         INTEGER PRIMARY KEY AUTOINCREMENT,
  category_id                INTEGER NOT NULL UNIQUE REFERENCES categories(id) ON DELETE CASCADE,
  content_markdown           TEXT NOT NULL DEFAULT '',
  last_rebuilt_at            TEXT,
  articles_count_at_rebuild  INTEGER NOT NULL DEFAULT 0,
  last_seen_at               TEXT,
  has_unread_updates         INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS job_logs (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  job_type       TEXT NOT NULL,
  target_ref     TEXT,
  status         TEXT NOT NULL,
  error_message  TEXT,
  attempt_count  INTEGER NOT NULL DEFAULT 1,
  started_at     TEXT NOT NULL,
  finished_at    TEXT
);
CREATE INDEX IF NOT EXISTS idx_joblogs_started ON job_logs(started_at DESC);

CREATE VIRTUAL TABLE IF NOT EXISTS articles_fts USING fts5(
  title, llm_summary, extracted_content,
  content='articles', content_rowid='id',
  tokenize='unicode61'
);

CREATE TRIGGER IF NOT EXISTS articles_ai AFTER INSERT ON articles BEGIN
  INSERT INTO articles_fts(rowid, title, llm_summary, extracted_content)
  VALUES (new.id, new.title, new.llm_summary, new.extracted_content);
END;
CREATE TRIGGER IF NOT EXISTS articles_ad AFTER DELETE ON articles BEGIN
  INSERT INTO articles_fts(articles_fts, rowid, title, llm_summary, extracted_content)
  VALUES ('delete', old.id, old.title, old.llm_summary, old.extracted_content);
END;
CREATE TRIGGER IF NOT EXISTS articles_au AFTER UPDATE ON articles BEGIN
  INSERT INTO articles_fts(articles_fts, rowid, title, llm_summary, extracted_content)
  VALUES ('delete', old.id, old.title, old.llm_summary, old.extracted_content);
  INSERT INTO articles_fts(rowid, title, llm_summary, extracted_content)
  VALUES (new.id, new.title, new.llm_summary, new.extracted_content);
END;
"""


def connect(path: str | Path) -> sqlite3.Connection:
    """연결을 연다. 모든 시각은 UTC(`datetime('now')`)로 저장한다.

    FastAPI는 동기 의존성(get_conn)과 동기 엔드포인트를 서로 다른 스레드풀 스레드에서 실행할 수 있다.
    연결 하나는 요청 하나가 순차로만 쓰므로 `check_same_thread=False`가 안전하다."""
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(path: str | Path) -> None:
    """DB 파일(과 상위 폴더)을 만들고 스키마를 적용한다. 여러 번 호출해도 안전하다."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = connect(path)
    try:
        conn.execute("PRAGMA journal_mode = WAL")  # 웹 조회와 수집 사이클의 동시 접근
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


def utcnow() -> str:
    """UTC ISO8601 (초 단위)."""
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def log_job(
    conn: sqlite3.Connection, job_type: str, target_ref: str | int | None, status: str,
    *, error: str | None = None, attempts: int = 1, started_at: str | None = None,
) -> None:
    """job_logs에 한 건 기록한다 (PRD §10)."""
    now = utcnow()
    conn.execute(
        """INSERT INTO job_logs(job_type, target_ref, status, error_message, attempt_count,
                                started_at, finished_at) VALUES (?,?,?,?,?,?,?)""",
        (job_type, None if target_ref is None else str(target_ref), status, error, attempts,
         started_at or now, now))
    conn.commit()
