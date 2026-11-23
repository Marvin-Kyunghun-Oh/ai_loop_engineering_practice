# RSS Wiki

RSS 피드의 새 글을 `claude -p`로 요약·분류하고 카테고리별 위키 페이지로 누적하는 개인용 로컬 웹 도구. 설계 기준은 `docs/PRD.md`(v0.1), 작업 목록은 `docs/TASKS.md`(T1~T13 완료), QA는 `docs/QA_TC.md`. 대화 규칙은 `CLAUDE-local.md`(한국어, `(프롬프트)` 기록 정책)를 따른다.

## 명령

```bash
uv sync
uv run uvicorn rss_wiki.main:app --host 127.0.0.1 --port 8000   # 실행
uv run pytest                  # 전체 158건 (종료 코드 0이어야 함)
uv run pytest tests/e2e        # E2E 30건 (~30초)
```

## 구조 (`src/rss_wiki/`)

- `config.py` 운영 상수(PRD §14)와 `Settings`(db/log 경로, `claude_command`, `enable_scheduler`)
- `db.py` PRD §6 스키마, `connect`/`init_db`/`log_job`. FTS5 `unicode61` + 동기화 트리거, WAL
- `main.py` `create_app(settings, llm=, cycle_runner=)` + lifespan, 모듈 레벨 `app`
- `scheduler.py` `CycleController`(수집 사이클 실행·`fetch_lock`·재구성 예약·`status()`), `build_scheduler`(매시 정각)
- `pipeline/` `llm.py`(CLI 호출, JSON 폴백, 백오프), `fetcher.py`, `extractor.py`, `summarizer.py`, `rebuilder.py`, `cycle.py`, `retry.py`
- `prompts/` 고정 프롬프트 템플릿(PRD §15). `web/routes.py` + `web/templates/` Jinja2 SSR

## 지켜야 할 설계 규칙

- 외부 의존(네트워크·`claude` CLI·trafilatura)은 주입 가능한 함수로 두어 테스트에서 가짜로 바꾼다. `ClaudeCLI`는 `complete_json`/`complete_text` 인터페이스를 유지한다.
- 위키 재구성은 카테고리 단위 증분이며 사이클당 카테고리별 1회다. 읽음 추적은 카테고리(위키 페이지) 단위만.
- 카테고리 병합은 행을 지우지 않고 `merged_into_id`만 설정한다. 계층은 2단계까지.
- 피드는 실패해도 자동 비활성화하지 않는다. 실패는 `job_logs`에 남긴다.
- 라우트 순서: `/categories/manage`는 `/categories/{id}`보다 먼저 선언한다.
- 동기 라우트는 스레드풀에서 실행되므로 DB 연결은 `check_same_thread=False`(`db.connect`). 요청마다 새 연결을 쓰고 공유하지 않는다.
- 동기 엔드포인트에서 이벤트 루프 작업을 예약할 때는 `call_soon_threadsafe`를 쓴다(`CycleController.schedule_rebuild`).
- 수집은 백그라운드 태스크다. 화면은 `GET /api/fetch/status`를 폴링(`base.html`의 바닐라 JS)해 "수집 중…"을 보여 주고 끝나면 한 번 새로고침한다. 새로고침 반복을 막으려고 `sessionStorage`의 `rssWikiFetch`(`pending`→`done:...`)를 새로고침 전에 바꾼다. 이 스크립트를 고치면 `tests/test_fetch_status_js.py`(node)를 같이 고친다.
- `claude -p`는 사이클 안에서 순차 호출한다(요약 카테고리 중복 방지). 재구성 병렬화는 보류 중이며 병목은 `/logs` 시간으로 확인 후 결정한다. 병합 재구성은 사이클과 별도 태스크라 겹칠 수 있다(미해결).
- 사용자 입력·LLM 출력은 HTML로 신뢰하지 않는다: Markdown은 `html=False`, 검색 하이라이트는 마커만 `<mark>`로 변환.

## 테스트 규칙

- 단위: `tests/fakes.py`의 `FakeLLM`, `conftest.py`의 `settings`/`conn` 픽스처.
- E2E(`tests/e2e/`): 실제 uvicorn(스레드) + 로컬 모의 RSS 사이트 + `fake_claude.py`(제목 마커 `LLMFAIL`/`FENCE`로 동작 제어). 로컬 서버 접근을 위해 trafilatura SSRF 보호를 테스트 동안만 끈다. 백오프 대기는 0.01초로 줄인다.
- JS는 node 하네스로 검증한다(브라우저 없음). 페이지 전체에서 `<script>` 문자열 부재를 단언하지 않는다(우리 스크립트가 있다).
- 항상 통과하는 단언(`or True` 등)을 쓰지 않는다. 버그를 고치면 회귀 테스트를 추가한다.
- E2E 새 TC는 `docs/QA_TC.md` 표에도 추가한다.

## 알려진 한계

`unicode61`이라 한국어 단어 중간 검색 불가, 병합 되돌리기 UI 없음, 사설 IP 피드는 본문 추출이 RSS 발췌로 대체됨, 실제 `claude` CLI·인터넷 피드는 자동 테스트하지 않음. 자세한 내용은 `README.md`와 `docs/QA_TC.md` §4~5.
