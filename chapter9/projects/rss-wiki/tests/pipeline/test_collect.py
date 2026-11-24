import logging

import pytest

from rss_wiki import pipeline, repo
from rss_wiki.db import connect, migrate
from rss_wiki.feeds import (
    FeedEntry,
    FeedFetchError,
    FeedParseError,
    FetchResult,
    ParsedFeed,
)

URL = "https://e.com/feed"


@pytest.fixture
def conn(tmp_path):
    c = connect(tmp_path / "t.db")
    migrate(c)
    yield c
    c.close()


@pytest.fixture
def fid(conn):
    return repo.add_feed(conn, URL, "t")


class FakeFetcher:
    def __init__(self, result=None, exc=None):
        self.result = result
        self.exc = exc
        self.calls = []

    def fetch(self, url, *, etag=None, last_modified=None):
        self.calls.append((url, etag, last_modified))
        if self.exc:
            raise self.exc
        return self.result


def entry(i, published="x", **kw):
    if published == "x":
        published = f"2024-01-{i:02d}T00:00:00+00:00"
    return FeedEntry(
        guid=kw.get("guid", f"g{i}"),
        link=kw.get("link", f"https://e.com/{i}"),
        title=f"t{i}",
        published=published,
        content=None,
        summary=None,
    )


def result(entries, etag="e1", lm="lm1"):
    return FetchResult(False, ParsedFeed("T", tuple(entries)), etag, lm)


def collect(conn, fid, fetcher, limit=10):
    return pipeline.collect_feed(
        conn, repo.get_feed(conn, fid), fetcher, first_fetch_limit=limit
    )


def statuses(conn, fid):
    rows = conn.execute(
        "SELECT entry_key, status FROM articles WHERE feed_id=?", (fid,)
    ).fetchall()
    return {r["entry_key"]: r["status"] for r in rows}


def test_first_fetch_limit_and_backfill(conn, fid):
    f = FakeFetcher(result([entry(i) for i in range(1, 13)]))
    r = collect(conn, fid, f)
    st = statuses(conn, fid)
    assert r.ok and not r.not_modified and r.error is None
    assert len(r.new_ids) == 10 and r.skipped_backfill == 2
    assert {k for k, s in st.items() if s == "skipped_backfill"} == {"guid:g1", "guid:g2"}
    assert sum(s == "new" for s in st.values()) == 10
    assert repo.get_feed(conn, fid)["initial_fetch_done"] == 1


def test_none_published_goes_backfill_first(conn, fid):
    entries = [entry(1, published=None), entry(2), entry(3)]
    r = collect(conn, fid, FakeFetcher(result(entries)), limit=2)
    st = statuses(conn, fid)
    assert st["guid:g1"] == "skipped_backfill"
    assert st["guid:g2"] == st["guid:g3"] == "new"
    assert r.skipped_backfill == 1


def test_idempotent_and_later_fetch_not_first(conn, fid):
    entries = [entry(i) for i in range(5, 17)]
    res = result(entries)
    f = FakeFetcher(res)
    collect(conn, fid, f)
    count = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
    r2 = collect(conn, fid, f)
    assert r2.new_ids == () and r2.skipped_backfill == 0
    assert conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0] == count
    # 저장된 etag/last_modified가 전달됨
    assert f.calls[1][1:] == ("e1", "lm1")
    # 가장 오래된 날짜의 새 항목: 첫 수집이 아니므로 new
    older = entry(1)
    f3 = FakeFetcher(result(entries + [older]))
    r3 = collect(conn, fid, f3)
    assert len(r3.new_ids) == 1 and r3.skipped_backfill == 0
    assert statuses(conn, fid)["guid:g1"] == "new"


def test_not_modified(conn, fid):
    repo.record_feed_success(conn, fid, etag="e0", last_modified="l0")
    f = FakeFetcher(FetchResult(True, None, "e0", "l0"))
    r = collect(conn, fid, f)
    row = repo.get_feed(conn, fid)
    assert r.ok and r.not_modified and r.new_ids == ()
    assert conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0] == 0
    assert row["consecutive_failures"] == 0 and row["etag"] == "e0"
    assert f.calls == [(URL, "e0", "l0")]


@pytest.mark.parametrize("exc", [FeedFetchError("boom"), FeedParseError("boom")])
def test_feed_error_recorded(conn, fid, exc):
    repo.record_feed_success(conn, fid, etag="e0", last_modified=None)
    r = collect(conn, fid, FakeFetcher(exc=exc))
    row = repo.get_feed(conn, fid)
    assert r.ok is False and r.error == "boom"
    assert row["consecutive_failures"] == 1 and row["last_error"] == "boom"
    assert row["etag"] == "e0"


def test_non_feed_error_propagates(conn, fid):
    with pytest.raises(RuntimeError):
        collect(conn, fid, FakeFetcher(exc=RuntimeError("x")))


def test_empty_message_error(conn, fid):
    r = collect(conn, fid, FakeFetcher(exc=FeedFetchError()))
    row = repo.get_feed(conn, fid)
    assert r.ok is False and r.error == "FeedFetchError"
    assert row["last_error"] == "FeedFetchError" and row["consecutive_failures"] == 1


def test_unidentified_skipped_with_warning(conn, fid, caplog):
    bad = FeedEntry(None, None, "no id", None, None, None)
    with caplog.at_level(logging.WARNING):
        r = collect(conn, fid, FakeFetcher(result([bad, entry(1)])))
    assert r.skipped_unidentified == 1 and len(r.new_ids) == 1
    recs = [
        x for x in caplog.records
        if x.name == "rss_wiki.pipeline" and x.levelno == logging.WARNING
    ]
    assert len(recs) == 1 and URL in recs[0].getMessage()


def test_invalid_limit(conn, fid):
    f = FakeFetcher(result([]))
    with pytest.raises(ValueError):
        collect(conn, fid, f, limit=0)
    assert f.calls == []
