# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 개요

`chapter4/quote-cli`는 MCP(Model Context Protocol)의 세 가지 기능(도구·리소스·프롬프트)을 모두 시연하는 파이썬 MCP 서버다. 상위 저장소(`ai_loop_engineering_practice`)는 챕터별 실습 모음이며, 챕터마다 독립된 프로젝트다. 코드 주석과 문서는 한국어로 작성한다(자바 개발자 독자를 대상으로 한 설명 주석 스타일).

## 명령어

패키지 관리는 `uv`를 사용한다. (Python 3.15, `.python-version` 참고)

```
uv sync           # 의존성 설치 (mcp[cli])
uv run main.py    # 서버를 stdio 모드로 직접 실행
uv run mcp dev main.py   # MCP Inspector로 디버깅 (mcp[cli] 제공)
uv run main.py --search 키워드   # 서버 없이 본문에 키워드가 포함된 명언만 출력 후 종료
uv run pytest tests -v    # 테스트 실행 (tests/test_search.py)
```

빌드·린트 설정은 없고, 테스트는 `tests/`의 pytest를 쓴다. `pyproject.toml`에 `[build-system]`을 두지 않은 것은 의도다. 두면 `uv run`이 존재하지 않는 `src/quote_cli`를 빌드하려다 실패해 MCP 연결이 `CONNECTION_CLOSED`로 끊긴다.

서버 기동 확인은 stdin으로 JSON-RPC `initialize` 요청을 보내 응답이 오는지 보면 된다.

## 아키텍처

- 모든 로직이 `main.py` 한 파일에 있다. `MCPServer("quote")` 인스턴스(`mcp`)에 데코레이터로 기능을 등록하는 구조다.
  - mcp 2.x 기준이다. 1.x의 `from mcp.server.fastmcp import FastMCP`는 2.x에서 `ModuleNotFoundError`가 나며, `from mcp.server.mcpserver import MCPServer`로 대체됐다(데코레이터 API는 동일).
  - `@mcp.tool()`: `get_random_quote`(읽기), `add_quote`(쓰기 — `quotes.json`을 덮어씀)
  - `@mcp.resource("quote://all")`: `quotes.json` 원문 반환
  - `@mcp.prompt()`: `quote_post(topic)` — Claude에게 `quote://all`에서 명언을 골라 글을 쓰도록 지시
- 함수 이름·독스트링·타입 힌트가 각각 MCP의 이름·설명·입력 스키마가 되므로, 시그니처를 바꾸면 노출되는 인터페이스가 바뀐다.
- `main.py --search 키워드`는 서버 모드와 분기된다. `mcp.run()`을 호출하지 않고 일치 항목을 stdout에 출력한 뒤 종료하므로, 아래 stdout 금지 규칙의 예외다(데이터 파일 오류는 stderr + 종료 코드 1).
- 전송은 stdio다. **stdout에 `print` 등으로 출력하면 MCP 프로토콜이 깨진다.** 로그는 stderr로 보낸다.
- 데이터는 `main.py`와 같은 폴더의 `quotes.json`(`QUOTES_FILE`)이며, DB 없이 파일을 매번 읽고 쓴다. `add_quote`가 파일을 다시 쓰면 들여쓰기 형식으로 바뀌고 끝 개행이 없어지므로, 호출 후 `quotes.json` diff가 크게 보일 수 있다.
- `.mcp.json`이 Claude Code에 `quote` 서버를 `uv run main.py`로 등록한다. 코드 변경 후에는 `/mcp`에서 서버를 재연결해야 반영된다.
- `.claude/settings.json`에 `PreToolUse` 훅이 등록돼 있다(스크립트는 `.claude/hooks/`).
  - `block-dangerous.sh`(`Bash`): `rm -rf` 계열을 차단한다(exit 2). 삭제가 필요하면 우회하지 말고 사용자가 `! ` 접두어로 직접 실행하게 안내한다. `jq`가 필요하다(Git Bash에서 인식돼야 함). 없으면 명령 JSON 전체를 검사해 heredoc 본문에 해당 문자열이 있어도 과잉 차단된다. 훅 테스트는 PowerShell의 `bash`(WSL)가 아니라 Git Bash를 직접 지정해 실행한다.
  - `audit-mcp.sh`(`mcp__quote__add_quote`): 호출 내역을 `.claude/mcp-audit.log`에 기록만 한다. 이 로그는 `.gitignore` 대상이다.
  - `.claude/settings.local.json`은 개인 설정이라 커밋하지 않는다.

## 알려진 불일치 (수정 시 주의)

- `requires-python = ">=3.15"`는 매우 최신 버전을 요구한다. 환경이 맞지 않으면 먼저 이 값을 확인한다.

## 문서

- `README.md`는 앱 기능 설명이 아니라 **MCP 실습 작업 기록**(수행한 작업, 트러블슈팅, 동작 확인) 관점으로 쓴다. 새 작업을 하면 해당 관점으로 이어서 갱신한다.

## 개발 규칙

- 모든 답변 및 문서 작성은 한국어가 기준이다.
