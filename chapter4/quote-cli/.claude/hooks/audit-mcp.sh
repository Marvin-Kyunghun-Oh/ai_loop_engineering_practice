#!/bin/bash
# =============================================================================
# MCP 호출 감사 로그 훅 (.claude/hooks/audit-mcp.sh)
#
# Claude가 도구(주로 MCP 도구)를 호출할 때마다 실행되어,
# "언제 / 어떤 도구를 / 어떤 입력으로" 호출했는지 로그 파일에 한 줄씩 기록합니다.
# 차단 훅과 달리 아무것도 막지 않고 기록만 합니다.
#
# 설계 원칙: fail-open (기록 실패가 도구 실행을 막으면 안 된다)
#   감사 훅은 기록이 목적이라, 어떤 오류가 나도 exit 0으로 끝내 도구는 그대로 실행됩니다.
#   (차단 훅 block-dangerous.sh는 반대로 fail-closed)
#
# 필요 도구: 없음 (jq가 있으면 정확히 파싱하고, 없으면 원본 JSON을 한 줄로 기록)
# =============================================================================

# 안전 옵션 (셸 스크립트의 관용적인 첫 줄)
#   -e          : 명령 하나라도 실패하면 스크립트를 즉시 종료
#   -u          : 정의되지 않은 변수를 쓰면 오류로 처리 (오타 방지)
#   -o pipefail : 파이프(|)로 이어진 명령 중 하나라도 실패하면 전체를 실패로 처리
set -euo pipefail

# 예상 못한 오류가 나도 도구 실행은 막지 않는다. (fail-open)
trap 'exit 0' ERR

# 1. 표준 입력으로 들어온 JSON 읽기
# 차단 훅(block-dangerous.sh)과 마찬가지로, 클로드 코드가 넣어 준
# 도구 호출 정보(JSON) 전체를 input 변수에 저장합니다.
# 들어오는 JSON 예:
#   {"tool_name": "mcp__quote__add_quote",
#    "tool_input": {"text": "명언 내용", "author": "작가"}, ...}
input="$(cat)"

# 2~3. 도구 이름과 입력값 추출
# jq가 있으면: .tool_name / .tool_input 만 정확히 꺼낸다.
#   // ""  : 값이 없으면 빈 문자열, // {} : 값이 없으면 빈 객체
#   -r     : 따옴표 없이 출력, -c : 줄바꿈 없는 한 줄 JSON으로 출력
# jq가 없으면: sed로 tool_name만 뽑고, 입력값 자리에는 원본 JSON 전체를 한 줄로 넣는다.
if command -v jq >/dev/null 2>&1; then
  tool="$(printf '%s' "$input" | jq -r '.tool_name // ""')"
  payload="$(printf '%s' "$input" | jq -c '.tool_input // {}')"
else
  tool="$(printf '%s' "$input" | sed -n 's/.*"tool_name"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -n 1)"
  payload="$(printf '%s' "$input" | tr -d '\r\n')"
fi

# 4. 시각, 도구 이름, 입력값을 한 줄로 로그 파일에 추가
# printf '%s\t%s\t%s\n' : 값 3개를 탭(\t)으로 구분하고 끝에 줄바꿈(\n)을 붙여 출력
#   1번째 값: $(date '+%Y-%m-%d %H:%M:%S') → 현재 시각 (예: 2026-11-18 20:30:15)
#   2번째 값: $tool                        → 도구 이름
#   3번째 값: $payload                     → 입력값(JSON 한 줄)
# 줄 끝의 \ 는 "다음 줄로 명령이 이어진다"는 표시입니다.
#
# >> : 파일 끝에 덧붙이기 (> 하나면 덮어쓰기이므로 주의)
# ${CLAUDE_PROJECT_DIR:-.} : 클로드 코드가 넣어 주는 프로젝트 루트 경로 환경 변수.
#   값이 없으면 :- 뒤의 기본값 "."(현재 폴더)을 사용합니다.
#   덕분에 어느 폴더에서 실행되든 항상 "프로젝트/.claude/mcp-audit.log"에 기록됩니다.
printf '%s\t%s\t%s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$tool" "$payload" \
  >> "${CLAUDE_PROJECT_DIR:-.}/.claude/mcp-audit.log"

# 기록만 하고 정상 종료(exit 0) → 도구는 평소처럼 실행됩니다.
exit 0