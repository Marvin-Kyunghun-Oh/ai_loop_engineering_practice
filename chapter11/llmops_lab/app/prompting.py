# app/prompting.py
# 고객 지원 티켓(SupportTicket)과, Langfuse에서 가져온 프롬프트에 티켓 값을 채우는 compile_prompt를 제공한다.
# 절차: 티켓 입력 → SupportTicket 데이터 모델 → Langfuse 프롬프트 객체의 변수 치환(compile) → 완성된 프롬프트
#
# ■ 이 버전의 핵심 변경 (이전 버전 = 로컬 파일 프롬프트, 커밋 158298f와 비교)
#   - 이전: render_prompt(ticket)이 prompts/support_answer.md 파일을 직접 읽고 str.format()으로 치환했다.
#   - 지금: 템플릿 읽기는 service.py가 Langfuse에서 하고(client.get_prompt),
#           이 파일은 "받은 프롬프트 객체에 티켓 값을 채우는 일"만 한다.
#   - 그래서 PROMPT_PATH 상수와 pathlib import가 사라졌다. (더 이상 상대 경로에 의존하지 않음)
#
# ■ 흐름
#   service.py: client.get_prompt(...)  ──> prompt_obj (Langfuse 프롬프트 객체)
#   service.py: compile_prompt(prompt_obj, ticket)
#       └─ prompt_obj.compile(ticket_id=..., customer_id=..., ...)   변수 자리에 값 채우기
#       └─ 완성된 문자열 반환 ──> run_claude(rendered)로 전달됨
#
# ■ 용어
#   - 프롬프트 객체 : Langfuse SDK가 돌려주는 프롬프트 한 건. 본문·버전·label 정보를 들고 있고,
#                    .compile(...)로 변수를 채울 수 있다.
#   - compile      : 프롬프트 본문의 변수 자리({{name}})를 실제 값으로 바꿔 최종 문자열을 만드는 동작.
#
# ■ 주의
#   Langfuse 프롬프트의 변수 표기는 이중 중괄호 `{{name}}`이다.
#   (이전 로컬 템플릿의 `{name}` 단일 중괄호 + str.format() 방식과 다르다.)
from dataclasses import dataclass, field


# 1. 입력 값을 데이터 모델로 변환
@dataclass
class SupportTicket:
    """고객 지원 티켓 한 건의 입력 데이터.

    priority 기본값은 "normal", required_keywords는 답변에 반드시 포함할 단어 목록.
    """
    ticket_id: str
    customer_id: str
    subject: str
    message: str
    product: str
    priority: str = "normal"
    required_keywords: list[str] = field(default_factory=list)


# 2. 티켓 값을 프롬프트의 변수로 매핑
def compile_prompt(prompt, ticket: SupportTicket) -> str:
    """Langfuse Prompt 객체와 티켓을 받아 렌더링된 문자열을 반환

    절차: required_keywords를 ", "로 결합 → prompt.compile()로 변수 치환
    (프롬프트에 없는 변수는 무시되고, 프롬프트에 있는데 여기서 안 넘긴 변수는 `{{name}}` 그대로 남는다)
    """
    return prompt.compile(
        ticket_id=ticket.ticket_id,
        customer_id=ticket.customer_id,
        product=ticket.product,
        priority=ticket.priority,
        subject=ticket.subject,
        # 리스트는 그대로 못 넣으므로 "a, b, c" 형태의 한 문자열로 합친다.
        required_keywords=", ".join(ticket.required_keywords),
        message=ticket.message,
    )
