import asyncio

import pytest
from fakes import FakeLLM

from rss_wiki.db import connect
from rss_wiki.pipeline.cycle import CycleBusy, run_cycle
from rss_wiki.pipeline.extractor import ExtractResult
from rss_wiki.pipeline.fetcher import FeedEntry, FeedFetchError, ParsedFeed
from rss_wiki.pipeline.llm import LLMError

PAGE = "# AI\n\n## 한줄 요약\n요약\n\n## 핵심 내용\n내용"


def entry(n):
    return FeedEntry(url=f"https://a.com/{n}", title=f"글{n}", published_at="2026-11-22T09:00:00+00:00",
                     raw_summary="<p>rss</p>")


def make_fetch(feed_map):
    async def fetch(feeds):
        return {fid: feed_map.get(fid, FeedFetchError("no")) for fid, _ in feeds}

    return fetch


async def good_extract(url, raw):
    return ExtractResult("본문 " + url, "extracted")


def llm_for(category="AI"):
    return FakeLLM(
        json_responses=[lambda p: {"summary": "요약.", "category_name": category, "is_new_category": True,
                                   "language_detected": "ko"}],
        text_responses=[PAGE])


def run(settings, llm, fetch, extract=good_extract, lock=None):
    return asyncio.run(run_cycle(settings.db_path, llm, lock=lock or asyncio.Lock(),
                                 fetch=fetch, extract=extract))


@pytest.fixture
def db(conn, settings):
    conn.execute("INSERT INTO feeds(id, url) VALUES (1, 'http://f1')")
    conn.execute("INSERT INTO feeds(id, url) VALUES (2, 'http://f2')")
    conn.commit()
    return conn


def test_end_to_end_one_rebuild_per_category(db, settings):
    llm = llm_for()
    fetch = make_fetch({1: ParsedFeed("피드1", [entry(1), entry(2)]), 2: ParsedFeed("피드2", [entry(2), entry(3)])})
    rep = run(settings, llm, fetch)
    assert (rep.feeds_ok, rep.new_articles, rep.summarized) == (2, 3, 3)  # entry(2) 중복은 한 번만
    assert len(llm.json_prompts) == 3
    assert len(llm.text_prompts) == 1 and len(rep.categories_rebuilt) == 1  # 사이클당 카테고리별 1회
    w = db.execute("SELECT * FROM wiki_pages").fetchone()
    assert w["has_unread_updates"] == 1 and w["articles_count_at_rebuild"] == 3
    assert db.execute("SELECT title FROM feeds WHERE id=1").fetchone()["title"] == "피드1"
    assert db.execute("SELECT last_fetched_at FROM feeds WHERE id=1").fetchone()[0]


def test_second_cycle_is_noop(db, settings):
    fetch = make_fetch({1: ParsedFeed("f", [entry(1)]), 2: ParsedFeed("f", [entry(1)])})
    run(settings, llm_for(), fetch)
    llm2 = FakeLLM(json_responses=[RuntimeError("호출되면 안 됨")], text_responses=[RuntimeError("호출되면 안 됨")])
    rep = run(settings, llm2, fetch)
    assert rep.new_articles == 0 and rep.categories_rebuilt == [] and llm2.json_prompts == []


def test_failed_feed_counted_never_auto_disabled(db, settings):
    fetch = make_fetch({1: ParsedFeed("f", [])})  # 피드 2는 항상 실패
    for _ in range(7):
        rep = run(settings, llm_for(), fetch)
    row = db.execute("SELECT is_active, consecutive_failures FROM feeds WHERE id=2").fetchone()
    assert rep.feeds_failed == 1 and row["is_active"] == 1 and row["consecutive_failures"] == 7
    assert db.execute("SELECT COUNT(*) c FROM job_logs WHERE job_type='fetch_feed' AND status='failed'").fetchone()["c"] == 7
    # 성공하면 연속 실패가 초기화된다
    run(settings, llm_for(), make_fetch({1: ParsedFeed("f", []), 2: ParsedFeed("f", [])}))
    assert db.execute("SELECT consecutive_failures FROM feeds WHERE id=2").fetchone()[0] == 0


def test_inactive_feed_skipped(db, settings):
    db.execute("UPDATE feeds SET is_active=0 WHERE id=2")
    db.commit()
    seen = []

    async def fetch(feeds):
        seen.extend(f for f, _ in feeds)
        return {1: ParsedFeed("f", [])}

    run(settings, llm_for(), fetch)
    assert seen == [1]


def test_summarize_failure_isolated_and_not_retried(db, settings):
    llm = FakeLLM(json_responses=[LLMError("boom", 4), {"summary": "ok.", "category_name": "AI"}],
                  text_responses=[PAGE])
    fetch = make_fetch({1: ParsedFeed("f", [entry(1), entry(2)]), 2: ParsedFeed("f", [])})
    rep = run(settings, llm, fetch)
    assert (rep.summarized, rep.summarize_failed) == (1, 1)
    assert db.execute("SELECT status FROM articles WHERE url='https://a.com/1'").fetchone()[0] == "failed"
    llm2 = llm_for()
    rep2 = run(settings, llm2, fetch)  # 실패한 글도 URL이 있으므로 다시 수집하지 않는다
    assert rep2.new_articles == 0 and llm2.json_prompts == []


def test_extract_fallback_logged(db, settings):
    async def fallback(url, raw):
        return ExtractResult("RSS 요약", "rss", 4, "본문 추출 실패: Timeout")

    run(settings, llm_for(), make_fetch({1: ParsedFeed("f", [entry(1)]), 2: ParsedFeed("f", [])}), fallback)
    log = db.execute("SELECT * FROM job_logs WHERE job_type='extract'").fetchone()
    assert log["status"] == "failed" and log["attempt_count"] == 4
    assert db.execute("SELECT extracted_content FROM articles").fetchone()[0] == "RSS 요약"


def test_failed_rebuild_caught_up_next_cycle(db, settings):
    fetch = make_fetch({1: ParsedFeed("f", [entry(1)]), 2: ParsedFeed("f", [])})
    llm = FakeLLM(json_responses=[lambda p: {"summary": "s.", "category_name": "AI"}],
                  text_responses=[LLMError("down", 4)])
    rep = run(settings, llm, fetch)
    assert len(rep.rebuild_failed) == 1 and db.execute("SELECT COUNT(*) c FROM wiki_pages").fetchone()["c"] == 0
    llm2 = FakeLLM(json_responses=[RuntimeError("x")], text_responses=[PAGE])
    rep2 = run(settings, llm2, fetch)  # 새 글이 없어도 뒤처진 카테고리를 따라잡는다
    assert len(rep2.categories_rebuilt) == 1 and len(llm2.text_prompts) == 1
    assert db.execute("SELECT articles_count_at_rebuild FROM wiki_pages").fetchone()[0] == 1


def test_lock_busy_raises(db, settings):
    async def go():
        lock = asyncio.Lock()
        async with lock:
            with pytest.raises(CycleBusy):
                await run_cycle(settings.db_path, llm_for(), lock=lock, fetch=make_fetch({}), extract=good_extract)

    asyncio.run(go())
