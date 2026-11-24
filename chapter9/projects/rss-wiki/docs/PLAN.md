# PLAN: rss-wiki

- 기준 문서: docs/PRD.md (초안 v1)
- 최종 갱신: 2026-11-24 (planner, 사이클 23)

## 현재 상태 (2026-11-24, 사이클 23 시작 시점)

- 사이클 22: T8r(`html_to_text` 블록 18개·버리기 3개 확장, `<br/>`·짝 없는 `</script>`·단어 중간 인라인 태그 고정, 빈 값 64건 조합) PASS 11/12, `tests/extract` 98 passed, 전체 356 passed, acceptance 변이 5종 잡힘.
- T8r REVIEW 메모: 새 블록 태그 대부분이 개별 테스트로 고정되지 않았다(감점 사유). `header`·`footer`·`table`·`nav`·`main` 등을 빼는 추가 변이 5종이 살아남았다. 버리기 깊이 카운터가 태그 종류를 구분하지 않아 `<noscript>a</script>b</noscript>ok` → `bok`이 된다(참고). → 둘 다 T8s(T9a 앞, 테스트 리터럴 목록 + 태그별 깊이)에 배정했다. 아래 M2 자체 결정 "버리기 깊이 태그별 분리"를 따른다. 닫히지 않은 버리기 태그가 뒤 내용을 버리는 것과 `textarea`·`iframe`·`option` 미포함은 결함이 아니라서 조치하지 않는다.
- 다음: T8s → T9a → T9b. M2는 T9b가 끝나면 완료된다.
- 아래는 사이클 22 시점 기록.

- 사이클 21: T8(`extract.py` `ContentExtractor`·`html_to_text`·`choose_body`·`Body`) PASS 11/12, `tests/extract` 32 passed, 전체 290 passed, acceptance 변이 9종 잡힘. 같은 evaluator가 T7b 회귀·변이 7종을 확인해 **T7b PASS**(체크 유지).
- T8 REVIEW 메모: IMPL에 적은 자체 결정 두 가지(`<br/>` startendtag 공백, 짝 없는 `</script>` 깊이 방어)와 단어 중간 인라인 시작 태그(`a<b>c</b>d`)가 테스트로 고정되지 않았다(감점 사유). IMPL의 "(6) 시작 태그만 바꾸면 동치" 서술은 틀렸다. HTML5 블록 요소(`dt`/`dd`, `figure` 등) 누락으로 단어가 붙고, `title`·`noscript`·`template` 내용이 남는다 → 아래 M2 자체 결정 "HTML 텍스트화 블록·버리기 목록 확장"으로 정하고 T8r(T9a 앞)에 배정했다. `a<b` 뒤 글자 유실과 `max_chars=True`는 결함이 아니라서 조치하지 않는다.
- T9를 둘로 나눴다. T9a는 HTTP 공통 기반(응답 크기 상한, 호스트별 요청 간격 래퍼, `feeds.py`), T9b는 실제 원문 추출기(`extract.py`, trafilatura)다. 아래 M2 자체 결정 "원문 추출기 HTTP 주입"을 따른다.
- 다음: T8r → T9a → T9b. M2는 T9b가 끝나면 완료된다.
- 아래는 사이클 21 시점 기록.

- 사이클 20: T7b(`pipeline.collect_feed`·`CollectResult`, bool status `match` 고정) generator 완료 보고(전체 258 passed, 변이 7종 모두 잡힘). planner가 코드로 확인했다: 검증이 fetcher 호출 전, `FeedError`의 빈 메시지 대체, `None` 항목 경고 로그, 첫 수집 `published` 내림차순 stable 정렬, 이미 있는 글 미집계, 성공 기록 후 `mark_initial_fetch_done`, 테스트 9개 함수(파라미터 포함 12건). 직전 REVIEW.md는 아직 T7 평가 → T7b는 다음 evaluator가 T8과 함께 회귀·변이를 확인한다. FAIL이면 다음 planner가 체크를 해제한다.
- 이번 사이클에 "T8 전 확인 사항"(대기·재시도 글의 피드 대체 본문 부재)을 스키마 변경 없는 자체 결정으로 정했다(아래 M2 "대기·재시도 글의 본문 확보"). 스키마·저장 형식을 바꾸지 않으므로 결정 합의 절차 대상이 아니다.
- 다음: T8(`extract.py` 본문 선택·HTML 텍스트화·자르기, 순수 함수) → T9(실제 추출 구현).
- 아래는 사이클 20 시점 기록.

