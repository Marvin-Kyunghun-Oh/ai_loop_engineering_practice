# 결정 U2: 요약 호출에 쓸 모델

## 맥락
PRD 4.3: 글마다 Claude Code CLI를 호출해 짧은 한국어 요약과 태그를 만든다. 실행 1회당 최대 50건. 비용·속도와 품질 사이의 균형이 필요하며, 아직 실제 비교는 하지 않았다.

## 후보
- A: CLI 기본 모델을 그대로 사용 (`--model` 미지정)
- B: `--model`로 가벼운 모델(Haiku 계열)을 코드에 고정
- C: 설정값(`claude_model`)으로 노출하고, 값이 없으면 `--model`을 붙이지 않음

## 기록 방법
`summary-model.planner.md` / `summary-model.evaluator.md` 첫 줄에 `선택: A`처럼 라벨 문자 하나만 쓴다.

합의: C (시도 1회)
