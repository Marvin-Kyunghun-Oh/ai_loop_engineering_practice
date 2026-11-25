# app/claude_runner.py
# 렌더링된 프롬프트를 Claude Code CLI(`claude -p`)로 실행하고 결과를 표준화해 반환하는 모듈.
# 절차: 환경변수 읽기 → CLI 호출(JSON 출력) → 실패 검사 → 답변·비용 추출

import subprocess
import json
import os
import time
from dataclasses import dataclass

# 1. 호출 결과를 표준화
@dataclass
class ClaudeResult:
    """Claude 호출 결과. 답변 본문과 함께 Langfuse trace에 기록할 메타데이터(소요 시간, 비용, 모델)를 담는다."""
    answer: str
    raw_payload: dict
    duration_ms: float
    cost_usd: float
    model: str

def run_claude(prompt: str) -> ClaudeResult:
    """프롬프트를 Claude Code CLI로 실행해 ClaudeResult를 반환한다.

    절차: CLAUDE_BIN/CLAUDE_MODEL/CLAUDE_TIMEOUT_SECONDS 읽기 → subprocess 호출 → 비정상 종료 시 RuntimeError
    """
    bin_path = os.getenv("CLAUDE_BIN", "claude")
    model = os.getenv("CLAUDE_MODEL", "sonnet")
    timeout = int(os.getenv("CLAUDE_TIMEOUT_SECONDS", "120"))

    started = time.time()
    # 2. 클로드코드의 답변을 json으로 받기.
    # - json의 값들이 곧 'Langfuse trace'에 들어갈 값
    result = subprocess.run(
        [bin_path, "-p", prompt,
         "--model", model,
         "--output-format", "json"], 
         capture_output=True,
         text=True,
         timeout=timeout,
    )
    duration_ms = (time.time() - started) * 1000

    # 3. 실패는 명시적으로 알림 (0이 아니면 에러)
    if result.returncode != 0:
        raise RuntimeError(f"claude failed: {result.stderr}")

    payload = json.loads(result.stdout)
    return ClaudeResult(
        # 4. 답변 본문과 비용 추출
        answer=payload.get("result", ""), 
        raw_payload=payload,
        duration_ms=duration_ms,
        cost_usd=payload.get("total_cost_usd", 0.0),
        model=model,
    )
