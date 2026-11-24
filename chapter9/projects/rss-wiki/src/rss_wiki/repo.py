"""DB 접근 계층. SQL은 이 파일과 db.py에만 둔다. 쓰기 함수는 커밋한다.

없는 id에 대한 쓰기는 `LookupError` 하위 예외(`ArticleNotFoundError`/`FeedNotFoundError`)를 낸다. 삭제(`delete_feed`)만 멱등이다.
쓰기 함수는 `with conn:`을 쓰므로 성공 시 호출자의 미커밋 작업까지 커밋하고, 예외 시 함께 롤백한다. 열린 트랜잭션에서 호출하지 않는다.
"""

from __future__ import annotations

import sqlite3

from rss_wiki.db import STATUSES

RUN_STATUSES = ("running", "finished", "aborted")


class DuplicateFeedError(ValueError):
    """같은 URL의 피드가 이미 있다."""


class ArticleNotFoundError(LookupError):
    """없는 글 id."""


class FeedNotFoundError(LookupError):
    """없는 피드 id."""


class RunNotFoundError(LookupError):
    """없는 실행 이력 id."""


# ---------------------------------------------------------------- 피드


def add_feed(conn: sqlite3.Connection, url: str, title: str | None) -> int:
    """피드를 추가하고 id를 반환한다.

    Raises:
        DuplicateFeedError: 같은 URL이 이미 있다.
        sqlite3.IntegrityError: 그 밖의 제약 위반(예: url이 NULL)은 그대로 전파된다.
    """
    try:
        with conn:
            cur = conn.execute("INSERT INTO feeds(url, title) VALUES (?, ?)", (url, title))
    except sqlite3.IntegrityError as e:
        if "UNIQUE constraint failed: feeds.url" in str(e):
            raise DuplicateFeedError(f"이미 등록된 피드입니다: {url}") from e
        raise
    return cur.lastrowid


def get_feed(conn: sqlite3.Connection, feed_id: int) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM feeds WHERE id = ?", (feed_id,)).fetchone()


def list_feeds(conn: sqlite3.Connection, *, enabled_only: bool = False) -> list[sqlite3.Row]:
    sql = "SELECT * FROM feeds"
    if enabled_only:
        sql += " WHERE enabled = 1"
    return conn.execute(sql + " ORDER BY id").fetchall()


def set_feed_enabled(conn: sqlite3.Connection, feed_id: int, enabled: bool) -> None:
    """피드 활성 여부를 바꾼다.

    Raises:
        FeedNotFoundError: 없는 feed_id.
    """
    with conn:
        cur = conn.execute(
            "UPDATE feeds SET enabled = ? WHERE id = ?", (1 if enabled else 0, feed_id)
        )
        if cur.rowcount == 0:
            raise FeedNotFoundError(f"피드 id {feed_id}를 찾을 수 없습니다")


def delete_feed(conn: sqlite3.Connection, feed_id: int) -> None:
    """피드를 삭제한다. 없는 id는 조용히 넘어간다(멱등)."""
    with conn:
        conn.execute("DELETE FROM feeds WHERE id = ?", (feed_id,))


def _require_feed(cur: sqlite3.Cursor, feed_id: int) -> None:
    if cur.rowcount == 0:
        raise FeedNotFoundError(f"피드 id {feed_id}를 찾을 수 없습니다")


def record_feed_success(
    conn: sqlite3.Connection, feed_id: int, *, etag: str | None, last_modified: str | None
) -> None:
    """수집 성공(304 포함)을 기록한다. etag·last_modified를 주어진 값으로 저장하고 실패 상태를 지운다.

    Raises:
        FeedNotFoundError: 없는 feed_id.
    """
    with conn:
        cur = conn.execute(
            "UPDATE feeds SET etag = ?, last_modified = ?, last_error = NULL, "
            "consecutive_failures = 0 WHERE id = ?",
            (etag, last_modified, feed_id),
        )
        _require_feed(cur, feed_id)


def record_feed_failure(conn: sqlite3.Connection, feed_id: int, error: str) -> int:
    """수집 실패를 기록하고 올린 consecutive_failures를 반환한다. etag·last_modified는 유지한다.

    Raises:
        ValueError: error가 str이 아니거나 공백뿐이다(DB 접근 전).
        FeedNotFoundError: 없는 feed_id.
    """
    if not isinstance(error, str) or not error.strip():
        raise ValueError("error는 비어 있지 않은 문자열이어야 합니다")
    with conn:
        cur = conn.execute(
            "UPDATE feeds SET last_error = ?, consecutive_failures = consecutive_failures + 1 "
            "WHERE id = ?",
            (error, feed_id),
        )
        _require_feed(cur, feed_id)
        return conn.execute(
            "SELECT consecutive_failures FROM feeds WHERE id = ?", (feed_id,)
        ).fetchone()[0]


def mark_initial_fetch_done(conn: sqlite3.Connection, feed_id: int) -> None:
    """첫 수집 완료를 표시한다(멱등).

    Raises:
        FeedNotFoundError: 없는 feed_id.
    """
    with conn:
        cur = conn.execute("UPDATE feeds SET initial_fetch_done = 1 WHERE id = ?", (feed_id,))
        _require_feed(cur, feed_id)


