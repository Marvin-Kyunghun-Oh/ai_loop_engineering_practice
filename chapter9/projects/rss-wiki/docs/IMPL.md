# IMPL

## 처리한 항목
T7b. 피드 1개 수집 `collect_feed` (`pipeline.py` 신규)

## 변경 파일
- `src/rss_wiki/pipeline.py` (신규: `CollectResult`, `collect_feed`; `feeds`·`repo`만 import)
- `tests/pipeline/test_collect.py` (신규, 12건)
- `tests/feeds/test_feeds.py` (`test_fetch_bool_status_rejected`에 `match="잘못된 HTTP 상태"` 한 줄)

## 검증
- `uv run pytest -x tests/pipeline/test_collect.py tests/feeds/` 93 passed
- `uv run pytest` 전체 258 passed (회귀 없음), `db.py`·`repo.py`·`feeds.py` 변경 없음, 새 의존성 없음
- 변이 확인(임시 수정 후 원복), 모두 테스트 실패로 잡힘:
  (1) 정렬 오름차순 2 failed / (2) 첫 수집 항상 취급 1 failed / (3) `record_feed_failure` 생략 3 failed
  (4) `mark_initial_fetch_done` 생략 2 failed / (5) 경고 로그 제거 1 failed / (6) 빈 메시지 대체 제거 1 failed
  (7) `feeds.py`의 bool status 검사 제거 1 failed (match 고정 덕에 잡힘)

## 참고
- 자체 결정: `published`는 ISO8601 문자열이라 사전식 비교로 정렬(`None`은 `""`로 가장 오래됨, stable 정렬로 동률은 피드 순서 유지).
- 자체 결정: `result.not_modified` 이거나 `feed is None`이면 not_modified 경로로 처리.
- 새 의존성 없음.