- 사이클 19: T7(`record_feed_success`·`record_feed_failure`·`mark_initial_fetch_done`, `status=True` 거부 테스트) PASS 12/12, `tests/repo` 85 passed, 전체 248 passed. 의미 있는 acceptance 변이 3종과 evaluator 추가 변이 4종이 모두 잡혔다. 변이 (4) bool 검사 제거는 동치 변이였다(메시지만 바뀜).
- T7 REVIEW 메모: 빈 메시지 `FeedError`가 `record_feed_failure`의 공백 거부에 걸려 `ValueError`가 샐 수 있음 → M2 자체 결정(아래 "피드 실패 오류 문자열")으로 정하고 T7b에 테스트 1건과 변이로 넣었다. `caplog` 단언은 경고 건수와 피드 url까지 확인하게 했다. bool 분기는 `match="잘못된 HTTP 상태"`로 고정한다(T7b 작은 보강). T7b 변이 (2) "첫 수집 판정 무시"가 잡히도록 세 번째 호출의 새 항목을 가장 오래된 날짜로 정했다. 미커밋 `feeds.py`·`tests/feeds/`·`feedparser` 의존성은 사람의 중간 커밋 대상이다(planner 권한 밖).
- 다음: T7b(`collect_feed`) → T8 전에 아래 "T8 전 확인 사항"을 정리한다.
- 아래는 사이클 19 시점 기록.

- 사이클 18: T6s(http/https scheme 제한·비정수 status·`HTTPError.headers is None` 방어) PASS 11/12, `tests/feeds` 82 passed, 전체 235 passed. 실제 `file://`·`ftp://`·`data:` 탐침에서 모두 `FeedFetchError`가 나서 T6r의 `TypeError` 누출이 해소됐다.
- T6s REVIEW 메모: `bool` status 거부(자체 결정)를 고정하는 테스트가 없다(감점 사유) → T7 앞부분에 테스트 1건을 넣는다. acceptance 변이 `.lower()` 제거는 동치 변이였다 → 아래 "acceptance 작성 규칙"에 반영했다. 웹 폼 URL 앞뒤 공백 → M5 자체 결정에 넣었다.
- 다음: T7(`repo.py` 피드 상태 기록 + bool status 테스트) → T7b(`collect_feed`) → T8 전에 아래 "T8 전 확인 사항"을 정리한다.
- 아래는 사이클 18 시점 기록.

- 사이클 17: T6r(URL 입력 오류 포장·비ASCII path/query 인코딩·헤더 정규화 `HttpResponse` 이동·`urllib_get` 성공 경로 테스트) PASS 11/12, `tests/feeds` 69 passed, 전체 222 passed, acceptance 변이 11종 모두 잡힘. 로컬 서버 탐침으로 한글 URL 인코딩·304·잘못된 URL → `FeedFetchError`를 evaluator가 확인했다.
- T6r REVIEW 메모: 존재하는 로컬 파일의 `file://` URL은 `urllib`이 읽어 `resp.status`가 `None`이 되고 `feeds.py:271`에서 `TypeError`가 샌다(PLAN M2 "URL 입력으로 `FeedError` 밖 예외 없음" 계약 위반, 감점 사유). `HTTPError.headers`가 `None`이면 `_lower_headers`에서 `AttributeError`(선택). → 아래 M2 자체 결정("피드 URL scheme은 http/https만")으로 정하고 T6s(T7 앞)에 배정. `HTTPError` 경로의 `url`이 인코딩 전 원래 url인 점은 결함 아님(본문 파싱 없음).
- 다음: T6s(작은 보강) → T7(`repo.py` 피드 상태 기록) → T7b(`collect_feed`).
- 아래는 사이클 17 시점 기록.

- 사이클 16: T6(`HttpFeedFetcher`, 주입형 `http_get`, 조건부 요청·304·오류 매핑) PASS 10/12, 전체 211 passed, acceptance 변이 7종 잡힘. 로컬 서버 탐침으로 200 → 304, 리다이렉트, 404, 연결 거부가 정상 동작함을 evaluator가 확인했다.
- T6 REVIEW 메모: 한글 path URL(`UnicodeEncodeError`)과 형식이 틀린 URL(`ValueError`)이 `FeedError` 계약 밖으로 샌다. `urllib_get` 성공 경로(헤더·timeout 전달, `geturl()`, 헤더 소문자화)가 테스트되지 않는다. 헤더 키 정규화가 `HttpResponse`가 아니라 `urllib_get`에만 있다(IMPL 보고와 불일치). 2xx 경계, `OSError`·`HTTPException` 매핑 테스트도 없다. → 모두 T6r(T7 앞)에 배정했다. URL 인코딩과 헤더 정규화 위치는 아래 M2 자체 결정으로 정했다. 응답 본문 크기 상한은 T9 원문 페이지 가져오기와 함께 공통 상한으로 처리한다(아래 M2 자체 결정). `Content-Type` charset 미전달은 결함이 아니므로 조치하지 않는다.
- 다음: T6r(작은 보강) → T7(`repo.py` 피드 상태 기록) → T7b(`collect_feed`).
- 아래는 사이클 16 시점 기록.

