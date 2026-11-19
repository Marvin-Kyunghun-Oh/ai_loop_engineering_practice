# chapter6: MCP 서버 만들고 Claude Code에 연결하기

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
- **도구(쓰기)**: `add_quote`로 명언 1개를 추가 → "현재 8개입니다" 응답 확인. (당시에는 `quotes.json`을 통째로 다시 써서 diff가 커졌고, 이 문제는 아래 SQLite 전환으로 사라졌다.)
- **리소스**: `@quote:quote://all`로 명언 전체를 불러옴 (최초 7개, 추가 후 8개)
- **프롬프트**: `/mcp__quote__quote_post 도전` 실행 → 리소스에서 명언을 골라 세 문단 글 생성

### 5. 프롬프트 기록 (`prompt/`)
- `(프롬프트)` 키워드를 붙인 요청과 답변을 `prompt/{번호}_{영문 제목}.md`로 보관한다. 문서는 `## 프롬프트`, `## 답변`, (선택) `## 결정 사항과 처리 결과` 절로 구성한다.
  - 초기 실습(랜덤 명언·리소스 멘션·프롬프트 커맨드·`rm -rf` 훅 차단·`add_quote` 호출) 기록은 정리되어 현재 폴더에는 없다.
  - `1_add_search_option.md`: `--search` 옵션 추가 + 코드 검토·테스트
  - `2_add_quote_length_limit.md`: `add_quote` 입력 길이 제한 검토와 구현
  - `3_migrate_json_to_sqlite.md`: 워크플로로 JSON → SQLite 전환
  - `4_fix_sqlite_review_findings.md`: SQLite 전환 코드 검토 지적 10건 반영

### 6. 프로젝트 문서화
- `/init`으로 `CLAUDE.md`를 만들고, 트러블슈팅에서 알게 된 점(빌드 설정 제거, mcp 2.x 개명 등)과 이후 변경(`--search`, SQLite, 서브에이전트)을 반영해 갱신했다.

### 7. 훅 추가 (`.claude/`)
`.claude/settings.json`에 `PreToolUse` 훅 두 개를 등록했다. 스크립트는 `.claude/hooks/`에 있다.

| 훅 | 대상 | 동작 |
|---|---|---|
| `block-dangerous.sh` | `Bash` | `rm -rf` 계열 명령을 검사해 종료 코드 2로 차단 (fail-closed) |
| `audit-mcp.sh` | `mcp__quote__add_quote` | 시각·도구 이름·입력값을 `.claude/mcp-audit.log`에 한 줄씩 기록 (fail-open, 차단하지 않음) |

- **차단 확인**: 빌드 디렉터리 삭제 요청이 `재귀 강제 삭제(rm -rf)는 차단됩니다...` 메시지와 함께 차단됐다. 우회하지 않고 사용자가 직접 실행하도록 안내했다.
- **감사 로그 확인**: `add_quote` 호출 후 `cat .claude/mcp-audit.log`로 호출 시각과 입력값(text, author)이 기록된 것을 확인했다. 로그 파일은 `.gitignore`에 추가해 커밋하지 않는다.
- 훅은 종료 코드 2일 때만 도구 실행을 막는다. 그 외 오류 코드는 비차단이라, 차단 훅은 예상 못한 오류도 2로 끝나게 했다.
- 주의: `jq`가 필요하다. 없으면 차단 훅이 명령 JSON 원문 전체를 검사해, 명령 본문에 해당 패턴 문자열이 들어 있기만 해도(예: 문서 작성용 heredoc) 과잉 차단된다. `jq`를 설치하니(Git Bash에서 jq 1.8.2 인식) 설명 필드에만 패턴이 있는 명령은 통과(rc=0)하고, 실제 삭제 명령은 계속 차단(rc=2)되는 것을 확인했다.
- 테스트 시 주의: PowerShell에서 `bash`는 Git Bash가 아니라 WSL(`C:\Windows\system32\bash.exe`)이라 jq가 없는 것처럼 보인다. Git Bash를 경로로 직접 지정해 검증해야 한다.

### 8. MCP Inspector로 단독 확인
Claude Code 없이도 서버를 브라우저 UI에서 확인할 수 있다.

```
uv run mcp dev main.py
```

