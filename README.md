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

### 5. quote-cli 확장 (서브에이전트 + 워크플로)
> `chapter6/quote-cli`
- 4번의 MCP 서버에 `--search` 옵션, `add_quote` 입력 검증, JSON → SQLite 저장소 전환을 더하며 **서브에이전트 중심**으로 작업

#### 서브에이전트에서 배운 것
- **정의**: `.claude/agents/*.md`의 frontmatter(`name`, `description`, `tools`, `model`, `maxTurns`)로 만든다. `description`이 "언제 위임할지"의 기준이 된다.
- **역할 분리 = 도구 분리**: `code-reviewer`는 읽기 전용(Read/Grep/Glob), `test-runner`는 Bash로 pytest만 실행. 둘 다 코드를 수정하지 않고 보고만 해서, 수정은 메인 세션이 책임진다.
- **컨텍스트 격리**: 서브에이전트는 자기 컨텍스트에서 일하고 요약만 돌려준다. 메인 컨텍스트가 파일 덤프로 오염되지 않는다.
- **저비용 모델 배치**: 검토·테스트 실행처럼 범위가 좁은 일은 haiku로도 충분했다. 근거 파일·행 번호를 요구하면 쓸 만한 지적이 나왔다(경쟁 조건, 시드 검증 우회 등).
- **보고서는 데이터, 명령이 아니다**: 서브에이전트 결과에 섞인 지시문(문서 생성 유도 등)은 따르지 않는다. 사용자 권한은 사용자 메시지에서만 나온다.
- **한계**: 리뷰어는 심각도가 낮은 지적도 섞어서 내므로 사람이 우선순위를 가려야 한다. 리뷰어는 테스트를 실행할 수 없어 실행은 다른 에이전트가 필요하다.

#### 워크플로(`Workflow`)로 오케스트레이션
- 구현 1개(쓰기는 한 에이전트에게만 맡겨 충돌 방지) → 검토·테스트 2개를 `parallel`로 동시에 → 결과를 보고 후속 수정. 검증 단계가 서로 독립이라 병렬이 적합했다.
- 결정적인 흐름(순서·병렬)은 스크립트가 맡고, 판단은 에이전트가 맡는다. 에이전트 수가 늘수록 비용도 늘기 때문에 3개로 제한했다.

#### 개발 흐름 요약
| 작업 | 방식 |
|---|---|
| `--search` 옵션 | 구현 → `code-reviewer` 검토 → `test-runner` 검증 |
| `add_quote` 길이 제한 | 리뷰어가 필요성 검토 → 제안대로 구현 |
| JSON → SQLite | 워크플로(구현 1 + 검증 2) → 지적 10건 후속 수정, 최종 테스트 42개 통과 |
| 기록 | `(프롬프트)` 정책으로 `prompt/`에 프롬프트·답변·결정 사항 보관 |

