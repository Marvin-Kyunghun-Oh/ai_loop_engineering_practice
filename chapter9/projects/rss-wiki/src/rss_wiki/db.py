"""SQLite 연결과 스키마 관리. 스키마 버전은 PRAGMA user_version으로 관리한다."""

from __future__ import annotations

import sqlite3
from pathlib import Path

STATUSES = (
    "new",
    "fetching_content",
    "summarizing",
    "done",
    "failed",
    "failed_permanent",
    "skipped_backfill",
)

_STATUS_SQL = ", ".join(f"'{s}'" for s in STATUSES)

# 순차 마이그레이션: MIGRATIONS[i]는 user_version i -> i+1 로 올리는 스크립트.
_V1 = f"""
CREATE TABLE feeds (
    id INTEGER PRIMARY KEY,
    url TEXT NOT NULL UNIQUE,
    title TEXT,
    enabled INTEGER NOT NULL DEFAULT 1,
    etag TEXT,
    last_modified TEXT,
    last_error TEXT,
    consecutive_failures INTEGER NOT NULL DEFAULT 0,
    initial_fetch_done INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE articles (
    id INTEGER PRIMARY KEY,
    feed_id INTEGER NOT NULL REFERENCES feeds(id) ON DELETE CASCADE,
    entry_key TEXT NOT NULL,
    title TEXT,
    url TEXT,
    published TEXT,
    fetched_at TEXT,
    source TEXT CHECK (source IN ('extracted', 'feed')),
    status TEXT NOT NULL DEFAULT 'new' CHECK (status IN ({_STATUS_SQL})),
    attempts INTEGER NOT NULL DEFAULT 0,
    last_error TEXT,
    summary TEXT,
    wiki_path TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (feed_id, entry_key)
);
CREATE INDEX idx_articles_status ON articles(status);
CREATE INDEX idx_articles_feed ON articles(feed_id);

CREATE TABLE tags (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE article_tags (
    article_id INTEGER NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
    tag_id INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY (article_id, tag_id)
);

CREATE TABLE runs (
    id INTEGER PRIMARY KEY,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    status TEXT,
    processed INTEGER NOT NULL DEFAULT 0,
    failed INTEGER NOT NULL DEFAULT 0
);

CREATE VIRTUAL TABLE articles_fts USING fts5(title, summary);

CREATE TRIGGER articles_ai AFTER INSERT ON articles BEGIN
    INSERT INTO articles_fts(rowid, title, summary)
    VALUES (new.id, COALESCE(new.title, ''), COALESCE(new.summary, ''));
END;

CREATE TRIGGER articles_ad AFTER DELETE ON articles BEGIN
    DELETE FROM articles_fts WHERE rowid = old.id;
END;

CREATE TRIGGER articles_au AFTER UPDATE OF title, summary ON articles BEGIN
    DELETE FROM articles_fts WHERE rowid = old.id;
    INSERT INTO articles_fts(rowid, title, summary)
    VALUES (new.id, COALESCE(new.title, ''), COALESCE(new.summary, ''));
END;
"""

MIGRATIONS = (_V1,)


def connect(db_path: Path) -> sqlite3.Connection:
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


def migrate(conn: sqlite3.Connection) -> None:
    """현재 user_version부터 최신까지 순차 적용한다. 반복 호출해도 안전하다.

    스크립트가 실패하면 롤백하고 원래 예외를 다시 던진다.
    DB 버전이 지원 버전보다 높으면 RuntimeError.
    열린 트랜잭션 없이 호출해야 한다(열려 있으면 RuntimeError).
    """
    if conn.in_transaction:
        raise RuntimeError(
            "열린 트랜잭션이 있어 migrate를 적용할 수 없습니다. "
            "커밋 또는 롤백 후 호출하세요"
        )
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    if version > len(MIGRATIONS):
        raise RuntimeError(
            f"DB 스키마 버전({version})이 지원 버전({len(MIGRATIONS)})보다 높습니다"
        )
    for target, script in enumerate(MIGRATIONS[version:], start=version + 1):
        # executescript는 암묵적으로 커밋하므로 한 스크립트 안에서 트랜잭션을 직접 둔다.
        try:
            conn.executescript(f"BEGIN;\n{script}\nPRAGMA user_version = {target};\nCOMMIT;")
        except BaseException:
            if conn.in_transaction:
                conn.rollback()
            raise


def reset_interrupted(conn: sqlite3.Connection) -> int:
    """중단된 처리 상태(fetching_content/summarizing)를 new로 되돌리고 건수를 반환한다."""
    with conn:
        cur = conn.execute(
            "UPDATE articles SET status = 'new', updated_at = CURRENT_TIMESTAMP "
            "WHERE status IN ('fetching_content', 'summarizing')"
        )
    return cur.rowcount
