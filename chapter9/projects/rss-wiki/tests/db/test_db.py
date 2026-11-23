import sqlite3

import pytest

from rss_wiki.db import MIGRATIONS, connect, migrate, reset_interrupted


@pytest.fixture
def conn(tmp_path):
    c = connect(tmp_path / "t.db")
    migrate(c)
    yield c
    c.close()


def add_feed(conn, url="http://a/feed"):
    cur = conn.execute("INSERT INTO feeds(url) VALUES (?)", (url,))
    return cur.lastrowid


def add_article(conn, feed_id, key="k1", status="new", **kw):
    cur = conn.execute(
        "INSERT INTO articles(feed_id, entry_key, status, title, summary) VALUES (?,?,?,?,?)",
        (feed_id, key, status, kw.get("title", "t"), kw.get("summary")),
    )
    return cur.lastrowid


def test_tables_created(conn):
    names = {r["name"] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"feeds", "articles", "tags", "article_tags", "runs", "articles_fts"} <= names


def test_migrate_idempotent(conn):
    migrate(conn)
    migrate(conn)
    assert conn.execute("PRAGMA user_version").fetchone()[0] == 1


def test_connect_creates_parent_dirs(tmp_path):
    p = tmp_path / "a" / "b" / "x.db"
    c = connect(p)
    migrate(c)
    c.close()
    assert p.exists()


def test_connect_pragmas(conn):
    assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    assert conn.row_factory is sqlite3.Row


def test_duplicate_entry_key(conn):
    f = add_feed(conn)
    add_article(conn, f, "k")
    with pytest.raises(sqlite3.IntegrityError):
        add_article(conn, f, "k")
    g = add_feed(conn, "http://b/feed")
    add_article(conn, g, "k")  # 다른 피드는 허용


def test_invalid_status(conn):
    f = add_feed(conn)
    with pytest.raises(sqlite3.IntegrityError):
        add_article(conn, f, status="bogus")


@pytest.mark.parametrize(
    "status",
    ["new", "fetching_content", "summarizing", "done", "failed", "failed_permanent", "skipped_backfill"],
)
def test_valid_statuses(conn, status):
    add_article(conn, add_feed(conn), status=status)


def test_fts_insert_update_delete(conn):
    f = add_feed(conn)
    a = add_article(conn, f, summary="quantum computing advances")
    q = "SELECT rowid FROM articles_fts WHERE articles_fts MATCH ?"
    assert [r[0] for r in conn.execute(q, ("quantum",))] == [a]
    conn.execute("UPDATE articles SET summary = 'gardening tips' WHERE id = ?", (a,))
    assert list(conn.execute(q, ("quantum",))) == []
    assert [r[0] for r in conn.execute(q, ("gardening",))] == [a]
    conn.execute("DELETE FROM articles WHERE id = ?", (a,))
    assert list(conn.execute(q, ("gardening",))) == []


def test_cascade_delete_feed(conn):
    f = add_feed(conn)
    a = add_article(conn, f)
    conn.execute("INSERT INTO tags(name) VALUES ('x')")
    conn.execute("INSERT INTO article_tags(article_id, tag_id) VALUES (?, 1)", (a,))
    conn.execute("DELETE FROM feeds WHERE id = ?", (f,))
    assert conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM article_tags").fetchone()[0] == 0


def test_migrate_failure_rolls_back(tmp_path, monkeypatch):
    from rss_wiki import db

    c = connect(tmp_path / "f.db")
    migrate(c)
    monkeypatch.setattr(
        db, "MIGRATIONS", (db.MIGRATIONS[0], "CREATE TABLE half (a); THIS IS NOT SQL;")
    )
    with pytest.raises(sqlite3.Error):
        db.migrate(c)
    assert c.execute("PRAGMA user_version").fetchone()[0] == 1
    assert c.in_transaction is False
    assert c.execute("SELECT name FROM sqlite_master WHERE name = 'half'").fetchone() is None
    c.close()


def test_future_version_rejected(conn):
    conn.execute("PRAGMA user_version = 99")
    with pytest.raises(RuntimeError, match="99") as ei:
        migrate(conn)
    assert str(len(MIGRATIONS)) in str(ei.value)


def test_migrate_rejects_open_transaction(tmp_path):
    c = connect(tmp_path / "tx.db")
    migrate(c)
    c.execute("INSERT INTO feeds(url) VALUES ('http://x/f')")
    assert c.in_transaction
    with pytest.raises(RuntimeError, match="열린 트랜잭션"):
        migrate(c)
    c.rollback()
    assert c.execute("SELECT COUNT(*) FROM feeds").fetchone()[0] == 0
    c.close()


def test_wal_and_busy_timeout(conn):
    assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    assert conn.execute("PRAGMA busy_timeout").fetchone()[0] == 5000


def test_cascade_delete_clears_fts(conn):
    f = add_feed(conn)
    add_article(conn, f, summary="alpha beta")
    conn.execute("DELETE FROM feeds WHERE id = ?", (f,))
    assert conn.execute("SELECT COUNT(*) FROM articles_fts").fetchone()[0] == 0


def test_invalid_source(conn):
    f = add_feed(conn)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO articles(feed_id, entry_key, source) VALUES (?, 'k', 'bogus')", (f,)
        )


def test_reset_interrupted_updates_updated_at(conn):
    f = add_feed(conn)
    a = add_article(conn, f, "a", status="summarizing")
    b = add_article(conn, f, "b", status="done")
    old = "2000-01-01 00:00:00"
    conn.execute("UPDATE articles SET updated_at = ?", (old,))
    assert reset_interrupted(conn) == 1
    ts = {r["id"]: r["updated_at"] for r in conn.execute("SELECT id, updated_at FROM articles")}
    assert ts[a] != old
    assert ts[b] == old


def test_fts_title_search(conn):
    f = add_feed(conn)
    a = add_article(conn, f, title="rustacean news")
    rows = conn.execute("SELECT rowid FROM articles_fts WHERE articles_fts MATCH 'rustacean'")
    assert [r[0] for r in rows] == [a]


def test_no_body_or_read_columns(conn):
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(articles)")}
    assert not cols & {"content", "body", "is_read", "read"}


def test_reset_interrupted(conn):
    f = add_feed(conn)
    ids = {s: add_article(conn, f, key=s, status=s) for s in
           ["fetching_content", "summarizing", "done", "failed", "new"]}
    assert reset_interrupted(conn) == 2
    st = {r["id"]: r["status"] for r in conn.execute("SELECT id, status FROM articles")}
    assert st[ids["fetching_content"]] == "new"
    assert st[ids["summarizing"]] == "new"
    assert st[ids["done"]] == "done"
    assert st[ids["failed"]] == "failed"
    assert reset_interrupted(conn) == 0
