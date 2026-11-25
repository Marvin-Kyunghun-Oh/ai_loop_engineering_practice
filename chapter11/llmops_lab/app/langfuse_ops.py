# app/langfuse_ops.py
# Langfuse(LLM 호출을 기록·관찰하는 서비스)로 trace를 보내는 코드 모음.
# service.py가 이 파일의 함수들을 `with`로 감싸 쓰면, 실행 구간마다 시작·끝 시간이 자동 기록된다.
#
# ■ 이 파일의 함수들 (service.py에서 호출되는 순서)
#   support_ticket_trace : 티켓 1건 전체를 감싸는 가장 바깥 구간(root). 고객·태그 정보를 붙인다.
#   claude_generation    : Claude 호출 구간 (generation 타입 = LLM 호출 전용)
#   quality_evaluator    : 품질 평가 구간 (evaluator 타입)
#   record_scores        : 평가 결과를 숫자 점수(score)로 기록
#
# ■ @contextmanager란?
#   함수를 `with 함수():` 형태로 쓸 수 있게 해 주는 도구다.
#   `yield` 앞 = 블록 진입 시 실행, `yield` 뒤 = 블록 종료 시 실행.
#   `yield`로 넘긴 값이 `with ... as 변수`의 변수가 된다. (예: `as root`)

import os
from contextlib import contextmanager

from langfuse import Langfuse, propagate_attributes

from .prompting import SupportTicket
from .claude_runner import ClaudeResult
from .evaluator import EvalResult

_client = None

# 1. 랭퓨즈 클라이언트는 하나만 만들어 재사용
#    매번 새로 만들면 연결이 낭비되므로, 처음 한 번만 만들고 `_client`에 보관한다.
#    접속 정보(키·주소)는 코드에 쓰지 않고 .env의 환경변수에서 읽는다.
def get_client() -> Langfuse:
    """Langfuse 클라이언트를 반환한다. 없으면 환경변수로 한 번만 생성한다."""
    global _client
    if _client is None:
        _client = Langfuse(
            public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
            secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
            host=os.getenv("LANGFUSE_BASE_URL"),
        )
    return _client


@contextmanager
def support_ticket_trace(ticket: SupportTicket):
    """티켓 한 건의 root span을 열고 trace 속성을 전파한다."""
    client = get_client()
    try:
        # 2. 티켓 전체를 감싸는 root span
        #    `start_as_current_observation`: 구간을 시작하고, 이 블록 안에서 새로 여는
        #    구간들을 자동으로 이 구간의 "자식"으로 연결한다. (그래서 트리 구조가 만들어진다)
        #    input/metadata는 Langfuse 화면에서 이 trace를 열었을 때 보이는 정보다.
        with client.start_as_current_observation(
            name="support-ticket-run",
            as_type="span",
            input={
                "ticket_id": ticket.ticket_id,
                "subject": ticket.subject,
                "message": ticket.message,
            },
            metadata={
                "product": ticket.product,
                "priority": ticket.priority,
            },
        ) as root:
            # 3. trace 전체에 붙는 속성
            # - 랭퓨즈 화면에서 '고객별', '태그별'로 trace를 필터링 할때 쓰는 값
            #   propagate_attributes: 이 블록 안에서 만들어지는 모든 하위 구간에
            #   user_id·tags를 똑같이 붙여 준다. (구간마다 일일이 달 필요가 없다)
            with propagate_attributes(
                user_id=ticket.customer_id,
                tags=["claude-p", "support", ticket.priority],
            ):
                yield root  # ← 여기서 service.py의 with 블록 본문이 실행된다
    finally:
        # 4. 모아 둔 데이터를 전송
        #    Langfuse는 기록을 모아 두었다가 백그라운드로 보낸다. 프로그램이 곧바로 끝나면
        #    전송 전에 사라질 수 있어서, 에러가 나도 반드시 실행되는 finally에서 flush로 강제 전송한다.
        client.flush()


@contextmanager
def claude_generation(prompt: str, model: str):
    """Claude 호출을 감싸는 generation span. 컨텍스트 안의 실제 호출 시간이 기록된다."""
    client = get_client()

    # 5. LLM 호출은 generation 타입으로 연다.
    #    generation으로 열어야 Langfuse가 모델·토큰·비용을 LLM 호출로 인식해 따로 집계한다.
    #    model·input에는 호출 시점에 알고 있는 값(모델명, 프롬프트)을 넣는다.
    #    답변·토큰·비용은 호출이 끝난 뒤 service.py의 gen.update에서 채운다.
    with client.start_as_current_observation(
        name="claude-p-answer",
        as_type="generation",
        model=model,
        input=prompt,
    ) as gen:
        yield gen


@contextmanager
def quality_evaluator(required_keywords: list[str]):
    """평가 단계를 감싸는 evaluator span."""
    client = get_client()

    # 6. 평가 단계는 evaluator 타입으로 연다.
    #    평가 구간임을 화면에서 구분해 보려는 용도다.
    with client.start_as_current_observation(
        name="quality-check",
        as_type="evaluator",
        input={"required_keywords": required_keywords},
    ) as ev:
        yield ev


def record_scores(
    root,
    claude_result: ClaudeResult,
    eval_result: EvalResult,
):
    """trace 단위 score 4종을 기록한다."""
    # 7. 비교 근거가 될 점수들 (점수 4개)
    #    score는 숫자여야 하므로, True/False는 1.0/0.0으로 바꿔서 보낸다.
    #    - keyword_coverage   : 필수 키워드 포함 비율 (0~1)
    #    - format_ok          : 섹션 형식 통과 여부 (1/0)
    #    - response_length_ok : 길이 기준 통과 여부 (1/0)
    #    - latency_ms         : Claude 응답 시간(밀리초)
    root.score_trace(name="keyword_coverage", value=eval_result.keyword_coverage)
    root.score_trace(name="format_ok", value=1.0 if eval_result.format_ok else 0.0)
    root.score_trace(
        name="response_length_ok", value=1.0 if eval_result.length_ok else 0.0
    )
    root.score_trace(name="latency_ms", value=claude_result.duration_ms)
