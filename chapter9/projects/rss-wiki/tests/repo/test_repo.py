import sqlite3

import pytest

from rss_wiki import repo
from rss_wiki.db import connect, migrate

OLD = "2000-01-01 00:00:00"


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "t.db"


@pytest.fixture
def conn(db_path):
    c = connect(db_path)
    migrate(c)
    yield c
    c.close()


@pytest.fixture
def feed_id(conn):
    return repo.add_feed(conn, "http://a/feed", "A")


def new_article(conn, feed_id, key="k1", **kw):
    return repo.insert_article_if_new(
        conn, feed_id, key, title=kw.get("title", "제목"), url="http://a/1", published=None
    )


def age(conn, aid):
    conn.execute("UPDATE articles SET updated_at = ? WHERE id = ?", (OLD, aid))
    conn.commit()


def updated_at(conn, aid):
    return repo.get_article(conn, aid)["updated_at"]


def test_feed_add_get_list(conn):
    a = repo.add_feed(conn, "http://a", "A")
    b = repo.add_feed(conn, "http://b", None)
    assert repo.get_feed(conn, a)["url"] == "http://a"
    assert [r["id"] for r in repo.list_feeds(conn)] == [a, b]


def test_duplicate_feed(conn):
    repo.add_feed(conn, "http://a", "A")
    with pytest.raises(repo.DuplicateFeedError):
        repo.add_feed(conn, "http://a", "A2")
    assert issubclass(repo.DuplicateFeedError, ValueError)
    assert len(repo.list_feeds(conn)) == 1


def test_enabled_only(conn):
    a = repo.add_feed(conn, "http://a", "A")
    b = repo.add_feed(conn, "http://b", "B")
    repo.set_feed_enabled(conn, a, False)
    assert [r["id"] for r in repo.list_feeds(conn, enabled_only=True)] == [b]
    repo.set_feed_enabled(conn, a, True)
    assert len(repo.list_feeds(conn, enabled_only=True)) == 2


def test_delete_feed(conn, feed_id):
    repo.delete_feed(conn, feed_id)
    assert repo.get_feed(conn, feed_id) is None


def test_insert_article_if_new(conn, feed_id):
    first = new_article(conn, feed_id, title="원래")
    assert isinstance(first, int)
    assert new_article(conn, feed_id, title="바뀜") is None
    assert conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0] == 1
    row = repo.get_article(conn, first)
    assert row["title"] == "원래"
    assert row["status"] == "new"
    assert row["fetched_at"]


def test_insert_bad_status_raises(conn, feed_id):
    with pytest.raises(sqlite3.IntegrityError):
        repo.insert_article_if_new(
            conn, feed_id, "k", title="t", url=None, published=None, status="bogus"
        )


def test_set_status_invalid(conn, feed_id):
    aid = new_article(conn, feed_id)
    with pytest.raises(ValueError):
        repo.set_status(conn, aid, "bogus")
    repo.set_status(conn, aid, "summarizing")
    assert repo.get_article(conn, aid)["status"] == "summarizing"


def test_mark_failed_progression(conn, feed_id):
    aid = new_article(conn, feed_id)
    assert repo.mark_failed(conn, aid, "e1") == "failed"
    assert repo.mark_failed(conn, aid, "e2") == "failed"
    assert repo.mark_failed(conn, aid, "e3") == "failed_permanent"
    row = repo.get_article(conn, aid)
    assert row["attempts"] == 3
    assert row["last_error"] == "e3"
    assert row["status"] == "failed_permanent"


def test_mark_failed_custom_max(conn, feed_id):
    aid = new_article(conn, feed_id)
    assert repo.mark_failed(conn, aid, "e", max_attempts=1) == "failed_permanent"


def test_mark_done(conn, feed_id):
    aid = new_article(conn, feed_id)
    repo.mark_failed(conn, aid, "boom")
    repo.mark_done(conn, aid, summary="양자 컴퓨팅 요약", source="extracted", wiki_path="a/b.md")
    row = repo.get_article(conn, aid)
    assert row["status"] == "done"
    assert row["last_error"] is None
    assert row["source"] == "extracted"
    assert row["wiki_path"] == "a/b.md"
    hits = conn.execute("SELECT rowid FROM articles_fts WHERE articles_fts MATCH '양자'").fetchall()
    assert [h[0] for h in hits] == [aid]


