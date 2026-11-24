# REVIEW

- 평가 대상: T7. `repo.py` 피드 상태 기록 (`record_feed_success`·`record_feed_failure`·`mark_initial_fetch_done`, `fetch`의 `status=True` 거부 테스트 1건)
- 평가일: 2026-11-24 (evaluator, 사이클 19)
- 화면 유무: 없음 (화면 완성도 축 제외, 12점 만점)

## 직접 확인한 내용

| 확인 | 결과 |
|---|---|
| `uv run pytest -x tests/repo/` | 85 passed (1.54s) |
| `uv run pytest -x tests/feeds/` | 83 passed (0.27s). `test_fetch_bool_status_rejected`가 있다(`tests/feeds/test_feeds.py:550-553`) |
| `uv run pytest` (전체) | 248 passed (2.34s). T6s 이후 235개에 회귀가 없고, IMPL.md 보고와 같다 |
| 독스트링 확인 명령(`FeedNotFoundError` 포함 여부) | 종료 코드 0 |
| touch 범위 대조 (`git diff`, 파일 수정 시각) | 이번 코드 변경은 `src/rss_wiki/repo.py`(+54줄, `:83-134`), `tests/repo/test_repo.py`(+83줄), `tests/feeds/test_feeds.py`(테스트 1건)뿐이다. `feeds.py`는 미추적 파일이라 diff로 볼 수 없다. 그래서 수정 시각을 봤고(12:15:54), T6s 평가(12:18:48)보다 앞서므로 이번 사이클에는 바뀌지 않았다. `db.py`는 diff가 없다. `pyproject.toml`/`uv.lock` diff는 T5의 `feedparser`가 아직 커밋되지 않은 것이고, 이번에 새 의존성은 없다 |
| acceptance 케이스 대조 | 전부 있다. 실패 2회 → 1, 2를 반환하고 etag·last_modified가 그대로 남은 뒤 성공 기록(`test_repo.py:308-321`) / `None` 저장(`:324-329`) / `mark_initial_fetch_done` 2회(`:332-336`) / 없는 id 3종 파라미터화와 `in_transaction is False`(`:339-351`) / 잘못된 error `"  "`·`None`·`""`에서 행 불변(`:354-359`) / 커밋 테스트 파라미터 3건(`:236-252`, `:282-284`) |
| acceptance 변이 4종 (임시 복사본 + `PYTHONPATH`. 임시 복사본의 모듈이 실제로 로드되는지 확인했고, 끝난 뒤 `git status`로 src/tests가 그대로임을 확인) | (1) failure가 `etag = NULL` → 1 failed (2) success가 `consecutive_failures` 초기화 생략 → 1 failed (3) `record_feed_failure`의 `with conn:` 제거 → 2 failed(커밋 테스트, 없는 id 롤백). **(4) `feeds.py:283`의 `or isinstance(resp.status, bool)` 제거 → 168 passed(안 잡힘).** `True`/`False`는 `1`/`0`이라 304에도 2xx에도 해당하지 않는다. 그래서 `:299`의 마지막 `raise FeedFetchError`가 어차피 예외를 낸다. 달라지는 것은 메시지 문구(`잘못된 HTTP 상태` → `HTTP True`)뿐이므로 동작이 같은 동치 변이다. IMPL.md도 사실대로 보고했다 |
| 추가 변이 (evaluator가 직접 만든 것) | (x) success가 `last_error = NULL` 생략 → 1 failed (y) error 검증에서 `strip()` 검사 제거 → 2 failed(`"  "`, `""`) (z) failure가 늘린 값 대신 상수 1 반환 → 1 failed (w) `mark_initial_fetch_done`의 `with conn:` 제거 → 2 failed. 모두 잡힌다 |
| `docs/decisions/` | 주제 파일 10개(`.planner.md`·`.evaluator.md` 없음)는 모두 합의가 끝났다(PLAN "합의된 결정 U1~U10", "미해결 의사결정: 없음"). 이전 사이클처럼 다시 평가하지 않았고 `.evaluator.md`도 쓰지 않았다(판단 기준: PLAN이 반영 완료로 명시한 잔여 파일) |

## 평가 표

