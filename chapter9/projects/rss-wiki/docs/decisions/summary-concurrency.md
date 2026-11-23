# 결정 U3: 요약 동시 실행 수

## 맥락
PRD 4.5: 실행 1회당 최대 50건을 요약한다. 요약은 글마다 Claude Code CLI 프로세스를 하나씩 띄운다. CLI에는 계정 단위 사용량 제한이 있다. 웹 UI는 진행 상황(처리/실패 건수)을 폴링으로 보여 준다.

## 후보
- A: 순차 처리(동시 1개)
- B: 2~4개 병렬 처리

## 기록 방법
`summary-concurrency.planner.md` / `summary-concurrency.evaluator.md` 첫 줄에 `선택: A`처럼 라벨 문자 하나만 쓴다.

합의: A (시도 1회)
