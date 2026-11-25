# app/history.py
# 실행할 때마다 결과를 로컬 파일(artifacts/app_runs.jsonl)에 한 줄씩 남기는 코드.
# Langfuse가 안 되거나 느릴 때도, 방금 실행이 어땠는지 파일로 바로 확인할 수 있다.

import json
from datetime import datetime, timezone
from pathlib import Path
from .prompting import SupportTicket
from .claude_runner import ClaudeResult
from .evaluator import EvalResult

# 기록 파일 위치 (상대 경로이므로 프로젝트 루트에서 실행해야 한다)
HISTORY_PATH = Path("artifacts/app_runs.jsonl")


def append_run(
        ticket: SupportTicket,
        claude_result: ClaudeResult,
        eval_result: EvalResult,
):
    """티켓 1건의 실행 요약을 JSONL 파일 끝에 한 줄 추가한다."""
    # artifacts 폴더가 없으면 만든다 (이미 있으면 그냥 넘어감)
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    # 1. 한 번의 실행을 한 줄로 요약
    #    티켓 정보 + 평가 결과 + 응답 시간·비용 + 답변 앞 200자만 담는다. (전문은 Langfuse에 있음)
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "ticket_id": ticket.ticket_id,
        "product": ticket.product,
        "priority": ticket.priority,
        "subject": ticket.subject,
        "keyword_coverage": eval_result.keyword_coverage,
        "format_ok": eval_result.format_ok,
        "length_ok": eval_result.length_ok,
        "latency_ms": claude_result.duration_ms,
        "cost_usd": claude_result.cost_usd,
        "answer_preview": claude_result.answer[:200],
    }
    # 2. JSONL로 누적
    # - 한 줄에 실행 한번의 로그
    # - 랭퓨즈와 무관하게 실행이 어떻게 됐는지를 즉시 확인하는 용도
    #   JSONL = 한 줄이 JSON 하나인 파일. "a"(append) 모드로 열어 기존 기록 뒤에 이어 붙이므로
    #   파일 전체를 다시 읽고 쓸 필요가 없다. ensure_ascii=False는 한글이 \uXXXX로 깨지지 않게 한다.
    with HISTORY_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