- 사이클 15: T5(`parse_feed`, feedparser 6.0.14 도입) PASS 11/12, 전체 191 passed, acceptance 변이 3종 잡힘. 런타임 의존성은 `feedparser`(+전이 `feedparser-sgmllib`)만 추가.
- T5 REVIEW 메모: bozo 허용 분기 미검증(감점 사유) + 빈 값 → `None`·strip 고정 케이스 → T6 앞부분 테스트 보강. content-only 피드에서 `summary`가 본문과 같아짐 → T8 본문 선택 규칙에 반영(아래 M2 자체 결정). `javascript:` link → M4/M5 렌더링 자체 결정(아래 M4). 본문 HTML 상대 링크 미절대화는 결함 아님(U4로 본문 미저장).
- 다음: T6(`HttpFeedFetcher` + bozo 테스트) → T7(`repo.py` 피드 상태 기록) → T7b(`collect_feed`).
- 아래는 사이클 15 시점 기록.

- 사이클 14: T4r(잘못된 link 처리·`feeds.py` 테스트 보강) PASS 12/12, 전체 184 passed, acceptance 변이 5종 모두 잡힘. `entry_key` 예외 누출 해소.
- T4r REVIEW 메모: `urljoin`이 잘못된 link에서 `ValueError` → T5에서 항목 link 원문 유지(아래 M2 자체 결정)와 acceptance 케이스로 반영. "잘못된 포트 + userinfo" 테스트 케이스 → T5 작은 보강. `entry_key is None` 건너뛰기 로그 확인 → T7 acceptance에 `caplog`로 넣기로 함. `:0443`·빈 포트는 결함 아님.
- 다음: T5(`parse_feed`) → T6(`HttpFeedFetcher`).
- 아래는 사이클 13 시점 기록.

- 사이클 12: T4(`feeds.py` 타입·`FeedFetcher` 프로토콜·`normalize_link`·`entry_key`) PASS 10/12, 전체 176 passed. evaluator가 T3b 회귀(변이 3종 잡힘)도 확인해 PASS → **M1 완료**.
- T4 REVIEW 메모: 잘못된 포트 link(`https://e.com:abc/`, `:99999`)에서 `entry_key`가 `ValueError`를 누출(파이프라인은 `FeedError`만 잡으므로 한 항목이 피드 처리를 멈출 수 있음) → 아래 M2 자체 결정으로 정하고 T4r에 배정. `test_no_internal_imports`가 상대 import를 못 잡음, `utmost` 경계·IPv6·userinfo·가짜 fetcher 인자 전달 미검증 → T4r. `.lower()` 중복·빈 쿼리 조각 제거는 결함 아님(조치 없음).
- 다음: T4r(작은 보강) → T5(`parse_feed`, feedparser 도입).
- 아래는 사이클 12 시점 기록.

- 사이클 11: T3b(처리 대상 조회·상태별 건수·실패 목록·`runs` 시작/종료/중단) generator 완료(153 passed, 변이 3종 확인 보고). 코드로 반영을 확인했으나 REVIEW.md는 아직 T3s 평가 → T3b는 다음 evaluator가 T4와 함께 회귀 확인. T3b가 PASS되면 M1 완료.
- 다음은 M2 시작: T4(`feeds.py` 타입·프로토콜·글 식별 키, 의존성 없음) → T5(`parse_feed`, feedparser 도입).
- 아래는 사이클 11 시점 기록.

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
| `extract.py` | `ContentExtractor` 프로토콜 + 실제 구현, 피드 본문 HTML 텍스트화, 본문 선택(`choose_body`)과 `source` 결정, 최대 길이 자르기 | — |
| `summarizer.py` | `Summarizer` 프로토콜 + Claude Code CLI 구현(지시문은 `-p` 인자, 본문은 stdin, `claude_model`이 있을 때만 `--model`), 사전 점검, JSON 검증 | `config` |
| `tags.py` | 태그 정규화(소문자, 케밥케이스, 공백/중복 제거) | — |
| `wiki.py` | 글 Markdown 렌더링, slug(충돌·Windows 금지 문자), 원자적 쓰기, 인덱스 전체 재생성 | `repo` |
| `pipeline.py` | 피드 1개 수집(`collect_feed`, M2 T7b)과 1회 실행 오케스트레이션: 수집 → 처리량 제한 → 본문 → 요약 → 위키 → 인덱스, 진행 상황 보고, 실패 격리 | 위 전부 (인터페이스로 주입) |
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
- 상태: 완료 (T1~T3b 모두 PASS, T3b는 사이클 12 evaluator가 회귀 확인)
- `list_failed_articles`는 `updated_at` 내림차순, 동률이면 `id` 내림차순. `finish_run`의 `processed`/`failed`는 0 이상만 받는다. (자체 결정)
- 처리 대상 순서는 `id` 오름차순(수집 순)이다. `runs.status`는 `running`/`finished`/`aborted`를 쓰고 스키마 CHECK 대신 `repo.py`에서 검증한다. 서버 시작 시 `db.reset_interrupted`와 `repo.abort_running_runs`를 함께 호출한다(M5에서 연결). (자체 결정)
- 태그 이름 정규화는 `tags.py`(M3) 책임이고 `repo.py`는 받은 이름을 그대로 저장한다. `list_tag_names`는 글이 연결된 태그만 돌려준다. (자체 결정)
- 검색은 `status = 'done'` 글만 대상으로 한다(요약이 있는 글만 검색 화면에 의미가 있음). (자체 결정)