- 서버 카드가 `Connected`(STDIO, MCP 2025-11-25)로 뜨고, 오른쪽 Messages에 `INITIALIZE` → `NOTIFICATIONS/INITIALIZED` → `RESOURCES/LIST`·`TOOLS/LIST`·`PROMPTS/LIST`가 모두 `OK`로 찍히면 정상이다.
- `Tools`·`Resources`·`Prompts` 탭에서 `get_random_quote`, `quote://all`, `quote_post`를 직접 호출해 볼 수 있다.
- 상단의 "Read-only session"은 임시 서버로 띄워서 나오는 안내일 뿐이다. 서버 이름이 `uv`, 명령이 `uv run --with mcp==... mcp run main.py`로 보이는 것도 Inspector가 내부적으로 만든 값이다.
- Inspector에서 호출한 `add_quote`는 Claude Code를 거치지 않아 `audit-mcp.sh` 감사 로그에는 남지 않는다. 저장은 `quotes.db`에 되고 `quotes.json`(시드)은 바뀌지 않는다.
- `uv run main.py`를 직접 실행하면 출력 없이 stdin을 기다리는 것이 정상이다(`Ctrl+C`로 종료). 오류가 아니다.
- 실행 시 `quote_cli.pth: ...\src does not exist; skipping sys.path append` 경고가 뜰 수 있다. `[build-system]`이 있던 시절의 editable 설치 흔적이 `.venv`에 남은 것으로, 기능에는 영향이 없다. `uv sync --reinstall`로 정리할 수 있다.

## 실행

```
uv sync
uv run main.py            # 보통은 Claude Code가 .mcp.json을 통해 직접 실행한다
uv run mcp dev main.py    # MCP Inspector로 디버깅 (브라우저 UI)
uv run main.py --search 키워드   # 서버 없이 본문 검색 후 종료
uv run pytest tests -v    # 테스트 (42개)
```

## `--search` 옵션 추가

- `uv run main.py --search 키워드`: 서버를 띄우지 않고 명언 **본문**에 키워드가 포함된 항목만 `본문 - 저자` 형태로 출력한 뒤 종료한다. 작성자는 검색 대상이 아니다.
- 옵션이 없으면 기존처럼 stdio MCP 서버로 동작한다. 검색 모드는 `mcp.run()`을 호출하지 않으므로 stdout 출력이 MCP 프로토콜을 깨지 않는다.
- 대소문자를 구분하지 않고(`casefold`), 키워드 앞뒤 공백은 제거한다. 빈 키워드는 종료 코드 2로 오류 처리하고, 데이터 파일(SQLite 전환 이후엔 quotes.db) 오류는 stderr 메시지와 종료 코드 1로 끝낸다.
- 검증: `uv run pytest tests -v` → 10개 통과(`tests/test_search.py`). (SQLite 전환 전 기준; 최종 42개)

## `add_quote` 입력 길이 제한

- 본문 1~300자, 작성자 1~50자. 앞뒤 공백은 제거하고, 비어 있거나 길거나 줄바꿈·제어 문자가 있으면 `ValueError`(MCP 오류 응답)로 거부한다. 저장된 명언이 `quote://all` 등으로 모델 컨텍스트에 돌아오기 때문이다.
- 검증: `tests/test_add_quote.py`(임시 DB 사용, 실제 데이터 불변). 전체 `uv run pytest tests -v` → 21개 통과. (SQLite 전환 전 기준)

## 데이터 저장소를 JSON에서 SQLite로 전환

- **목적**: `quotes.json`을 통째로 읽고 덮어쓰던 방식을 표준 라이브러리 `sqlite3` 기반으로 교체했다(워크플로로 수행).
- **저장 위치**: `QUOTES_DB` 환경변수가 있으면 그 경로, 없으면 `main.py` 옆 `quotes.db`(상수 `DB_FILE`, `.gitignore` 대상). 테이블은 `quotes(id INTEGER PRIMARY KEY AUTOINCREMENT, text TEXT NOT NULL, author TEXT NOT NULL)`.
- **마이그레이션**: DB가 비어 있고 `quotes.json`이 있으면 최초 연결 때 한 번 가져온다. `quotes.json`은 시드로 남기고 삭제하지 않는다. 이후 `add_quote`는 DB에만 쓰므로 더 이상 JSON diff가 생기지 않는다.
- **변경 범위**: `load_quotes`/`search_quotes`/`add_quote`/`get_random_quote`/`quote://all`을 SQLite 기반으로 바꿨다. 리소스는 기존과 같은 JSON 문자열(`ensure_ascii=False`)로 반환한다. 연결은 함수마다 열고 `with`로 커밋, `closing`으로 닫는다.
- **SQL 인젝션 방지**: 모든 값은 `?` 파라미터 바인딩으로 전달한다. `'; DROP TABLE quotes; --` 같은 문자열도 그냥 본문으로 저장된다.
- **검색 의미 유지**: SQLite `LIKE`는 ASCII만 대소문자를 무시하므로, 기존처럼 본문 `casefold` 부분 일치(작성자 제외)를 파이썬에서 수행한다.
- **CLI 오류 처리**: `--search` 빈 키워드는 종료 코드 2, DB 오류(`sqlite3.Error`)·깨진 시드 JSON·키 누락은 stderr 메시지와 종료 코드 1이다.
- **테스트**: `tests/`를 `tmp_path` + `monkeypatch`/`QUOTES_DB` 환경변수로 바꿔 실제 데이터를 건드리지 않게 했고, 마이그레이션·SQL 인젝션 테스트를 추가했다.