@pytest.mark.parametrize(
    "call",
    [
        lambda c, a: repo.set_status(c, a, "done"),
        lambda c, a: repo.mark_failed(c, a, "e"),
        lambda c, a: repo.mark_done(c, a, summary="s", source="feed", wiki_path="p"),
    ],
    ids=["set_status", "mark_failed", "mark_done"],
)
def test_transitions_update_updated_at(conn, feed_id, call):
    aid = new_article(conn, feed_id)
    age(conn, aid)
    assert updated_at(conn, aid) == OLD
    call(conn, aid)
    assert updated_at(conn, aid) != OLD


def test_add_feed_null_url_is_not_duplicate(conn):
    with pytest.raises(sqlite3.IntegrityError) as ei:
        repo.add_feed(conn, None, "t")
    assert not isinstance(ei.value, repo.DuplicateFeedError)
    assert conn.execute("SELECT COUNT(*) FROM feeds").fetchone()[0] == 0


@pytest.mark.parametrize(
    "call",
    [
        lambda c: repo.set_status(c, 999, "done"),
        lambda c: repo.mark_failed(c, 999, "e"),
        lambda c: repo.mark_done(c, 999, summary="s", source="feed", wiki_path="p"),
    ],
    ids=["set_status", "mark_failed", "mark_done"],
)
def test_missing_article_raises(conn, call):
    with pytest.raises(repo.ArticleNotFoundError):
        call(conn)
    assert conn.in_transaction is False
    assert issubclass(repo.ArticleNotFoundError, LookupError)
    assert issubclass(repo.FeedNotFoundError, LookupError)


def test_missing_feed(conn):
    with pytest.raises(repo.FeedNotFoundError):
        repo.set_feed_enabled(conn, 999, True)
    repo.delete_feed(conn, 999)


def test_mark_failed_bad_max_attempts(conn, feed_id):
    aid = new_article(conn, feed_id)
    with pytest.raises(ValueError):
        repo.mark_failed(conn, aid, "e", max_attempts=0)
    row = repo.get_article(conn, aid)
    assert row["status"] == "new"
    assert row["attempts"] == 0


def _prep_article(c):
    fid = repo.add_feed(c, "http://a", "A")
    return fid, new_article(c, fid)


def _check_add_feed(c, other):
    fid = repo.add_feed(c, "http://z", "Z")
    return lambda: repo.get_feed(other, fid) is not None


def _check_set_feed_enabled(c, other):
    fid = repo.add_feed(c, "http://z", "Z")
    repo.set_feed_enabled(c, fid, False)
    return lambda: repo.get_feed(other, fid)["enabled"] == 0


def _check_delete_feed(c, other):
    fid = repo.add_feed(c, "http://z", "Z")
    repo.delete_feed(c, fid)
    return lambda: repo.get_feed(other, fid) is None


def _check_insert(c, other):
    fid = repo.add_feed(c, "http://z", "Z")
    aid = new_article(c, fid)
    return lambda: repo.get_article(other, aid) is not None


def _check_set_status(c, other):
    _, aid = _prep_article(c)
    repo.set_status(c, aid, "summarizing")
    return lambda: repo.get_article(other, aid)["status"] == "summarizing"


def _check_mark_failed(c, other):
    _, aid = _prep_article(c)
    repo.mark_failed(c, aid, "e")
    return lambda: repo.get_article(other, aid)["status"] == "failed"


def _check_set_article_tags(c, other):
    _, aid = _prep_article(c)
    repo.set_article_tags(c, aid, ["x"])
    return lambda: repo.get_article_tags(other, aid) == ["x"]


def _check_mark_done(c, other):
    _, aid = _prep_article(c)
    repo.mark_done(c, aid, summary="요약", source="feed", wiki_path="p")
    return lambda: repo.get_article(other, aid)["status"] == "done"


def _check_start_run(c, other):
    rid = repo.start_run(c)
    return lambda: repo.get_latest_run(other)["id"] == rid


