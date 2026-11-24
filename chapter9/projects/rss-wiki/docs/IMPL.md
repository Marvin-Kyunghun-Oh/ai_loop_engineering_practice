# IMPL

## 처리한 항목
T8s. `html_to_text` 태그 목록 개별 고정과 버리기 깊이의 태그별 분리

## 변경 파일
- `src/rss_wiki/extract.py`: `_TextParser._skip`을 단일 정수에서 태그별 깊이 `dict[str, int]`로 변경. 시작 태그는 해당 태그 +1, 끝 태그는 같은 태그 깊이가 0보다 클 때만 -1, `handle_data`는 어느 태그든 깊이가 0보다 크면 버림.
- `tests/extract/test_extract.py`: 리터럴 블록 태그 38개·버리는 태그 5개 목록, 블록 태그 36종 파라미터화, void 태그(`br`/`hr`/`hr/`) 3건, 버리는 태그 5종, 리터럴↔모듈 상수 일치 테스트, 태그별 깊이 5건 추가.

## 검증
- `uv run pytest -x tests/extract/` 148 passed
- `uv run pytest` 전체 406 passed (기존 356 회귀 없음), 새 의존성 없음, `extract.py` 외 src 변경 없음
- 변이 확인(임시 복사본 + `PYTHONPATH`, 코드 원복 불필요), 7종 모두 테스트 실패로 잡힘:
  (1) header 제거 / (2) dd 제거 / (3) nav 제거 / (4) hr 제거 / (5) `_SKIP_TAGS`에서 template 제거 /
  (6) 단일 카운터로 복귀 / (7) 끝 태그의 "깊이 > 0" 검사 제거

## 참고
- 결정: 깊이 판정은 `any(self._skip.values())`로 한다(가장 단순).
