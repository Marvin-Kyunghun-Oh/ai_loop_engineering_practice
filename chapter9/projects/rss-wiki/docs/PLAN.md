# PLAN: rss-wiki

- 기준 문서: docs/PRD.md (초안 v1)
- 최종 갱신: 2026-11-23 (planner, 사이클 11)

## 현재 상태 (2026-11-23, 사이클 11 시작 시점)

- 사이클 10: T3s(검색 테스트 보강·`search_articles` limit 검증·`set_article_tags` str 거부) PASS 12/12, 전체 133 passed, acceptance 변이 4종 + 추가 변이 3종 모두 잡힘.
- T3s REVIEW 메모: T3b 검증을 DB 접근·조기 반환보다 앞에 두고 경계값 `limit=0` 테스트 포함 → T3b acceptance에 반영. 따옴표 든 글의 실제 검색 확인 → T3b 작은 보강으로 배정. `set_article_tags`의 `bytes`·비문자열 원소(`b"ab"`→`97`,`98`, `3`→`'3'`) → M3 `tags.py` 정규화에서 `str`이 아닌 원소를 거부하기로 함(아래 M3).
- 아래는 사이클 10 시점 기록.

- 사이클 9: T3a(태그 교체 저장·FTS 접두사 검색·예외 문서화) PASS 11/12, 전체 124 passed, 변이 15종 중 12종 잡힘.
- T3a REVIEW 메모: 따옴표 이스케이프·영숫자 필터·bm25 정렬·리터럴 `OR` 검색 테스트 부재, `search_articles(limit<1)` 무제한, `set_article_tags`에 `str` 전달 시 글자 단위 태그 → 모두 T3s(T3b 앞)에 배정. 입력 검증은 아래 자체 결정으로 정함. 피드 삭제 뒤 남는 `tags` 고아 행은 `list_tag_names`가 제외하므로 결함 아님, M6에서 필요 시 정리.
- 아래는 사이클 9 시점 기록.

- 사이클 8: T3r(`repo.py` 오류 표면 정리, 함수별 커밋 테스트) PASS 11/12, 전체 106 passed, 변이 11종 모두 잡힘.
- T3r REVIEW 메모: 새 예외(`ArticleNotFoundError`/`FeedNotFoundError`/`ValueError`)가 독스트링에 없음, `with conn:`의 호출자 트랜잭션 커밋·롤백 성질 미문서화, `test_missing_article_raises`에 `in_transaction`·`LookupError` 상속 확인 없음 → 모두 T3a 앞부분(예외 문서화)에 배정. 트랜잭션 경계는 아래 자체 결정("repo 쓰기 함수는 열린 트랜잭션에서 호출하지 않는다")으로 정함.
- 아래는 사이클 8 시점 기록.

- 사이클 7: T3(`repo.py` 피드 CRUD·글 신규 저장·상태 전이) PASS 9/12, 전체 94 passed. T2b 회귀도 evaluator가 확인함.
- T3 REVIEW 메모: `add_feed`가 URL `NOT NULL` 위반을 `DuplicateFeedError`로 오분류, `mark_failed`가 없는 id에 `TypeError`, `set_status`/`mark_done`/`set_feed_enabled`가 없는 id를 조용히 무시, 커밋 테스트가 `add_feed` 커밋 누락을 못 잡음(변이 확인) → T3r. 호출자 트랜잭션까지 커밋하는 `with conn:` 동작은 결함 아님, 여러 repo 호출을 한 트랜잭션으로 묶을 필요는 M3/M5 파이프라인 설계 때 판단.
- 아래는 사이클 7 시점 기록.

- 사이클 6: T2b(`migrate` 열린 트랜잭션 거부, `except BaseException`, 테스트 3건 보강) generator 완료(전체 80 passed 보고). 코드로 반영을 확인했으나 REVIEW.md는 아직 T2a 평가 → T2b는 다음 evaluator가 T3과 함께 회귀 확인. T2a REVIEW 메모는 T2b(코드)와 M6(WAL 백업 안내)로 모두 배정됨.
- 아래는 사이클 6 시점 기록(테스트 수 등은 T2b 이후 80개로 갱신).

