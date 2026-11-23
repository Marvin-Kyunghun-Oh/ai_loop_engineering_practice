# IMPL — T3b `repo.py` 처리 대상 조회와 실행 이력

## 처리한 항목
- T3b (TASKS.md 체크 완료)

## 변경 파일
- `src/rss_wiki/repo.py`: `RUN_STATUSES`, `RunNotFoundError`, `list_articles_to_process`, `count_articles_by_status`, `list_failed_articles`, `start_run`, `finish_run`, `get_latest_run`, `abort_running_runs` 추가
- `tests/repo/test_repo.py`: 처리 대상·상태 집계·실패 목록·실행 이력 테스트, 커밋 테스트에 `start_run`/`finish_run`/`abort_running_runs` 3건 추가, 따옴표 리터럴 검색 테스트 1건

## 검증 결과
- `uv run pytest -x` → 153 passed (기존 133개 회귀 없음)
- Raises 문서화 확인 명령 종료 코드 0
- 변이 확인(모두 코드 원복, 원복 후 153 passed)
  1. `limit < 1` → `limit < 0`: 1 failed (limit=0 케이스)
  2. `attempts < ?` → `attempts <= ?`: 1 failed
  3. `finish_run`의 `with conn:` 제거: 2 failed (커밋 테스트 + 미존재 run 롤백/트랜잭션 테스트)
- `db.py` 변경 없음, 스키마 `_V1` 불변, 새 의존성 없음

## 참고
- 자체 결정: `list_failed_articles`는 요구 컬럼 외에 `updated_at`도 포함한다.
- 자체 결정: `finish_run`은 `status='running'`도 거부한다(마감 함수이므로).
