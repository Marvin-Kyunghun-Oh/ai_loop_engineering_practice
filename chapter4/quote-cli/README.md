# chapter4: MCP 서버 만들고 Claude Code에 연결하기

> 명언 MCP 서버(`quote`)를 직접 만들어 Claude Code에 연결하고, MCP의 세 가지 기능(도구·리소스·프롬프트)을 하나씩 써 본 실습 기록.

## 수행한 작업

### 1. MCP 서버 작성 (`main.py`)
- 파이썬 MCP SDK(`mcp[cli]`)로 서버를 만들고, 한 서버에서 세 가지 기능을 모두 노출했다.

| MCP 기능 | 이름 | Claude Code에서 쓰는 방법 |
|---|---|---|
| 도구(Tool) | `get_random_quote`, `add_quote` | 대화 중 Claude가 필요할 때 호출 |
| 리소스(Resource) | `quote://all` | `@quote:quote://all` 멘션으로 대화에 불러오기 |
| 프롬프트(Prompt) | `quote_post` | `/mcp__quote__quote_post <주제>` 슬래시 커맨드 |

- 함수 이름·독스트링·타입 힌트가 각각 도구 이름·설명·입력 스키마가 된다는 점을 확인했다.
- 전송 방식은 stdio라 별도의 포트 설정이 필요 없다.

### 2. Claude Code에 서버 등록 (`.mcp.json`)
- 프로젝트 루트의 `.mcp.json`에 `uv run main.py`를 stdio 서버로 등록했다.
- `/mcp`로 연결 상태를 확인하고, 코드를 고친 뒤에는 `/mcp`에서 재연결해 반영했다.

### 3. 연결 실패 트러블슈팅
처음에는 `/mcp`에서 `quote (CONNECTION_CLOSED)`로 연결에 실패했다. `uv run main.py`를 터미널에서 직접 실행해 원인을 하나씩 찾았다.

| 순서 | 증상 | 원인 | 조치 |
|---|---|---|---|
| 1 | `Failed to build quote-cli ... Expected a Python module at: src\quote_cli\__init__.py` | `uv init` 템플릿의 `[build-system]`이 남아 있어, `uv run`이 존재하지 않는 패키지를 먼저 빌드하려다 실패 | `pyproject.toml`에서 `[build-system]`, `[project.scripts]` 삭제 |
| 2 | `No module named 'mcp.server.fastmcp'` | mcp 2.x에서 `FastMCP`가 `MCPServer`로 개명 | `from mcp.server.mcpserver import MCPServer`로 변경 (데코레이터 API는 동일) |
| 3 | 도구 호출 시 `TypeError` | 코드는 `{text, author}` 객체를 기대하는데 `quotes.json`은 `"명언 - 저자"` 문자열 배열 | `quotes.json`을 `{text, author}` 객체 배열로 변환 |

- 팁: 서버가 뜨는지는 stdin으로 JSON-RPC `initialize` 요청을 보내 응답을 확인하면 Claude Code 없이도 점검할 수 있다.

### 4. 동작 확인
- **도구**: `get_random_quote` 호출 → 무작위 명언 반환 확인
- **도구(쓰기)**: `add_quote`로 명언 1개를 추가 → "현재 8개입니다" 응답, `quotes.json`에 반영 확인. 이때 파일이 들여쓰기 형식의 JSON으로 다시 쓰인다(기존 한 줄 형식과 달라 diff가 커짐).
- **리소스**: `@quote:quote://all`로 명언 전체를 불러옴 (최초 7개, 추가 후 8개)
- **프롬프트**: `/mcp__quote__quote_post 도전` 실행 → 리소스에서 명언을 골라 세 문단 글 생성

### 5. 프롬프트 기록 (`prompt/`)
- `(프롬프트)` 키워드를 붙인 요청과 답변을 `prompt/{번호}_{영문 제목}.md`로 보관했다.
  - `1_print_random_quote.md`: 도구 호출
  - `2_read_quote_resource.md`: 리소스 멘션
  - `3_write_challenge_quote_post.md`: 프롬프트 커맨드
  - `4_delete_build_directory.md`: 재귀 강제 삭제 요청이 훅에 차단된 기록
  - `5_add_quote.md`: `add_quote` 도구로 명언 추가

### 6. 프로젝트 문서화
- `/init`으로 `CLAUDE.md`를 만들고, 위 트러블슈팅에서 알게 된 점(빌드 설정 제거, mcp 2.x 개명 등)을 반영해 갱신했다.

### 7. 훅 추가 (`.claude/`)
`.claude/settings.json`에 `PreToolUse` 훅 두 개를 등록했다. 스크립트는 `.claude/hooks/`에 있다.

| 훅 | 대상 | 동작 |
|---|---|---|
| `block-dangerous.sh` | `Bash` | `rm -rf` 계열 명령을 검사해 종료 코드 2로 차단 (fail-closed) |
| `audit-mcp.sh` | `mcp__quote__add_quote` | 시각·도구 이름·입력값을 `.claude/mcp-audit.log`에 한 줄씩 기록 (fail-open, 차단하지 않음) |

- **차단 확인**: 빌드 디렉터리 삭제 요청이 `재귀 강제 삭제(rm -rf)는 차단됩니다...` 메시지와 함께 차단됐다. 우회하지 않고 사용자가 직접 실행하도록 안내했다.
- **감사 로그 확인**: `add_quote` 호출 후 `cat .claude/mcp-audit.log`로 호출 시각과 입력값(text, author)이 기록된 것을 확인했다. 로그 파일은 `.gitignore`에 추가해 커밋하지 않는다.
- 훅은 종료 코드 2일 때만 도구 실행을 막는다. 그 외 오류 코드는 비차단이라, 차단 훅은 예상 못한 오류도 2로 끝나게 했다.
- 주의: `jq`가 없으면 차단 훅이 명령 JSON 원문 전체를 검사하므로, 명령 본문에 해당 패턴 문자열이 들어 있기만 해도(예: 문서 작성용 heredoc) 차단된다. 그런 작업은 Edit 같은 파일 도구로 한다.

## 실행

```
uv sync
uv run main.py   # 보통은 Claude Code가 .mcp.json을 통해 직접 실행한다
```