- `pyproject.toml`: 런타임 의존성 없음, dev 의존성 pytest, `testpaths = ["tests"]`, 엔트리포인트 `rss-wiki = "rss_wiki:main"`, `requires-python >=3.15`
- `src/rss_wiki/__init__.py`: `main()`이 인사말만 출력
- `src/rss_wiki/config.py`: `Settings`/`load_settings` 구현, 오류 메시지에 설정 파일 경로 포함, port 1~65535, UTF-8(BOM 없음) 강제와 CP949/UTF-16 오류 포장, 경로 `~` 확장 (T1 PASS 10/12, T1a PASS 11/12, T1b PASS 11/12)
- `src/rss_wiki/db.py`: `connect`(WAL, `busy_timeout=5000`)/`migrate`(user_version v1, 실패 시 롤백, 미래 버전 거부)/`reset_interrupted`, 5개 테이블 + `articles_fts`(unicode61) + 동기화 트리거 (T2 PASS 9/12, T2a PASS 11/12)
- 테스트: 전체 79개 통과(config 55, db 24)
- T2a REVIEW 메모: `migrate`가 `executescript` 때문에 호출자의 열린 트랜잭션을 암묵 커밋함, `except Exception`이라 `KeyboardInterrupt` 시 롤백 없음, 테스트 사소한 공백 2건 → T2b. WAL `-wal`/`-shm` 파일과 백업 안내 → M6 README 범위.
- T1b REVIEW 메모(작은 보강, 별도 항목 불필요): 공백만 있는 경로(`wiki_dir = " "`) 허용, POSIX `~없는사용자`의 `RuntimeError` 미포장, README 부재 → M6 T-README 항목에서 함께 처리(아래 M6 범위)
- T2 REVIEW 메모: `migrate` 실패 시 롤백 없음, 미래 버전 DB 무경고, WAL/`busy_timeout` 미설정, 테스트 공백(FTS 연쇄 삭제·`source` CHECK·`updated_at`·제목 FTS) → T2a. 한국어 FTS 검색(조사 붙은 단어) → 아래 자체 결정(접두사 검색)으로 정하고 검색 함수 항목(T3a)에서 구현. `updated_at` 갱신 주체 → `repo.py` 상태 전이 함수(T3).
- `README.md` 비어 있음
- 결정 U1~U10 합의 완료, PRD 본문에 (자체 결정: 합의)로 반영

→ M1 진행 중. 설정 로더(T1·T1a·T1b)·스키마(T2·T2a·T2b)·`repo.py` 기본(T3·T3r) 완료. 다음은 예외 문서화 + 태그·FTS 접두사 검색(T3a) → 처리 대상 조회·실행 이력(T3b).

## 모듈 책임

모든 모듈은 `src/rss_wiki/` 아래에 둔다. 테스트는 `tests/` 아래 모듈별 폴더.

| 모듈 | 책임 | 의존 |
|---|---|---|
| `config.py` | TOML 설정 로드, 기본값, 경로 해석 (`Settings` dataclass) | 표준 라이브러리만 |
| `db.py` | SQLite 연결(WAL, `busy_timeout`), 스키마 생성/마이그레이션(`PRAGMA user_version`, 실패 시 롤백, 미래 버전 거부, 열린 트랜잭션에서 호출 거부), FTS5, 중단된 상태 복구. `Path`만 받고 `config`에 의존하지 않음 | 표준 라이브러리만 |
| `repo.py` | 피드/글/태그/실행 이력 CRUD와 상태 전이 함수(항상 `updated_at` 갱신), FTS 검색 질의 생성(접두사 검색) (SQL은 여기와 `db.py`에만) | `db` |
| `feeds.py` | `FeedFetcher` 프로토콜 + 실제 구현(HTTP 조건부 요청, 파싱), 글 식별 키 계산 | — |
| `extract.py` | `ContentExtractor` 프로토콜 + 실제 구현, 피드 본문 대체, 최대 길이 자르기 | — |
| `summarizer.py` | `Summarizer` 프로토콜 + Claude Code CLI 구현(지시문은 `-p` 인자, 본문은 stdin, `claude_model`이 있을 때만 `--model`), 사전 점검, JSON 검증 | `config` |
| `tags.py` | 태그 정규화(소문자, 케밥케이스, 공백/중복 제거) | — |
| `wiki.py` | 글 Markdown 렌더링, slug(충돌·Windows 금지 문자), 원자적 쓰기, 인덱스 전체 재생성 | `repo` |
| `pipeline.py` | 1회 실행 오케스트레이션: 수집 → 처리량 제한 → 본문 → 요약 → 위키 → 인덱스, 진행 상황 보고, 실패 격리 | 위 전부 (인터페이스로 주입) |
| `opml.py` | OPML 파싱 → 피드 URL 목록 | — |
| `web/` | FastAPI 앱, Jinja2 템플릿, htmx, 정적 CSS. 백그라운드 실행 1개 제한 | `repo`, `pipeline` |
| `cli.py` | `rss-wiki` 진입점(`serve` 등), 로그 설정 | `config`, `web` |