# ---------------------------------------------------------------- 글


def insert_article_if_new(
    conn: sqlite3.Connection,
    feed_id: int,
    entry_key: str,
    *,
    title: str | None,
    url: str | None,
    published: str | None,
    status: str = "new",
) -> int | None:
    """새로 넣으면 id, 이미 있으면 None. CHECK 위반은 IntegrityError로 드러난다."""
    with conn:
        cur = conn.execute(
            "INSERT INTO articles(feed_id, entry_key, title, url, published, status, fetched_at) "
            "VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP) "
            "ON CONFLICT(feed_id, entry_key) DO NOTHING",
            (feed_id, entry_key, title, url, published, status),
        )
    return cur.lastrowid if cur.rowcount == 1 else None


def get_article(conn: sqlite3.Connection, article_id: int) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM articles WHERE id = ?", (article_id,)).fetchone()


# ---------------------------------------------------------------- 상태 전이


def _require_article(cur: sqlite3.Cursor, article_id: int) -> None:
    if cur.rowcount == 0:
        raise ArticleNotFoundError(f"글 id {article_id}를 찾을 수 없습니다")


def set_status(conn: sqlite3.Connection, article_id: int, status: str) -> None:
    """글 상태를 바꾼다.

    Raises:
        ValueError: db.STATUSES에 없는 status.
        ArticleNotFoundError: 없는 article_id.
    """
    if status not in STATUSES:
        raise ValueError(f"알 수 없는 status: {status!r}")
    with conn:
        cur = conn.execute(
            "UPDATE articles SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (status, article_id),
        )
        _require_article(cur, article_id)


def mark_failed(
    conn: sqlite3.Connection, article_id: int, error: str, *, max_attempts: int = 3
) -> str:
    """attempts를 올리고 last_error를 기록한다. 한도에 닿으면 failed_permanent, 아니면 failed.

    바뀐 상태를 반환한다.

    Raises:
        ValueError: max_attempts < 1.
        ArticleNotFoundError: 없는 article_id.
    """
    if max_attempts < 1:
        raise ValueError(f"max_attempts는 1 이상이어야 합니다: {max_attempts}")
    with conn:
        cur = conn.execute(
            "UPDATE articles SET attempts = attempts + 1, last_error = ?, "
            "status = CASE WHEN attempts + 1 >= ? THEN 'failed_permanent' ELSE 'failed' END, "
            "updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (error, max_attempts, article_id),
        )
        _require_article(cur, article_id)
        row = conn.execute("SELECT status FROM articles WHERE id = ?", (article_id,)).fetchone()
    return row["status"]


def mark_done(
    conn: sqlite3.Connection, article_id: int, *, summary: str, source: str, wiki_path: str
) -> None:
    """요약·출처·위키 경로를 저장하고 done으로 바꾼다.

    위키 파일 쓰기가 성공한 뒤에만 호출해야 한다(호출자 책임).

    Raises:
        ArticleNotFoundError: 없는 article_id.
    """
    with conn:
        cur = conn.execute(
            "UPDATE articles SET summary = ?, source = ?, wiki_path = ?, status = 'done', "
            "last_error = NULL, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (summary, source, wiki_path, article_id),
        )
        _require_article(cur, article_id)


# ---------------------------------------------------------------- 태그


def set_article_tags(conn: sqlite3.Connection, article_id: int, names: list[str]) -> None:
    """글의 태그를 names로 교체한다. 이름은 받은 그대로 저장한다(정규화는 호출자 책임).

    Raises:
        TypeError: names가 str(글자 단위 태그로 쪼개지는 것 방지, DB 접근 전).
        ArticleNotFoundError: 없는 article_id(빈 목록이어도, 아무것도 바꾸지 않는다).
    """
    if isinstance(names, str):
        raise TypeError("names는 문자열이 아니라 문자열의 목록이어야 합니다")
    with conn:
        if conn.execute("SELECT 1 FROM articles WHERE id = ?", (article_id,)).fetchone() is None:
            raise ArticleNotFoundError(f"글 id {article_id}를 찾을 수 없습니다")
        conn.execute("DELETE FROM article_tags WHERE article_id = ?", (article_id,))
        for name in dict.fromkeys(names):
            conn.execute("INSERT INTO tags(name) VALUES (?) ON CONFLICT(name) DO NOTHING", (name,))
            conn.execute(
                "INSERT INTO article_tags(article_id, tag_id) "
                "SELECT ?, id FROM tags WHERE name = ?",
                (article_id, name),
            )


def get_article_tags(conn: sqlite3.Connection, article_id: int) -> list[str]:
    rows = conn.execute(
        "SELECT t.name FROM tags t JOIN article_tags x ON x.tag_id = t.id "
        "WHERE x.article_id = ? ORDER BY t.name",
        (article_id,),
    ).fetchall()
    return [r["name"] for r in rows]


