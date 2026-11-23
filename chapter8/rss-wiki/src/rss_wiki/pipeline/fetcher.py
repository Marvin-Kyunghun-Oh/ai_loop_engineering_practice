"""feedparser 래퍼 (PRD §7.1). 다운로드는 httpx로 하고 타임아웃 30초, 병렬도 5."""
from __future__ import annotations

import asyncio
import calendar
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Awaitable, Callable

from .. import config
from .retry import Sleep, with_backoff


class FeedFetchError(Exception):
    pass


@dataclass
class FeedEntry:
    url: str
    title: str
    author: str | None = None
    published_at: str | None = None  # UTC ISO8601
    raw_summary: str | None = None


@dataclass
class ParsedFeed:
    title: str | None = None
    entries: list[FeedEntry] = field(default_factory=list)


# download(url, timeout) -> 응답 본문 bytes. 실패하면 예외.
Downloader = Callable[[str, float], Awaitable[bytes]]


async def http_download(url: str, timeout: float) -> bytes:  # pragma: no cover - 네트워크
    import httpx

    async with httpx.AsyncClient(follow_redirects=True, timeout=timeout,
                                 headers={"User-Agent": "rss-wiki/0.1"}) as client:
        r = await client.get(url)
        r.raise_for_status()
        return r.content


def parse_feed_bytes(content: bytes) -> ParsedFeed:
    import feedparser

    parsed = feedparser.parse(content)
    entries: list[FeedEntry] = []
    for e in parsed.entries:
        link, title = e.get("link"), e.get("title")
        if not link or not title:
            continue
        ts = e.get("published_parsed") or e.get("updated_parsed")
        published = (datetime.fromtimestamp(calendar.timegm(ts), tz=timezone.utc)
                     .isoformat(timespec="seconds") if ts else None)
        body = (e.get("content") or [{}])[0].get("value") or e.get("summary")
        entries.append(FeedEntry(url=link, title=title, author=e.get("author"),
                                 published_at=published, raw_summary=body))
    if not entries and parsed.bozo:
        raise FeedFetchError(f"피드 파싱 실패: {parsed.bozo_exception}")
    return ParsedFeed(title=parsed.feed.get("title"), entries=entries)


async def fetch_feed(
    url: str,
    *,
    download: Downloader = http_download,
    timeout: float = config.FEED_FETCH_TIMEOUT,
    sleep: Sleep = asyncio.sleep,
) -> ParsedFeed:
    """피드를 가져와 파싱한다. 네트워크 오류·타임아웃은 지수 백오프로 재시도한다."""

    async def once() -> ParsedFeed:
        try:
            content = await asyncio.wait_for(download(url, timeout), timeout)
        except asyncio.TimeoutError as e:
            raise FeedFetchError(f"타임아웃({timeout}초)") from e
        except Exception as e:
            raise FeedFetchError(f"{type(e).__name__}: {e}") from e
        return await asyncio.to_thread(parse_feed_bytes, content)

    result, _ = await with_backoff(once, retryable=(FeedFetchError,), sleep=sleep)
    return result


async def fetch_many(
    feeds: list[tuple[int, str]],
    *,
    fetch: Callable[[str], Awaitable[ParsedFeed]] = fetch_feed,
    concurrency: int = config.FEED_CONCURRENCY,
) -> dict[int, ParsedFeed | Exception]:
    """(feed_id, url) 목록을 최대 `concurrency`개씩 병렬로 가져온다. 실패는 예외 객체로 돌려준다."""
    sem = asyncio.Semaphore(concurrency)

    async def one(feed_id: int, url: str):
        async with sem:
            try:
                return feed_id, await fetch(url)
            except Exception as e:
                return feed_id, e

    return dict(await asyncio.gather(*(one(i, u) for i, u in feeds)))
