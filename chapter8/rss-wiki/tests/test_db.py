import sqlite3

import pytest

from rss_wiki.db import connect, init_db

TABLES = {"feeds", "categories", "articles", "wiki_pages", "job_logs", "articles_fts"}


def test_init_creates_tables_and_parent_dir(settings):
    init_db(settings.db_path)
    conn = connect(settings.db_path)
    names = {r["name"] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert TABLES <= names


def test_init_is_idempotent(settings):
    init_db(settings.db_path)
    init_db(settings.db_path)


def add_feed_article(conn, url="https://a.com/1", title="인공지능 소식"):
    conn.execute("INSERT OR IGNORE INTO feeds(id, url) VALUES (1, 'http://f')")
    cur = conn.execute("INSERT INTO articles(feed_id, url, title) VALUES (1, ?, ?)", (url, title))
    conn.commit()
    return cur.lastrowid


def fts(conn, q):
    return [r["rowid"] for r in conn.execute("SELECT rowid FROM articles_fts WHERE articles_fts MATCH ?", (q,))]


def test_article_url_unique(conn):
    add_feed_article(conn)
    with pytest.raises(sqlite3.IntegrityError):
        add_feed_article(conn)


def test_fts_insert_update_delete_triggers(conn):
    aid = add_feed_article(conn, title="인공지능 소식")
    assert fts(conn, "인공지능") == [aid]
    conn.execute("UPDATE articles SET llm_summary='언어모델 요약' WHERE id=?", (aid,))
    assert fts(conn, "언어모델") == [aid]
    conn.execute("UPDATE articles SET title='반도체' WHERE id=?", (aid,))
    assert fts(conn, "인공지능") == [] and fts(conn, "반도체") == [aid]
    conn.execute("DELETE FROM articles WHERE id=?", (aid,))
    assert fts(conn, "반도체") == []


def test_deleting_feed_cascades_articles_and_fts(conn):
    aid = add_feed_article(conn)
    conn.execute("DELETE FROM feeds WHERE id=1")
    assert conn.execute("SELECT COUNT(*) c FROM articles").fetchone()["c"] == 0
    assert fts(conn, "인공지능") == []


def test_category_parent_set_null_and_wiki_cascade(conn):
    conn.execute("INSERT INTO categories(id, name) VALUES (1, 'P')")
    conn.execute("INSERT INTO categories(id, name, parent_id) VALUES (2, 'C', 1)")
    conn.execute("INSERT INTO wiki_pages(category_id) VALUES (2)")
    conn.execute("DELETE FROM categories WHERE id=1")
    assert conn.execute("SELECT parent_id FROM categories WHERE id=2").fetchone()["parent_id"] is None
    conn.execute("DELETE FROM categories WHERE id=2")
    assert conn.execute("SELECT COUNT(*) c FROM wiki_pages").fetchone()["c"] == 0


def test_connection_usable_from_another_thread(settings):
    """회귀: FastAPI 스레드풀이 연결 생성 스레드와 다른 스레드에서 쓰면 ProgrammingError가 나던 문제."""
    import threading

    init_db(settings.db_path)
    c = connect(settings.db_path)
    out = []
    t = threading.Thread(target=lambda: out.append(c.execute("SELECT 1").fetchone()[0]))
    t.start(); t.join()
    c.close()
    assert out == [1]