### M2. 수집과 본문 확보
- 범위: `feeds.py`, `extract.py`, `repo.py` 확장
- 내용: 글 식별(guid/id → 정규화 link), 중복 건너뛰기, ETag/Last-Modified, 피드 실패 기록(마지막 오류·연속 실패), 첫 수집 최근 10개 + `skipped_backfill`, 실행당 50개 상한(나머지 `new`로 대기), 본문 추출 → `content` → `summary` 대체와 `source` 기록, 최대 길이 자르기, 호스트별 요청 간격
- 상태: 진행 중 (T4·T4r·T5·T6·T6r·T6s·T7·T7b·T8·T8r PASS, 다음 T8s → T9a → T9b)
- 항목 분할(예정, 한 세션 크기)
  - T4 `feeds.py` 타입(`FeedEntry`/`ParsedFeed`/`FetchResult`)·`FeedError` 계층·`FeedFetcher` 프로토콜·`normalize_link`·`entry_key` (의존성 없음) — PASS
  - T4r 잘못된 link 처리와 `feeds.py` 테스트 보강 (T4 REVIEW 메모) — PASS
  - T5 `parse_feed`(feedparser, 3.15 설치 불가 시 표준 라이브러리 대체), 항목 link `urljoin` 실패 시 원문 유지 (T4r REVIEW 메모) — PASS
  - T6 실제 `HttpFeedFetcher`: 조건부 요청(`If-None-Match`/`If-Modified-Since`, 304 → `not_modified`), 타임아웃(`http_timeout_sec`), 일반 클라이언트명 User-Agent(`rss-wiki/0.1`), HTTP 오류·네트워크 오류 → `FeedFetchError`. HTTP 계층은 주입 가능한 `http_get` 함수(기본 `urllib.request`, 새 의존성 없음)로 분리해 테스트에서 가짜로 바꾼다. 앞부분에 bozo·빈 값 고정 테스트 보강 (T5 REVIEW 메모) — PASS
  - T6r URL 입력 오류의 `FeedFetchError` 포장과 비ASCII path·query 퍼센트 인코딩, 헤더 키 정규화를 `HttpResponse`로 이동, `urllib_get` 성공 경로·2xx 경계·`OSError`/`HTTPException` 매핑 테스트 (T6 REVIEW 메모) — PASS
  - T6s 피드 URL scheme을 `http`/`https`로 제한(`fetch`·`urllib_get` 양쪽, 요청 전 거부), `fetch`의 비정수 `status` 방어, `HTTPError.headers is None` 방어 (T6r REVIEW 메모) — PASS
  - T7 `repo.py` 피드 상태 기록: `record_feed_success`(etag·last_modified·오류 초기화·연속 실패 0)/`record_feed_failure`(마지막 오류·연속 실패 +1, etag 유지)/`mark_initial_fetch_done`. 앞부분에 `fetch`의 `bool` status 거부 테스트 1건(T6s REVIEW 메모) — PASS
  - T7b 수집 함수 `collect_feed(conn, feed_row, fetcher, *, first_fetch_limit) -> CollectResult`를 `pipeline.py`에 둔다(아래 자체 결정): fetch → 새 글 저장(첫 수집이면 `published` 최신 `first_fetch_limit`개 외 `skipped_backfill`) → `record_feed_success`·`mark_initial_fetch_done`, `FeedError`면 `record_feed_failure` 후 예외 없이 실패 결과 반환. `entry_key`가 `None`인 항목은 건너뛰고 경고 로그를 남기며, acceptance에 `caplog` 확인을 넣는다 (T4r REVIEW 메모)
  - T8 `extract.py`(순수 함수, 표준 라이브러리만): `ContentExtractor` 프로토콜, `html_to_text`, 본문 선택 `choose_body`(추출 → `content` → `summary` → 짧은 추출, 아래 자체 결정), `source` 결정, `content_max_chars` 자르기. `content`와 `summary`가 같은 값일 수 있음(T5 REVIEW 탐침)을 테스트 케이스로 넣는다
  - T8r `html_to_text` 테스트 고정(`<br/>`, 짝 없는 `</script>`, 단어 중간 인라인 태그)과 블록·버리기 목록 확장 (T8 REVIEW 메모) — PASS
  - T8s 블록·버리기 태그를 테스트 리터럴 목록으로 하나씩 고정, 버리기 깊이를 태그별로 분리 (T8r REVIEW 메모)
  - T9a HTTP 공통 기반(`feeds.py`): `urllib_get` 응답 본문 크기 상한(`MAX_RESPONSE_BYTES`), 호스트별 요청 간격 래퍼 `throttle_by_host(http_get, ...)`(T6 REVIEW 선택 메모)
  - T9b 실제 원문 추출기 `HttpContentExtractor`(`extract.py`, 주입된 `http_get` + trafilatura, 3.15/Windows에서 설치 불가 시 `html_to_text` 기반 대체)
