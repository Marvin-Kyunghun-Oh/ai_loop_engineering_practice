# TASKS

- 기준: docs/PLAN.md
- 규칙: 위에서부터 첫 미완료 항목을 처리한다. 한 항목은 한 세션(10~20분) 크기다.
- 테스트는 실제 네트워크·Claude Code CLI를 호출하지 않는다.

## M1. 기반: 설정·DB·테스트 체계

- [x] T1. pytest 도입 + 설정 로더(`config.py`)
  - 내용
    - `uv add --dev pytest`로 테스트 의존성을 추가한다. `pyproject.toml`에 `[tool.pytest.ini_options] testpaths = ["tests"]`를 둔다.
    - `src/rss_wiki/config.py`에 `Settings` dataclass(frozen)와 `load_settings(path: Path | None = None) -> Settings`를 만든다. 표준 라이브러리 `tomllib`만 쓴다.
    - 필드와 기본값: `wiki_dir=./wiki`, `db_path=./rss-wiki.db`, `log_dir=./logs`, `port=8000`, `first_fetch_limit=10`, `max_per_run=50`, `content_max_chars=12000`, `http_timeout_sec=20`, `claude_timeout_sec=120`, `claude_path="claude"`, `claude_model=None`. 호스트는 `127.0.0.1` 고정 상수로 두고 설정 키로 받지 않는다.
    - `path=None`이면 현재 디렉터리의 `rss-wiki.toml`을 찾고, 없으면 기본값을 쓴다. 명시한 경로가 없으면 `FileNotFoundError`.
    - 경로 필드는 `Path`로 변환하고, 상대 경로는 설정 파일의 디렉터리(설정 파일이 없으면 현재 디렉터리) 기준 절대 경로로 해석한다.
    - 정수 필드에 음수·0·비정수, 알 수 없는 키가 오면 키 이름을 담은 `ValueError`를 낸다.
  - acceptance
    - `uv run pytest -x tests/config/test_config.py` 통과. 최소 다음 경우를 포함:
      설정 파일 없음 → 기본값 / TOML 값 덮어쓰기 / 상대 경로가 설정 파일 디렉터리 기준으로 해석됨(`tmp_path` 사용) / 잘못된 값·알 수 없는 키 → `ValueError` / 명시 경로 없음 → `FileNotFoundError`
    - `uv run python -c "from rss_wiki.config import load_settings; print(load_settings().port)"`가 종료 코드 0으로 `8000` 출력 (`rss-wiki.toml`이 없는 디렉터리에서)
  - touch: `src/rss_wiki/config.py`, `tests/config/`, `tests/conftest.py`(필요 시), `pyproject.toml`, `uv.lock`

- [x] T1a. 설정 로더 테스트·오류 메시지 보강 (T1 REVIEW 메모 해소)
  - 내용
    - `tests/config/test_config.py`
      - 정수 필드 6개(`port`, `first_fetch_limit`, `max_per_run`, `content_max_chars`, `http_timeout_sec`, `claude_timeout_sec`) 전부를 0 / 음수 / 문자열 / 실수 / bool로 파라미터화해 키 이름이 담긴 `ValueError`를 확인한다.
      - `claude_path`/`claude_model`의 빈 문자열·비문자열(예: `3`), 경로 필드(`wiki_dir` 등)의 비문자열(예: `5`) → 키 이름이 담긴 `ValueError`.
      - 깨진 TOML → `ValueError`(`tomllib.TOMLDecodeError` 포함)이며 메시지에 설정 파일 경로가 들어 있음.
      - `test_settings_frozen`의 죽은 코드(`:91`)와 재import(`:93`)를 정리한다.
    - `src/rss_wiki/config.py`
      - 설정 파일에서 온 오류(TOML 파싱 오류, 알 수 없는 키, 값 검증 오류)의 메시지에 설정 파일 경로를 포함한다. TOML 파싱 오류는 `ValueError`로 감싸 다시 낸다(`from` 체인 유지).
      - `port`는 1~65535만 허용한다.
    - README·설정 예시는 M6에서 다룬다(이번 범위 아님).
  - acceptance
    - `uv run pytest -x tests/config/test_config.py` 통과, 위 경우가 모두 테스트로 존재
    - `port = 65536` → `ValueError`(메시지에 `port`), `port = 65535` → 정상 로드
    - 기존 T1 acceptance(`rss-wiki.toml` 없는 디렉터리에서 `load_settings().port` → `8000`, 종료 코드 0) 유지
  - touch: `src/rss_wiki/config.py`, `tests/config/test_config.py`

- [x] T1b. 설정 파일 인코딩 오류 처리와 `~` 확장 (T1a REVIEW 메모 해소, 작은 항목)
  - 내용
    - `src/rss_wiki/config.py`
      - 설정 파일 읽기(`config.py:50-54`)에서 `UnicodeDecodeError`도 `ValueError`로 감싸고(`from` 체인 유지) 메시지에 설정 파일 경로와 "UTF-8로 저장하라"는 안내를 넣는다.
      - 파일이 UTF-8 BOM(`b"\xef\xbb\xbf"`)으로 시작하면 파싱 전에 감지해 경로와 "UTF-8(BOM 없음)으로 저장하라"는 안내가 담긴 `ValueError`를 낸다. (BOM을 조용히 허용하지 않고 명확히 거부한다 — 자체 결정)
      - 경로 필드(`wiki_dir`, `db_path`, `log_dir`)는 `Path.expanduser()`를 적용한 뒤 절대/상대를 판정한다. (자체 결정: `~`는 홈 디렉터리로 확장)
    - `tests/config/test_config.py`에 다음을 각 1건 이상 추가
      - CP949(예: `"wiki_dir = \"위키\"".encode("cp949")`)로 저장한 파일 → `ValueError`, 메시지에 파일 경로, `__cause__`가 `UnicodeDecodeError`
      - BOM으로 시작하는 UTF-8 파일 → `ValueError`, 메시지에 파일 경로와 `BOM`
      - `wiki_dir = "~/w"` → `Path.home() / "w"`로 해석 (`monkeypatch`로 `HOME`/`USERPROFILE`을 `tmp_path`로 바꿔 실제 홈에 의존하지 않음)
      - `wiki_dir = ""` → 키 이름이 담긴 `ValueError`
      - 문자열 필드(`claude_path = ""`)와 경로 필드(`db_path = 5`) 오류 메시지에 설정 파일 경로가 포함됨
    - (REVIEW 메모의 "설정 파일 없을 때 경로 접미사 생략" 테스트는 기본값이 항상 유효해 오류를 유발할 수 없으므로 다루지 않는다.)
  - acceptance
    - `uv run pytest -x tests/config/test_config.py` 통과, 위 경우가 테스트로 존재
    - 기존 T1 acceptance(`rss-wiki.toml` 없는 디렉터리에서 `load_settings().port` → `8000`, 종료 코드 0) 유지
  - touch: `src/rss_wiki/config.py`, `tests/config/test_config.py`

- [x] T2. SQLite 스키마와 연결(`db.py`)
  - 내용
    - `src/rss_wiki/db.py`에 `connect(db_path: Path) -> sqlite3.Connection`(부모 디렉터리 생성, `foreign_keys=ON`, `row_factory=sqlite3.Row`)과 `migrate(conn)`를 만든다. 스키마 버전은 `PRAGMA user_version`으로 관리하고, `migrate`를 여러 번 불러도 안전해야 한다(멱등).
    - 테이블(최소 컬럼)
      - `feeds`: id, url(UNIQUE), title, enabled(기본 1), etag, last_modified, last_error, consecutive_failures(기본 0), initial_fetch_done(기본 0), created_at
      - `articles`: id, feed_id(FK, ON DELETE CASCADE), entry_key, title, url, published, fetched_at, source(`extracted`|`feed`|NULL), status, attempts(기본 0), last_error, summary(3줄을 `\n`으로 이은 텍스트), wiki_path, created_at, updated_at, UNIQUE(feed_id, entry_key)
      - `tags`: id, name(UNIQUE) / `article_tags`: article_id, tag_id, PK(article_id, tag_id)
      - `runs`: id, started_at, finished_at, status, processed, failed
      - `articles_fts`: FTS5 가상 테이블(title, summary), `articles`와 트리거로 동기화
    - `status`는 CHECK 제약으로 `new, fetching_content, summarizing, done, failed, failed_permanent, skipped_backfill`만 허용한다.
    - 원문 본문 컬럼은 두지 않는다(PRD 5, 결정 U4 합의: 저장 안 함). 읽음 플래그 컬럼도 두지 않는다(U6).
    - `reset_interrupted(conn) -> int`: `fetching_content`/`summarizing` 글을 `new`로 되돌리고 바꾼 건수를 반환한다(PRD 7 서버 중단 복구).
  - acceptance
    - `uv run pytest -x tests/db/test_db.py` 통과. 최소 다음 경우를 포함:
      빈 DB에 `migrate` 후 5개 테이블과 `articles_fts` 존재 / `migrate` 2회 호출해도 오류 없음 / 같은 (feed_id, entry_key) 중복 INSERT는 `IntegrityError` / 허용되지 않은 status는 `IntegrityError` / 글 INSERT·UPDATE 후 `articles_fts MATCH`로 요약 키워드 검색됨 / 피드 삭제 시 글도 삭제 / `reset_interrupted`가 두 상태만 `new`로 바꾸고 건수 반환
    - 모든 테스트는 `tmp_path`의 DB 파일을 쓴다.
    - `connect`가 존재하지 않는 부모 디렉터리(`tmp_path / "a" / "b" / "x.db"`)를 만들어 연결하는 테스트 포함.
    - `uv run pytest` 전체 통과(기존 설정 테스트 55개 포함, 회귀 없음).
    - `db.py`는 표준 라이브러리 `sqlite3`만 쓰고 새 의존성을 추가하지 않는다(`pyproject.toml`/`uv.lock` 변경 없음).
  - touch: `src/rss_wiki/db.py`, `tests/db/`

