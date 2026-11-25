# tests/test_prompting.py
# app.prompting 테스트: SupportTicket 값이 Langfuse 프롬프트의 {{변수}}에 올바르게 채워지는지 검증한다.

import re

from app.prompting import SupportTicket, compile_prompt


class FakePrompt:
    """Langfuse 프롬프트 객체 대신 쓰는 가짜. {{name}}을 kwargs 값으로 바꾸는 compile만 흉내 낸다."""

    template = (
        "티켓 ID: {{ticket_id}}\n고객 ID: {{customer_id}}\n제품: {{product}}\n"
        "우선순위: {{priority}}\n제목: {{subject}}\n문의 내용: {{message}}\n"
        "필수 키워드: {{required_keywords}}"
    )

    def compile(self, **kwargs):
        return re.sub(r"\{\{(\w+)\}\}", lambda m: str(kwargs[m.group(1)]), self.template)


def test_프롬프트_렌더링시_티켓_값이_플레이스홀더에_채워진다():
    # 모든 필드를 채운 티켓을 렌더링 → 각 값이 결과 문자열에 포함되고 키워드는 ", "로 결합되는지 확인
    ticket = SupportTicket(
        ticket_id="t1",
        customer_id="c1",
        subject="환불 문의",
        message="환불 가능한가요?",
        product="LangOps Pro",
        required_keywords=["환불", "결제일"],
    )
    rendered = compile_prompt(FakePrompt(), ticket)

    assert "t1" in rendered
    assert "c1" in rendered
    assert "환불 문의" in rendered
    assert "환불 가능한가요?" in rendered
    assert "LangOps Pro" in rendered
    assert "환불, 결제일" in rendered


def test_필수_키워드가_없어도_프롬프트가_렌더링된다():
    # required_keywords를 생략한 티켓 → 에러 없이 "필수 키워드: " 라인이 렌더링되는지 확인
    ticket = SupportTicket(
        ticket_id="t1",
        customer_id="c1",
        subject="제목",
        message="문의 내용",
        product="LangOps Pro",
    )
    rendered = compile_prompt(FakePrompt(), ticket)

    assert "필수 키워드: " in rendered
