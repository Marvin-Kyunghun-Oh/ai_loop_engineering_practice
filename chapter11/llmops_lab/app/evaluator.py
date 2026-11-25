# app/evaluator.py
# 모델 답변의 품질을 규칙 기반으로 자동 평가하는 모듈 (외부 호출 없음).
# 절차: 키워드 커버리지 계산 → 섹션 형식 검사 → 길이 검사 → EvalResult 반환

from dataclasses import dataclass

@dataclass
class EvalResult:
    """품질 평가 결과. keyword_coverage는 0~1 비율, format_ok·length_ok는 통과 여부."""
    keyword_coverage: float
    format_ok: bool
    length_ok: bool

# 프롬프트 템플릿이 요구하는 필수 섹션 제목
REQUIRED_SECTIONS = ["요약", "답변", "다음 단계"]

def evaluate(answer: str, required_keywords: list[str]) -> EvalResult:
    """답변이 키워드·형식·길이 기준을 만족하는지 평가해 EvalResult로 반환한다.

    키워드가 없으면 coverage는 1.0, 길이 기준은 50자 이상 4000자 이하.
    """
    # 1. [품질체크] - 키워드 커버리지: 필수 키워드 중 답변에 포함된 비율
    if required_keywords:
        hit = sum(1 for kw in required_keywords if kw in answer)
        coverage = hit / len(required_keywords)
    else:
        coverage = 1.0

    # 2. [품질체크] - 형식 : 필수 섹션이 모두 있는지?
    format_ok = all(section in answer for section in REQUIRED_SECTIONS)

    # 3. [품질체크] - 길이 : 너무 짧거나 길지 않은지?
    length_ok = 50 <= len(answer) <= 4000

    return EvalResult(
        keyword_coverage=coverage,
        format_ok=format_ok,
        length_ok=length_ok
    )