- [x] T2a. DB 계층 보강: 마이그레이션 롤백·미래 버전 거부·WAL·테스트 공백 (T2 REVIEW 메모 해소, 작은 항목)
  - 내용
    - `src/rss_wiki/db.py`
      - `migrate`: `executescript` 실패 시 `conn.rollback()`(트랜잭션이 열려 있으면) 후 원래 예외를 다시 던진다. 실패한 스크립트의 일부 테이블이 남지 않고 `user_version`도 그대로여야 한다.
      - `migrate`: DB의 `user_version`이 `len(MIGRATIONS)`보다 크면 DB 버전과 지원 버전을 메시지에 담은 `RuntimeError`를 낸다. (자체 결정)
      - `connect`: `PRAGMA journal_mode = WAL`, `PRAGMA busy_timeout = 5000`을 설정한다. (자체 결정, PLAN 참고)
      - 스키마(`_V1`)는 바꾸지 않는다. 한국어 검색은 스키마 변경 없이 검색 계층 접두사 질의로 처리하기로 했다(PLAN 자체 결정, 구현은 T3a).
    - `tests/db/test_db.py`에 다음을 각 1건 이상 추가
      - 마이그레이션 실패: `monkeypatch.setattr(db, "MIGRATIONS", (db.MIGRATIONS[0], "CREATE TABLE half (a); THIS IS NOT SQL;"))`로 v1 적용 DB에 `migrate` → `sqlite3.Error` 발생, `user_version == 1`, `conn.in_transaction is False`, `half` 테이블 없음
      - 미래 버전: `PRAGMA user_version = 99` 후 `migrate` → `RuntimeError`, 메시지에 `99`
      - `connect` 후 `PRAGMA journal_mode` → `wal`, `PRAGMA busy_timeout` → `5000`
      - 피드 삭제(CASCADE) 후 `articles_fts` 행 0건
      - `source = 'bogus'` INSERT → `IntegrityError`
      - `reset_interrupted`가 `updated_at`을 바꿈(사전에 `updated_at = '2000-01-01 00:00:00'`으로 맞춘 뒤 호출하고 값이 달라졌는지 확인, 대상이 아닌 상태의 글은 그대로)
      - 제목 키워드로 `articles_fts MATCH` 검색됨
  - acceptance
    - `uv run pytest -x tests/db/test_db.py` 통과, 위 경우가 모두 테스트로 존재
    - `uv run pytest` 전체 통과(기존 72개 회귀 없음)
    - 새 의존성 없음(`pyproject.toml`/`uv.lock` 변경 없음)
  - touch: `src/rss_wiki/db.py`, `tests/db/test_db.py`

- [x] T2b. `migrate` 전제 강제와 테스트 사소한 보강 (T2a REVIEW 메모 해소, 5분 크기의 작은 항목)
  - 내용
    - `src/rss_wiki/db.py`
      - `migrate` 진입 시 `conn.in_transaction`이 참이면 아무것도 적용하지 않고 `RuntimeError`(메시지에 "열린 트랜잭션"과 "커밋 또는 롤백 후 호출" 안내)를 낸다. `executescript`가 호출자 트랜잭션을 암묵 커밋하는 것을 막기 위함이다. (자체 결정: 경고 대신 거부)
      - `migrate`의 `except Exception`(`db.py:123`)을 `except BaseException`으로 바꿔 `KeyboardInterrupt` 등에서도 롤백한다.
      - `migrate` 독스트링에 "열린 트랜잭션 없이 호출해야 한다(열려 있으면 RuntimeError)"를 적는다.
    - `tests/db/test_db.py`
      - 새 테스트: 미커밋 `INSERT`(예: `feeds` 1행)가 있는 연결로 `migrate` → `RuntimeError`, 이어서 `conn.rollback()` 후 `feeds` 행 0건(호출자 트랜잭션이 커밋되지 않았음)
      - `test_future_version_rejected`: 메시지에 지원 버전 `1`(또는 `str(len(db.MIGRATIONS))`)도 있는지 확인
      - `test_reset_interrupted_updates_updated_at`: `reset_interrupted` 반환 건수(1) 확인
  - acceptance
    - `uv run pytest -x tests/db/test_db.py` 통과, 위 세 경우가 테스트로 존재
    - `uv run pytest` 전체 통과(기존 79개 회귀 없음)
    - 새 의존성 없음(`pyproject.toml`/`uv.lock` 변경 없음), 스키마 `_V1` 불변
  - touch: `src/rss_wiki/db.py`, `tests/db/test_db.py`
  - 상태 메모(planner, 사이클 7): generator 완료 보고(80 passed). 코드에서 `in_transaction` 거부·`except BaseException`·독스트링, 테스트 3건(`test_migrate_rejects_open_transaction` 등)을 확인함. 직전 REVIEW.md는 T2a 평가라 T2b 전용 평가는 없음 → 다음 evaluator가 T3 평가 때 `tests/db/` 회귀와 함께 확인한다.

- [x] T3. `repo.py` 기본: 피드 CRUD, 글 신규 저장, 상태 전이
  - 내용
    - `src/rss_wiki/repo.py`를 만든다. 모든 함수는 첫 인자로 `sqlite3.Connection`을 받고, 쓰기 함수는 `with conn:`으로 커밋한다. SQL은 이 파일과 `db.py`에만 둔다.
    - 피드
      - `add_feed(conn, url, title) -> int`: 새 피드 id 반환. 같은 URL이 이미 있으면 `DuplicateFeedError`(이 모듈에 정의, `ValueError` 하위)를 낸다.
      - `get_feed(conn, feed_id) -> sqlite3.Row | None`, `list_feeds(conn, *, enabled_only=False) -> list[sqlite3.Row]`(id 순)
      - `set_feed_enabled(conn, feed_id, enabled: bool) -> None`, `delete_feed(conn, feed_id) -> None`
    - 글
      - `insert_article_if_new(conn, feed_id, entry_key, *, title, url, published, status="new") -> int | None`: 새로 넣으면 id, 같은 `(feed_id, entry_key)`가 있으면 `None`(기존 행 변경 없음). `INSERT OR IGNORE`는 CHECK 위반까지 삼키므로 쓰지 말고 `ON CONFLICT(feed_id, entry_key) DO NOTHING`을 쓴다. `fetched_at`은 현재 시각.
      - `get_article(conn, article_id) -> sqlite3.Row | None`
    - 상태 전이(모두 `updated_at = CURRENT_TIMESTAMP` 갱신)
      - `set_status(conn, article_id, status) -> None`: `db.STATUSES`에 없는 값이면 `ValueError`
      - `mark_failed(conn, article_id, error: str, *, max_attempts: int = 3) -> str`: `attempts`를 1 올리고 `last_error` 기록, 올린 뒤 `attempts >= max_attempts`이면 `failed_permanent`, 아니면 `failed`로 바꾸고 바뀐 상태를 반환
      - `mark_done(conn, article_id, *, summary: str, source: str, wiki_path: str) -> None`: 요약·출처·위키 경로 저장, `status='done'`, `last_error=NULL`. (파일 쓰기 성공 뒤에만 부른다는 규칙은 호출자 책임, 독스트링에 명시)
    - 태그·검색·처리 대상 조회·실행 이력은 이번 범위가 아니다(T3a 이후).
  - acceptance
    - `uv run pytest -x tests/repo/test_repo.py` 통과. 최소 다음 경우를 포함(`tmp_path` DB, `db.connect` + `db.migrate` 사용):
      피드 추가·조회·목록 / 같은 URL 재추가 → `DuplicateFeedError` / `enabled_only=True`가 비활성 피드를 제외 / 피드 삭제 후 `get_feed`가 `None`
      / `insert_article_if_new` 두 번째 호출이 `None`이고 행 수 1 / 잘못된 status로 `insert_article_if_new` → `IntegrityError`(조용히 무시되지 않음)
      / `set_status`에 잘못된 값 → `ValueError` / `mark_failed` 1·2회째 `failed`, 3회째 `failed_permanent`, `attempts == 3`, `last_error`가 마지막 메시지
      / `mark_done` 후 `status == 'done'`, `last_error is None`, `articles_fts MATCH`로 요약 키워드 검색됨
      / 상태 전이 함수(`set_status`, `mark_failed`, `mark_done`) 각각이 `updated_at`을 바꿈(사전에 과거 값으로 맞춘 뒤 확인)
      / 쓰기 함수가 커밋함: `add_feed`·`mark_done` 직후 같은 DB 파일에 새로 연 두 번째 연결에서 결과가 보임(웹 요청과 백그라운드 실행이 연결을 따로 여는 PLAN 원칙 대비)
    - `uv run pytest` 전체 통과(T2b 반영 후 기존 80개 회귀 없음), 새 의존성 없음(`pyproject.toml`/`uv.lock` 변경 없음)
    - `repo.py`는 `sqlite3`와 `rss_wiki.db`(`STATUSES`)만 import하고 `config`에 의존하지 않는다.
  - touch: `src/rss_wiki/repo.py`, `tests/repo/`

