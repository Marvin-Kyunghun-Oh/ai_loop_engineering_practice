# REVIEW

- 평가 대상: T3s. 검색 테스트 보강과 입력 검증 (T3a REVIEW 메모 해소)
- 평가일: 2026-11-23 (evaluator, 사이클 10)
- 화면 유무: 없음 (화면 완성도 축 제외, 12점 만점)

## 직접 확인한 내용

| 확인 | 결과 |
|---|---|
| `uv run pytest -x tests/repo/` | 53 passed (0.93s). T3a의 44개에서 9개 늘었음 |
| `uv run pytest` (전체) | 133 passed (1.53s). T3a 이후 124개 회귀 없음. IMPL.md 보고(133 passed, 9건 추가)와 일치 |
| T3a 예외 문서화 확인 명령(`python -c ... NotFoundError`) | 종료 코드 0 (회귀 없음) |
| 변경 파일과 touch 범위 대조 (파일 수정 시각) | 이번 사이클 변경은 `src/rss_wiki/repo.py`(23:52:48), `tests/repo/test_repo.py`(23:52:35)뿐. `db.py`(23:36:39)·`config.py`(23:26:30)·`pyproject.toml`(20:02:14)·`uv.lock`(20:02:06)은 그대로 → 새 의존성 없음, `db.py` 변경 없음 |
| acceptance 변이 4종 (작업 트리는 건드리지 않고 임시 복사본에서 실행) | **4종 모두 잡힘**. (1) 이스케이프 제거 → `test_build_fts_query_quote_escape`, `test_search_quote_input[a"b]`, `[say"hi]` 3건 실패(뒤 두 건은 `sqlite3.OperationalError`) (2) 영숫자 필터를 `if True:`로 → `test_build_fts_query_alnum_filter` 실패 (3) `ORDER BY a.id` → `test_search_bm25_order` 실패(`[1, 2, 3]`) (4) `ORDER BY a.id DESC` → 같은 테스트 실패(`[3, 2, 1]`). IMPL.md 보고와 일치 |
| 추가 변이 3종 (새 입력 검증) | 모두 잡힘. `limit` 검사 제거 → `test_search_bad_limit[0]`·`[-1]` 실패 / 경계를 `limit < 0`으로 바꿈 → `[0]` 실패 / `str` 검사 제거 → `test_set_tags_str_rejected` 실패 |
| 탐침: `search_articles(conn, 'say"hi')` | 제목이 `say"hi there`인 done 글을 실제로 찾음(구문 오류 없음, 리터럴 따옴표 검색 동작) |
| 탐침: 빈 질의 + 잘못된 limit (`""`, `limit=0`)·(`"  "`, `limit=-1`) | 둘 다 `ValueError`. 검증이 `build_fts_query`의 `None` 조기 반환보다 앞에 있음(`repo.py:234-238`) |
| 탐침: `set_article_tags`에 `("a","b")`·`None`·`b"ab"`·`["ok", 3]` | 튜플은 정상 저장. `None`은 `dict.fromkeys`에서 `TypeError`, 롤백되어 기존 태그 유지·`in_transaction is False`. `b"ab"`는 `str` 검사를 통과해 태그 `97`, `98`로 저장됨. `3`은 `'3'`으로 저장됨(아래 메모, 감점 없음) |
| `docs/decisions/` | 주제 파일 10개 모두 `합의` 줄이 있고 `.planner.md`/`.evaluator.md` 대기 파일이 없음 → 새 `.evaluator.md`를 쓰지 않음(이전 사이클과 같은 판단) |

## 평가 표

