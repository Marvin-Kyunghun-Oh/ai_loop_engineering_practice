# app/service.py
# 티켓 한 건을 처음부터 끝까지 처리하는 "총괄" 함수(process_ticket)가 있는 파일.
# 앞서 만든 부품(프롬프트·Claude 호출·평가·Langfuse·로컬 기록)을 순서대로 이어 붙이는 역할만 한다.
#
# ■ 이 버전의 핵심 변경 (이전 버전 = 로컬 파일 프롬프트, 커밋 158298f와 비교)
#   - 프롬프트를 로컬 파일(prompts/support_answer.md)이 아니라 "Langfuse에 등록된 프롬프트"에서 읽어 온다.
#   - 읽어 온 프롬프트 객체(prompt_obj)를 generation에 연결(prompt=prompt_obj)한다.
#     → Langfuse 화면에서 "이 답변이 어떤 프롬프트 버전으로 만들어졌는지"가 추적된다.
#
# ■ 전체 흐름 (위에서 아래로 실행됨)
#
#   smoke_run.py / web_app.py ──> process_ticket(ticket)
#     1. get_client            Langfuse 클라이언트 가져오기              (langfuse_ops.py)
#     2. client.get_prompt     Langfuse에서 프롬프트 가져오기            (이름 + label)
#     3. compile_prompt        프롬프트에 티켓 값 채우기 → 완성 문장      (prompting.py)
#     4. [trace 열기]         Langfuse에 "티켓 1건 처리 시작" 표시      (langfuse_ops.py)
#     5.   [generation 열기]  "Claude 호출 구간" 표시 + 프롬프트 버전 연결
#     6.     run_claude       실제로 claude CLI 호출                   (claude_runner.py)
#     7.     gen.update       답변·토큰·비용을 generation에 기록
#     8.   [generation 닫기]
#     9.   [evaluator 열기]   "품질 평가 구간" 표시
#    10.     evaluate         키워드·형식·길이 평가                    (evaluator.py)
#    11.   [evaluator 닫기]
#    12.   record_scores      평가 결과를 Langfuse 점수(score)로 기록
#    13. [trace 닫기]
#    14. append_run           같은 내용을 로컬 파일에도 한 줄 기록     (history.py)
#
# ■ Langfuse 용어 (이 파일에서 계속 나옴)
#   - trace      : 실행 1건 전체. Langfuse 화면의 목록 한 줄이 trace 하나다.
#   - span       : trace 안의 "구간". 시작~끝 시간이 자동으로 기록된다.
#   - generation : LLM 호출 전용 span. 모델·토큰·비용을 함께 기록할 수 있다.
#   - score      : trace에 붙는 점수. 나중에 점수로 필터링·비교하려고 남긴다.
#   - prompt     : Langfuse에 이름·버전·label로 보관되는 프롬프트 템플릿.
#   - label      : 프롬프트 버전에 붙는 별칭. "production"이 붙은 버전이 현재 운영 버전이다.
#
# ■ 왜 이런 구조인가 (프롬프트를 Langfuse에서 읽는 이유)
#   프롬프트가 코드(파일) 안에 있으면 문구를 바꿀 때마다 코드를 수정·배포해야 하고,
#   어느 답변이 어느 문구로 만들어졌는지 남지 않는다.
#   Langfuse에 두면 ① 코드 수정 없이 버전을 바꾸고 ② label로 운영 버전을 지정하며
#   ③ trace마다 사용된 프롬프트 버전이 기록되어, 버전별 점수를 숫자로 비교할 수 있다.

import os
from dataclasses import dataclass
from .prompting import SupportTicket, compile_prompt
from .claude_runner import run_claude, ClaudeResult
from .evaluator import evaluate, EvalResult
from .langfuse_ops import (
    get_client,
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
    """티켓 1건을 처리한다: 프롬프트 조회 → Claude 호출 → 품질 평가 → Langfuse·로컬 기록."""
    # 1. Langfuse 클라이언트 가져오기
    #    프롬프트 조회와 trace 전송에 같은 클라이언트를 쓴다. (최초 1회만 생성되어 재사용됨)
    client = get_client()

    # 2. Langfuse에서 프롬프트 가져오기
    #    "support-answer-v1" 이름 중 label이 "production"인 버전을 가져온다.
    #    프롬프트를 새 버전으로 올리고 production label만 옮기면, 이 코드는 수정 없이 새 버전을 쓴다.
    #    ※ 이름이 Langfuse에 등록된 이름과 정확히 같아야 한다. (seed_prompts.py의 등록 이름 참고)
    prompt_obj = client.get_prompt("support-answer-v1", label="production")

    # 3. 프롬프트 렌더링
    #    가져온 프롬프트의 변수 자리에 티켓 값을 채워 Claude에게 보낼 최종 문장을 만든다.
    rendered = compile_prompt(prompt_obj, ticket)
    model = os.getenv("CLAUDE_MODEL", "sonnet")

    # `with`는 "블록 시작 = 구간 시작, 블록 끝 = 구간 끝"으로 동작한다.
    # Langfuse는 이 시작·끝 시각으로 각 구간의 소요 시간을 자동 계산한다.
    # `with`를 중첩하면 바깥 구간 안에 안쪽 구간이 들어간 트리 구조로 화면에 보인다.
    #   support-ticket-run (root)
    #   ├─ claude-p-answer (generation)  ← 사용한 프롬프트 버전이 함께 연결됨
    #   └─ quality-check   (evaluator)
    # 평가 구간도 root 블록 안에 둬야 같은 trace의 자식으로 묶인다.
    with support_ticket_trace(ticket) as root:
        # 4. generation에 프롬프트 객체 연결
        #    prompt=prompt_obj를 넘기면 Langfuse가 "이 호출은 프롬프트 X의 N번째 버전"으로 기록한다.
        #    (프롬프트 화면에서 버전별 호출 수·비용·지연·점수를 모아 볼 수 있게 됨)
        with claude_generation(rendered, model=model, prompt=prompt_obj) as gen:
            # 5. 클로드 호출
            #    이 호출이 generation 블록 안에서 일어나므로, 호출에 걸린 시간이 그대로 기록된다.
            claude_result = run_claude(rendered)
            usage = claude_result.raw_payload.get("usage", {})

            # 6. generation에 결과와 사용량 기록 (갱신)
            #    구간을 열 때는 결과를 알 수 없으므로, 호출이 끝난 뒤 update로 채워 넣는다.
            #    - output        : 모델의 답변
            #    - model         : 실제로 응답한 모델명 (열 때 넣은 별칭 "sonnet"을 실제 이름으로 덮어씀)
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
                    "cache_creation_input_tokens": usage.get(
                        "cache_creation_input_tokens", 0
                    ),
                },
            )

        with quality_evaluator(ticket.required_keywords) as ev:
            # 7. 품질 평가
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

        # 8. 점수 기록
        #    평가 결과를 Langfuse score로 남긴다. 이렇게 숫자로 남겨야 나중에
        #    "프롬프트를 바꾸기 전/후 점수가 올랐나?"를 화면에서 비교할 수 있다.
        #    root가 닫히기 전(블록 안)에 호출해야 점수가 이 trace에 붙는다.
        record_scores(root, claude_result, eval_result)
        root.update(output=claude_result.answer)

    # 9. 로컬 기록
    #    Langfuse와 무관하게, 실행 결과를 artifacts/app_runs.jsonl에 한 줄 남긴다.
    append_run(ticket, claude_result, eval_result)

    return RunResult(
        answer=claude_result.answer,
        claude_result=claude_result,
        eval_result=eval_result,
    )