def list_tag_names(conn: sqlite3.Connection) -> list[str]:
    """글이 하나 이상 연결된 태그 이름을 오름차순으로 반환한다."""
    rows = conn.execute(
        "SELECT name FROM tags WHERE id IN (SELECT tag_id FROM article_tags) ORDER BY name"
    ).fetchall()
    return [r["name"] for r in rows]


# ---------------------------------------------------------------- 검색


def build_fts_query(text: str) -> str | None:
    """공백 단위 단어를 `"단어"*` 접두사 질의로 만들어 AND로 묶는다. 단어가 없으면 None."""
    terms = []
    for word in text.split():
        if any(ch.isalnum() for ch in word):
            terms.append('"' + word.replace('"', '""') + '"*')
    return " ".join(terms) or None


def search_articles(conn: sqlite3.Connection, text: str, *, limit: int = 50) -> list[sqlite3.Row]:
    """done 글을 제목·요약 접두사 검색으로 찾아 bm25 순으로 반환한다.

    Raises:
        ValueError: limit < 1(SQLite의 음수 LIMIT은 무제한이므로 DB 접근 전에 거부).
    """
    if limit < 1:
        raise ValueError(f"limit은 1 이상이어야 합니다: {limit}")
    query = build_fts_query(text)
    if query is None:
        return []
    return conn.execute(
        "SELECT a.id, a.title, a.summary, a.feed_id FROM articles_fts "
        "JOIN articles a ON a.id = articles_fts.rowid "
        "WHERE articles_fts MATCH ? AND a.status = 'done' "
        "ORDER BY bm25(articles_fts) LIMIT ?",
        (query, limit),
    ).fetchall()


# ---------------------------------------------------------------- 처리 대상


def list_articles_to_process(
    conn: sqlite3.Connection, *, limit: int, max_attempts: int = 3
) -> list[sqlite3.Row]:
    """처리할 글(new, 또는 attempts < max_attempts인 failed)을 id 오름차순으로 최대 limit개 반환한다.

    Raises:
        ValueError: limit < 1 또는 max_attempts < 1(DB 접근 전).
    """
    if limit < 1:
        raise ValueError(f"limit은 1 이상이어야 합니다: {limit}")
    if max_attempts < 1:
        raise ValueError(f"max_attempts는 1 이상이어야 합니다: {max_attempts}")
    return conn.execute(
        "SELECT * FROM articles WHERE status = 'new' "
        "OR (status = 'failed' AND attempts < ?) ORDER BY id LIMIT ?",
        (max_attempts, limit),
    ).fetchall()


def count_articles_by_status(conn: sqlite3.Connection) -> dict[str, int]:
    """db.STATUSES의 모든 키를 담은 상태별 글 수. 없는 상태는 0."""
    counts = dict.fromkeys(STATUSES, 0)
    for r in conn.execute("SELECT status, COUNT(*) AS n FROM articles GROUP BY status"):
        counts[r["status"]] = r["n"]
    return counts


def list_failed_articles(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """failed·failed_permanent 글을 updated_at, id 내림차순으로 반환한다."""
    return conn.execute(
        "SELECT id, feed_id, title, status, attempts, last_error, updated_at FROM articles "
        "WHERE status IN ('failed', 'failed_permanent') ORDER BY updated_at DESC, id DESC"
    ).fetchall()


# ---------------------------------------------------------------- 실행 이력


def start_run(conn: sqlite3.Connection) -> int:
    """running 상태의 실행 이력을 만들고 id를 반환한다."""
    with conn:
        cur = conn.execute(
            "INSERT INTO runs(started_at, status) VALUES (CURRENT_TIMESTAMP, 'running')"
        )
    return cur.lastrowid


def finish_run(
    conn: sqlite3.Connection,
    run_id: int,
    *,
    processed: int,
    failed: int,
    status: str = "finished",
) -> None:
    """실행 이력을 마감한다.

    Raises:
        ValueError: status가 RUN_STATUSES에 없거나 'running', 또는 processed·failed가 음수(DB 접근 전).
        RunNotFoundError: 없는 run_id(롤백되어 부작용 없음).
    """
    if status not in RUN_STATUSES or status == "running":
        raise ValueError(f"finish_run에 쓸 수 없는 status: {status!r}")
    if processed < 0 or failed < 0:
        raise ValueError(f"processed·failed는 0 이상이어야 합니다: {processed}, {failed}")
    with conn:
        cur = conn.execute(
            "UPDATE runs SET finished_at = CURRENT_TIMESTAMP, status = ?, processed = ?, "
            "failed = ? WHERE id = ?",
            (status, processed, failed, run_id),
        )
        if cur.rowcount == 0:
            raise RunNotFoundError(f"실행 id {run_id}를 찾을 수 없습니다")


def get_latest_run(conn: sqlite3.Connection) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM runs ORDER BY id DESC LIMIT 1").fetchone()


def abort_running_runs(conn: sqlite3.Connection) -> int:
    """남은 running 이력을 aborted로 바꾸고 건수를 반환한다(서버 시작 시 복구용)."""
    with conn:
        cur = conn.execute(
            "UPDATE runs SET status = 'aborted', finished_at = CURRENT_TIMESTAMP "
            "WHERE status = 'running'"
        )
    return cur.rowcount
