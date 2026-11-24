# REVIEW

- 평가 대상: T8r. `html_to_text` 테스트 고정과 블록·버리기 목록 확장 (T8 REVIEW 메모 해소)
- 평가일: 2026-11-24 (evaluator, 사이클 22)
- 화면 유무: 없음 (화면 완성도 축 제외, 12점 만점)

## 직접 확인한 내용

| 확인 | 결과 |
|---|---|
| `uv run pytest -x tests/extract/` | 98 passed (0.07s). IMPL.md 보고와 같다(32 − 기존 빈 값 9 + 64 조합 + 새 `html_to_text` 11 = 98) |
| `uv run pytest` (전체) | 356 passed (2.37s). T8 이후 290개 회귀 없음 |
| touch 범위 대조 (`git status`, `git diff --stat -- pyproject.toml uv.lock src/`) | 추적 중인 src·`pyproject.toml`·`uv.lock`에 diff가 없다. 바뀐 것은 미추적인 `src/rss_wiki/extract.py`와 `tests/extract/test_extract.py`뿐이다(touch 안). `extract.py`가 미추적이라 T8 대비 diff는 직접 읽어서 대조했다. `handle_*`·`choose_body` 로직은 T8 REVIEW에 적힌 것과 같고, 줄 번호만 3줄씩 밀렸다 |
| acceptance 케이스 대조 | 전부 있다. `a<br/>b`(`test_extract.py:24`), `a</script>b`(`:25`), `a<b>c</b>d`·`Py<span>thon</span>`(`:26-27`), `dl/dt/dd`·`figure/figcaption`·`header/footer`·`table/tr/td + p`(`:28-31`), `title`·`noscript`·`template`(`:32-34`). `test_all_empty_is_none`은 세 축 4값씩 64건 조합이다(`:67-71`, 추출 축은 `"\n\t"`) |
| 코드 대조 | `_BLOCK_TAGS`에 지정한 18개가 모두 있다(`extract.py:19-21`). `_SKIP_TAGS`는 `script, style, title, noscript, template`이다(`:24`). 독스트링에 버리는 태그 5개가 모두 드러난다(`:73`). 짝 없는 끝 태그 깊이 방어는 그대로다(`:57-58`) |
| acceptance 변이 5종 (임시 복사본 + `PYTHONPATH`. 임시 복사본 모듈이 로드되는 것을 `__file__`로 확인했고, 끝난 뒤 `git status`로 src/tests가 그대로임을 확인) | (1) `handle_startendtag` 블록 공백 제거 → 1 failed (2) `if self._skip:` 제거 → 1 failed (3) 시작 태그 `elif tag in _BLOCK_TAGS` → `else` → 2 failed (4) `dt`·`dd` 함께 제거 → 1 failed (5) `noscript` 제거 → 1 failed. **5종 모두 잡힌다** |
| 추가 변이 (evaluator가 직접 만든 것) | 잡힘: `title` 제거, `template` 제거, `figcaption` 제거, 끝 태그 `elif` → `else`. **안 잡힘**: `header`만 제거, `footer`만 제거, `table` 제거, `nav` 제거, `main`·`aside`·`details`·`summary`·`address`를 함께 제거. 모두 98 passed다. 같은 식으로 따져 보면 `dt`만 또는 `dd`만 빼도(이웃 태그가 공백을 대신 넣음) 잡히지 않고, `figure`, `dl`, `thead`/`tbody`/`tfoot`, `caption`도 고정하는 케이스가 없다 |
| 입력 탐침 | 모두 예외 없음. `<details><summary>s</summary>d</details>` → `s d`, `<main>a</main><aside>b</aside>` → `a b`, `<table><caption>c</caption><tbody>…<td>a</td>…` → `c a`, `<svg><title>icon</title></svg>text` → `text`, `<noscript><p>x</p></noscript>ok` → `ok`, 중첩 `<template>` → `ok`. 동작 참고: `<noscript>a</script>b</noscript>ok` → `bok`(버리기 깊이 카운터가 태그 종류 구분 없이 하나라서, 짝 없는 `</script>`가 noscript 깊이를 빼서 `b`가 샌다). 닫히지 않은 `<title>x`는 뒤 내용을 모두 버린다(`<script>`와 같은 동작). Python 3.15.2 |
| IMPL.md 정정 줄 | 있다(`IMPL.md:18`). `a<b>c</b>`가 `a c`가 된다는 서술이 맞고, 변이 (3)이 그 케이스(`:26-27`)로 2건 실패하는 것을 확인했다 |
| `docs/decisions/` | 주제 파일 10개는 모두 합의가 끝났다(PLAN "합의된 결정 U1~U10", "미해결 의사결정: 없음"). 이전 사이클처럼 `.evaluator.md`를 다시 쓰지 않았다 |

## 평가 표

