# TASKS-M2.md

## M2. 오류 경로

- [x] T4. 오류 입력 ValueError 처리
  - 내용
    - PRD 2번의 8종(빈 문자열, 공백만, 음수, 단위 중복, 순서 뒤바뀜, 단위 없는 숫자, 모르는 단위, 대문자 단위, 중간 공백)을 `ValueError`로 처리한다. 메시지에 `repr(입력)`을 넣는다.
    - 빈 문자열과 공백만 있는 문자열은 `strip()` 결과가 비었는지 따로 검사한다.
  - acceptance
    - `python3 -m compileall -q src` 가 오류 없이 끝난다.
    - 오류 입력 9개(`''`, `'  '`, `'-5m'`, `'1h1h'`, `'30m1h'`, `'90'`, `'5d'`, `'1H'`, `'1h 30m'`)의 동작은 T5 테스트가 검증한다.
  - touch: `src/durations.py`

- [x] T5. 오류 입력 8종 테스트 작성
  - 내용
    - PRD 2번의 8가지 오류 입력을 각각 별도 테스트 메서드로 검증한다. 오류 종류와 메시지의 `repr(입력)` 포함 여부를 모두 확인한다.
    - 빈 문자열과 공백만 있는 문자열은 한 항목으로 본다. 나머지 입력은 각각 한 항목이다.
  - acceptance
    - `python3 -m unittest tests.test_durations -v` 가 통과한다. 오류 테스트가 8개 이상이다.
  - touch: `tests/test_durations.py`