- [x] T3r. `repo.py` 오류 표면 정리와 커밋 테스트 보강 (T3 REVIEW 메모 해소, 10분 크기의 작은 항목, T3a보다 먼저)
  - 내용
    - `src/rss_wiki/repo.py`
      - `add_feed`(`repo.py:22`): 중복 판정을 `"UNIQUE constraint failed: feeds.url" in str(e)`로 좁힌다. URL 누락(`NOT NULL`) 등 다른 `IntegrityError`는 그대로 다시 던진다.
      - 예외 클래스 `ArticleNotFoundError(LookupError)`, `FeedNotFoundError(LookupError)`를 이 모듈에 정의한다. (자체 결정: 없는 id를 조용히 무시하지 않고 명시적 예외로 드러낸다)
      - `set_status`·`mark_failed`·`mark_done`: UPDATE의 `cur.rowcount == 0`이면 `with conn:` 블록 안에서 id를 담은 `ArticleNotFoundError`를 낸다(롤백되어 부작용 없음). `mark_failed`는 이 검사를 SELECT 전에 해서 `TypeError`가 나지 않게 한다.
      - `set_feed_enabled`: 같은 방식으로 없는 id면 `FeedNotFoundError`.
      - `delete_feed`: 없는 id는 조용히 넘어간다(삭제는 멱등, 웹에서 두 번 눌러도 오류 아님). 독스트링에 명시. (자체 결정)
      - `mark_failed`: `max_attempts < 1`이면 `ValueError`.
    - `tests/repo/test_repo.py`
      - `add_feed(conn, None, "t")` → `sqlite3.IntegrityError`이며 `DuplicateFeedError`가 **아님**(`not isinstance(e, DuplicateFeedError)`), 피드 행 0건
      - 없는 id(예: 999)로 `set_status`·`mark_failed`·`mark_done` → `ArticleNotFoundError`(파라미터화), `set_feed_enabled` → `FeedNotFoundError`, `delete_feed(conn, 999)` → 예외 없음
      - `mark_failed(..., max_attempts=0)` → `ValueError`, 글 상태·`attempts` 불변
      - `test_writes_are_committed`를 쓰기 함수별 파라미터화로 바꾼다: `add_feed`, `set_feed_enabled`, `delete_feed`, `insert_article_if_new`, `set_status`, `mark_failed`, `mark_done` 각각에 대해 준비 작업을 먼저 끝낸 뒤 **검사 대상 함수를 마지막 쓰기로** 호출하고, 곧바로 같은 DB 파일에 새로 연 두 번째 연결에서 결과가 보이는지 확인한다. (검사 대상 함수에서 `with conn:`을 빼면 그 케이스가 실패해야 한다)
  - acceptance
    - `uv run pytest -x tests/repo/test_repo.py` 통과, 위 경우가 모두 테스트로 존재
    - 변이 확인: `add_feed`의 `with conn:`을 일시적으로 빼면 `test_writes_are_committed[add_feed]`가 실패함(IMPL.md에 확인 결과 기록, 코드는 원복)
    - `uv run pytest` 전체 통과(기존 94개 회귀 없음), 새 의존성 없음(`pyproject.toml`/`uv.lock` 변경 없음), `db.py` 변경 없음
  - touch: `src/rss_wiki/repo.py`, `tests/repo/test_repo.py`

- [x] T3a. `repo.py` 확장: 글 태그 저장과 FTS 접두사 검색 + 예외 문서화 (T3r REVIEW 메모 해소 포함, T2a REVIEW 한국어 검색 메모 해소)
  - 내용
    - 예외 문서화(T3r REVIEW 메모, 먼저 처리, 코드 동작 변경 없음)
      - 모듈 독스트링(`repo.py:1`)에 다음 두 줄을 추가한다: "없는 id에 대한 쓰기는 `LookupError` 하위 예외(`ArticleNotFoundError`/`FeedNotFoundError`)를 낸다. 삭제(`delete_feed`)만 멱등이다." / "쓰기 함수는 `with conn:`을 쓰므로 성공 시 호출자의 미커밋 작업까지 커밋하고, 예외 시 함께 롤백한다. 열린 트랜잭션에서 호출하지 않는다."
      - `set_status`(`ValueError`, `ArticleNotFoundError`), `set_feed_enabled`(`FeedNotFoundError`), `mark_failed`(`ValueError`에 `ArticleNotFoundError` 추가), `mark_done`(`ArticleNotFoundError`), 새 `set_article_tags`(`ArticleNotFoundError`) 독스트링에 `Raises:` 형태로 던지는 예외를 적는다. `add_feed`에도 `DuplicateFeedError`(같은 URL)와 그 밖의 `sqlite3.IntegrityError`는 그대로 전파됨을 적는다.
      - `tests/repo/test_repo.py`의 `test_missing_article_raises`에 예외 후 `conn.in_transaction is False`와 `issubclass(repo.ArticleNotFoundError, LookupError)`·`issubclass(repo.FeedNotFoundError, LookupError)` 확인을 추가한다.
    - 태그(`src/rss_wiki/repo.py`)
      - `set_article_tags(conn, article_id, names: list[str]) -> None`: 글의 태그를 주어진 목록으로 **교체**한다(기존 연결 삭제 후 재연결, 재요약 덮어쓰기 대비). 없는 태그는 `INSERT ... ON CONFLICT(name) DO NOTHING`으로 만든다. 입력 안의 중복 이름은 한 번만 연결한다. 빈 목록이면 연결을 모두 지운다. 이름 정규화(소문자·케밥케이스)는 호출자(`tags.py`, M3) 책임이며 이 함수는 받은 그대로 저장한다(독스트링에 명시). 없는 `article_id`면 빈 목록이어도 `ArticleNotFoundError`(T3r)를 내고 아무것도 바꾸지 않는다. 쓰기는 하나의 `with conn:` 안에서 처리한다.
      - `get_article_tags(conn, article_id) -> list[str]`: 이름 오름차순
      - `list_tag_names(conn) -> list[str]`: 글이 1개 이상 연결된 태그만 이름 오름차순(요약 프롬프트의 "기존 태그 목록" 용도, 연결이 끊긴 태그는 제외)
    - 검색(`src/rss_wiki/repo.py`, PLAN 자체 결정 "한국어 검색")
      - `build_fts_query(text: str) -> str | None`: 공백으로 나눈 각 단어에서 `"`를 `""`로 이스케이프하고 `"단어"*` 형태로 감싼 뒤 공백으로 이어 AND로 묶는다. 토큰이 하나도 없으면(빈 문자열·공백만·특수문자만) `None`.
      - `search_articles(conn, text, *, limit: int = 50) -> list[sqlite3.Row]`: `build_fts_query`가 `None`이면 `[]`. `articles_fts MATCH`로 찾고 `status = 'done'`인 글만, `bm25` 순으로 `limit`개 반환(행에 `id`, `title`, `summary`, `feed_id` 포함).
  - acceptance
    - `uv run pytest -x tests/repo/` 통과. 최소 다음 경우를 포함(`tmp_path` DB, T3 함수로 피드·글 준비, `mark_done`으로 요약 저장):
      `set_article_tags` 후 `get_article_tags`가 오름차순 목록 / 다른 목록으로 다시 호출하면 교체됨(이전 태그 연결 없음) / 입력 중복 `["a","a"]` → 연결 1개 / 빈 목록 → 연결 0개 / 두 글이 같은 태그를 쓰면 `tags` 행은 1개
      / `list_tag_names`가 연결이 끊긴 태그를 제외
      / `build_fts_query("양자 컴퓨팅")` == `'"양자"* "컴퓨팅"*'`, `build_fts_query("  ")` is `None`
      / 요약이 "양자 컴퓨팅의 미래"인 done 글을 `search_articles(conn, "컴퓨팅")`으로 찾음(조사 붙은 단어), 2글자 `"양자"`로도 찾음, 제목 키워드로도 찾음
      / 여러 단어는 AND: 한 단어만 맞는 글은 결과에 없음
      / 특수 입력 `'"'`, `'*'`, `'-'`, `'OR'`, `'a OR'`, `'('`, `'NEAR('`가 예외 없이 리스트를 반환(`sqlite3.OperationalError` 없음)
      / `status = 'new'`인 글은 제목이 맞아도 결과에 없음 / `limit` 적용
      / 없는 `article_id`로 `set_article_tags(conn, 999, [])`·`(conn, 999, ["a"])` → `ArticleNotFoundError`, `tags` 행 0건
      / `set_article_tags` 직후 두 번째 연결에서 태그가 보임(커밋 확인, T3r의 파라미터화 커밋 테스트에 케이스 추가로 충분)
      / `test_missing_article_raises`가 예외 후 `conn.in_transaction is False`와 두 NotFound 예외의 `LookupError` 상속을 확인
    - `uv run python -c "import rss_wiki.repo as r; import sys; sys.exit(0 if all('NotFoundError' in (f.__doc__ or '') for f in (r.set_status, r.set_feed_enabled, r.mark_failed, r.mark_done, r.set_article_tags)) else 1)"`가 종료 코드 0 (예외 문서화 확인)
    - `uv run pytest` 전체 통과(T3r 이후 106개 회귀 없음), 새 의존성 없음, 스키마 `_V1` 불변(`db.py` 변경 없음)
  - touch: `src/rss_wiki/repo.py`, `tests/repo/`

- [x] T3s. 검색 테스트 보강과 입력 검증 (T3a REVIEW 메모 해소, 10분 크기의 작은 항목, T3b보다 먼저)
  - 내용
    - `tests/repo/test_repo.py`에 다음을 추가한다(T3a에서 놓친 변이 3종을 잡기 위함).
      - 따옴표 이스케이프: `build_fts_query('a"b') == '"a""b"*'`, 그리고 `search_articles(conn, 'a"b')`·`search_articles(conn, 'say"hi')`가 예외 없이 리스트를 반환. (`repo.py:221`의 `replace('"', '""')`를 지우면 실패해야 한다)
      - 영숫자 필터: `build_fts_query('"') is None`, `build_fts_query('* - (') is None`, `build_fts_query('양자 *') == '"양자"*'`. (`repo.py:220`의 필터를 지우면 실패해야 한다)
      - `bm25` 정렬: 요약 길이를 비슷하게 맞춘 done 글 3개를 A(`양자` 2회), B(`양자` 4회), C(`양자` 1회) 순서로 만든 뒤 `search_articles(conn, "양자")`의 id 순서가 [B, A, C]임을 확인. (id 오름차순 [A, B, C]·내림차순 [C, B, A] 어느 쪽으로 바꿔도 실패하도록 준비한 배치다)
      - 리터럴 검색: 제목이 `OR 게이트`인 done 글을 `search_articles(conn, "OR")`로 찾음(결과 id에 포함). 기존 특수 입력 테스트(`isinstance(list)`만 확인)는 그대로 둔다.
    - `src/rss_wiki/repo.py` 입력 검증 (자체 결정: T3b `list_articles_to_process`와 같은 규칙으로 일관성 확보)
      - `search_articles`: `limit < 1`이면 DB 접근 전에 `ValueError`(SQLite에서 음수 `LIMIT`은 무제한이 되기 때문). 독스트링 `Raises:`에 적는다.
      - `set_article_tags`: `names`가 `str`이면 DB 접근 전에 `TypeError`(문자열이 글자 단위 태그로 쪼개져 저장되는 것 방지). 독스트링 `Raises:`에 적는다.
  - acceptance
    - `uv run pytest -x tests/repo/` 통과, 위 경우가 모두 테스트로 존재하고 다음도 포함: `search_articles(conn, "x", limit=0)`·`limit=-1` → `ValueError` / `set_article_tags(conn, a, "abc")` → `TypeError`이고 기존 태그 연결 불변·`tags` 행 수 불변
    - 변이 확인(IMPL.md에 결과 기록, 코드는 원복): (1) `repo.py:221` 이스케이프 제거, (2) `repo.py:220` 영숫자 필터 제거, (3) `ORDER BY bm25(...)`를 `ORDER BY a.id`로, (4) `ORDER BY a.id DESC`로 교체 — 네 경우 모두 새 테스트 중 하나 이상이 실패
    - `uv run pytest` 전체 통과(T3a 이후 124개 회귀 없음), 새 의존성 없음, `db.py` 변경 없음
  - touch: `src/rss_wiki/repo.py`, `tests/repo/test_repo.py`

