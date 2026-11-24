# IMPL: T13 format_duration 구현과 왕복 테스트

## 처리한 항목
- T13. format_duration 구현과 왕복 테스트

## 전제 확인
- `docs/decisions/format-style.md`에 `합의: A`가 있음 (`parse_duration`이 읽는 형식, 0초는 `0s`).

## 변경 파일
- `src/durations.py`: `format_duration(seconds: int) -> str` 추가. 음수는 ValueError(메시지에 repr 포함). `divmod`로 h, m, s를 나누어 0이 아닌 단위만 h, m, s 순서로 잇고, 결과가 비면 `"0s"`를 쓴다.
- `tests/test_durations.py`: `FormatDurationTests` 클래스 추가 (테스트 7개). import에 `format_duration`을 더했다.
- `docs/TASKS.md`: T13 체크박스를 `[x]`로 변경.

## 동작 계약
- `0` → `"0s"`, `60` → `"1m"`, `3600` → `"1h"`, `5400` → `"1h30m"`, `3661` → `"1h1m1s"`.
- 왕복 `parse_duration(format_duration(n)) == n`을 0, 59, 60, 3600, 5400, 86399에서 확인 (subTest).
- 음수 입력은 ValueError이며 메시지에 입력값(repr)이 들어간다.

## 자체 결정 (PRD에 없던 세부)
- 시간 단위가 24시간을 넘어도 `h`로 계속 센다 (예: 86400 → `"24h"`). 일 단위는 도입하지 않는다. parse_duration이 `d`를 받지 않기 때문이다.
- 음수 오류 메시지는 한국어 문장으로 쓰고 입력값 repr을 붙인다. parse_duration의 메시지 규칙과 맞춘다.
- 정수가 아닌 입력(예: float)의 검사는 하지 않는다. 타입 힌트 `int`를 따른다.

## 검증
- `python3 -m unittest tests.test_durations -v` → 29 tests OK (FormatDurationTests 7개 포함).
- `python3 -m unittest discover -s tests -t .` → Ran 40 tests, OK.
- `python3 -m compileall -q src` → 출력 없음 (성공).

## 참고
- 새 의존성 없음. 표준 라이브러리만 사용.
- 화면 없음. 서버 실행 명령 해당 없음.
