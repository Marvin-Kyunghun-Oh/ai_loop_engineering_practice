# TASKS-M1.md

## M1. 골격과 정상 경로

- [x] T1. 패키지 골격과 parse_duration 스텁
  - 내용
    - `src/__init__.py`, `tests/__init__.py`를 빈 파일로 만든다.
    - `src/durations.py`에 `parse_duration(text: str) -> int` 시그니처만 두고 본문은 `raise NotImplementedError`로 둔다.
  - acceptance
    - `python3 -m compileall -q src` 가 오류 없이 끝난다(종료 코드 0). import 동작은 T3 테스트가 확인한다.
  - touch: `src/__init__.py`, `src/durations.py`, `tests/__init__.py`
  - BLOCKED(1회째): 허용되지 않은 명령 필요: `python3 -c "from src.durations import parse_duration; print('ok')"` (acceptance 검증 명령, 하네스 허용 목록 밖)

- [x] T2. 정상 입력 파싱 구현
  - 내용
    - `strip()` 후 `h`, `m`, `s` 단위를 순서대로 최대 한 번씩 읽어 초 단위 정수로 합산한다.
    - 정규식 하나로 형식을 검사한다. 이 항목에서는 오류 입력 처리를 하지 않는다.
  - acceptance
    - `python3 -m compileall -q src` 가 오류 없이 끝난다.
    - 정상 예 5개(`"1h30m"`→5400, `"90s"`→90, `"2h"`→7200, `" 45m "`→2700, `"1h1m1s"`→3661)의 값은 T3 테스트가 검증한다.
  - touch: `src/durations.py`

- [x] T3. 정상 입력 테스트 작성
  - 내용
    - `tests/test_durations.py`를 `unittest`로 만들고 정상 입력 5개 이상을 검증한다.
  - acceptance
    - `python3 -m unittest tests.test_durations -v` 가 통과한다. 정상 입력 테스트가 5개 이상이다.
  - touch: `tests/test_durations.py`
