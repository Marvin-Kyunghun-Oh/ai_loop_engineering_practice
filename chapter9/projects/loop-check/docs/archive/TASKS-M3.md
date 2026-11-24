# TASKS-M3.md

## M3. 독스트링

- [x] T8. 앞뒤 공백 입력 경계 명시 확인 (BACKLOG: M2 마감)
  - 내용
    - PRD 1번의 "앞뒤 공백 무시"를 테스트로 명시한다. `" 1h "`이 3600을 돌려주는 것을 정상 입력 테스트로 고정한다.
    - 중간 공백(`"1h 30m"`) 오류는 이미 오류 테스트에 있으므로 건드리지 않는다. 구현 변경은 하지 않는다.
  - acceptance
    - `python3 -m unittest tests.test_durations -v` 가 통과한다.
    - `tests/test_durations.py`에 `" 1h "` 입력과 기대값 3600을 확인하는 테스트가 있다.
    - `python3 -m unittest discover -s tests -t .` 가 통과한다.
  - touch: `tests/test_durations.py`

- [x] T6. 모듈과 함수 독스트링 작성
  - 내용
    - `src/durations.py` 모듈 독스트링과 `parse_duration` 독스트링에 허용 형식, 단위 규칙, 오류 조건을 적는다.
  - acceptance
    - `python3 -m compileall -q src` 가 오류 없이 끝난다.
    - `src/durations.py`를 Read로 열어 모듈 독스트링과 `parse_duration` 독스트링이 있는지 확인한다. 두 독스트링에 `h`, `m`, `s`, `ValueError` 문자열이 모두 들어 있어야 한다.
  - touch: `src/durations.py`
