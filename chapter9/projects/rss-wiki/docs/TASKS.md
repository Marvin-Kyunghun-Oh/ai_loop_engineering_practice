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