| 축 | 점수 | 근거 |
|---|---|---|
| 사양 충족 | 3 | TASKS T3s 내용을 모두 구현했다. `search_articles`가 DB 접근 전(그리고 빈 질의 조기 반환 전)에 `limit < 1`을 `ValueError`로 거부한다(`repo.py:234-235`). 독스트링 `Raises:`에 이유(음수 LIMIT은 무제한)를 적었다(`repo.py:231-232`). `set_article_tags`는 `with conn:` 진입 전에 `str`을 `TypeError`로 거부하고(`repo.py:184-185`) `Raises:`에 적었다(`repo.py:181`). 테스트 항목 4종(이스케이프, 영숫자 필터, bm25 정렬, 리터럴 OR)과 acceptance 추가 항목(`limit` 0/-1, `str` 태그 거부 후 기존 연결·`tags` 행 수 불변)이 모두 있다. 변이 4종 확인, 전체 133 통과, 의존성·`db.py` 불변을 직접 확인했다. |
| 모듈 경계 | 3 | 변경이 touch 범위(`repo.py`, `tests/repo/test_repo.py`) 안에만 있다. 입력 검증은 저장 계층의 계약을 지키는 수준(개수 범위, 목록 타입)에 그쳤고, 태그 이름 정규화는 여전히 호출자(`tags.py`, M3) 책임으로 남겨 `repo.py:178`의 문서와 PLAN의 책임 구분을 지켰다. 기존 특수 입력 테스트(`test_repo.py:324-327`)는 지시대로 그대로 두고 새 테스트를 별도 구획(`test_repo.py:344-388`)에 추가했다. |
| 테스트 충실도 | 3 | 직전 REVIEW에서 놓친 변이 3종과 acceptance 변이 4종, 새 검증에 대한 변이 3종까지 모두 실패로 잡힌다. 실패 경로를 상태 불변까지 확인한다: `str` 거부 후 기존 태그 `["keep"]` 유지와 `tags` 행 1개(`test_repo.py:382-388`). bm25 테스트는 요약 길이를 9~10 토큰으로 맞추고 기대 순서를 [B, A, C]로 두어 id 오름차순·내림차순 어느 쪽과도 겹치지 않게 했다(`test_repo.py:363-367`). 리터럴 `OR` 테스트는 `isinstance(list)`가 아니라 맞는 글 id 포함을 확인한다(`test_repo.py:370-372`). 경미한 사항(감점 없음): `test_search_quote_input`(`:351-354`)은 리스트 여부만 보고 따옴표가 든 글을 실제로 찾는지는 확인하지 않는다(탐침으로는 찾음). `test_search_bad_limit`(`:375-379`)은 유효한 질의 `"x"`만 써서, 검증을 빈 질의 조기 반환 뒤로 옮기는 변경은 잡지 못한다. |
| 운영 고려 | 3 | 직전 REVIEW 메모(검색 테스트 보강 4건, 입력 검증 2건)를 모두 해소했다. 새 예외는 독스트링 `Raises:`에 이유와 함께 적혀 있고, 메시지에 잘못된 값이 담긴다(`repo.py:235`). `limit` 규칙을 T3b `list_articles_to_process`와 같게 맞춘 자체 결정을 IMPL.md에 기록했다. 새 의존성이 없다. IMPL.md의 보고(133 passed, 변이 4종 결과)가 실제와 일치한다. |
| **합계** | **12 / 12** | |

## 합격 여부

**PASS** (화면 없는 항목, 합계 12점 ≥ 9점)

채점 기준 메모: 테스트 충실도는 이전 사이클과 같이 "구현의 핵심 줄을 무력화하면 해당 테스트가 실패하는가"(임시 복사본 변이 7종)로 판단했다. 저장 계층이라 로그는 해당 없음으로 보고, 실패 후 상태 불변 확인을 3점 기준의 "실패 경로"로 인정했다.

## 다음 사이클로 넘기는 메모

- 다음 항목은 TASKS 순서대로 T3b(M1 마지막). T3b의 `list_articles_to_process`도 `search_articles`와 같이 검증을 DB 접근 **및 모든 조기 반환보다 앞에** 두고, 테스트에 경계값 `limit=0`을 넣을 것(이번 `limit < 0` 변이를 잡은 것이 `[0]` 케이스였다).
- (선택, 결함 아님) `set_article_tags`는 `bytes`를 거부하지 않아 `b"ab"`가 태그 `97`, `98`로 저장되고, 정수 `3`은 `'3'`으로 저장된다. 호출자는 M3 `tags.py`이므로 그때 정규화 단계에서 `str`이 아닌 원소를 걸러내면 충분하다. `repo.py`에서 막으려면 `isinstance(names, (str, bytes))` 정도로 넓히면 된다.
- (선택) `test_search_quote_input`에 따옴표가 든 제목의 글을 실제로 찾는지 확인하는 단언을 하나 더하면 이스케이프의 의미(리터럴 검색)까지 검증된다.
- 환경 참고: 하네스의 `VIRTUAL_ENV` 때문에 `uv run` 경고가 나온다(결과에는 영향 없음).
