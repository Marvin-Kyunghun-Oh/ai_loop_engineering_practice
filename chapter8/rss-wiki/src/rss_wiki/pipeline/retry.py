from __future__ import annotations

import asyncio
from typing import Awaitable, Callable, TypeVar

from .. import config

T = TypeVar("T")
Sleep = Callable[[float], Awaitable[None]]


async def with_backoff(
    fn: Callable[[], Awaitable[T]],
    *,
    retryable: tuple[type[BaseException], ...] = (Exception,),
    sleep: Sleep = asyncio.sleep,
) -> tuple[T, int]:
    """fn을 실행한다. retryable 예외면 2s→4s→8s 대기 후 최대 3회 재시도.
    (결과, 시도 횟수)를 돌려주고, 끝내 실패하면 마지막 예외에 `attempts` 속성을 붙여 던진다."""
    total = config.LLM_MAX_RETRIES + 1
    for attempt in range(1, total + 1):
        try:
            return await fn(), attempt
        except retryable as e:
            e.attempts = attempt  # type: ignore[attr-defined]
            if attempt == total:
                raise
            await sleep(config.LLM_BACKOFF_SECONDS[attempt - 1])
    raise AssertionError("unreachable")
