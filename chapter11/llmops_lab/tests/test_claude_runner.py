# tests/test_claude_runner.py
# app.claude_runner 통합 테스트: 실제 Claude Code CLI를 호출하므로 비용이 들고 .env 설정에 의존한다.

import pytest
from dotenv import load_dotenv
from app.claude_runner import run_claude

load_dotenv()

@pytest.mark.integration
def test_클로드_호출시_답변과_메타데이터를_반환한다():
    # 간단한 프롬프트로 실제 호출 → 답변이 비어 있지 않고, 소요 시간·모델명이 채워지는지 확인
    result = run_claude("간단히 'pong'이라고만 답해주세요.")
    assert result.answer
    assert result.duration_ms > 0
    assert result.model