원칙
- 네트워크·CLI를 부르는 모듈(`feeds`, `extract`, `summarizer`)은 프로토콜 뒤에 두고 테스트에서는 가짜 구현을 쓴다(PRD 8).
- 경로는 모두 `pathlib.Path`.
- 상태 전이는 `repo.py`의 함수로만 바꾼다(파일 쓰기 성공 후에만 `done`).
- Python 3.15를 유지한다(U8 합의). 의존성 추가 시 3.15/Windows 휠 가용성을 확인한다.
- 원문 본문은 DB·위키 어디에도 저장하지 않는다(U4). 글 레코드는 영구 보존한다(U7). 읽음 상태는 두지 않는다(U6).
- 요약은 순차 처리(U3). 재요약 시 글 파일 덮어쓰기(U5). 인덱스는 매 실행 끝 전체 재생성(U9). 웹 상세는 DB 사본 렌더링(U10).
- SQLite 연결은 스레드마다 따로 연다. 백그라운드 실행 스레드와 웹 요청 처리가 연결 객체를 공유하지 않는다(`sqlite3` 기본 `check_same_thread=True` 유지).

## 마일스톤

### M1. 기반: 설정·DB·테스트 체계
- 범위: `config.py`, `db.py`, `repo.py`의 기본, pytest 도입
- 완료 조건: 설정 파일 유무와 관계없이 `Settings`를 얻고, 빈 DB에 스키마(FTS5 포함)를 만들 수 있으며, 서버 재시작 시 `fetching_content`/`summarizing` → `new` 복구 함수가 테스트로 검증됨
- 상태: 진행 중 (T1·T1a·T1b·T2·T2a·T2b·T3·T3r·T3a·T3s 완료, 남은 항목 T3b(처리 대상 조회·상태별 건수·실패 목록, 실행 이력 `runs`와 중단 실행 `aborted` 처리, TASKS에 상세화). T3b PASS로 M1 완료)
- `list_failed_articles`는 `updated_at` 내림차순, 동률이면 `id` 내림차순. `finish_run`의 `processed`/`failed`는 0 이상만 받는다. (자체 결정)
- 처리 대상 순서는 `id` 오름차순(수집 순)이다. `runs.status`는 `running`/`finished`/`aborted`를 쓰고 스키마 CHECK 대신 `repo.py`에서 검증한다. 서버 시작 시 `db.reset_interrupted`와 `repo.abort_running_runs`를 함께 호출한다(M5에서 연결). (자체 결정)
- 태그 이름 정규화는 `tags.py`(M3) 책임이고 `repo.py`는 받은 이름을 그대로 저장한다. `list_tag_names`는 글이 연결된 태그만 돌려준다. (자체 결정)
- 검색은 `status = 'done'` 글만 대상으로 한다(요약이 있는 글만 검색 화면에 의미가 있음). (자체 결정)

### M2. 수집과 본문 확보
- 범위: `feeds.py`, `extract.py`, `repo.py` 확장
- 내용: 글 식별(guid/id → 정규화 link), 중복 건너뛰기, ETag/Last-Modified, 피드 실패 기록(마지막 오류·연속 실패), 첫 수집 최근 10개 + `skipped_backfill`, 실행당 50개 상한(나머지 `new`로 대기), 본문 추출 → `content` → `summary` 대체와 `source` 기록, 최대 길이 자르기, 호스트별 요청 간격

