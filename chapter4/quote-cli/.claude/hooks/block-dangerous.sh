#!/bin/bash
# =============================================================================
# 위험 명령 차단 훅 (.claude/hooks/block-dangerous.sh)
#
# Claude가 Bash 도구로 셸 명령을 실행하기 "직전"(PreToolUse)에 호출됩니다.
# 실행될 명령을 검사해서 rm -rf 계열이면 실행을 막고, 아니면 그대로 통과시킵니다.
#
# 설계 원칙: fail-closed (실패하면 막는다)
#   Claude Code 훅은 종료 코드 2일 때만 도구 실행을 막습니다.
#   0도 2도 아닌 코드(예: jq 없음 -> 127)는 "비차단 오류"라서 명령이 그대로 실행됩니다.
#   그래서 이 스크립트는 예상 못한 오류가 나면 무조건 exit 2로 끝나게 합니다.
#
# 필요 도구: 없음 (jq가 있으면 정확한 추출에 쓰고, 없으면 원본 JSON 문자열을 검사)
# =============================================================================

# 안전 옵션
#   -e          : 명령 하나라도 실패하면 스크립트를 즉시 종료
#   -u          : 정의되지 않은 변수를 쓰면 오류로 처리 (오타 방지)
#   -o pipefail : 파이프(|)로 이어진 명령 중 하나라도 실패하면 전체를 실패로 처리
set -euo pipefail

# 예상 못한 오류가 나면(ERR) 통과시키지 않고 차단(exit 2)한다. (fail-closed 핵심)
# 자바로 치면 catch (Exception e) { throw new BlockedException(); } 와 같다.
trap 'echo "block-dangerous.sh: 훅 내부 오류로 안전을 위해 차단합니다." >&2; exit 2' ERR

# 1. 표준 입력으로 들어온 JSON 읽기
# 들어오는 JSON 예:
#   {"tool_name": "Bash", "tool_input": {"command": "rm -rf build"}, ...}
input="$(cat)"

# 2. 검사 대상 문자열 결정
# jq가 있으면 tool_input.command만 정확히 꺼내고,
# 없으면 JSON 원문 전체를 검사한다. (description 등에 rm -rf가 들어 있어도 막히는
# 과잉 차단이 생길 수 있지만, 놓치는 것보다 안전하다.)
if command -v jq >/dev/null 2>&1; then
  target="$(printf '%s' "$input" | jq -r '.tool_input.command // ""')"
else
  target="$input"
fi

# 3. rm -rf 계열(옵션 순서 변형 포함)인지 검사
# 정규식 풀이:
#   rm[[:space:]]+              : "rm" 뒤에 공백이 1개 이상
#   -[a-zA-Z]*r[a-zA-Z]*f       : -로 시작하고 r 다음에 f가 오는 옵션 (-rf, -rvf, -Rrf 등)
#   |                           : 또는
#   -[a-zA-Z]*f[a-zA-Z]*r       : f 다음에 r이 오는 옵션 (-fr, -fvr 등)
# grep 종료 코드: 0=일치, 1=불일치, 그 외(2, 127 등)=grep 자체 오류.
# if 조건 안에서 grep을 쓰면 오류도 "불일치"로 취급되어 통과해 버리므로(fail-open),
# 종료 코드를 직접 받아 0/1이 아니면 차단한다. ( || rc=$? 는 set -e / ERR trap을 피하는 관용구 )
rc=0
printf '%s' "$target" | grep -Eq 'rm[[:space:]]+(-[a-zA-Z]*r[a-zA-Z]*f|-[a-zA-Z]*f[a-zA-Z]*r)' || rc=$?
if [ "$rc" -gt 1 ]; then
  echo "block-dangerous.sh: 패턴 검사(grep) 오류로 안전을 위해 차단합니다. (rc=$rc)" >&2
  exit 2
fi
if [ "$rc" -eq 0 ]; then
  # 4. 차단: stderr에 이유를 쓰고 exit 2. (jq 없이도 동작, stderr 내용은 Claude에게 전달됨)
  echo "재귀 강제 삭제(rm -rf)는 차단됩니다. 필요하면 대상 경로를 명시해 직접 실행해주세요." >&2
  exit 2
fi

# 5. 패턴이 없으면 통과 (exit 0이면 도구는 평소처럼 실행됨)
exit 0
