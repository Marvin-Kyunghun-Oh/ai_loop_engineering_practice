import asyncio

import pytest
from fakes import FakeLLM

from rss_wiki.pipeline.fetcher import FeedEntry
from rss_wiki.pipeline.llm import LLMError
from rss_wiki.pipeline.summarizer import (build_prompt, detect_language, resolve_category,
                                          summarize_article)


def run(c):
    return asyncio.run(c)


@pytest.fixture
def db(conn):
    conn.execute("INSERT INTO feeds(id, url) VALUES (1, 'http://f')")
    conn.commit()
    return conn


def entry(n=1):
    return FeedEntry(url=f"https://a.com/{n}", title=f"글{n}", published_at="2026-11-22T09:00:00+00:00",
                     raw_summary="<p>rss</p>")


GOOD = {"summary": "한국어 요약입니다.", "category_name": "LLM 에이전트",
        "is_new_category": True, "language_detected": "en"}


def go(db, llm, n=1, content="Some english body"):
    return run(summarize_article(db, llm, feed_id=1, entry=entry(n), content=content))


def test_detect_language():
    assert detect_language("안녕하세요 반갑습니다") == "ko"
    assert detect_language("Hello world") == "en"
    assert detect_language("12345 !!!") == "기타"


def test_prompt_lists_existing_categories_and_renders_input(db):
    db.execute("INSERT INTO categories(name, description) VALUES ('AI', '인공지능')")
    db.execute("INSERT INTO categories(name, merged_into_id) VALUES ('ML', 1)")
    p = build_prompt(db, entry(), "본문 텍스트")
    assert "- AI: 인공지능" in p and "- ML" not in p
    assert "제목: 글1" in p and "원문 URL: https://a.com/1" in p and "본문 텍스트" in p
    assert "언어: ko" in p and "유효한 JSON 객체 하나만" in p


def test_success_creates_category_and_article(db):
    out = go(db, FakeLLM([GOOD]))
    assert out.status == "ok"
    art = db.execute("SELECT * FROM articles WHERE id=?", (out.article_id,)).fetchone()
    assert art["llm_summary"] == "한국어 요약입니다." and art["status"] == "ok" and art["language"] == "en"
    assert db.execute("SELECT name FROM categories WHERE id=?", (art["primary_category_id"],)).fetchone()["name"] == "LLM 에이전트"
    assert db.execute("SELECT status FROM job_logs WHERE job_type='summarize'").fetchone()["status"] == "ok"


def test_existing_category_reused_and_merged_followed(db):
    db.execute("INSERT INTO categories(id, name) VALUES (1, 'A')")
    db.execute("INSERT INTO categories(id, name, merged_into_id) VALUES (2, 'B', 1)")
    db.commit()
    assert resolve_category(db, "A") == 1
    assert resolve_category(db, "B") == 1
    assert resolve_category(db, " 새 이름 ") not in (1, 2)
    assert db.execute("SELECT COUNT(*) c FROM categories").fetchone()["c"] == 3


def test_llm_failure_records_failed_article_and_log(db):
    out = go(db, FakeLLM([LLMError("타임아웃", attempts=4)]))
    assert out.status == "failed"
    art = db.execute("SELECT * FROM articles WHERE url='https://a.com/1'").fetchone()
    assert art["status"] == "failed" and art["llm_summary"] is None and art["primary_category_id"] is None
    log = db.execute("SELECT * FROM job_logs").fetchone()
    assert log["status"] == "failed" and log["attempt_count"] == 4 and "타임아웃" in log["error_message"]


def test_bad_format_recorded_as_failed(db):
    out = go(db, FakeLLM([{"summary": "", "category_name": "X"}]))
    assert out.status == "failed" and "형식 오류" in out.error


def test_duplicate_url_ignored(db):
    go(db, FakeLLM([GOOD]))
    assert go(db, FakeLLM([GOOD])).status == "duplicate"
    assert db.execute("SELECT COUNT(*) c FROM articles").fetchone()["c"] == 1


def test_article_searchable_via_fts_after_insert(db):
    go(db, FakeLLM([GOOD]))
    rows = db.execute("SELECT rowid FROM articles_fts WHERE articles_fts MATCH '요약입니다'").fetchall()
    assert len(rows) == 1
