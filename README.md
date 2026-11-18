# 요즘 AI 루프 엔지니어링 ... 책의 실습 로그
> 요즘 AI 루프 엔지니어링, 클로드 코드, 스킬, MCP, 훅, 컨텍스트, 하네스, 리뷰, 오케스트레이션, LLMOps, Langfuse 

### 1. quote-cli
> `chapter1/quote-cli`
- 명언을 한 줄 출력해주는 자바 애플리케이션

#### `/code-review`
- 코드 품질, 누락된 예외, 테스트 커버리지, 문서 일관성의 관점에서 품질을 피드백

### 2. todo-cli
> `chapter2/todo-cli`
- CLI로 할 일을 등록하고 옮기는 자바 애플리케이션

#### `에이전트 루프`
  - `[컨텍스트 수집 -> 작업수행 -> 결과 검증]`을 반복.
  
#### `프롬프트 캐싱`
```
claude -p "todos.json 스키마를 한 줄로 설명하시오" --output-format json
```

### 3. skills-example
> `chapter3/skills-example/task-keeper`

#### 스킬 생성하여 워크플로우 반자동화
1. create-issue : 고쳐야 할 버그나 추가 작업을 이슈로 생성 
2. git-commit : 이슈를 수정하는 과정에서 발생한 코드 변경을 작은 단위로 저장
3. create-pr : 내 변경을 원본과 합치기 전, 검토를 요청하는 단계
4. review-pr : (검토를 요청받은 사람이) 변경에 대한 피드백을 남기는 단계.
5. apply-pr-review : 피드백을 처리하는 단계 (코드 수정, 기록 추가)
- commit-and-pr : `git-commit` + `create-pr`

### 4. quote-cli (MCP 서버 + 훅)
> `chapter4/quote-cli`
- 명언을 제공하는 파이썬 MCP 서버를 만들어 Claude Code에 연결

#### MCP로 등록
- 한 서버(`quote`)에서 MCP의 세 가지 기능을 모두 노출

| MCP 기능 | 이름 | 사용 방법 |
|---|---|---|
| 도구(Tool) | `get_random_quote`, `add_quote` | 대화 중 Claude가 필요할 때 호출 |
| 리소스(Resource) | `quote://all` | `@quote:quote://all` 멘션 |
| 프롬프트(Prompt) | `quote_post` | `/mcp__quote__quote_post <주제>` |

- `.mcp.json`에 `uv run main.py`를 stdio 서버로 등록하고, `/mcp`로 연결 상태 확인
- 연결 실패(`CONNECTION_CLOSED`) 원인: `[build-system]` 잔존, mcp 2.x의 `FastMCP` → `MCPServer` 개명, 데이터 형식 불일치

#### HOOK
- `.claude/settings.json`에 `PreToolUse` 훅 2개 등록 (스크립트: `.claude/hooks/`)

| 훅 | 대상 | 동작 |
|---|---|---|
| `block-dangerous.sh` | `Bash` | 재귀 강제 삭제(`rm -rf`) 명령을 종료 코드 2로 차단 |
| `audit-mcp.sh` | `add_quote` | 호출 시각·입력값을 `.claude/mcp-audit.log`에 기록 (차단하지 않음) |

- 훅은 종료 코드 2일 때만 실행을 막는다. 그래서 차단 훅은 오류가 나도 2로 끝나게(fail-closed), 감사 훅은 오류가 나도 0으로 끝나게(fail-open) 설계
- `jq`가 있어야 명령 필드만 정확히 검사한다. 없으면 JSON 전체를 검사해 과잉 차단됨