def _check_finish_run(c, other):
    rid = repo.start_run(c)
    repo.finish_run(c, rid, processed=1, failed=0)
    return lambda: repo.get_latest_run(other)["status"] == "finished"


def _check_abort_runs(c, other):
    repo.start_run(c)
    repo.abort_running_runs(c)
    return lambda: repo.get_latest_run(other)["status"] == "aborted"


@pytest.mark.parametrize(
    "check",
    [
        _check_add_feed,
        _check_set_feed_enabled,
        _check_delete_feed,
        _check_insert,
        _check_set_status,
        _check_mark_failed,
        _check_mark_done,
        _check_set_article_tags,
        _check_start_run,
        _check_finish_run,
        _check_abort_runs,
    ],
    ids=lambda f: f.__name__.removeprefix("_check_"),
)
def test_writes_are_committed(conn, db_path, check):
    other = connect(db_path)
    try:
        verify = check(conn, other)
        assert verify()
    finally:
        other.close()


# ---------------------------------------------------------------- 태그·검색


def done_article(conn, feed_id, key, title, summary):
    aid = new_article(conn, feed_id, key, title=title)
    repo.mark_done(conn, aid, summary=summary, source="feed", wiki_path=f"{key}.md")
    return aid


def test_tags_set_replace_dedupe_clear(conn, feed_id):
    aid = new_article(conn, feed_id)
    repo.set_article_tags(conn, aid, ["b", "a"])
    assert repo.get_article_tags(conn, aid) == ["a", "b"]
    repo.set_article_tags(conn, aid, ["c"])
    assert repo.get_article_tags(conn, aid) == ["c"]
    repo.set_article_tags(conn, aid, ["a", "a"])
    assert repo.get_article_tags(conn, aid) == ["a"]
    repo.set_article_tags(conn, aid, [])
    assert repo.get_article_tags(conn, aid) == []


def test_shared_tag_single_row(conn, feed_id):
    a = new_article(conn, feed_id, "k1")
    b = new_article(conn, feed_id, "k2")
    repo.set_article_tags(conn, a, ["x"])
    repo.set_article_tags(conn, b, ["x"])
    assert conn.execute("SELECT COUNT(*) FROM tags").fetchone()[0] == 1


def test_list_tag_names_excludes_orphans(conn, feed_id):
    a = new_article(conn, feed_id)
    repo.set_article_tags(conn, a, ["old", "keep"])
    repo.set_article_tags(conn, a, ["keep"])
    assert repo.list_tag_names(conn) == ["keep"]


@pytest.mark.parametrize("names", [[], ["a"]])
def test_set_tags_missing_article(conn, names):
    with pytest.raises(repo.ArticleNotFoundError):
        repo.set_article_tags(conn, 999, names)
    assert conn.execute("SELECT COUNT(*) FROM tags").fetchone()[0] == 0


def test_build_fts_query():
    assert repo.build_fts_query("양자 컴퓨팅") == '"양자"* "컴퓨팅"*'
    assert repo.build_fts_query("  ") is None
    assert repo.build_fts_query("") is None


def test_search_korean_prefix_and_title(conn, feed_id):
    aid = done_article(conn, feed_id, "k1", "다른 제목", "양자 컴퓨팅의 미래")
    other = done_article(conn, feed_id, "k2", "고양이 사진", "귀여운 것")
    assert [r["id"] for r in repo.search_articles(conn, "컴퓨팅")] == [aid]
    assert [r["id"] for r in repo.search_articles(conn, "양자")] == [aid]
    assert [r["id"] for r in repo.search_articles(conn, "고양이")] == [other]
    row = repo.search_articles(conn, "양자")[0]
    assert {"id", "title", "summary", "feed_id"} <= set(row.keys())


def test_search_and_semantics(conn, feed_id):
    both = done_article(conn, feed_id, "k1", "t1", "양자 컴퓨팅")
    done_article(conn, feed_id, "k2", "t2", "양자 역학")
    assert [r["id"] for r in repo.search_articles(conn, "양자 컴퓨팅")] == [both]


@pytest.mark.parametrize("q", ['"', "*", "-", "OR", "a OR", "(", "NEAR("])
def test_search_special_input(conn, feed_id, q):
    done_article(conn, feed_id, "k1", "t", "요약")
    assert isinstance(repo.search_articles(conn, q), list)


