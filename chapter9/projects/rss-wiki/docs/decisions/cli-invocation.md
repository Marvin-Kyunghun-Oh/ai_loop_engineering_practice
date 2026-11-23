# 결정 U1: Claude Code CLI 호출 세부 방식

## 맥락
PRD 4.3: 글마다 Claude Code CLI를 비대화형(`claude -p ...`)으로 호출해 한국어 3줄 요약과 태그 3~5개를 JSON으로 받는다. 주 사용 환경은 Windows 11이며 `claude.cmd`를 실행할 수 있어야 한다. 본문은 설정값 길이로 잘라 넘긴다.

## 후보
- A: `claude -p "<지시문 + 본문>" --output-format json` — 본문을 프롬프트 인자에 포함
- B: 지시문만 `-p` 인자로 넘기고 본문은 stdin으로 전달
- C: 본문을 임시 파일에 쓰고 그 경로를 넘겨 CLI가 파일을 읽게 함

## 기록 방법
`cli-invocation.planner.md` / `cli-invocation.evaluator.md` 첫 줄에 `선택: A`처럼 라벨 문자 하나만 쓴다.

합의: B (시도 1회)