- [x] T3b. `repo.py` 확장: 처리 대상 조회와 실행 이력(`runs`) (T3s 다음, M1 마지막 항목, T3s REVIEW 메모 반영)
  - 내용
    - 처리 대상(`src/rss_wiki/repo.py`, PRD 4.5·7)
      - `list_articles_to_process(conn, *, limit: int, max_attempts: int = 3) -> list[sqlite3.Row]`: `status = 'new'` 또는 (`status = 'failed'` 이고 `attempts < max_attempts`)인 글을 `id` 오름차순(수집 순, 자체 결정)으로 최대 `limit`개 반환. `failed_permanent`·`skipped_backfill`·`done`·진행 중 상태는 제외. `limit < 1` 또는 `max_attempts < 1`이면 `ValueError`. 검증은 함수 첫머리, DB 접근과 모든 조기 반환보다 앞에 둔다(T3s REVIEW 메모).
      - `count_articles_by_status(conn) -> dict[str, int]`: `db.STATUSES`의 모든 키를 담고 없는 상태는 0 (진행 상황·대기 건수 표시용).
      - `list_failed_articles(conn) -> list[sqlite3.Row]`: `failed`·`failed_permanent` 글을 `updated_at` 내림차순, 같은 `updated_at`이면 `id` 내림차순(`CURRENT_TIMESTAMP`가 초 단위라 동률이 흔함, 자체 결정), 행에 `id`, `feed_id`, `title`, `status`, `attempts`, `last_error` 포함(PRD 3 실패 목록 화면용).
    - 실행 이력(`runs`, 스키마 변경 없음)
      - `runs.status` 값은 `running`, `finished`, `aborted` 세 가지로 쓴다(스키마 CHECK 없이 `repo.py`의 상수 `RUN_STATUSES`로 검증, 자체 결정).
      - `RunNotFoundError(LookupError)`를 이 모듈에 정의한다.
      - `start_run(conn) -> int`: `started_at = CURRENT_TIMESTAMP`, `status='running'` 행을 넣고 id 반환.
      - `finish_run(conn, run_id, *, processed: int, failed: int, status: str = "finished") -> None`: `finished_at`·카운트·상태 기록. `status`가 `RUN_STATUSES`에 없거나 `'running'`이면 `ValueError`, `processed`·`failed`가 음수면 `ValueError`(0은 허용, 자체 결정), 이 검증들은 DB 접근 전. 없는 `run_id`면 `RunNotFoundError`(`with conn:` 안에서 rowcount 검사, 롤백되어 부작용 없음).
      - `get_latest_run(conn) -> sqlite3.Row | None`: id 최댓값 행.
      - `abort_running_runs(conn) -> int`: 서버 시작 시 남은 `running` 행을 `aborted`로 바꾸고 `finished_at`을 채운 뒤 건수 반환(PRD 7 서버 중단 복구, `db.reset_interrupted`와 함께 호출할 용도).
    - 새 함수 독스트링에 던지는 예외를 `Raises:`로 적는다(T3a에서 정한 규칙).
    - (작은 보강, T3s REVIEW 선택 메모) `test_search_quote_input` 근처에 제목이 `say"hi there`인 done 글을 만들고 `search_articles(conn, 'say"hi')` 결과 id에 그 글이 포함되는지 확인하는 테스트 1건을 추가한다(이스케이프가 리터럴 검색으로 동작함을 검증).
  - acceptance
    - `uv run pytest -x tests/repo/` 통과. 최소 다음 경우를 포함:
      `new` 2건·`failed`(attempts 1) 1건·`failed`(attempts 3) 1건·`failed_permanent`·`skipped_backfill`·`done`·`summarizing` 각 1건 준비 → `list_articles_to_process(limit=50)`가 앞의 3건만 id 순 / `limit=2`면 2건 / `max_attempts=4`면 attempts 3인 `failed`도 포함
      / 경계값: `limit=0`·`limit=-1`·`max_attempts=0` → `ValueError`(파라미터화), `limit=1` → 1건 (경계를 `< 0`으로 바꾸는 변이를 `0` 케이스가 잡아야 함)
      / 대상 글이 하나도 없는 빈 DB에서도 `limit=0` → `ValueError`(검증이 조기 반환·DB 조회보다 앞에 있음을 확인)
      / `count_articles_by_status`가 7개 키를 모두 담고 값이 준비한 건수와 일치, 빈 DB에서는 7개 키 모두 0
      / `list_failed_articles`가 `failed`·`failed_permanent`만 반환, `updated_at`을 같은 값으로 맞춘 두 글은 id 내림차순
      / `start_run` → `get_latest_run`의 `status == 'running'`, `finished_at is None` / `finish_run` 후 `finished`, 카운트 반영, `finished_at` 채워짐 / `finish_run(status='bogus')`·`'running'`·`processed=-1`·`failed=-1` → `ValueError`이고 행 불변 / 없는 `run_id` → `RunNotFoundError`(`LookupError` 하위), 예외 후 `conn.in_transaction is False` / 빈 DB의 `get_latest_run` → `None`
      / `abort_running_runs`가 `running` 행만 `aborted`로 바꾸고 `finished_at`을 채우며 건수 반환, `finished` 행은 그대로, 두 번째 호출은 0
      / 커밋 테스트 파라미터에 `start_run`, `finish_run`, `abort_running_runs` 추가(두 번째 연결에서 결과 보임)
      / 따옴표 리터럴 검색 테스트(위 작은 보강)
    - `uv run python -c "import rss_wiki.repo as r, sys; sys.exit(0 if all('Raises' in (f.__doc__ or '') for f in (r.list_articles_to_process, r.finish_run)) else 1)"`가 종료 코드 0
    - 변이 확인(IMPL.md에 결과 기록, 코드는 원복): (1) `list_articles_to_process`의 `limit < 1`을 `limit < 0`으로 (2) `attempts < max_attempts`를 `attempts <= max_attempts`로 (3) `finish_run`의 `with conn:` 제거 — 세 경우 모두 테스트 하나 이상 실패
    - `uv run pytest` 전체 통과(T3s 이후 133개 회귀 없음), 새 의존성 없음, 스키마 `_V1` 불변(`db.py` 변경 없음)
  - touch: `src/rss_wiki/repo.py`, `tests/repo/`
  - 상태 메모(planner, 사이클 12): generator 완료 보고(153 passed, 변이 3종 확인). 코드에서 `RUN_STATUSES`·`RunNotFoundError`·`list_articles_to_process`(검증이 함수 첫머리)·`finish_run`·`abort_running_runs` 등을 확인함. 직전 REVIEW.md는 T3s 평가라 T3b 전용 평가는 없음 → 다음 evaluator가 T4 평가 때 T3b acceptance(변이 3종 포함)와 `tests/repo/` 회귀를 함께 확인한다. FAIL이면 다음 planner가 체크를 해제한다.
  - 상태 메모(planner, 사이클 13): 사이클 12 evaluator가 회귀 확인(`tests/repo/` 73 passed, 변이 3종 잡힘, 문서 확인 명령 종료 코드 0) → PASS, 체크 유지. M1 완료.

## M2. 수집과 본문 확보