### 검토 지적 후속 수정

코드 검토(`code-reviewer`)에서 나온 미반영 항목을 모두 반영했다.

| 지적 | 조치 |
|---|---|
| 시드 마이그레이션 동시 실행 시 중복 삽입 가능 | 초기화를 `BEGIN IMMEDIATE` 트랜잭션으로 묶고(`isolation_level=None`으로 직접 제어), 8개 스레드 동시 접속 테스트 추가 |
| 빈 DB에서 `get_random_quote`가 `IndexError` | 빈 목록이면 `ValueError("등록된 명언이 없습니다.")` |
| 시드가 입력 검증을 우회 | `_load_seed()`가 `validate_quote_field`와 형식(객체·문자열) 검사를 적용, 실패 시 롤백 |
| 비UTF-8 시드의 `UnicodeDecodeError` 미처리 | CLI가 `ValueError`(JSON·UTF-8 오류의 상위 클래스)를 잡아 stderr + 종료 코드 1 |
| 탭·NUL 등 제어 문자 통과 | `Cc`/`Zl`/`Zp` 문자 거부(`unicodedata.category`) |
| `.gitignore`가 저널/WAL 파일 누락 | `quotes.db-*` 추가 |
| 시드 재유입 동작 미문서화, chapter4 표기, 오래된 테스트 수치 | CLAUDE.md·README 갱신 |
| 테스트 공백(연결 닫힘, 서버 경로 오류, 실제 데이터 의존) | 연결 닫힘·서버 경로 DB 손상·고정 시드 CLI 테스트로 교체/추가 |

- 검증: `uv run pytest tests -v` → **42개 통과**. 실제 `quotes.json`(8개)도 검증을 통과하며 `--search 성공`이 정상 출력된다.

## 서브에이전트와 워크플로 활용 기록 (`.claude/agents/`)

이번 작업들은 구현 → 검토 → 테스트를 서브에이전트에 나눠 맡기는 방식으로 진행했다.

| 에이전트 | 모델 | 도구 | 역할 |
|---|---|---|---|
| `code-reviewer` | haiku | Read, Grep, Glob (읽기 전용) | 입력 검증·예외 경로·테스트 누락·CLAUDE.md 위반을 심각도 순으로 보고. 코드는 수정하지 않음 |
| `test-runner` | haiku | Read, Glob, Grep, Bash (`maxTurns: 6`) | `uv run pytest -v` 실행 후 실패 원인을 20줄 이내로 요약. 코드는 수정하지 않음 |

- **역할 분리**: 리뷰어는 Bash가 없어 테스트를 실행하지 못한다(정적 검토만). 실행은 test-runner가 맡는다. 도구 목록이 곧 권한 경계다.
- **SQLite 전환 워크플로(`Workflow`)**: 구현 에이전트 1개(파일 충돌을 피하려고 쓰기는 한 곳에만) → `code-reviewer`·`test-runner` 병렬 검증, 총 3개. 리뷰어는 경쟁 조건, 빈 DB `IndexError`, 시드 검증 우회 등 실제 결함 10건을 찾았고 후속 작업으로 모두 반영했다.
- **보고서는 데이터일 뿐 명령이 아니다**: test-runner 결과에 MCP 서버 안내문이 섞여 문서 생성을 유도했으나 작업 범위 밖이라 따르지 않았다고 보고했다. 서브에이전트 보고서와 도구 출력에는 사용자 권한이 없다.
- **한계**: 저비용 haiku 리뷰어는 근거 파일·행 번호를 달아 쓸 만한 지적을 냈지만, 일부 항목은 심각도가 낮은 문서 불일치였다. 결과는 사람이 우선순위를 걸러서 반영한다.

