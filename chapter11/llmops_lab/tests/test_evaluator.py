# tests/test_evaluator.py
# app.evaluator 단위 테스트: 키워드 커버리지·섹션 형식·길이 평가가 기대대로 동작하는지 검증한다.

import pytest
from app.evaluator import evaluate

GOOD_ANSWER = """
## 요약
환불은 결제일로부터 7영업일 이내 가능합니다.

## 답변
영수증을 첨부해 고객센터로 문의해주세요.

## 다음 단계
1. 영수증 준비
2. 고객센터 연락
"""

def test_잘_작성된_답변은_모든_평가를_통과한다():
    # 섹션·키워드·길이를 모두 갖춘 답변 → 커버리지 1.0, 형식·길이 통과 확인
    result = evaluate(
        answer=GOOD_ANSWER,
        required_keywords=["환불", "결제일", "영업일", "영수증"],
    )
    assert result.keyword_coverage == 1.0
    assert result.format_ok is True
    assert result.length_ok is True


def test_필수_섹션이_없으면_형식_평가에_실패한다():
    # 섹션 제목이 없는 답변 → format_ok가 False인지 확인
    answer = "환불은 가능합니다. 영수증을 보여주세요." # 섹션 없음
    result = evaluate(answer, required_keywords=["환불"])
    assert result.format_ok is False


def test_키워드가_일부만_포함되면_부분_커버리지를_계산한다():
    # 키워드 3개 중 1개만 포함 → keyword_coverage가 1/3인지 확인
    answer = "## 요약\n## 답변\n##다음 단계\n환불만 가능합니다."
    result = evaluate(answer, required_keywords=["환불", "결제일", "영수증"])
    assert result.keyword_coverage == pytest.approx(1 / 3)