- [x] T4. `feeds.py` 기본: 데이터 타입·`FeedFetcher` 프로토콜·글 식별 키 (새 의존성 없음, 순수 함수)
  - 내용
    - `src/rss_wiki/feeds.py`를 만든다. 표준 라이브러리만 쓴다(`dataclasses`, `typing.Protocol`, `urllib.parse`).
    - 데이터 타입(모두 `@dataclass(frozen=True)`)
      - `FeedEntry`: `guid: str | None`, `link: str | None`, `title: str`, `published: str | None`(ISO8601), `content: str | None`, `summary: str | None`
      - `ParsedFeed`: `title: str | None`, `entries: tuple[FeedEntry, ...]`
      - `FetchResult`: `not_modified: bool`, `feed: ParsedFeed | None`(`not_modified`이면 `None`), `etag: str | None`, `last_modified: str | None`
    - 예외: `FeedError(Exception)`, 하위 `FeedFetchError`(네트워크·HTTP 오류), `FeedParseError`(파싱 오류). 파이프라인(M5)은 `FeedError`만 잡아 그 피드를 건너뛴다(PRD 7).
    - `class FeedFetcher(Protocol)`: `def fetch(self, url: str, *, etag: str | None = None, last_modified: str | None = None) -> FetchResult`. 실패는 `FeedError` 하위 예외로 알린다(독스트링 `Raises:`에 명시). 실제 구현은 T6.
    - `normalize_link(url: str) -> str` (자체 결정, PLAN M2 참고)
      - 앞뒤 공백 제거, scheme·host 소문자, 기본 포트(`http`의 `:80`, `https`의 `:443`) 제거, fragment(`#...`) 제거, 쿼리에서 `utm_`으로 시작하는 키 제거(나머지 키 순서·값 유지, 남은 키가 없으면 `?`도 제거), 빈 path는 `/`. 그 밖의 path는 건드리지 않는다(끝 `/` 추가·제거 없음).
    - `entry_key(entry: FeedEntry) -> str | None`
      - `guid`가 공백 제거 후 비어 있지 않으면 `"guid:" + guid.strip()`, 아니면 `link`가 비어 있지 않으면 `"link:" + normalize_link(link)`, 둘 다 없으면 `None`(식별 불가, 호출자가 건너뛰고 로그를 남긴다). 접두사로 guid 값과 link 값이 우연히 같아도 서로 다른 키가 된다.
  - acceptance
    - `uv run pytest -x tests/feeds/test_feeds.py` 통과. 최소 다음 경우를 포함(파라미터화 권장):
      `normalize_link("HTTPS://Example.COM:443/a/b?utm_source=x&id=1#top")` == `"https://example.com/a/b?id=1"`
      / `"http://example.com:80"` → `"http://example.com/"` / `"http://example.com:8080/x"`는 포트 유지 / `"https://e.com/a/?utm_medium=y"` → `"https://e.com/a/"`(끝 `/` 유지, `?` 제거)
      / 쿼리 순서 유지: `"https://e.com/p?b=2&a=1"` 그대로 / path 대소문자 유지: `"https://e.com/A"` 그대로 / 앞뒤 공백 제거
      / `entry_key`: guid 있음 → `"guid:abc"`(guid `"  abc "`) / guid가 `None`·`""`·`"  "`이면 link 기반 `"link:https://example.com/a"` / guid·link 둘 다 없음 → `None`
      / 같은 글을 가리키는 두 link(`"https://E.com/a#x"`, `"https://e.com/a?utm_source=rss"`)의 `entry_key`가 같음
      / `FeedEntry`가 frozen(속성 대입 시 `dataclasses.FrozenInstanceError`) / `FeedFetchError`·`FeedParseError`가 `FeedError` 하위
      / 프로토콜 적합성: 테스트 안의 가짜 fetcher 클래스(정해진 `FetchResult`를 돌려줌)를 `FeedFetcher` 타입 변수에 대입해 `fetch` 호출 결과 확인 (PRD 8 가짜 구현 대비)
    - `uv run pytest` 전체 통과(T3b 이후 153개 회귀 없음), 새 의존성 없음(`pyproject.toml`/`uv.lock` 변경 없음), `db.py`·`repo.py` 변경 없음
    - `feeds.py`는 `rss_wiki` 내부 모듈을 import하지 않는다.
  - touch: `src/rss_wiki/feeds.py`, `tests/feeds/`

- [x] T4r. 잘못된 link 처리와 `feeds.py` 테스트 보강 (T4 REVIEW 메모 해소, 10분 크기의 작은 항목, T5보다 먼저)
  - 내용
    - `src/rss_wiki/feeds.py` (PLAN M2 자체 결정 "외부 피드의 잘못된 link")
      - `normalize_link`: `parts.port`가 `ValueError`를 내면(포트가 숫자가 아니거나 범위 초과) 기본 포트 제거를 하지 않고, netloc의 `@` 뒤 부분(host:port 원문)을 소문자로 바꿔 쓴다. userinfo는 지금처럼 그대로 둔다. 나머지 처리(fragment·`utm_` 제거, 빈 path → `/`)는 동일하다.
      - `entry_key`: `normalize_link` 호출에서 `ValueError`가 나면(예: `urlsplit`이 거부하는 `http://[::1`) `None`을 돌려준다. guid가 있으면 link를 보지 않으므로 영향 없음.
      - 두 함수 독스트링에 위 동작을 적는다(`entry_key`: "예외를 던지지 않는다, 해석할 수 없는 link는 `None`").
    - `tests/feeds/test_feeds.py`
      - `normalize_link` 파라미터에 추가: `"https://E.com:abc/x#f"` → `"https://e.com:abc/x"`, `"https://e.com:99999/"` → `"https://e.com:99999/"`, `"https://e.com/a?utmost=1"` → 그대로(`utm_` 경계), `"http://[::1]:80/x"` → `"http://[::1]/x"`, `"https://u:p@E.com:443/a"` → `"https://u:p@e.com/a"`
      - `entry_key`: link `"https://e.com:abc/"` → `"link:https://e.com:abc/"`(예외 없음), link `"http://[::1"` → `None`, 같은 link에 guid `"g"`가 있으면 `"guid:g"`
      - `test_no_internal_imports`를 `ast`로 바꾼다: `feeds.py` 소스를 파싱해 `Import`/`ImportFrom` 노드를 모으고, `ImportFrom.level > 0`이거나 모듈 이름이 `rss_wiki`로 시작하는 import가 하나도 없음을 단언한다. 소스 경로는 `feeds.__file__`로 얻는다.
      - 가짜 fetcher가 받은 `etag`/`last_modified`를 속성에 기록하고, `fetch(url, etag="e1", last_modified="lm1")` 호출 뒤 기록값이 `"e1"`/`"lm1"`임을 단언한다.
  - acceptance
    - `uv run pytest -x tests/feeds/test_feeds.py` 통과, 위 경우가 모두 테스트로 존재
    - 변이 확인(IMPL.md에 결과 기록, 코드는 원복): (1) `startswith("utm_")` → `startswith("utm")` (2) IPv6 대괄호 복원(`feeds.py:69-70`) 제거 (3) userinfo 보존(`feeds.py:72-76`) 제거 (4) `feeds.py`에 `from . import db` 추가 (5) `normalize_link`의 포트 `ValueError` 처리 제거 — 다섯 경우 모두 테스트 하나 이상 실패
    - `uv run pytest` 전체 통과(T4 이후 176개 회귀 없음), 새 의존성 없음(`pyproject.toml`/`uv.lock` 변경 없음), `db.py`·`repo.py` 변경 없음
  - touch: `src/rss_wiki/feeds.py`, `tests/feeds/test_feeds.py`
  - 상태 메모(planner, 사이클 15): 사이클 14 evaluator PASS 12/12(184 passed, 변이 5종 잡힘). 선택 메모("잘못된 포트 + userinfo" 조합 케이스)는 T5에 작은 보강으로 넣음.

- [x] T5. `feeds.py` 파싱: `parse_feed`(RSS 2.0·Atom 1.0 → `ParsedFeed`) (T4r 다음, T4r REVIEW 메모 반영)
  - 내용
    - `uv add feedparser`로 런타임 의존성을 추가한다(자체 결정, PLAN M2 참고). 먼저 Python 3.15 환경에서 설치·`import feedparser`가 되는지 확인한다. 설치나 import가 실패하면 의존성을 추가하지 말고 표준 라이브러리 `xml.etree.ElementTree`로 RSS 2.0·Atom 1.0만 지원하는 구현으로 바꾸고, 그 사실과 실패 메시지를 IMPL.md에 기록한다(acceptance는 동일).
    - `parse_feed(data: bytes, *, url: str) -> ParsedFeed`
      - 피드 형식을 식별하지 못하면(feedparser의 `version`이 빈 값, 예: HTML 페이지) `FeedParseError`(메시지에 `url`). 형식은 식별됐지만 `bozo`인 경우(사소한 인코딩 경고 등)는 항목을 그대로 쓴다.
      - 각 항목: `guid`는 RSS `guid`/Atom `id`, `link`는 `urllib.parse.urljoin(url, link)`로 절대 URL화(단, `urljoin`이 `ValueError`를 내는 잘못된 link — 예: `http://[::1`, NFKC 위반 netloc — 는 앞뒤 공백만 제거한 원문을 그대로 두고 피드 전체를 실패시키지 않는다. 자체 결정, T4r REVIEW 메모. 이 경우 guid가 없으면 `entry_key`(T4r)가 `None`을 돌려 호출자가 건너뛴다), `title`이 없거나 공백이면 `"(제목 없음)"`, `published`는 `published_parsed` → 없으면 `updated_parsed`를 UTC `datetime`의 `isoformat()`으로(둘 다 없으면 `None`), `content`는 첫 `content` 항목의 값, `summary`는 `summary`(없으면 `None`).
      - 항목 순서는 피드에 나온 순서 그대로 둔다(첫 수집 최근 10개 선정은 T7에서 `published` 기준으로 판단).
      - 독스트링에 `Raises: FeedParseError`와 "항목 하나의 잘못된 link는 예외 없이 원문 유지"를 적는다.
    - 테스트는 `tests/feeds/` 안의 인라인 바이트 문자열(또는 `tests/feeds/fixtures/`의 작은 XML 파일)을 쓴다. 네트워크 없음.
    - (작은 보강, T4r REVIEW 선택 메모) `test_normalize_link` 파라미터에 `"https://U:P@E.com:abc/x"` → `"https://U:P@e.com:abc/x"` 케이스를 추가한다(잘못된 포트 분기의 userinfo 보존·대소문자 유지 확인). `normalize_link` 코드는 바꾸지 않는다.
  - acceptance
    - `uv run pytest -x tests/feeds/` 통과. 최소 다음 경우를 포함:
      RSS 2.0(항목 2개, `guid`·`pubDate`·`description`·`content:encoded`) → 제목·항목 수·`guid`·`content`·`summary` 일치, `published`가 `"2026-11-20T00:00:00+00:00"` 형식
      / Atom 1.0(`id`·`updated`만 있고 `published` 없음) → `published`가 `updated` 값, `link`가 `rel="alternate"` href
      / 상대 링크 `<link>/posts/1</link>`가 `url="https://example.com/feed.xml"` 기준 `"https://example.com/posts/1"`로 바뀜
      / 제목 없는 항목 → `"(제목 없음)"` / 날짜 없는 항목 → `published is None`
      / HTML(`b"<html><body>hi</body></html>"`)·빈 바이트 → `FeedParseError`이고 메시지에 url 포함
      / 한국어 제목(UTF-8) 그대로 보존
      / `parse_feed` 결과 항목에 `entry_key`(T4)를 적용하면 guid 있는 항목은 `guid:`, 없는 항목은 `link:` 키
      / 잘못된 link: guid 없는 항목의 `<link>http://[::1</link>`와 정상 항목이 함께 있는 RSS → `parse_feed`가 예외 없이 두 항목을 모두 돌려주고, 잘못된 항목의 `link == "http://[::1"`, `entry_key(...) is None`, 정상 항목은 `link:` 키
      / `test_normalize_link`의 `"https://U:P@E.com:abc/x"` 케이스(위 작은 보강)
    - 변이 확인(IMPL.md에 결과 기록, 코드는 원복): (1) `urljoin`의 `ValueError` 처리 제거 (2) `published_parsed` → `updated_parsed` 대체 제거 (3) 형식 미식별 시 `FeedParseError` 대신 빈 `ParsedFeed` 반환 — 세 경우 모두 테스트 하나 이상 실패
    - `uv run python -c "import rss_wiki.feeds"` 종료 코드 0
    - `uv run pytest` 전체 통과(T4r 이후 184개 회귀 없음). feedparser를 쓴 경우 `pyproject.toml`의 `dependencies`에 `feedparser`만 추가되고 그 밖의 의존성 변경 없음. `db.py`·`repo.py` 변경 없음
  - touch: `src/rss_wiki/feeds.py`, `tests/feeds/`, `pyproject.toml`, `uv.lock`
  - 상태 메모(planner, 사이클 16): 사이클 15 evaluator PASS 11/12(191 passed, acceptance 변이 3종 잡힘). 감점 사유(bozo 허용 분기 미검증)와 선택 메모(빈 guid·채널 title 없음·잘못된 link strip 고정)는 T6 앞부분 보강으로 넣음. content-only 피드의 `summary` 중복은 T8, `javascript:` link는 M4/M5 자체 결정으로 넘김(PLAN).