def test_search_only_done_and_limit(conn, feed_id):
    new_article(conn, feed_id, "kn", title="양자 새글")
    for i in range(3):
        done_article(conn, feed_id, f"d{i}", f"양자 {i}", "요약")
    assert len(repo.search_articles(conn, "양자")) == 3
    assert len(repo.search_articles(conn, "양자", limit=2)) == 2


def test_docstrings_document_not_found():
    for f in (repo.set_status, repo.set_feed_enabled, repo.mark_failed, repo.mark_done,
              repo.set_article_tags):
        assert "NotFoundError" in f.__doc__


# ---------------------------------------------------------------- T3s 보강


def test_build_fts_query_quote_escape():
    assert repo.build_fts_query('a"b') == '"a""b"*'


@pytest.mark.parametrize("q", ['a"b', 'say"hi'])
def test_search_quote_input(conn, feed_id, q):
    done_article(conn, feed_id, "k1", "t", "요약")
    assert isinstance(repo.search_articles(conn, q), list)


def test_build_fts_query_alnum_filter():
    assert repo.build_fts_query('"') is None
    assert repo.build_fts_query("* - (") is None
    assert repo.build_fts_query("양자 *") == '"양자"*'


def test_search_bm25_order(conn, feed_id):
    a = done_article(conn, feed_id, "a", "tA", "양자 하나 둘 셋 양자 넷 다섯 여섯 일곱 여덟")
    b = done_article(conn, feed_id, "b", "tB", "양자 양자 양자 양자 다섯 여섯 일곱 여덟 아홉")
    c = done_article(conn, feed_id, "c", "tC", "양자 하나 둘 셋 넷 다섯 여섯 일곱 여덟 아홉")
    assert [r["id"] for r in repo.search_articles(conn, "양자")] == [b, a, c]


def test_search_literal_or(conn, feed_id):
    aid = done_article(conn, feed_id, "k1", "OR 게이트", "요약")
    assert aid in [r["id"] for r in repo.search_articles(conn, "OR")]


@pytest.mark.parametrize("limit", [0, -1])
def test_search_bad_limit(conn, feed_id, limit):
    done_article(conn, feed_id, "k1", "x", "x")
    with pytest.raises(ValueError):
        repo.search_articles(conn, "x", limit=limit)


def test_set_tags_str_rejected(conn, feed_id):
    aid = new_article(conn, feed_id)
    repo.set_article_tags(conn, aid, ["keep"])
    with pytest.raises(TypeError):
        repo.set_article_tags(conn, aid, "abc")
    assert repo.get_article_tags(conn, aid) == ["keep"]
    assert conn.execute("SELECT COUNT(*) FROM tags").fetchone()[0] == 1


def test_search_quote_literal_match(conn, feed_id):
    aid = done_article(conn, feed_id, "k1", 'say"hi there', "요약")
    assert aid in [r["id"] for r in repo.search_articles(conn, 'say"hi')]


# ---------------------------------------------------------------- 처리 대상


def _set(conn, aid, status, attempts=0):
    conn.execute(
        "UPDATE articles SET status = ?, attempts = ? WHERE id = ?", (status, attempts, aid)
    )
    conn.commit()
    return aid


def _mixed(conn, feed_id):
    n1 = new_article(conn, feed_id, "n1")
    n2 = new_article(conn, feed_id, "n2")
    f1 = _set(conn, new_article(conn, feed_id, "f1"), "failed", 1)
    f3 = _set(conn, new_article(conn, feed_id, "f3"), "failed", 3)
    for i, st in enumerate(["failed_permanent", "skipped_backfill", "done", "summarizing"]):
        _set(conn, new_article(conn, feed_id, f"o{i}"), st, 3)
    return n1, n2, f1, f3


def test_list_to_process(conn, feed_id):
    n1, n2, f1, f3 = _mixed(conn, feed_id)

    def ids(**kw):
        return [r["id"] for r in repo.list_articles_to_process(conn, **kw)]

    assert ids(limit=50) == [n1, n2, f1]
    assert ids(limit=2) == [n1, n2]
    assert ids(limit=1) == [n1]
    assert ids(limit=50, max_attempts=4) == [n1, n2, f1, f3]