- 실행당 50개 상한은 이미 `repo.list_articles_to_process(limit=...)`로 지원되므로 M5 파이프라인에서 연결한다.
- 글 식별 키는 `"guid:" + guid` 또는 `"link:" + normalize_link(link)`로 저장한다. 둘 다 없으면 저장하지 않고 건너뛴다(로그). `normalize_link`는 scheme·host 소문자, 기본 포트·fragment·`utm_*` 쿼리 제거, 빈 path → `/`만 하고 path는 건드리지 않는다. (자체 결정)
- 피드 파싱은 사실상 표준인 `feedparser`를 쓴다(RSS 0.9x/1.0/2.0·Atom·인코딩 처리). 순수 Python이라 3.15에서 동작할 가능성이 높지만, 설치·import가 안 되면 표준 라이브러리 `xml.etree`로 RSS 2.0·Atom 1.0만 지원한다. `published`는 UTC ISO8601 문자열로 정규화한다. (자체 결정)
- 피드 fetch·parse 실패는 `FeedError` 하위 예외(`FeedFetchError`/`FeedParseError`)로 통일해 파이프라인이 한 종류만 잡게 한다. (자체 결정)
- 외부 피드의 잘못된 link는 예외로 새지 않게 한다. `normalize_link`는 포트를 해석할 수 없으면(`:abc`, 범위 초과) 기본 포트 제거만 생략하고 host:port 원문을 소문자로 둔다(글을 버리지 않음). 그 밖에 `urlsplit` 자체가 실패하는 link(`http://[::1` 등)는 `entry_key`가 `ValueError`를 잡아 `None`(식별 불가 → 건너뛰고 로그)을 돌려준다. 결과적으로 `entry_key`는 `FeedEntry`에 대해 예외를 던지지 않는다. (자체 결정, T4 REVIEW 메모)
- `parse_feed`에서 항목 link의 `urljoin`이 `ValueError`를 내면 그 항목의 link를 공백만 제거한 원문으로 두고 피드 전체를 실패시키지 않는다(정보 보존, guid가 없으면 `entry_key`가 `None`이 되어 호출자가 건너뜀). (자체 결정, T4r REVIEW 메모)
- HTTP는 표준 라이브러리 `urllib.request`로 처리한다(새 의존성 없음). User-Agent는 `rss-wiki/0.1`. 리다이렉트 후 최종 URL을 `parse_feed`의 상대 link 기준으로 쓴다. (자체 결정)
- 피드 하나의 수집 흐름(`collect_feed`)은 `feeds`와 `repo`를 함께 쓰므로 `pipeline.py`에 둔다. `repo.py`는 `feeds.py` 타입에 의존하지 않고 원시 값만 받는다. 글 저장과 `mark_initial_fetch_done`은 별도 트랜잭션이며, 그 사이에 중단되면 다음 실행에서 첫 수집으로 다시 처리된다(이미 저장된 글은 중복 키로 건너뜀). 이 경우 backfill 판정이 남은 글 기준으로 다시 되는 것은 v1에서 허용한다. (자체 결정)
- 본문 선택(T8)에서 `content`와 `summary`가 같은 값이면(feedparser가 `content:encoded`만 있는 항목의 `summary`를 본문으로 채움) 같은 본문으로 보고 별도 짧은 요약문으로 가정하지 않는다. `source`는 둘 다 `feed`다. (자체 결정, T5 REVIEW 메모)
- 피드 URL의 비ASCII 문자(한글 태그 피드 `/tag/한글/feed` 등)는 오류로 거부하지 않는다. `urllib_get`이 요청 전에 path와 query를 UTF-8 퍼센트 인코딩한다(이미 있는 `%XX`는 유지, 이중 인코딩 없음). host는 바꾸지 않는다. 그래도 `Request` 생성이나 `urlopen`에서 `ValueError`(`UnicodeEncodeError` 포함)가 나면 url과 원인을 담은 `FeedFetchError`로 바꾼다. 결과적으로 `HttpFeedFetcher.fetch`는 URL 입력 때문에 `FeedError` 밖의 예외를 던지지 않는다. (자체 결정, T6 REVIEW 메모)
- 응답 헤더 키 소문자 정규화는 `HttpResponse.__post_init__`에서 한 번만 한다(frozen이므로 `object.__setattr__`). 어떤 `http_get` 구현이든 대소문자가 섞인 키를 줘도 `fetch`가 ETag·Last-Modified를 읽는다. (자체 결정, T6 REVIEW 메모)
- 피드 URL scheme은 `http`/`https`만 허용한다(대소문자 무시). 그 밖의 scheme(`file`, `ftp`, scheme 없음 등)은 요청을 보내기 전에 url을 담은 `FeedFetchError`로 거부한다. 검사는 `HttpFeedFetcher.fetch`(주입된 `http_get` 호출 전, 계약 경계)와 공개 함수 `urllib_get`(직접 호출 대비 방어) 양쪽에서 같은 내부 함수 하나로 한다. 로컬 파일 읽기를 막고 M4의 "http/https만 링크화" 결정과 맞춘다. 추가 방어로 `fetch`는 `resp.status`가 `int`가 아니면(리다이렉트 등으로 비HTTP 응답이 온 경우) 상태 판정 전에 `FeedFetchError`를 낸다. `HTTPError.headers`가 `None`이면 빈 헤더로 처리한다. M5 피드 추가 화면도 같은 `FeedFetchError`로 거부 메시지를 보여주면 된다. (자체 결정, T6r REVIEW 메모)
- `fetch`는 `resp.status`가 `bool`이어도 거부한다(`True == 1`이 정수 검사를 통과하지 않게). T7에서 행동을 테스트로 고정했고, 분기 자체는 T7b에서 `match="잘못된 HTTP 상태"`로 고정한다(분기를 지우면 메시지만 `HTTP True`로 바뀌는 동치 동작이므로 메시지로 구분). (자체 결정, T6s·T7 REVIEW 메모)
- 피드 실패 오류 문자열: `collect_feed`는 `FeedError`를 `str(e).strip() or type(e).__name__`으로 기록한다. 메시지가 빈 예외도 실패 목록에 사유가 남고, `record_feed_failure`의 공백 거부(`ValueError`)가 수집 루프 밖으로 새지 않는다. (자체 결정, T7 REVIEW 메모)
- 첫 수집 backfill 판정은 식별된 항목을 `published` 내림차순(`None`은 가장 오래된 것으로, 동률이면 피드 순서 유지)으로 정렬해 앞의 `first_fetch_limit`개만 `new`로 둔다. (자체 결정, T7b)
- 대기·재시도 글의 본문 확보(사이클 21에 "T8 전 확인 사항"을 해소): 피드 본문도 DB에 저장하지 않는다(U4의 취지와 스키마 `_V1`을 유지, 스키마 변경 없음). M5 실행 파이프라인은 이번 실행에서 받은 항목을 메모리 캐시 `{(feed_id, entry_key): FeedEntry}`에 둔다. 처리 대상 글(`new` 대기분, `failed` 재시도분 포함)의 항목이 캐시에 없으면 먼저 원문 추출만 해 본다. 추출 결과가 `choose_body`의 "충분한 길이"를 넘지 못하면, 그 피드를 실행당 최대 1회 조건 헤더 없이(`etag=None`, `last_modified=None`) 다시 받아 캐시를 채운 뒤 `choose_body`를 다시 부른다. 그래도 본문이 없으면 PRD 7 "원문도 피드 본문도 없음"으로 `failed`다. 이 재요청은 본문 확보용 예외 경로이고 PRD 4.1 조건부 요청 규칙(수집 단계)은 그대로다. 재요청 결과의 새 항목은 저장하지 않는다(수집은 `collect_feed`만 한다). 되돌리기 쉬운 결정이다. 나중에 저장 방식으로 바꾸려면 그때 결정 합의를 거친다. (자체 결정)
- 본문 선택 규칙(T8): 원문 추출 텍스트가 공백 제거 후 `min_chars`(기본 200자, 모듈 상수 `MIN_EXTRACTED_CHARS`, 설정 키는 만들지 않음) 이상이면 `extracted`. 아니면 피드 `content`를 HTML 텍스트화한 값이 비어 있지 않으면 `feed`, 다음으로 `summary`도 같은 방식으로 본다. 피드 본문이 모두 비었는데 짧은 추출 텍스트가 있으면 실패 대신 그것을 `extracted`로 쓴다. 넷 다 없으면 `None`(호출자가 `failed`). 피드 본문에만 HTML 텍스트화를 적용한다(추출기 결과는 이미 평문). 선택한 텍스트는 `max_chars`(설정 `content_max_chars`)로 자른다. (자체 결정)
- HTML 텍스트화(T8): 표준 라이브러리 `html.parser`로 태그를 없애고 문자 참조를 풀며 `script`·`style` 안 내용은 버린다. 블록 요소(`p`, `div`, `br`, `li`, `h1`~`h6`, `tr`, `blockquote`, `pre` 등) 경계에는 공백을 넣고 인라인 요소 경계에는 넣지 않는다. 연속 공백은 공백 하나로 합치고 앞뒤를 제거한다. 새 의존성은 없다. (자체 결정)
- 응답 본문 크기 상한은 T9에서 원문 페이지 가져오기와 함께 공통 상한(기본 10MB, 초과 시 `FeedFetchError`·추출 실패)으로 넣는다. 피드와 원문 HTTP 경로가 같은 상한을 쓰도록 하기 위해 T6r에서는 넣지 않는다. (자체 결정, T6 REVIEW 선택 메모)
- HTML 텍스트화 블록·버리기 목록 확장(T8r): `_BLOCK_TAGS`에 `dl`, `dt`, `dd`, `table`, `thead`, `tbody`, `tfoot`, `caption`, `figure`, `figcaption`, `header`, `footer`, `nav`, `main`, `aside`, `details`, `summary`, `address`를 더한다. `_SKIP_TAGS`에 `title`, `noscript`, `template`을 더한다(내용 버림). 짝 없는 끝 태그는 깊이를 0 아래로 내리지 않는다(지금 동작 유지, 테스트로 고정). 새 의존성은 없다. (자체 결정, T8 REVIEW 메모)
- 버리기 깊이 태그별 분리(T8s): `_TextParser`는 버리는 태그마다 깊이를 따로 센다. 끝 태그는 같은 태그의 깊이가 0보다 클 때만 1 줄이고, 어느 태그든 깊이가 남아 있으면 텍스트를 버린다. 다른 종류의 짝 없는 끝 태그(`<noscript>` 안의 `</script>`)가 버리기를 끝내지 않게 하기 위함이다. 테스트는 태그 목록을 모듈 상수에서 읽지 않고 리터럴로 적는다(목록 원소 제거 변이를 잡기 위함). 리터럴과 상수가 같은지 확인하는 테스트도 둔다. 새 의존성은 없다. (자체 결정, T8r REVIEW 메모)
- 원문 추출기 HTTP 주입(T9a·T9b): `extract.py`는 내부 모듈을 import하지 않는 원칙을 유지한다. 실제 추출기 `HttpContentExtractor`는 `feeds.HttpGet`과 같은 모양의 `http_get` 함수를 생성자 인자로 받는다. 연결은 M5 파이프라인이 `feeds.urllib_get`을 넘겨서 한다. 호스트별 요청 간격은 `feeds.throttle_by_host(http_get, *, min_interval=1.0, clock=time.monotonic, sleep=time.sleep) -> HttpGet` 래퍼 하나로 처리한다. 파이프라인은 실행마다 래퍼 하나를 만들어 피드 fetcher와 원문 추출기가 함께 쓰게 한다. 같은 호스트(`urlsplit(url).hostname`, 소문자)에 대한 직전 요청 시작 시각으로부터 `min_interval`초가 지나지 않았으면 남은 시간만큼 `sleep`한다. 호스트를 해석할 수 없는 url은 기다리지 않고 그대로 넘긴다(오류 처리는 안쪽 `http_get`이 한다). 간격 기본값은 1초이고 설정 키는 만들지 않는다. 순차 처리(U3)라 스레드 안전성은 요구하지 않는다. (자체 결정)
- 응답 크기 상한(T9a): `feeds.MAX_RESPONSE_BYTES = 10 * 1024 * 1024`. `urllib_get`은 `resp.read(MAX_RESPONSE_BYTES + 1)`로 읽어서 상한을 넘으면 url과 상한을 담은 `FeedFetchError`를 낸다. `urllib_get`에 키워드 인자 `max_bytes`(기본 `MAX_RESPONSE_BYTES`)를 두되, `HttpGet` 시그니처(위치 인자 3개)는 바꾸지 않는다. 원문 추출기는 `http_get`이 낸 예외를 `Exception`으로 잡아서 `None`을 돌려준다(`extract.py`는 `feeds`를 import하지 않음, T9b, `ContentExtractor` 계약). (자체 결정)