- [x] T6. `feeds.py` 실제 가져오기: `HttpFeedFetcher` (조건부 요청·타임아웃·User-Agent, T5 다음, 새 의존성 없음, T5 REVIEW 메모 반영)
  - 내용
    - (먼저 처리, T5 REVIEW 메모, `parse_feed` 코드 변경 없음, 테스트만 추가) `tests/feeds/test_feeds.py`
      - bozo 피드: `<title>a&nbsp;b</title>`처럼 형식은 식별되지만 bozo인 RSS 2.0(항목 1개 이상) → 테스트 안에서 먼저 `feedparser.parse(data).bozo`가 참이고 `version`이 비어 있지 않음을 단언한 뒤, `parse_feed`가 예외 없이 항목을 돌려주는지 확인한다. (`parse_feed`에 `if d.bozo: raise FeedParseError(...)`를 넣는 변이를 잡아야 한다)
      - 자체 결정 고정(선택 메모, 빈 값 → `None`): `<guid></guid>`인 항목 → `guid is None` / 채널 `<title></title>`(빈 요소)인 RSS → `ParsedFeed.title is None` / `<description></description>`(빈 요소)이고 `content:encoded`도 없는 항목 → `summary is None` / `<link>  http://[::1  </link>`(guid 없음) → `link == "http://[::1"`(strip된 원문). 빈 요소를 쓰는 이유: 요소가 아예 없으면 feedparser가 이미 `None`/키 없음을 주어 `or None` 제거 변이를 못 잡는다. (`content:encoded`만 있으면 feedparser가 `summary`에 본문을 채우므로 섞지 않는다)
    - HTTP 계층 분리(자체 결정, 표준 라이브러리 `urllib.request`만 사용)
      - `@dataclass(frozen=True) class HttpResponse`: `status: int`, `headers: Mapping[str, str]`(키 대소문자 무시 조회를 위해 저장 시 키를 소문자로), `body: bytes`, `url: str`(리다이렉트 후 최종 URL)
      - `HttpGet = Callable[[str, Mapping[str, str], float], HttpResponse]` (url, 요청 헤더, 타임아웃 초)
      - `urllib_get(url, headers, timeout) -> HttpResponse`: `urllib.request.urlopen(Request(url, headers=headers), timeout=timeout)`. `HTTPError`(304 포함)는 예외로 두지 않고 그 `code`·헤더로 `HttpResponse(body=b"")`를 만든다. `URLError`·`TimeoutError`·`OSError`·`http.client.HTTPException`은 url과 원인을 담은 `FeedFetchError`로 바꾼다(`from` 체인 유지).
    - `DEFAULT_USER_AGENT = "rss-wiki/0.1"` (일반 클라이언트명, 개인 정보 없음, PRD 6)
    - `class HttpFeedFetcher`: `__init__(self, *, timeout: float, user_agent: str = DEFAULT_USER_AGENT, http_get: HttpGet = urllib_get)`, `timeout <= 0`이면 `ValueError`. `FeedFetcher` 프로토콜을 만족한다.
      - `fetch(url, *, etag=None, last_modified=None)`: 헤더 `User-Agent`, `etag`가 있으면 `If-None-Match`, `last_modified`가 있으면 `If-Modified-Since`.
      - 304 → `FetchResult(not_modified=True, feed=None, etag=응답 ETag 또는 전달받은 etag, last_modified=응답 Last-Modified 또는 전달받은 값)`
      - 200~299 → `parse_feed(body, url=response.url)`, `FetchResult(not_modified=False, feed=..., etag=응답 ETag 또는 None, last_modified=응답 Last-Modified 또는 None)`. 파싱 실패는 `FeedParseError` 그대로 전파.
      - 그 밖의 상태 코드 → 상태 코드와 url을 담은 `FeedFetchError`
    - 호스트별 요청 간격은 이번 범위가 아니다(T9).
  - acceptance
    - `uv run pytest -x tests/feeds/` 통과. 가짜 `http_get`(받은 url·헤더·타임아웃을 기록하고 정해진 `HttpResponse`를 돌려줌)으로 최소 다음 경우를 포함:
      etag·last_modified 없이 호출 → 헤더에 `User-Agent`만(조건부 헤더 없음), 타임아웃 값 전달 / 둘 다 주면 `If-None-Match`·`If-Modified-Since` 전달
      / 304 → `not_modified is True`, `feed is None`, 응답에 ETag가 없으면 전달받은 etag 유지
      / 200 + RSS 바이트 → `feed.entries` 개수 일치, 응답 `ETag`·`Last-Modified`(헤더 대소문자 달라도) 반영
      / 200 + 상대 link 피드에서 `response.url`(리다이렉트 후 URL) 기준으로 절대화됨
      / 404·500 → `FeedFetchError`, 메시지에 상태 코드와 url / 200 + HTML → `FeedParseError`
      / `timeout=0` → `ValueError`
      / `urllib_get`: `monkeypatch`로 `urllib.request.urlopen`을 바꿔 `URLError`·`TimeoutError`를 던지면 `FeedFetchError`(`__cause__` 유지), `HTTPError(304)`를 던지면 `status == 304`인 `HttpResponse` (실제 네트워크 없음)
      / `HttpFeedFetcher(...)`를 `FeedFetcher` 타입 변수에 대입
      / 위 bozo 테스트와 빈 값 → `None` 고정 케이스 4건(T5 REVIEW 메모)
    - 변이 확인(IMPL.md에 결과 기록, 코드는 원복): (1) `parse_feed`에 `if d.bozo: raise FeedParseError(url)` 삽입 (2) guid의 `or None` 제거(`feeds.py:151`) (3) 피드 title의 `or None` 제거(`:159`) (4) summary의 `or None` 제거(`:156`) (5) `_absolute`의 `except` 분기 `.strip()` 제거(`:129`) (6) `HttpFeedFetcher.fetch`에서 `If-None-Match` 헤더 생략 (7) 304에서 전달받은 etag 대신 `None` 반환 — 일곱 경우 모두 테스트 하나 이상 실패
    - `uv run pytest` 전체 통과(T5 이후 191개 회귀 없음), 새 의존성 없음(`pyproject.toml`/`uv.lock` 변경 없음), `db.py`·`repo.py` 변경 없음, `feeds.py`는 `rss_wiki` 내부 모듈을 import하지 않음(`test_no_internal_imports` 유지)
  - touch: `src/rss_wiki/feeds.py`, `tests/feeds/`
  - 상태 메모(planner, 사이클 17): 사이클 16 evaluator PASS 10/12(211 passed, acceptance 변이 7종 잡힘, 로컬 서버 탐침 정상). 감점 사유(URL 입력 예외 누출, `urllib_get` 성공 경로 미검증, 헤더 정규화 위치)는 T6r로 넘겼다. 본문 크기 상한은 T9로 넘겼다(PLAN).

