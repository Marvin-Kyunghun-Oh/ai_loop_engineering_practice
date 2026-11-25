# app/prompting.py
# 고객 지원 티켓을 LLM 프롬프트 문자열로 변환하는 모듈.
# 절차: 티켓 입력 → SupportTicket 데이터 모델 → 템플릿 파일의 플레이스홀더 치환 → 완성된 프롬프트
from pathlib import Path
from dataclasses import dataclass, field

# 프롬프트 템플릿 경로 (상대 경로이므로 프로젝트 루트에서 실행해야 한다)
PROMPT_PATH = Path("prompts/support_answer.md")

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

# 2. 입력 값을 템플릿의 값으로 매핑
def render_prompt(ticket: SupportTicket) -> str:
    """티켓 값을 템플릿의 {플레이스홀더}에 채워 완성된 프롬프트 문자열을 반환한다.

    절차: 템플릿 읽기 → required_keywords를 ", "로 결합 → str.format()으로 치환
    (템플릿은 `{name}` 단일 중괄호를 써야 하며, `{{name}}`은 치환되지 않는다)
    """
    template = PROMPT_PATH.read_text(encoding="utf-8")
    return template.format(
        ticket_id = ticket.ticket_id,
        customer_id = ticket.customer_id,
        product = ticket.product,
        priority = ticket.priority,
        subject = ticket.subject,
        message = ticket.message,
        required_keywords=", ".join(ticket.required_keywords),
    )
