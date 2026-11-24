# TASKS

## M1. 골격과 정상 경로

- [x] T1. 패키지 골격과 parse_duration 스텁 — PASS 7/9 · 결정: - · 상세: archive/TASKS-M1.md#T1

- [x] T2. 정상 입력 파싱 구현 — PASS 9/9 · 결정: 정규식 fullmatch 하나로 순서·중복을 강제한다 · 상세: archive/TASKS-M1.md#T2

- [x] T3. 정상 입력 테스트 작성 — PASS 10/12 · 결정: 정상 입력 테스트는 입력당 메서드 하나 · 상세: archive/TASKS-M1.md#T3

## M2. 오류 경로

- [x] T4. 오류 입력 ValueError 처리 — PASS 9/12 · 결정: 빈 입력은 정규식 전에 strip으로 따로 거른다 · 상세: archive/TASKS-M2.md#T4

- [x] T5. 오류 입력 8종 테스트 작성 — PASS 11/12 · 결정: 오류 테스트는 헬퍼로 예외 종류와 repr 포함을 함께 검증 · 상세: archive/TASKS-M2.md#T5

## M3. 독스트링

- [x] T8. 앞뒤 공백 입력 경계 명시 확인 (BACKLOG: M2 마감) — PASS 12/12 · 결정: 공백 경계 테스트는 입력당 메서드 하나로 추가 · 상세: archive/TASKS-M3.md#T8

- [x] T6. 모듈과 함수 독스트링 작성 — PASS 10/12 · 결정: 독스트링은 한국어로, 오류 메시지에 repr 포함을 명시 · 상세: archive/TASKS-M3.md#T6

## M4. 최종 검증

- [x] T7. 전체 테스트 실행과 PRD 대조 — PASS 10/12 · 결정: - · 상세: archive/TASKS-M4.md#T7

## M5. 프리셋 저장 (PRD M2)

- [x] T9. 프리셋 저장과 불러오기 구현 — - · 결정: - · 상세: archive/TASKS-M5.md#T9

- [x] T10. 프리셋 테스트 작성 — PASS 11/12 · 결정: 중복 이름 테스트는 csv.writer로 파일을 직접 만든다 · 상세: archive/TASKS-M5.md#T10

- [x] T11. load_presets 잘못된 CSV 행의 예외 계약 정리 (BACKLOG: M5 마감) — PASS 10/12 · 결정: 빈 이름·열 부족 행도 ValueError로 통일 · 상세: archive/TASKS-M5.md#T11

## M6. 시간 계산과 출력 (PRD M3)

- [x] T12. total_minutes 구현과 테스트
  - 내용
    - `src/durations.py`에 `total_minutes(text: str) -> int`를 만든다. `parse_duration(text)` 결과를 60으로 내림한 값이다. 오류 입력은 parse_duration이 던지는 ValueError를 그대로 전파한다.
    - 예: `"1h30m"` → 90, `"59s"` → 0, `"1h1m1s"` → 61.
    - `tests/test_durations.py`에 테스트를 추가한다. 정상 예 3개 이상과 오류 입력 `"5d"`의 ValueError를 확인한다.
  - acceptance
    - `python3 -m unittest tests.test_durations -v` 가 통과하고, `total_minutes`의 `"1h30m"`→90, `"59s"`→0 기대값 테스트가 있다.
    - `python3 -m unittest discover -s tests -t .` 가 통과한다.
  - touch: `src/durations.py`, `tests/test_durations.py`

- [x] T13. format_duration 구현과 왕복 테스트
  - 전제 충족: `docs/decisions/format-style.md`에 `합의: A`가 있다(사이클 14 확인).
  - 내용
    - `src/durations.py`에 `format_duration(seconds: int) -> str`를 만든다. `parse_duration`이 읽는 형식으로 쓰고, 0초는 `0s`다. `0` 이상만 받고 음수는 ValueError다.
    - 예: `0` → `"0s"`, `60` → `"1m"`, `3600` → `"1h"`, `5400` → `"1h30m"`, `3661` → `"1h1m1s"`.
    - 왕복 `parse_duration(format_duration(n)) == n`을 0, 59, 60, 3600, 5400, 86399에서 확인한다. 음수 입력 ValueError 테스트를 추가한다.
  - acceptance
    - `python3 -m unittest tests.test_durations -v` 가 통과하고, 왕복 값 0, 59, 60, 3600, 5400, 86399 를 다루는 테스트와 음수 ValueError 테스트가 있다.
    - `python3 -m unittest discover -s tests -t .` 가 통과한다.
  - touch: `src/durations.py`, `tests/test_durations.py`