### M3. 요약과 태그
- 범위: `summarizer.py`, `tags.py`
- 내용: `claude -p` 비대화형 호출(지시문 인자 + 본문 stdin, U1), 순차 처리(U3), JSON 응답 검증(요약 3문장, 태그 3~5개), 타임아웃, Windows `claude.cmd`, 실행 파일 경로·모델 설정, 기존 태그 목록을 프롬프트에 포함, 사전 점검(미설치/미로그인), 실패 시 `attempts` 증가와 `failed_permanent` 전환
- `tags.py` 정규화 함수는 `str`이 아닌 원소(`bytes`, 정수 등)를 `TypeError`로 거부한다. `repo.set_article_tags`는 받은 그대로 저장하므로 검증은 정규화 단계 책임이다. (자체 결정, T3s REVIEW 메모)

### M4. Markdown 위키
- 범위: `wiki.py`
- 내용: `articles/YYYY/MM/{slug}.md`(PRD 4.6 frontmatter 형식), `index.md`·`feeds/`·`tags/` 전체 재생성, slug 충돌 접미사, Windows 금지 문자 제거, 원자적 쓰기, 쓰기 실패 시 `failed`

### M5. 실행 파이프라인과 웹 UI
- 범위: `pipeline.py`, `web/`, `cli.py`, `opml.py`
- 내용: `rss-wiki serve`(127.0.0.1, 포트 설정), 요약 목록/상세 + 피드·태그 필터, 피드 관리(추가 시 파싱 검증·제목 자동, 삭제, 활성/비활성, OPML 가져오기), "새 글 가져오기" 백그라운드 실행(동시 1개) + htmx 폴링 진행 표시, 실패 목록과 수동 재시도, FTS5 검색 화면

### M6. 운영 마감과 완료 기준 검증
- 범위: 로그(파일 + 콘솔), README(`rss-wiki.toml` 예시와 키 설명, 파일 인코딩 UTF-8(BOM 없음)·`~` 확장·상대 경로 기준(설정 파일 디렉터리) 안내 포함, T1/T1a/T1b REVIEW 메모; WAL로 생기는 `rss-wiki.db-wal`/`-shm`과 백업 방법(서버 정지 후 세 파일 함께 복사 또는 `sqlite3 .backup`) 안내, T2a REVIEW 메모), 멱등성/실패 격리 통합 테스트
- 설정 로더 잔여 보강(T1b REVIEW 메모, README 작업 때 함께): `config.py` 경로 검사를 `not str(raw).strip()`로 바꿔 공백만 있는 경로 거부, `expanduser()`의 `RuntimeError`를 키 이름·파일 경로가 담긴 `ValueError`로 포장
- 내용: PRD 9 완료 기준 1~6을 가짜 구현 기반 통합 테스트와 수동 확인 절차로 검증

## 자체 결정 (되돌리기 쉬운 구현 기본값)

