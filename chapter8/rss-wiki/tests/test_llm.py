import asyncio
import sys

import pytest

from rss_wiki.pipeline.llm import (JSON_RETRY_NOTE, JSON_SUFFIX, ClaudeCLI, LLMError, LLMJSONError,
                                   RunResult, parse_json_object)


def run(coro):
    return asyncio.run(coro)


async def nosleep(_):
    pass


def scripted(*results):
    """미리 정해 둔 결과를 순서대로 돌려주는 runner. 호출된 프롬프트도 기록한다."""
    calls = []
    it = iter(results)

    async def runner(prompt, timeout):
        calls.append(prompt)
        r = next(it)
        if isinstance(r, BaseException):
            raise r
        return r

    runner.calls = calls
    return runner


def ok(text):
    return RunResult(0, text)


@pytest.mark.parametrize("text", [
    '{"a": 1}',
    '```json\n{"a": 1}\n```',
    '```\n{"a": 1}\n```',
    '설명입니다.\n{"a": 1}\n끝',
])
def test_parse_fallback_chain(text):
    assert parse_json_object(text) == {"a": 1}


@pytest.mark.parametrize("text", ["", "no json", "[1, 2]", "{not json}"])
def test_parse_failure_returns_none(text):
    assert parse_json_object(text) is None


def test_json_success_first_try_appends_suffix():
    r = scripted(ok('{"summary": "요약"}'))
    resp = run(ClaudeCLI(runner=r, sleep=nosleep).complete_json("프롬프트"))
    assert resp.value == {"summary": "요약"} and resp.attempts == 1
    assert r.calls[0].endswith(JSON_SUFFIX)


def test_json_reask_once_with_note():
    r = scripted(ok("죄송합니다"), ok('{"a": 1}'))
    resp = run(ClaudeCLI(runner=r, sleep=nosleep).complete_json("p"))
    assert resp.value == {"a": 1} and resp.attempts == 2
    assert JSON_RETRY_NOTE in r.calls[1] and JSON_RETRY_NOTE not in r.calls[0]


def test_json_fails_after_reask():
    r = scripted(ok("x"), ok("y"))
    with pytest.raises(LLMJSONError) as e:
        run(ClaudeCLI(runner=r, sleep=nosleep).complete_json("p"))
    assert e.value.attempts == 2 and len(r.calls) == 2


def test_backoff_2_4_8_then_success():
    sleeps = []

    async def sl(s):
        sleeps.append(s)

    r = scripted(RunResult(1, "", "boom"), asyncio.TimeoutError(), RunResult(1, "", "boom"), ok("끝"))
    resp = run(ClaudeCLI(runner=r, sleep=sl).complete_text("p"))
    assert resp.value == "끝" and resp.attempts == 4 and sleeps == [2, 4, 8]


def test_gives_up_after_three_retries():
    sleeps = []

    async def sl(s):
        sleeps.append(s)

    r = scripted(*[RunResult(2, "", "bad")] * 4)
    with pytest.raises(LLMError) as e:
        run(ClaudeCLI(runner=r, sleep=sl).complete_text("p"))
    assert e.value.attempts == 4 and sleeps == [2, 4, 8] and "종료 코드 2" in str(e.value)


def test_rate_limit_hint_with_empty_stdout_is_retried():
    r = scripted(RunResult(0, "", "Error: rate limit exceeded"), ok("ok"))
    assert run(ClaudeCLI(runner=r, sleep=nosleep).complete_text("p")).attempts == 2


def test_missing_cli_not_retried():
    r = scripted(FileNotFoundError("claude"))
    with pytest.raises(LLMError) as e:
        run(ClaudeCLI(runner=r, sleep=nosleep).complete_text("p"))
    assert e.value.attempts == 1 and len(r.calls) == 1


def test_real_subprocess_passes_prompt_via_stdin():
    cmd = (sys.executable, "-c", "import sys; print(sys.stdin.read().upper())")
    resp = run(ClaudeCLI(command=cmd, sleep=nosleep).complete_text("hello 한글"))
    assert resp.value.strip() == "HELLO 한글"


def test_real_subprocess_timeout_is_retried_then_fails():
    cmd = (sys.executable, "-c", "import time; time.sleep(5)")
    with pytest.raises(LLMError) as e:
        run(ClaudeCLI(command=cmd, sleep=nosleep, timeout=0.2).complete_text("p"))
    assert "타임아웃" in str(e.value) and e.value.attempts == 4