@pytest.mark.parametrize("kw", [{"limit": 0}, {"limit": -1}, {"limit": 5, "max_attempts": 0}])
def test_list_to_process_bad_args(conn, kw):
    with pytest.raises(ValueError):
        repo.list_articles_to_process(conn, **kw)


def test_count_by_status(conn, feed_id):
    from rss_wiki.db import STATUSES

    assert repo.count_articles_by_status(conn) == dict.fromkeys(STATUSES, 0)
    _mixed(conn, feed_id)
    c = repo.count_articles_by_status(conn)
    assert set(c) == set(STATUSES) and len(c) == 7
    assert c["new"] == 2 and c["failed"] == 2 and c["done"] == 1
    assert c["failed_permanent"] == 1 and c["summarizing"] == 1
    assert c["skipped_backfill"] == 1 and c["fetching_content"] == 0


def test_list_failed(conn, feed_id):
    _n1, _n2, f1, f3 = _mixed(conn, feed_id)
    fp = conn.execute("SELECT id FROM articles WHERE status='failed_permanent'").fetchone()[0]
    conn.execute("UPDATE articles SET updated_at = ?", (OLD,))
    conn.commit()
    rows = repo.list_failed_articles(conn)
    assert [r["id"] for r in rows] == [fp, f3, f1]
    for k in ("id", "feed_id", "title", "status", "attempts", "last_error"):
        assert k in rows[0].keys()


def test_list_failed_updated_at_desc(conn, feed_id):
    a = _set(conn, new_article(conn, feed_id, "a"), "failed", 1)
    b = _set(conn, new_article(conn, feed_id, "b"), "failed", 1)
    conn.execute("UPDATE articles SET updated_at = ? WHERE id = ?", (OLD, b))
    conn.commit()
    assert [r["id"] for r in repo.list_failed_articles(conn)] == [a, b]


# ---------------------------------------------------------------- 실행 이력


def test_runs_lifecycle(conn):
    assert repo.get_latest_run(conn) is None
    rid = repo.start_run(conn)
    r = repo.get_latest_run(conn)
    assert r["id"] == rid and r["status"] == "running" and r["finished_at"] is None
    repo.finish_run(conn, rid, processed=3, failed=1)
    r = repo.get_latest_run(conn)
    assert (r["status"], r["processed"], r["failed"]) == ("finished", 3, 1)
    assert r["finished_at"] is not None


@pytest.mark.parametrize(
    "kw", [{"status": "bogus"}, {"status": "running"}, {"processed": -1}, {"failed": -1}]
)
def test_finish_run_invalid(conn, kw):
    rid = repo.start_run(conn)
    args = {"processed": 0, "failed": 0, **kw}
    with pytest.raises(ValueError):
        repo.finish_run(conn, rid, **args)
    r = repo.get_latest_run(conn)
    assert r["status"] == "running" and r["finished_at"] is None


def test_finish_run_zero_allowed(conn):
    rid = repo.start_run(conn)
    repo.finish_run(conn, rid, processed=0, failed=0, status="aborted")
    assert repo.get_latest_run(conn)["status"] == "aborted"


def test_finish_run_missing(conn):
    assert issubclass(repo.RunNotFoundError, LookupError)
    with pytest.raises(repo.RunNotFoundError):
        repo.finish_run(conn, 999, processed=0, failed=0)
    assert conn.in_transaction is False


def test_abort_running_runs(conn):
    done = repo.start_run(conn)
    repo.finish_run(conn, done, processed=1, failed=0)
    r1, r2 = repo.start_run(conn), repo.start_run(conn)
    assert repo.abort_running_runs(conn) == 2
    rows = {r["id"]: r for r in conn.execute("SELECT * FROM runs")}
    assert rows[done]["status"] == "finished"
    for i in (r1, r2):
        assert rows[i]["status"] == "aborted" and rows[i]["finished_at"] is not None
    assert repo.abort_running_runs(conn) == 0


def test_docstrings_raises():
    fns = (repo.list_articles_to_process, repo.finish_run)
    assert all("Raises" in (f.__doc__ or "") for f in fns)
