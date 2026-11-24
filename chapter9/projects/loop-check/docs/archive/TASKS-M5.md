# TASKS-M5.md

## M5. 프리셋 저장 (PRD M2)

- [x] T9. 프리셋 저장과 불러오기 구현
  - 내용
    - `src/presets.py`에 `save_presets(path, presets: dict[str, str])`와 `load_presets(path) -> dict[str, int]`를 만든다.
    - 저장 형식은 CSV로 확정됐다(PRD M2, 합의 B). 표준 라이브러리 `csv` 모듈을 쓴다.
    - 파일은 UTF-8 with BOM(`encoding="utf-8-sig"`)으로 쓰고 읽는다. 엑셀에서 한글 이름이 깨지지 않게 하기 위함이다.
    - 1행은 헤더 `name,duration`, 이후 행은 `이름,시간 문자열`(예: `집중,25m`)이다. 저장 시 헤더는 항상 쓴다.
    - save는 모든 값을 `parse_duration`으로 먼저 검증한다. 잘못된 값이 하나라도 있으면 `ValueError`를 던지고 파일을 만들거나 바꾸지 않는다.
    - load는 파일이 없으면 빈 dict를 돌려준다. 파일 안에 같은 이름이 두 번 나오면 `ValueError`를 던진다. 값은 `parse_duration`으로 초 단위 정수가 된다.
  - acceptance
    - `python3 -m compileall -q src` 가 오류 없이 끝난다.
    - `src/presets.py`에 `save_presets`와 `load_presets` 정의가 있다.
  - touch: `src/presets.py`

- [x] T10. 프리셋 테스트 작성
  - 내용
    - `tests/test_presets.py`를 `unittest`로 작성한다. 임시 폴더(`tempfile`)를 쓴다.
    - 확인할 것: 저장 후 불러오기가 같은 값을 준다, 잘못된 값이면 ValueError이고 파일이 생기지 않는다, 파일이 없으면 빈 dict다, 파일에 이름이 중복되면 ValueError다.
  - acceptance
    - `python3 -m unittest tests.test_presets -v` 가 통과하고, 위 4가지 각각에 대응하는 테스트가 있다.
    - `python3 -m unittest discover -s tests -t .` 가 통과한다.
  - touch: `tests/test_presets.py`

- [x] T11. load_presets 잘못된 CSV 행의 예외 계약 정리 (BACKLOG: M5 마감)
  - 내용
    - `load_presets`가 헤더에 `name` 또는 `duration` 열이 없거나, 값이 빈 행을 만나면 KeyError나 `parse_duration(None)`의 예외가 새지 않게 한다.
    - 이런 경우 모두 ValueError로 통일한다. 오류 메시지에 열 이름 또는 행 번호를 넣는다. 중복 이름 ValueError와 같은 계약이다.
    - 정상 파일 동작(BOM 포함 읽기, 파일 없음 → 빈 dict)은 바꾸지 않는다.
  - acceptance
    - `python3 -m unittest tests.test_presets -v` 가 통과하고, 헤더에 `duration` 열이 없는 파일과 `duration` 값이 빈 행 각각에 대해 `ValueError`를 기대하는 테스트가 있다.
    - `python3 -m unittest discover -s tests -t .` 가 통과한다.
  - touch: `src/presets.py`, `tests/test_presets.py`