- [x] T6r. `HttpFeedFetcher` 견고성 보강: URL 입력 오류 포장·비ASCII 인코딩·헤더 정규화 위치·`urllib_get` 성공 경로 테스트 (T6 REVIEW 메모 해소, 10~15분 크기의 작은 항목, T7보다 먼저, 새 의존성 없음)
  - 내용
    - `src/rss_wiki/feeds.py` (PLAN M2 자체 결정 "피드 URL의 비ASCII 문자", "응답 헤더 키 소문자 정규화")
      - `_encode_url(url: str) -> str`(내부 함수): `urllib.parse.urlsplit` 뒤 path와 query를 각각 `urllib.parse.quote(part, safe="/%:@!$&'()*+,;=~")`로 인코딩하고 `urlunsplit`으로 다시 묶는다. 이미 있는 `%XX`는 유지된다(이중 인코딩 없음). scheme·netloc은 바꾸지 않는다. ASCII URL은 결과가 원래 URL과 같다.
      - `urllib_get`: `_encode_url(url)` 호출, `urllib.request.Request(...)` 생성, `urlopen`을 **모두 같은 `try` 안에** 둔다. 기존 예외 매핑에 `ValueError`(`UnicodeEncodeError` 포함)를 추가해 url과 원인을 담은 `FeedFetchError`로 바꾼다(`from` 체인 유지). `HTTPError` 분기는 그대로 둔다(`HTTPError`는 `URLError` 하위이므로 `except` 순서를 유지한다). 독스트링 `Raises:`에 "잘못된 URL"을 추가한다.
      - `HttpResponse`: `__post_init__`에서 `headers`를 키 소문자 `dict`로 바꿔 `object.__setattr__`으로 다시 넣는다. `urllib_get`의 `_lower_headers` 호출은 `dict(msg.items())`로 바꾸거나 그대로 둬도 된다(정규화의 정본은 `HttpResponse`). `headers` 필드 주석을 "생성 시 키를 소문자로 정규화"로 고친다.
    - `tests/feeds/test_feeds.py` (가짜 `urlopen`은 `monkeypatch.setattr(urllib.request, "urlopen", fake)`로 바꾸고 실제 네트워크는 쓰지 않는다. `fake`는 받은 `Request`와 `timeout`을 기록하고, `status`·`headers`(`email.message.Message` 또는 `http.client.HTTPMessage`)·`read()`·`geturl()`·컨텍스트 매니저를 갖춘 객체를 돌려준다.)
      - 성공 경로: `urllib_get("https://e.com/feed", {"User-Agent": "ua/1", "If-None-Match": "e1"}, 7.5)` → 기록된 `Request.get_header("User-agent") == "ua/1"`, `get_header("If-none-match") == "e1"`, 기록된 `timeout == 7.5`, 응답 헤더 `ETag: X`가 결과 `headers["etag"] == "X"`, `geturl()`이 `"https://e.com/final"`이면 결과 `url == "https://e.com/final"`, `body`가 `read()` 값
      - 사용자 지정 User-Agent: `HttpFeedFetcher(timeout=1, user_agent="custom/9", http_get=가짜)` → 가짜가 받은 `User-Agent == "custom/9"`
      - 헤더 정규화: `HttpResponse(200, {"ETag": "X", "Last-Modified": "LM"}, RSS 바이트, url)`를 돌려주는 가짜 `http_get`으로 `fetch` → `etag == "X"`, `last_modified == "LM"`. 304 응답에서도 같은 방식으로 `{"ETag": "Y"}` → `etag == "Y"`. `HttpResponse(...).headers`의 키가 모두 소문자임을 직접 단언
      - 비ASCII URL: 가짜 `urlopen`으로 `urllib_get("https://e.com/tag/한글/feed?q=값", {}, 1)` → 예외 없이 응답, 기록된 `Request.full_url`이 `"https://e.com/tag/%ED%95%9C%EA%B8%80/feed?q=%EA%B0%92"`. 이미 인코딩된 `"https://e.com/a%20b"`는 그대로(`%2520` 아님)
      - 잘못된 URL: 가짜 `urlopen`을 둔 상태에서 `"not a url"`, `"http://[::1"` → `FeedFetchError`, 메시지에 원래 url 포함, `__cause__`가 `ValueError`(파라미터화). `HttpFeedFetcher(timeout=1).fetch("not a url")`(기본 `urllib_get`, 가짜 `urlopen`)도 `FeedFetchError`
      - 예외 매핑(파라미터화): 가짜 `urlopen`이 `ConnectionResetError()`·`http.client.IncompleteRead(b"")`를 던지면 `FeedFetchError`이고 `__cause__` 유지
      - 2xx 경계(가짜 `http_get`, 본문은 RSS 바이트): `204`·`299` → `not_modified is False`이고 `feed`가 있음, `300` → `FeedFetchError`(메시지에 `300`)
  - acceptance
    - `uv run pytest -x tests/feeds/` 통과, 위 경우가 모두 테스트로 존재
    - 변이 확인(IMPL.md에 결과 기록, 코드는 원복, 작업 트리를 바꾸지 않는 임시 복사본 방식 권장): (1) `Request`에 headers를 넘기지 않음 (2) `urlopen`에 `timeout`을 넘기지 않음 (3) `HttpResponse.__post_init__`의 소문자화 제거(`urllib_get`의 `_lower_headers`를 남겼다면 함께 제거) (4) `resp.geturl()` 대신 요청 url 사용 (5) `fetch`가 `self._user_agent` 대신 `DEFAULT_USER_AGENT` 사용 (6) 예외 매핑에서 `ValueError` 제거 (7) `_encode_url` 호출 제거 (8) `OSError` 제외 (9) `http.client.HTTPException` 제외 (10) 성공 판정 `< 300` → `<= 300` (11) 성공 판정을 `== 200`으로 좁힘 — 열한 경우 모두 테스트 하나 이상 실패
    - `uv run pytest` 전체 통과(T6 이후 211개 회귀 없음), 새 의존성 없음(`pyproject.toml`/`uv.lock` 변경 없음), `db.py`·`repo.py` 변경 없음, `test_no_internal_imports` 유지
  - touch: `src/rss_wiki/feeds.py`, `tests/feeds/test_feeds.py`
  - 상태 메모(planner, 사이클 18): 사이클 17 evaluator PASS 11/12(`tests/feeds` 69 passed, 전체 222 passed, acceptance 변이 11종 잡힘). 감점 사유(`file://` URL의 로컬 파일 읽기와 `TypeError` 누출)와 선택 메모(`HTTPError.headers is None`)는 T6s로 넘겼다(PLAN M2 자체 결정 "피드 URL scheme").

- [x] T6s. 피드 URL scheme 제한과 응답 방어 (T6r REVIEW 메모 해소, 5~10분 크기의 작은 항목, T7보다 먼저, 새 의존성 없음)
  - 내용
    - `src/rss_wiki/feeds.py` (PLAN M2 자체 결정 "피드 URL scheme은 `http`/`https`만")
      - 내부 함수 `_require_http_url(url: str) -> None`: `urllib.parse.urlsplit(url).scheme.lower()`가 `http`·`https`가 아니면 url과 허용 scheme을 담은 `FeedFetchError`를 낸다. `urlsplit` 자체가 `ValueError`를 내면 같은 `FeedFetchError`로 바꾼다(`from` 체인 유지).
      - `HttpFeedFetcher.fetch`: 헤더를 만들기 전, `self._http_get` 호출 전에 `_require_http_url(url)`을 부른다(거부된 URL은 `http_get`이 호출되지 않음).
      - `urllib_get`: 함수 첫머리(`Request`·`urlopen` 전)에서 `_require_http_url(url)`을 부른다.
      - `fetch`: `resp.status`가 `int`가 아니면 304·2xx 판정보다 앞에서 url과 받은 값(`repr`)을 담은 `FeedFetchError`를 낸다.
      - `urllib_get`의 `HTTPError` 분기: `_lower_headers(e.headers or {})`로 바꿔 `headers`가 `None`이어도 빈 헤더 응답을 만든다.
      - `fetch`·`urllib_get` 독스트링 `Raises:`에 "http/https 이외의 scheme"을 추가한다.
    - `tests/feeds/test_feeds.py`
      - 거부 scheme(파라미터화): `tmp_path`에 실제로 만든 파일의 `Path.as_uri()`(`file://...`), `"ftp://x/y"`, `"javascript:alert(1)"`, `"//e.com/feed"`(scheme 없음) → `HttpFeedFetcher(timeout=1, http_get=기록용 가짜).fetch(url)`가 `FeedFetchError`, 메시지에 url 포함, 가짜 `http_get` 호출 0회
      - 같은 입력으로 `urllib_get(url, {}, 1)`(가짜 `urlopen`을 `monkeypatch`) → `FeedFetchError`, 가짜 `urlopen` 호출 0회
      - 허용 scheme 대소문자: `"HTTPS://e.com/feed"`·`"Http://e.com/feed"` → 가짜 `http_get`이 호출되고 정상 `FetchResult`
      - 비정수 status: `HttpResponse(status=None, headers={}, body=RSS 바이트, url=...)`를 돌려주는 가짜 `http_get` → `FeedFetchError`(`TypeError` 아님)
      - `HTTPError` 헤더 없음: 가짜 `urlopen`이 `urllib.error.HTTPError(url, 304, "nm", None, None)`을 던지면 `urllib_get` 결과가 `status == 304`, `headers == {}`
  - acceptance
    - `uv run pytest -x tests/feeds/` 통과, 위 경우가 모두 테스트로 존재
    - 변이 확인(IMPL.md에 결과 기록, 코드는 원복, 임시 복사본 방식 권장): (1) `fetch`의 `_require_http_url` 호출 제거 (2) `urllib_get`의 `_require_http_url` 호출 제거 (3) `_require_http_url`의 `.lower()` 제거 (4) 비정수 `status` 방어 제거 (5) `e.headers or {}`를 `e.headers`로 되돌림 — 다섯 경우 모두 테스트 하나 이상 실패
    - `uv run pytest` 전체 통과(T6r 이후 222개 회귀 없음), 새 의존성 없음(`pyproject.toml`/`uv.lock` 변경 없음), `db.py`·`repo.py` 변경 없음, `test_no_internal_imports` 유지
  - touch: `src/rss_wiki/feeds.py`, `tests/feeds/test_feeds.py`
  - 상태 메모(planner, 사이클 19): 사이클 18 evaluator PASS 11/12(`tests/feeds` 82 passed, 전체 235 passed, 의미 있는 변이 4종 잡힘, 실제 `file://` 탐침 해소). 변이 (3) `.lower()` 제거는 `urlsplit`이 scheme을 이미 소문자로 돌려주기 때문에 동작이 같은 동치 변이라 제외했다. 감점 사유(`bool` status 거부 미테스트)는 T7 앞부분의 작은 보강으로 넘겼다.

