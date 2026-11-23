# TASKS

`docs/PRD.md`(v0.1) 기반 구현 작업 목록. 한 번에 TASK 하나만 구현하고, 끝나면 `[x]`로 바꾼다.
막히면 해당 항목에 `BLOCKED`를 적고 다음으로 넘어간다. 외부 의존(네트워크·`claude` CLI·trafilatura)은 주입 가능한 함수로 만들어 테스트에서는 가짜로 대체한다. 디렉토리 구조는 PRD §14.1을 따른다.

- [x] T1. 스캐폴딩: `pyproject.toml`(uv, Python 3.11+), `src/rss_wiki/` 패키지, `config.py`(PRD §14 운영 상수), `.gitignore`(`data/`)
- [x] T2. `db.py`: PRD §6 스키마 그대로(`CREATE TABLE IF NOT EXISTS`, FTS5 + 동기화 트리거), 연결 헬퍼, 앱 시작 시 초기화
- [x] T3. `pipeline/llm.py`: `claude -p --output-format text` subprocess(stdin 전달, 120초 타임아웃), JSON 파싱 폴백 체인 4단계, 지수 백오프(3회, 2→4→8초)
- [x] T4. `pipeline/fetcher.py`·`extractor.py`: feedparser 래퍼(30초 타임아웃, 병렬 5), trafilatura 래퍼(20초 타임아웃, 실패 시 RSS summary 대체)
- [x] T5. `prompts/article_summarize.txt` + `pipeline/summarizer.py`: 기존 카테고리 주입, 카테고리 재사용·신규 생성, 글 저장, 실패 시 `status='failed'` 기록
- [x] T6. `prompts/wiki_rebuild.txt` + `pipeline/rebuilder.py`: 증분 재구성, 입력 100,000자 가드(10→5→3→0), 최초 빌드 최신 20개, `has_unread_updates=1`
- [x] T7. 수집 사이클(`pipeline/cycle.py`): 활성 피드 → 새 글 판별 → 추출·요약(순차) → 영향받은 카테고리 사이클당 1회 재구성, `fetch_lock`, `job_logs` 기록, 자동 비활성화 없음
- [x] T8. `scheduler.py` + `main.py`: APScheduler 매시 정각 등록, FastAPI 앱·lifespan, `POST /api/fetch`(실행 중이면 409)
- [x] T9. 피드 관리 화면: `/feeds`, `/feeds/add`(중복 409), `/feeds/{id}/toggle`, `/feeds/{id}/delete`
- [x] T10. 카테고리 화면: `/`(최상위만, 안읽음 상단 정렬, 하위 드릴다운), `/categories/{id}`(Markdown 렌더, 방문 시 읽음 처리, 원문 링크)
- [x] T11. 카테고리 편집: `/categories/manage`, rename, merge(글 이동·소스 위키 삭제·대상 재구성 트리거), parent(2단계 한정)
- [x] T12. `/search`(FTS5 MATCH, 제목/요약/본문 하이라이트)와 `/logs`(`job_logs` 최근 200건)
- [x] T13. `README.md`(실행 방법), 전체 테스트 점검