### M3. 요약과 태그
- 범위: `summarizer.py`, `tags.py`
- 내용: `claude -p` 비대화형 호출(지시문 인자 + 본문 stdin, U1), 순차 처리(U3), JSON 응답 검증(요약 3문장, 태그 3~5개), 타임아웃, Windows `claude.cmd`, 실행 파일 경로·모델 설정, 기존 태그 목록을 프롬프트에 포함, 사전 점검(미설치/미로그인), 실패 시 `attempts` 증가와 `failed_permanent` 전환
- `tags.py` 정규화 함수는 `str`이 아닌 원소(`bytes`, 정수 등)를 `TypeError`로 거부한다. `repo.set_article_tags`는 받은 그대로 저장하므로 검증은 정규화 단계 책임이다. (자체 결정, T3s REVIEW 메모)

### M4. Markdown 위키
- 범위: `wiki.py`
- 내용: `articles/YYYY/MM/{slug}.md`(PRD 4.6 frontmatter 형식), `index.md`·`feeds/`·`tags/` 전체 재생성, slug 충돌 접미사, Windows 금지 문자 제거, 원자적 쓰기, 쓰기 실패 시 `failed`
- 원문 링크 안전성: 피드의 link는 `javascript:` 등 임의 scheme일 수 있다(T5 REVIEW 탐침). 위키 Markdown의 `[원문 보기](...)`와 웹 UI(M5)의 `href`는 scheme이 `http`/`https`일 때만 링크로 만들고, 그 밖에는 링크 없이 텍스트로만 표시한다. frontmatter `url`에는 원문을 그대로 기록한다. Jinja2 자동 이스케이프는 켠다. (자체 결정, T5 REVIEW 메모)