- 설정 파일 기본 위치는 현재 디렉터리의 `rss-wiki.toml`. 없으면 기본값으로 동작한다. 설정 파일 안의 상대 경로는 설정 파일이 있는 디렉터리 기준, 설정 파일이 없으면 현재 디렉터리 기준으로 해석한다. (자체 결정)
- DB 기본 경로 `./rss-wiki.db`, 로그 기본 경로 `./logs/`. (자체 결정)
- 설정 기본값: 본문 최대 12000자, HTTP 타임아웃 20초, CLI 타임아웃 120초. 설정의 알 수 없는 키는 오타를 잡기 위해 오류로 처리한다. (자체 결정)
- 바인딩 주소는 PRD 2에 따라 `127.0.0.1` 고정이며 설정으로 노출하지 않는다. (자체 결정)
- PRD 4.5의 "대기" 상태는 별도 상태값을 두지 않고 `new`로 남겨 다음 실행에서 처리한다. (자체 결정)
- 설정 파일은 UTF-8(BOM 없음)만 받는다. 다른 인코딩이나 BOM이면 파일 경로와 저장 방법 안내를 담은 `ValueError`를 낸다. 경로 설정값의 `~`는 홈 디렉터리로 확장한다. README(M6)에 명시한다. (자체 결정)
- DB 스키마 변경은 `PRAGMA user_version` 기반 순차 마이그레이션으로 관리해 이후 변경을 되돌리기 쉽게 한다. (자체 결정)
- 한국어 검색: `articles_fts`의 `unicode61` 토크나이저는 그대로 두고, 검색 계층(`repo.py`)에서 사용자 질의를 공백으로 나눠 각 단어를 큰따옴표로 감싼 접두사 질의(`"컴퓨팅"*`)로 바꿔 AND로 묶는다. 조사가 붙은 단어(`컴퓨팅의`)를 찾을 수 있고 스키마 변경이 없다. 단어 중간 일치(`양자컴퓨팅`에서 `컴퓨팅`)는 v1에서 지원하지 않는다. 필요해지면 `MIGRATIONS` v2로 `trigram` 전환을 검토한다. (자체 결정, T2 REVIEW 후보 (a))
- SQLite 연결은 `journal_mode=WAL`, `busy_timeout=5000`으로 연다(웹 폴링 읽기와 백그라운드 쓰기 동시 접근 대비). (자체 결정)
- `updated_at`은 트리거가 아니라 `repo.py`의 상태 전이·수정 함수가 명시적으로 `CURRENT_TIMESTAMP`로 갱신한다. (자체 결정)
- DB의 `user_version`이 코드가 아는 최신 버전보다 크면 두 버전을 담은 `RuntimeError`로 거부한다. (자체 결정)
- `repo.py`의 쓰기 함수는 없는 id를 조용히 무시하지 않는다. 글 대상 함수는 `ArticleNotFoundError`, 피드 대상 함수는 `FeedNotFoundError`(둘 다 `LookupError` 하위)를 낸다. 단, `delete_feed`는 멱등으로 없는 id도 예외 없이 넘어간다. `DuplicateFeedError`는 `feeds.url`의 UNIQUE 위반일 때만 쓴다. (자체 결정, T3 REVIEW 메모)
- `repo.py` 쓰기 함수는 각자 `with conn:`으로 한 트랜잭션씩 커밋하며, 호출자는 열린 트랜잭션에서 부르지 않는다(성공 시 호출자 작업까지 커밋, 예외 시 함께 롤백되기 때문). 파이프라인(M5)은 글 하나의 처리 단계마다 repo 함수를 따로 호출하고, 여러 쓰기를 원자적으로 묶어야 하는 경우가 생기면 그 묶음 전체를 `repo.py`의 새 함수 하나로 만든다. 모듈 독스트링에 명시한다(T3a). (자체 결정, T3r REVIEW 메모)
- `repo.py`의 개수 인자(`limit`, `max_attempts`)는 1 미만이면 DB 접근 전에 `ValueError`로 거부한다(SQLite 음수 `LIMIT`이 무제한이 되는 것 방지). 목록 인자에 `str`이 오면 `TypeError`로 거부한다(글자 단위 분해 방지). (자체 결정, T3a REVIEW 메모)
- `migrate`는 열린 트랜잭션이 있는 연결로 호출되면 경고 대신 `RuntimeError`로 거부한다(`executescript`의 암묵 커밋 방지). 서버 시작 시 새 연결에서 부르는 것이 정상 경로다. (자체 결정)

## 합의된 결정 (2026-11-23, 사이클 2에서 PRD 반영)

U1~U10 모두 1회 시도에 합의했고, PRD 본문에 (자체 결정: 합의)로 반영했다.
U1 B(본문 stdin) · U2 C(`claude_model` 설정, 없으면 `--model` 생략) · U3 A(순차) · U4 A(본문 저장 안 함) · U5 A(덮어씀) · U6 A(읽음 관리 안 함) · U7 A(영구 보존) · U8 A(3.15 유지) · U9 A(전체 재생성) · U10 A(DB 사본 렌더링)

참고: `docs/decisions/*.md` 주제 파일 10개는 반영이 끝났지만, 이번 세션의 권한 제한으로 삭제하지 못하고 남아 있다. 사람이 지우거나 run.py가 정리해도 된다. 아래 미해결 섹션이 비어 있으므로 다시 처리되지 않는다.

## 미해결 의사결정

(없음)
