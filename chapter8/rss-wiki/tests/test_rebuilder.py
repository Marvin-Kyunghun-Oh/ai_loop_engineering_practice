import asyncio

import pytest
from fakes import FakeLLM

from rss_wiki.pipeline.llm import LLMError
from rss_wiki.pipeline.rebuilder import (build_rebuild_prompt, clean_markdown, one_line,
                                         rebuild_category)

PAGE = "# AI\n\n## 한줄 요약\n요약\n\n## 핵심 내용\n내용\n\n## 참고한 글\n- [t](u) — 2026-11-22 — x"


def run(c):
    return asyncio.run(c)


@pytest.fixture
def db(conn):
    conn.execute("INSERT INTO feeds(id, url) VALUES (1, 'http://f')")
    conn.execute("INSERT INTO categories(id, name) VALUES (1, 'AI')")
    conn.commit()
    return conn


def add(db, n, summary=None):
    cur = db.execute(
        """INSERT INTO articles(feed_id, url, title, published_at, llm_summary, primary_category_id)
           VALUES (1, ?, ?, ?, ?, 1)""",
        (f"https://a.com/{n}", f"글{n:03d}", f"2026-10-{(n % 28) + 1:02d}T00:00:00+00:00",
         summary or f"요약{n}번. 두번째 문장."))
    db.commit()
    return cur.lastrowid


def test_one_line():
    assert one_line("첫 문장입니다. 둘째 문장.") == "첫 문장입니다."
    assert len(one_line("가" * 200)) == 80


def test_first_build_includes_latest_20_of_all_articles(db):
    ids = [add(db, n) for n in range(1, 31)]
    p = build_rebuild_prompt(db, 1, ids[-2:])
    assert "(없음 — 최초 생성)" in p
    assert p.count("— 요약") == 20  # existing_recent_articles 20개
    assert p.count("  요약: ") == 2


def test_incremental_uses_previous_and_10_recent_excluding_new(db):
    ids = [add(db, n) for n in range(1, 31)]
    db.execute("INSERT INTO wiki_pages(category_id, content_markdown, articles_count_at_rebuild) "
               "VALUES (1, '# AI 이전 위키', 28)")
    db.commit()
    p = build_rebuild_prompt(db, 1, ids[-2:])
    assert "# AI 이전 위키" in p and "(없음" not in p
    assert p.count("— 요약") == 10 and p.count("  요약: ") == 2
    new_titles = [f"글{n:03d}" for n in (29, 30)]
    recent_part = p.split("[기존 글 중 최근 맥락용")[1]
    assert not any(t in recent_part for t in new_titles)


def test_token_guard_shrinks_recent_10_5_3_0(db):
    ids = [add(db, n, summary="가" * 3000) for n in range(1, 21)]
    db.execute("INSERT INTO wiki_pages(category_id, content_markdown, articles_count_at_rebuild) "
               "VALUES (1, '# AI', 10)")
    db.commit()
    new = ids[-5:]
    full = len(build_rebuild_prompt(db, 1, new, char_limit=10**9))
    seen = []
    for limit in range(full, full - 3000, -40):  # 상한을 조금씩 낮춰 가며 관찰
        p = build_rebuild_prompt(db, 1, new, char_limit=limit)
        assert p.count("  요약: ") == 5  # new_articles는 절대 줄이지 않음
        seen.append(p.count("— 가"))
    assert seen[0] == 10 and seen[-1] == 0
    assert list(dict.fromkeys(seen)) == [10, 5, 3, 0]  # 10→5→3→0 순서로만 줄어듦
    assert seen == sorted(seen, reverse=True)


def test_catch_up_mode_when_new_ids_none(db):
    for n in range(1, 6):
        add(db, n)
    db.execute("INSERT INTO wiki_pages(category_id, content_markdown, articles_count_at_rebuild) "
               "VALUES (1, '# AI', 3)")
    db.commit()
    p = build_rebuild_prompt(db, 1, None)
    assert p.count("  요약: ") == 2


def test_rebuild_success_saves_and_marks_unread(db):
    ids = [add(db, n) for n in range(1, 4)]
    llm = FakeLLM(text_responses=["```markdown\n" + PAGE + "\n```"])
    assert run(rebuild_category(db, llm, 1, ids)) is True
    w = db.execute("SELECT * FROM wiki_pages WHERE category_id=1").fetchone()
    assert w["content_markdown"] == PAGE and w["articles_count_at_rebuild"] == 3
    assert w["has_unread_updates"] == 1 and w["last_rebuilt_at"]
    assert db.execute("SELECT status FROM job_logs WHERE job_type='rebuild_wiki'").fetchone()["status"] == "ok"


def test_rebuild_overwrites_and_keeps_last_seen(db):
    ids = [add(db, 1)]
    db.execute("INSERT INTO wiki_pages(category_id, content_markdown, last_seen_at, has_unread_updates) "
               "VALUES (1, '# old', '2026-11-01 00:00:00', 0)")
    db.commit()
    run(rebuild_category(db, FakeLLM(text_responses=[PAGE]), 1, ids))
    w = db.execute("SELECT * FROM wiki_pages").fetchone()
    assert w["content_markdown"] == PAGE and w["last_seen_at"] == "2026-11-01 00:00:00"
    assert db.execute("SELECT COUNT(*) c FROM wiki_pages").fetchone()["c"] == 1


@pytest.mark.parametrize("reply", ["그냥 설명입니다", "# AI\n\n## 한줄 요약\n만 있음"])
def test_bad_structure_keeps_old_page_and_logs(db, reply):
    ids = [add(db, 1)]
    db.execute("INSERT INTO wiki_pages(category_id, content_markdown) VALUES (1, '# old')")
    db.commit()
    assert run(rebuild_category(db, FakeLLM(text_responses=[reply]), 1, ids)) is False
    assert db.execute("SELECT content_markdown FROM wiki_pages").fetchone()[0] == "# old"
    assert db.execute("SELECT status FROM job_logs").fetchone()["status"] == "failed"


def test_llm_error_logged_with_attempts(db):
    ids = [add(db, 1)]
    assert run(rebuild_category(db, FakeLLM(text_responses=[LLMError("down", attempts=4)]), 1, ids)) is False
    log = db.execute("SELECT * FROM job_logs").fetchone()
    assert log["attempt_count"] == 4 and log["target_ref"] == "1"


def test_empty_category_skipped(db):
    assert run(rebuild_category(db, FakeLLM(text_responses=[PAGE]), 1, [])) is False
    assert clean_markdown("```\n# x\n```") == "# x"