### M5. 실행 파이프라인과 웹 UI
- 범위: `pipeline.py`, `web/`, `cli.py`, `opml.py`
- 내용: `rss-wiki serve`(127.0.0.1, 포트 설정), 요약 목록/상세 + 피드·태그 필터, 피드 관리(추가 시 파싱 검증·제목 자동, 삭제, 활성/비활성, OPML 가져오기), "새 글 가져오기" 백그라운드 실행(동시 1개) + htmx 폴링 진행 표시, 실패 목록과 수동 재시도, FTS5 검색 화면
- 피드 추가 폼과 OPML 가져오기는 URL을 `strip()`한 뒤 검증·저장한다(`feeds.url`에 앞뒤 공백이 남지 않게). (자체 결정, T6s REVIEW 메모)
- 1회 실행의 본문 단계는 M2 자체 결정 "대기·재시도 글의 본문 확보"(실행 내 항목 캐시, 캐시에 없으면 추출 먼저, 부족하면 피드를 조건 헤더 없이 실행당 1회 재요청)를 따른다.

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
- acceptance 작성 규칙: 변이 목록에는 표준 라이브러리가 이미 보장하는 동작을 지우는 변이(예: `urlsplit` 결과 scheme의 `.lower()`)처럼 동작이 같은 동치 변이를 넣지 않는다. IMPL.md에 적은 자체 결정은 테스트로 고정한다. (자체 결정, T6s REVIEW 메모)
- `migrate`는 열린 트랜잭션이 있는 연결로 호출되면 경고 대신 `RuntimeError`로 거부한다(`executescript`의 암묵 커밋 방지). 서버 시작 시 새 연결에서 부르는 것이 정상 경로다. (자체 결정)

## 합의된 결정 (2026-11-23, 사이클 2에서 PRD 반영)

U1~U10 모두 1회 시도에 합의했고, PRD 본문에 (자체 결정: 합의)로 반영했다.
U1 B(본문 stdin) · U2 C(`claude_model` 설정, 없으면 `--model` 생략) · U3 A(순차) · U4 A(본문 저장 안 함) · U5 A(덮어씀) · U6 A(읽음 관리 안 함) · U7 A(영구 보존) · U8 A(3.15 유지) · U9 A(전체 재생성) · U10 A(DB 사본 렌더링)

참고: `docs/decisions/*.md` 주제 파일 10개는 반영이 끝났지만, 이번 세션의 권한 제한으로 삭제하지 못하고 남아 있다. 사람이 지우거나 run.py가 정리해도 된다. 아래 미해결 섹션이 비어 있으므로 다시 처리되지 않는다.

## 미해결 의사결정

(없음)