| 축 | 점수 | 근거 |
|---|---|---|
| 사양 충족 | 3 | TASKS T8r 내용을 모두 구현했다. 블록 태그 18개 추가(`extract.py:19-21`), 버리는 태그 3개 추가(`:24`), 독스트링 갱신(`:73`)이 있고, `handle_*`(`:45-64`)와 `choose_body`(`:89-129`)는 바꾸지 않았다. acceptance 케이스가 모두 테스트로 있고 변이 5종도 모두 잡힌다. IMPL 정정 한 줄도 있다. 탐침으로 새 태그들이 실제로 단어를 나누고 내용을 버리는 것을 확인했다 |
| 모듈 경계 | 3 | `extract.py`와 `tests/extract/test_extract.py`만 바꿨다(touch 안). 표준 라이브러리만 쓰고 내부 import가 없다(`test_no_internal_imports`, `test_extract.py:113-120`). 새 의존성은 없다 |
| 테스트 충실도 | 2 | TASKS가 지정한 케이스와 변이 5종은 모두 충족했다. 64건 조합으로 빈 값 축도 빠짐없이 덮었다. 감점 사유는 이번에 추가한 블록 태그 18개 중 하나만 빠져도 실패하는 케이스가 `figcaption`뿐이라는 점이다. `header`/`footer`는 서로 공백을 대신 넣고(`:30`), `table`은 `tr`/`td`가 대신 넣는다(`:31`). `dt`·`dd`도 서로 대신 넣어서 하나씩 빼면 잡히지 않는다(`:28`). `nav`, `main`, `aside`, `details`, `summary`, `address`, `dl`, `figure`, `thead`/`tbody`/`tfoot`, `caption`은 케이스가 아예 없다. 추가 변이 5종이 98 passed로 살아남았다. 이번 항목의 목적인 "목록 확장"이 대부분 테스트로 고정되지 않은 것이다(PLAN "IMPL.md에 적은 자체 결정은 테스트로 고정한다"). acceptance 목록 자체가 그렇게 짜여 있었다는 점은 참작해 1점만 감점했다. 순수 함수라 로그는 해당하지 않는다 |
| 운영 고려 | 3 | 새 의존성이 없고 `pyproject.toml`/`uv.lock`도 그대로다. 독스트링이 실제 버리는 태그와 일치한다. IMPL.md의 테스트 수(98/356), 변이 결과, 정정 서술이 실제와 같다. 깨진 HTML 탐침에서 예외가 나지 않았다. noscript 안의 짝 없는 `</script>` 누출은 실제 피드에서 드물고 예외도 아니어서 감점하지 않고 메모로 넘긴다 |
| **합계** | **11 / 12** | |

## 합격 여부

**PASS** (화면 없는 항목, 합계 11점 ≥ 9점)

채점 기준 메모: 테스트 충실도는 이전 사이클과 같이 "구현의 핵심 줄이나 목록 원소를 무력화하면 테스트가 실패하는가"(임시 복사본 변이)로 판단했다. 목록 원소는 이웃 태그가 공백을 대신 넣지 않는 단독 케이스가 있어야 고정된 것으로 보았다.

## 다음 사이클로 넘기는 메모

- (선택, T9a 앞이나 T9b의 `tests/extract/` 작업 때 함께, 테스트만) 블록 태그를 하나씩 고정하는 파라미터 테스트를 넣는다. 예: `@pytest.mark.parametrize("tag", sorted(extract._BLOCK_TAGS - {"br", "hr"}))`로 `f"a<{tag}>b</{tag}>c"` → `"a b c"`. void 태그 `br`/`hr`은 `"a<br>b"`/`"a<hr>b"` → `"a b"`로 따로 본다. `_SKIP_TAGS`도 같은 방식으로 `f"<{tag}>x</{tag}>ok"` → `"ok"`. 그러면 지금 살아남는 변이(`header`·`footer`·`table`·`nav`·`main` 등 제거, `dt`·`dd` 한쪽만 제거)가 모두 잡힌다. 다만 목록을 테스트가 그대로 읽으면 "목록에서 빼는" 변이는 잡히지 않는다. 그래서 기대 목록을 테스트 안에 리터럴로 적는 쪽을 권한다.
- (참고, planner 판단) 버리기 깊이 카운터가 태그 종류를 구분하지 않아서 `<noscript>a</script>b</noscript>ok` → `bok`처럼 다른 종류의 짝 없는 끝 태그가 깊이를 뺀다(`extract.py:55-58`). 태그별 카운터나 스택으로 바꾸면 고칠 수 있다. 실제 피드 본문에서는 드물어서 조치하지 않아도 된다. 고친다면 자체 결정과 테스트 1건으로 충분하다.
- (참고, 결함 아님) 닫히지 않은 `<title>`·`<noscript>`·`<template>`는 뒤 내용을 모두 버린다(`<script>`와 같은 동작). `<textarea>`·`<iframe>`·`<option>`은 목록에 없지만 피드 본문에서 드물어서 조치할 필요는 없다.
- (운영 참고) `src/rss_wiki/extract.py`와 `tests/extract/`가 아직 git 미추적이다. 사람이 중간 커밋하면 이후 평가에서 diff로 범위를 정확히 대조할 수 있다.
- 환경 참고: 하네스의 `VIRTUAL_ENV` 때문에 `uv run` 경고가 나온다(결과에는 영향 없음).