- [x] T7. `repo.py` 피드 상태 기록 (T6s 다음, 작은 항목, 새 의존성 없음, 스키마 불변, T6s REVIEW 메모 반영)
  - 내용
    - (먼저 처리, T6s REVIEW 메모, 테스트만 추가하고 `feeds.py`는 바꾸지 않음) `tests/feeds/test_feeds.py`의 비정수 status 테스트 옆에 `HttpResponse(status=True, headers={}, body=RSS 바이트, url=URL)`을 돌려주는 가짜 `http_get`으로 `fetch` → `FeedFetchError` 케이스 1건을 추가한다(`True == 1`이 정수로 통과하지 않음을 고정, PLAN M2 자체 결정).
    - `src/rss_wiki/repo.py` (PRD 4.1 조건부 요청 값 보관, PRD 7 피드 실패 기록)
      - `record_feed_success(conn, feed_id, *, etag: str | None, last_modified: str | None) -> None`: `etag`·`last_modified`를 주어진 값으로 저장(304여도 T6의 `FetchResult` 값을 그대로 넘기면 됨), `last_error = NULL`, `consecutive_failures = 0`.
      - `record_feed_failure(conn, feed_id, error: str) -> int`: `last_error = error`, `consecutive_failures`를 1 올리고 올린 값을 반환. `etag`·`last_modified`는 바꾸지 않는다(다음 실행에서 조건부 요청 유지). `error`가 `str`이 아니거나 공백뿐이면 DB 접근 전에 `ValueError`.
      - `mark_initial_fetch_done(conn, feed_id) -> None`: `initial_fetch_done = 1`. 이미 1이어도 오류 없음(멱등).
      - 세 함수 모두 없는 `feed_id`면 `with conn:` 안에서 `FeedNotFoundError`(T3r 규칙, rowcount 검사, 롤백되어 부작용 없음). 독스트링 `Raises:`에 적는다.
    - `tests/repo/test_repo.py`
      - 기존 커밋 테스트 파라미터에 세 함수를 추가한다.
  - acceptance
    - `uv run pytest -x tests/repo/` 통과. 최소 다음 경우를 포함:
      `record_feed_failure` 2회 → 반환값 1, 2, `consecutive_failures == 2`, `last_error`가 마지막 메시지, 사전에 넣은 `etag` 그대로
      / 이어서 `record_feed_success(etag="e2", last_modified="lm2")` → `consecutive_failures == 0`, `last_error is None`, `etag == "e2"`, `last_modified == "lm2"`
      / `record_feed_success(etag=None, last_modified=None)` → 두 값이 `None`으로 저장됨
      / `mark_initial_fetch_done` 2회 호출 → 오류 없이 `initial_fetch_done == 1`
      / 없는 id(999)로 세 함수 → `FeedNotFoundError`(파라미터화), 예외 후 `conn.in_transaction is False`
      / `record_feed_failure(conn, fid, "  ")`·`(conn, fid, None)` → `ValueError`, 피드 행 불변
      / 커밋 테스트 파라미터 3건(두 번째 연결에서 결과 보임)
    - `uv run python -c "import rss_wiki.repo as r, sys; sys.exit(0 if all('FeedNotFoundError' in (f.__doc__ or '') for f in (r.record_feed_success, r.record_feed_failure, r.mark_initial_fetch_done)) else 1)"` 종료 코드 0
      / `uv run pytest -x tests/feeds/` 통과, `status=True` 케이스 존재
    - 변이 확인(IMPL.md에 결과 기록, 코드는 원복, 임시 복사본 방식 권장): (1) `record_feed_failure`가 `etag`를 `NULL`로 지움 (2) `record_feed_success`가 `consecutive_failures`를 초기화하지 않음 (3) `record_feed_failure`의 `with conn:` 제거 (4) `feeds.py:283`의 `or isinstance(resp.status, bool)` 제거 — 네 경우 모두 테스트 하나 이상 실패
    - `uv run pytest` 전체 통과(T6s 이후 235개 회귀 없음), 새 의존성 없음, `db.py`·`feeds.py` 변경 없음(스키마 `_V1` 불변)
  - touch: `src/rss_wiki/repo.py`, `tests/repo/test_repo.py`, `tests/feeds/test_feeds.py`(테스트 1건만)
  - 상태 메모(planner, 사이클 20): 사이클 19 evaluator PASS 12/12(`tests/repo` 85 passed, 전체 248 passed, 의미 있는 변이 3종과 추가 변이 4종 잡힘). 변이 (4)는 동치 변이였다. REVIEW 메모(빈 메시지 `FeedError`의 `ValueError` 누출 방지, `caplog` 건수·url 단언, bool 분기 메시지 고정)는 T7b에 넣었다.

- [x] T7b. 피드 1개 수집 `collect_feed` (`pipeline.py` 신규, T7 다음, 새 의존성 없음, 스키마 불변, T7 REVIEW 메모 반영)
  - 내용 (PLAN M2 자체 결정 "피드 하나의 수집 흐름은 `pipeline.py`")
    - `src/rss_wiki/pipeline.py`를 만든다. `feeds`·`repo`만 import한다(`config`·네트워크 직접 호출 없음, fetcher는 인자로 주입).
    - `@dataclass(frozen=True) class CollectResult`: `feed_id: int`, `ok: bool`, `not_modified: bool`, `new_ids: tuple[int, ...]`(이번에 `new`로 저장한 글 id), `skipped_backfill: int`, `skipped_unidentified: int`, `error: str | None`
    - `collect_feed(conn, feed_row, fetcher, *, first_fetch_limit: int) -> CollectResult`
      - `first_fetch_limit < 1`이면 DB·fetcher 접근 전에 `ValueError`.
      - `fetcher.fetch(feed_row["url"], etag=feed_row["etag"], last_modified=feed_row["last_modified"])`
      - `FeedError`가 나면 오류 문자열 `error = str(e).strip() or type(e).__name__`(메시지가 빈 `FeedFetchError()`도 `record_feed_failure`의 공백 거부 `ValueError`에 걸리지 않게, 자체 결정, T7 REVIEW 메모)을 만들어 `repo.record_feed_failure(conn, id, error)` 후 `ok=False`, `error=error`인 결과를 돌려준다(예외를 밖으로 던지지 않음, PRD 7). `FeedError`가 아닌 예외는 그대로 전파한다.
      - `not_modified`이면 `record_feed_success(etag, last_modified)`만 하고 `ok=True, not_modified=True`(글 저장 없음).
      - 그 밖에는 항목마다 `feeds.entry_key`를 계산한다. `None`이면 건너뛰고 피드 url·항목 제목을 담은 `logging.getLogger(__name__).warning`을 남긴다(`skipped_unidentified` +1).
      - 첫 수집(`feed_row["initial_fetch_done"] == 0`)이면 식별된 항목을 `published` 내림차순(`None`은 가장 오래된 것으로 취급, 동률이면 피드 순서 유지)으로 정렬해 앞의 `first_fetch_limit`개만 `status="new"`, 나머지는 `status="skipped_backfill"`로 `insert_article_if_new` 한다. 첫 수집이 아니면 모두 `new`.
      - 이미 있는 글(`insert_article_if_new`가 `None`)은 건너뛰며 어떤 카운트에도 넣지 않는다(멱등, PRD 8).
      - 저장 후 `record_feed_success(etag, last_modified)`, 첫 수집이면 `mark_initial_fetch_done`.
      - 쓰기는 repo 함수별 개별 트랜잭션이다(PLAN 자체 결정, 중간 중단 시 다음 실행에서 첫 수집으로 다시 처리됨을 독스트링에 적는다).
    - (작은 보강, T7 REVIEW 선택 메모, `feeds.py` 코드 변경 없음) `tests/feeds/test_feeds.py`의 `test_fetch_bool_status_rejected`에 `match="잘못된 HTTP 상태"`를 넣어 `feeds.py:283`의 bool 분기를 고정한다.
  - acceptance
    - `uv run pytest -x tests/pipeline/test_collect.py` 통과. 가짜 fetcher(정해진 `FetchResult`를 돌려주거나 `FeedFetchError`를 던지고, 받은 인자를 기록)와 `tmp_path` DB로 최소 다음 경우를 포함:
      첫 수집, 날짜가 서로 다른 항목 12개, `first_fetch_limit=10` → 최신 10개 `new`, 오래된 2개 `skipped_backfill`, `initial_fetch_done == 1`, 결과 `len(new_ids) == 10`, `skipped_backfill == 2`
      / `published is None` 항목은 backfill 쪽으로 먼저 밀림
      / 같은 `FetchResult`로 두 번째 호출 → 새 글 0건, 글 행 수 불변(멱등). 이어서 **가장 오래된 `published`**(기존 12개보다 이른 날짜)의 새 항목 1개를 추가한 결과로 세 번째 호출 → 첫 수집이 아니므로 그 1개가 `new`(첫 수집으로 잘못 판정하면 `skipped_backfill`이 되어 변이 (2)를 잡는다), `new_ids` 길이 1
      / 두 번째 이후 호출은 `repo.get_feed`로 다시 읽은 행을 넘기고, 저장된 etag·last_modified가 fetcher 인자로 전달됨
      / `not_modified` 결과 → 글 저장 없음, `consecutive_failures == 0`, etag 유지
      / `FeedFetchError` → 예외 없이 `ok is False`, `error`에 메시지, 피드의 `consecutive_failures == 1`·`last_error` 기록, 기존 etag 유지
      / `FeedParseError`도 같은 실패 처리 / `RuntimeError`를 던지는 fetcher → 예외 전파
      / 메시지가 빈 `FeedFetchError()`를 던지는 fetcher → 예외 없이 `ok is False`, `error == "FeedFetchError"`, 피드 `last_error == "FeedFetchError"`, `consecutive_failures == 1` (T7 REVIEW 메모)
      / guid·link 둘 다 없는 항목 → 저장 안 됨, `skipped_unidentified == 1`, `caplog`에서 logger 이름이 `rss_wiki.pipeline`이고 레벨이 `WARNING`인 레코드가 **정확히 1건**이며 그 메시지에 피드 url이 들어 있음 (T4r·T7 REVIEW 메모)
      / `first_fetch_limit=0` → `ValueError`, fetcher 호출 0회
    - `uv run pytest -x tests/feeds/` 통과, `test_fetch_bool_status_rejected`에 `match="잘못된 HTTP 상태"` 존재
    - 변이 확인(IMPL.md에 결과 기록, 코드는 원복, 임시 복사본 방식): (1) 정렬을 오름차순으로 (2) 첫 수집 판정 무시(항상 첫 수집 취급) (3) `FeedError` 분기에서 `record_feed_failure` 생략 (4) `mark_initial_fetch_done` 생략 (5) 경고 로그 제거 (6) 빈 메시지 대체(`or type(e).__name__`) 제거 (7) `feeds.py:283`의 `or isinstance(resp.status, bool)` 제거 — 일곱 경우 모두 테스트 하나 이상 실패 (모두 동작이나 메시지를 바꾸는 변이다. PLAN "acceptance 작성 규칙")
    - `uv run pytest` 전체 통과(T7 이후 248개 회귀 없음), 새 의존성 없음, `db.py`·`repo.py`·`feeds.py` 변경 없음, `pipeline.py`는 `rss_wiki` 안에서 `feeds`·`repo`만 import
  - touch: `src/rss_wiki/pipeline.py`, `tests/pipeline/`, `tests/feeds/test_feeds.py`(`match=` 한 줄만)
