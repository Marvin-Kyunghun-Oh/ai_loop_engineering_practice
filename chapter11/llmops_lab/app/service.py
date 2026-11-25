# app/service.py
# 티켓 한 건을 처음부터 끝까지 처리하는 "총괄" 함수(process_ticket)가 있는 파일.
# 앞서 만든 부품(프롬프트·Claude 호출·평가·Langfuse·로컬 기록)을 순서대로 이어 붙이는 역할만 한다.
#
# ■ 전체 흐름 (위에서 아래로 실행됨)
#
#   smoke_run.py ──> process_ticket(ticket)
#     1. render_prompt        티켓 → 프롬프트 문장 만들기              (prompting.py)
#     2. [trace 열기]         Langfuse에 "티켓 1건 처리 시작" 표시      (langfuse_ops.py)
#     3.   [generation 열기]  "Claude 호출 구간" 표시 → 시간 자동 측정
#     4.     run_claude       실제로 claude CLI 호출                   (claude_runner.py)
#     5.     gen.update       답변·토큰·비용을 generation에 기록
#     6.   [generation 닫기]
#     7. [evaluator 열기]     "품질 평가 구간" 표시
#     8.   evaluate           키워드·형식·길이 평가                    (evaluator.py)
#     9. [evaluator 닫기]
#    10. record_scores        평가 결과를 Langfuse 점수(score)로 기록
#    11. append_run           같은 내용을 로컬 파일에도 한 줄 기록     (history.py)
#
# ■ Langfuse 용어 (이 파일에서 계속 나옴)
#   - trace      : 실행 1건 전체. Langfuse 화면의 목록 한 줄이 trace 하나다.
#   - span       : trace 안의 "구간". 시작~끝 시간이 자동으로 기록된다.
#   - generation : LLM 호출 전용 span. 모델·토큰·비용을 함께 기록할 수 있다.
#   - score      : trace에 붙이는 점수. 나중에 점수로 필터링·비교하려고 남긴다.

import os
from dataclasses import dataclass

from .prompting import SupportTicket, render_prompt
from .claude_runner import run_claude, ClaudeResult
from .evaluator import evaluate, EvalResult
from .langfuse_ops import (
    support_ticket_trace,
    claude_generation,
    quality_evaluator,
    record_scores,
)
from .history import append_run


@dataclass
class RunResult:
    """process_ticket의 최종 반환값. 답변과, 호출·평가 결과를 한 묶음으로 돌려준다."""
    answer: str
    claude_result: ClaudeResult
    eval_result: EvalResult


def process_ticket(ticket: SupportTicket) -> RunResult:
    """티켓 1건을 처리한다: 프롬프트 생성 → Claude 호출 → 품질 평가 → Langfuse·로컬 기록."""
    # 1. 프롬프트 렌더링
    #    티켓 정보를 템플릿(prompts/support_answer.md)에 끼워 Claude에게 보낼 문장을 만든다.
    prompt = render_prompt(ticket)
    model = os.getenv("CLAUDE_MODEL", "sonnet")

    # `with`는 "블록 시작 = 구간 시작, 블록 끝 = 구간 끝"으로 동작한다.
    # Langfuse는 이 시작·끝 시각으로 각 구간의 소요 시간을 자동 계산한다.
    # `with`를 중첩하면 바깥 구간 안에 안쪽 구간이 들어간 트리 구조로 화면에 보인다.
    #   support-ticket-run (root)
    #   ├─ claude-p-answer (generation)
    #   └─ quality-check   (evaluator)
    # 평가 구간도 root 블록 안에 둬야 같은 trace의 자식으로 묶인다.
    with support_ticket_trace(ticket) as root:
        with claude_generation(prompt, model) as gen:
            # 2. 클로드 호출
            #    이 호출이 generation 블록 안에서 일어나므로, 호출에 걸린 시간이 그대로 기록된다.
            claude_result = run_claude(prompt)
            usage = claude_result.raw_payload.get("usage", {})

            # 3. generation에 결과와 사용량 기록 (갱신)
            #    구간을 열 때는 결과를 알 수 없으므로, 호출이 끝난 뒤 update로 채워 넣는다.
            #    - output        : 모델의 답변
            #    - cost_details  : 이번 호출 비용(USD)
            #    - usage_details : 토큰 수. input/output 외에 캐시 읽기·생성 토큰도 따로 기록한다.
            gen.update(
                output=claude_result.answer,
                model=claude_result.model,
                cost_details={"total": claude_result.cost_usd},
                usage_details={
                    "input": usage.get("input_tokens", 0),
                    "output": usage.get("output_tokens", 0),
                    "cache_read_input_tokens": usage.get("cache_read_input_tokens", 0),
                    "cache_creation_input_tokens": usage.get("cache_creation_input_tokens", 0),
                },
            )

        with quality_evaluator(ticket.required_keywords) as ev:
            # 4. 품질 평가
            #    규칙 기반(외부 호출 없음)으로 키워드 커버리지·섹션 형식·길이를 확인한다.
            eval_result = evaluate(
                answer=claude_result.answer,
                required_keywords=ticket.required_keywords,
            )
            ev.update(
                output={
                    "keyword_coverage": eval_result.keyword_coverage,
                    "format_ok": eval_result.format_ok,
                    "response_length_ok": eval_result.length_ok,
                },
            )

        # 5. 점수 기록
        #    평가 결과를 Langfuse score로 남긴다. 이렇게 숫자로 남겨야 나중에
        #    "프롬프트를 바꾸기 전/후 점수가 올랐나?"를 화면에서 비교할 수 있다.
        #    root가 닫히기 전(블록 안)에 호출해야 점수가 이 trace에 붙는다.
        record_scores(root, claude_result, eval_result)
        root.update(output=claude_result.answer)

    # 6. 로컬 기록
    #    Langfuse와 무관하게, 실행 결과를 artifacts/app_runs.jsonl에 한 줄 남긴다.
    append_run(ticket, claude_result, eval_result)

    return RunResult(
        answer=claude_result.answer,
        claude_result=claude_result,
        eval_result=eval_result,
    )
