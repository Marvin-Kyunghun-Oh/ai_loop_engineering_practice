# tests/test_prompting.py
# app.prompting 테스트: SupportTicket 값이 프롬프트 템플릿에 올바르게 채워지는지 검증한다.

from app.prompting import SupportTicket, render_prompt

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
    rendered = render_prompt(ticket)

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
    rendered = render_prompt(ticket)

    assert "필수 키워드: " in rendered