| 축 | 점수 | 근거 |
|---|---|---|
| 사양 충족 | 3 | TASKS T7 내용을 모두 구현했다. `record_feed_success`는 etag·last_modified를 주어진 값으로 저장하고 `last_error = NULL`, `consecutive_failures = 0`으로 둔다(`repo.py:88-102`). `record_feed_failure`는 DB에 접근하기 전에 `str`이 아니거나 공백뿐인 error를 `ValueError`로 거부한다(`:113-114`). 이어서 etag를 건드리지 않고 `consecutive_failures + 1`로 갱신하고, 같은 트랜잭션 안에서 갱신된 값을 다시 읽어 반환한다(`:115-123`). `mark_initial_fetch_done`은 멱등이다(`:126-134`). 세 함수 모두 `with conn:` 안에서 `_require_feed`(`:83-85`, rowcount 0이면 `FeedNotFoundError`)로 롤백한다. 독스트링 `Raises:`도 갖췄다. acceptance 명령 3개와 전체 248 passed를 확인했다. 변이 (4)가 잡히지 않는 것은 동치 변이이기 때문이고 구현 결함이 아니어서 감점하지 않았다 |
| 모듈 경계 | 3 | 변경은 touch 범위 안에만 있다. `tests/feeds/test_feeds.py`에는 테스트 1건만 추가했다. `repo.py`는 `feeds.py` 타입을 import하지 않고 원시 값만 받는다(PLAN M2 자체 결정). SQL은 `repo.py`에만 있다. 공통 rowcount 검사를 `_require_feed` 하나로 묶어 기존 T3r 규칙과 맞췄다. `db.py`·`feeds.py`는 변경이 없고 스키마 `_V1`도 그대로다 |
| 테스트 충실도 | 3 | acceptance 케이스가 전부 있고, 의미 있는 acceptance 변이 3종과 추가 변이 4종(x, y, z, w)이 모두 잡힌다. 실패 경로도 검증한다. 없는 id에서는 `in_transaction is False`를 보고, 잘못된 입력에서는 행 전체를 `tuple`로 비교해 불변을 본다(`:355-359`). 커밋 경로는 두 번째 연결로 확인한다. 직전 REVIEW 감점 사유였던 `bool` status 거부도 이제 행동 수준에서 고정됐다(`test_feeds.py:550-553`). 참고로 이 테스트는 메시지를 단언하지 않아 `:283`의 분기 자체는 구분하지 못한다. 다만 이 분기는 동작상 중복이라 결함으로 보지 않았다(아래 메모). 로그는 해당 없다(T7b 범위) |
| 운영 고려 | 3 | 새 의존성이 없다. 오류 메시지에 피드 id를 넣었다(`:85`). 공백뿐인 오류 메시지를 거부해서 실패 목록 화면(M5)에 빈 사유가 남지 않는다. IMPL.md의 테스트 수, 변이 결과(동치 변이 설명 포함), 자체 결정(`""` 거부)이 실제와 같다. IMPL은 (4)를 "원리적으로 잡을 수 없음"이라고 적었는데, 메시지를 단언하면 구분할 수는 있으므로 표현이 약간 과하다. 결과에는 영향이 없다 |
| **합계** | **12 / 12** | |

## 합격 여부

**PASS** (화면 없는 항목, 합계 12점 ≥ 9점)

채점 기준 메모: 이전 사이클과 같이 테스트 충실도는 "구현의 핵심 줄을 무력화하면 테스트가 실패하는가"(임시 복사본 변이)로 판단했다. acceptance에 든 동치 변이는 구현·테스트 어느 쪽도 감점하지 않았다.

## 다음 사이클로 넘기는 메모

- (planner 참고) T7 acceptance 변이 (4)도 동치 변이였다. PLAN "acceptance 작성 규칙"(동치 변이 제외)을 T7b 변이 목록에 다시 적용한다. T7b의 변이 5종은 모두 동작을 바꾸는 변이로 보인다. 다만 (5) "경고 로그 제거"가 잡히려면 `caplog` 단언이 경고 **건수와 피드 url**을 확인해야 한다.
- (선택, 동작 변화 없음) `feeds.py:283`의 `or isinstance(resp.status, bool)`은 동작상 중복이다(bool은 어떤 성공 판정에도 들지 않는다). 남겨 두려면 `test_fetch_bool_status_rejected`에 `match="잘못된 HTTP 상태"`를 넣어 분기를 고정하고, 아니면 이 조건을 지워도 된다. 둘 다 한 줄짜리라 T7b나 이후 작은 항목에 끼워 넣으면 충분하다.
- (T7b 참고) `record_feed_failure`는 공백뿐인 error를 거부한다. `collect_feed`가 `str(e)`를 넘길 때 메시지가 빈 `FeedError()`(예: 인자 없이 만든 예외)가 오면 `ValueError`가 새어 나와 "예외를 밖으로 던지지 않음"(PRD 7) 계약이 깨진다. T7b에서는 `str(e) or type(e).__name__`처럼 빈 메시지를 대체하는 처리와 테스트 1건을 넣는 것을 권한다.
- (운영 참고) `src/rss_wiki/feeds.py`와 `tests/feeds/`가 아직 git 미추적이다. `pyproject.toml`/`uv.lock`의 `feedparser` 추가(T5)도 커밋되지 않았다. 이번 평가에서는 diff 대신 파일 수정 시각으로 touch 범위를 판단했다. 사람이 중간 커밋하면 이후 평가에서 범위를 정확히 대조할 수 있다.
- 환경 참고: 하네스의 `VIRTUAL_ENV` 때문에 `uv run` 경고가 나온다(결과에는 영향 없음).
