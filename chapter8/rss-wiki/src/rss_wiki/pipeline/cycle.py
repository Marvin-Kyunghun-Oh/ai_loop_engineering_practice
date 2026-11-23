"""수집 사이클 (PRD §7.1): 피드 수집 → 본문 추출 → 요약·분류 → 영향받은 카테고리 위키 1회 재구성."""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Awaitable, Callable

from ..db import connect, log_job, utcnow
from .extractor import ExtractResult, extract_article
from .fetcher import FeedEntry, ParsedFeed, fetch_many
from .rebuilder import rebuild_category
from .summarizer import summarize_article

log = logging.getLogger("rss_wiki.cycle")


class CycleBusy(Exception):
    """이미 수집 사이클이 실행 중."""


@dataclass
class CycleReport:
    feeds_ok: int = 0
    feeds_failed: int = 0
    new_articles: int = 0
    summarized: int = 0
    summarize_failed: int = 0
    categories_rebuilt: list[int] = field(default_factory=list)
    rebuild_failed: list[int] = field(default_factory=list)


FetchMany = Callable[[list[tuple[int, str]]], Awaitable[dict[int, ParsedFeed | Exception]]]
Extract = Callable[[str, str | None], Awaitable[ExtractResult]]


async def run_cycle(
    db_path: str | Path, llm, *, lock: asyncio.Lock,
    fetch: FetchMany = fetch_many, extract: Extract = extract_article,
) -> CycleReport:
    if lock.locked():
        raise CycleBusy("이미 수집이 진행 중입니다")
    async with lock:
        conn = connect(db_path)
        try:
            return await _run(conn, llm, fetch, extract)
        finally:
            conn.close()


async def _run(conn, llm, fetch: FetchMany, extract: Extract) -> CycleReport:
    report = CycleReport()

    # 1. 활성 피드를 병렬(최대 5)로 수집. 실패해도 자동 비활성화하지 않는다(수동 비활성화만).
    feeds = conn.execute("SELECT id, url, title FROM feeds WHERE is_active=1 ORDER BY id").fetchall()
    results = await fetch([(f["id"], f["url"]) for f in feeds])
    parsed: dict[int, ParsedFeed] = {}
    for f in feeds:
        res = results.get(f["id"])
        started = utcnow()
        if isinstance(res, ParsedFeed):
            parsed[f["id"]] = res
            report.feeds_ok += 1
            conn.execute(
                "UPDATE feeds SET last_fetched_at=?, consecutive_failures=0, title=COALESCE(title, ?) "
                "WHERE id=?", (utcnow(), res.title, f["id"]))
            conn.commit()
            log_job(conn, "fetch_feed", f["id"], "ok", started_at=started)
        else:
            report.feeds_failed += 1
            msg = str(res) if res is not None else "결과 없음"
            conn.execute("UPDATE feeds SET consecutive_failures=consecutive_failures+1 WHERE id=?",
                         (f["id"],))
            conn.commit()
            log_job(conn, "fetch_feed", f["id"], "failed", error=msg,
                    attempts=getattr(res, "attempts", 1), started_at=started)
            log.warning("피드 %s 수집 실패: %s", f["url"], msg)

    # 2. 새 글 판별 (articles.url UNIQUE 기준)
    pending: list[tuple[int, FeedEntry]] = []
    seen: set[str] = set()
    for feed_id, feed in parsed.items():
        for e in feed.entries:
            if e.url in seen:
                continue
            seen.add(e.url)
            if conn.execute("SELECT 1 FROM articles WHERE url=?", (e.url,)).fetchone() is None:
                pending.append((feed_id, e))
    report.new_articles = len(pending)

    # 3. 추출 → 요약 (LLM 호출 직렬화)
    new_by_category: dict[int, list[int]] = {}
    for feed_id, e in pending:
        started = utcnow()
        ex = await extract(e.url, e.raw_summary)
        if ex.error:
            log_job(conn, "extract", e.url, "failed", error=ex.error, attempts=ex.attempts,
                    started_at=started)
        out = await summarize_article(conn, llm, feed_id=feed_id, entry=e,
                                      content=ex.content or e.title, raw_summary=e.raw_summary)
        if out.status == "ok":
            report.summarized += 1
            new_by_category.setdefault(out.category_id, []).append(out.article_id)
        elif out.status == "failed":
            report.summarize_failed += 1

    # 4. 영향받은 카테고리를 사이클당 1회 재구성. 이전 재구성이 실패해 뒤처진 카테고리도 따라잡는다.
    stale = [r["id"] for r in conn.execute(
        """SELECT c.id FROM categories c
           LEFT JOIN wiki_pages w ON w.category_id = c.id
           WHERE c.merged_into_id IS NULL
             AND (SELECT COUNT(*) FROM articles a WHERE a.primary_category_id=c.id AND a.status='ok')
                 != COALESCE(w.articles_count_at_rebuild, 0)""")]
    for cid in dict.fromkeys([*new_by_category, *stale]):
        ok = await rebuild_category(conn, llm, cid, new_by_category.get(cid))
        (report.categories_rebuilt if ok else report.rebuild_failed).append(cid)
    return report
