"""Claude CLI `-p` 모드 호출 (PRD §7.2)."""
from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from .. import config

JSON_SUFFIX = "응답은 반드시 유효한 JSON 객체 하나만 출력하세요. 마크다운 코드펜스, 설명, 인사말 일절 금지."
JSON_RETRY_NOTE = "이전 응답이 JSON이 아니었다. JSON만 출력하라"
_RATE_LIMIT_HINTS = ("rate limit", "rate_limit", "429", "overloaded", "too many requests")


class LLMError(Exception):
    def __init__(self, message: str, attempts: int = 1):
        super().__init__(message)
        self.attempts = attempts


class LLMJSONError(LLMError):
    """JSON 폴백 체인과 재호출까지 모두 실패."""


@dataclass
class RunResult:
    returncode: int
    stdout: str
    stderr: str = ""


@dataclass
class LLMResponse:
    value: Any  # complete_json → dict, complete_text → str
    attempts: int


# runner(prompt, timeout) -> RunResult. 타임아웃이면 asyncio.TimeoutError, CLI가 없으면 FileNotFoundError.
Runner = Callable[[str, float], Awaitable[RunResult]]
Sleep = Callable[[float], Awaitable[None]]


def subprocess_runner(command: tuple[str, ...]) -> Runner:
    async def run(prompt: str, timeout: float) -> RunResult:
        proc = await asyncio.create_subprocess_exec(
            *command, stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        try:
            out, err = await asyncio.wait_for(proc.communicate(prompt.encode("utf-8")), timeout)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            raise
        return RunResult(proc.returncode, out.decode("utf-8", "replace"), err.decode("utf-8", "replace"))

    return run


def parse_json_object(text: str) -> dict | None:
    """폴백 체인 1~3단계. 실패하면 None."""
    candidates = [text.strip()]
    fence = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.I)
    candidates.append(fence.strip())
    m = re.search(r"\{[\s\S]*\}", text)
    if m:
        candidates.append(m.group(0))
    for c in candidates:
        try:
            data = json.loads(c)
        except (json.JSONDecodeError, ValueError):
            continue
        if isinstance(data, dict):
            return data
    return None


class ClaudeCLI:
    def __init__(
        self,
        command: tuple[str, ...] = ("claude", "-p", "--output-format", "text"),
        runner: Runner | None = None,
        sleep: Sleep = asyncio.sleep,
        timeout: float = config.CLAUDE_TIMEOUT,
    ):
        self._run = runner or subprocess_runner(command)
        self._sleep = sleep
        self._timeout = timeout

    async def complete_text(self, prompt: str) -> LLMResponse:
        """프로세스 단계 오류는 지수 백오프(2s→4s→8s, 최대 3회 재시도)로 다시 시도한다."""
        last = "알 수 없는 오류"
        total = config.LLM_MAX_RETRIES + 1
        for attempt in range(1, total + 1):
            try:
                r = await self._run(prompt, self._timeout)
            except asyncio.TimeoutError:
                last = f"claude 타임아웃({self._timeout}초)"
            except FileNotFoundError as e:
                raise LLMError(f"claude CLI를 찾을 수 없습니다: {e}", attempt) from e
            else:
                hint = any(h in r.stderr.lower() for h in _RATE_LIMIT_HINTS)
                if r.returncode == 0 and not (hint and not r.stdout.strip()):
                    return LLMResponse(r.stdout, attempt)
                last = f"claude 종료 코드 {r.returncode}: {r.stderr.strip()[:300]}"
            if attempt < total:
                await self._sleep(config.LLM_BACKOFF_SECONDS[attempt - 1])
        raise LLMError(last, total)

    async def complete_json(self, prompt: str) -> LLMResponse:
        if JSON_SUFFIX not in prompt:
            prompt = f"{prompt}\n\n{JSON_SUFFIX}"
        first = await self.complete_text(prompt)
        data = parse_json_object(first.value)
        if data is not None:
            return LLMResponse(data, first.attempts)
        try:
            second = await self.complete_text(f"{prompt}\n\n{JSON_RETRY_NOTE}")
        except LLMError as e:
            raise LLMError(str(e), first.attempts + e.attempts) from e
        attempts = first.attempts + second.attempts
        data = parse_json_object(second.value)
        if data is None:
            raise LLMJSONError("JSON 파싱 실패(재호출 포함)", attempts)
        return LLMResponse(data, attempts)
