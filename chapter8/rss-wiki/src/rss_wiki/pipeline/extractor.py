"""trafilatura 래퍼 (PRD §7.1). 추출 실패 시 RSS summary로 대체한다."""
from __future__ import annotations

import asyncio
import html
import re
from dataclasses import dataclass
from typing import Awaitable, Callable

from .. import config
from .retry import Sleep, with_backoff

# extract(url) -> 본문 또는 None(본문 없음). 네트워크 오류 등은 예외.
ExtractFn = Callable[[str], str | None]

_SCRIPT_RE = re.compile(r"<(script|style)\b.*?</\1>", re.I | re.S)
_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def strip_html(text: str | None) -> str:
    if not text:
        return ""
    text = _TAG_RE.sub(" ", _SCRIPT_RE.sub(" ", text))
    return _WS_RE.sub(" ", html.unescape(text)).strip()


def trafilatura_extract(url: str) -> str | None:  # pragma: no cover - 네트워크
    import trafilatura

    downloaded = trafilatura.fetch_url(url)
    if downloaded is None:
        raise ConnectionError(f"다운로드 실패: {url}")
    return trafilatura.extract(downloaded)


@dataclass
class ExtractResult:
    content: str
    source: str  # 'extracted' | 'rss'
    attempts: int = 1
    error: str | None = None  # 대체(fallback)한 이유


async def extract_article(
    url: str,
    raw_summary: str | None,
    *,
    extract: ExtractFn = trafilatura_extract,
    timeout: float = config.EXTRACT_TIMEOUT,
    sleep: Sleep = asyncio.sleep,
) -> ExtractResult:
    """링크에서 전문을 추출한다. 타임아웃(20초)·오류는 지수 백오프로 재시도하고, 끝내 실패하거나
    본문이 비어 있으면 RSS summary로 대체한다(본문이 비어 있는 경우는 재시도하지 않는다)."""
    fallback = strip_html(raw_summary)

    async def once() -> str | None:
        return await asyncio.wait_for(asyncio.to_thread(extract, url), timeout)

    try:
        text, attempts = await with_backoff(once, sleep=sleep)
    except Exception as e:
        err = "타임아웃" if isinstance(e, asyncio.TimeoutError) else f"{type(e).__name__}: {e}"
        return ExtractResult(fallback, "rss", getattr(e, "attempts", 1), f"본문 추출 실패: {err}")
    text = strip_html(text)
    if not text:
        return ExtractResult(fallback, "rss", attempts, "본문 추출 결과가 비어 있음")
    return ExtractResult(text, "extracted", attempts)
