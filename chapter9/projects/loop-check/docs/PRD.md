# PRD: 시간 문자열 변환기 (loop-check)

하네스의 FAIL → 재작업 루프와 결정 합의 불발 HALT를 확인하려는 아주 작은 프로젝트다.
요구가 많은 것은 의도다. 한 번에 다 만족시키기 어렵게 썼다.

## 목표

타이머 입력처럼 `"1h30m"` 형태의 문자열을 초 단위 정수로 바꾸는 함수를 만든다.
잘못된 입력은 조용히 넘기지 않고 이유가 보이는 오류로 알린다.
자주 쓰는 시간은 이름을 붙여 저장해 두고 꺼내 쓸 수 있어야 한다.
**저장한 목록은 개발자가 아닌 사람이 스프레드시트(엑셀 등)로 열어 직접 고친다.** 이것이 저장 방식 선택의 가장 중요한 기준이다.

## 요구

### M1. parse_duration

1. `src/durations.py`에 `parse_duration(text: str) -> int`를 만든다.
   - 단위는 `h`(시간), `m`(분), `s`(초)이고 소문자만 허용한다. 결과는 초 단위 정수다.
   - 단위는 `h`, `m`, `s` 순서로만 쓸 수 있고 각각 한 번까지만 쓴다. 일부만 써도 된다.
   - 앞뒤 공백은 무시한다. 중간 공백은 허용하지 않는다.
   - 정상 예: `"1h30m"` → 5400, `"90s"` → 90, `"2h"` → 7200, `" 45m "` → 2700, `"1h1m1s"` → 3661.
2. 아래 입력은 모두 `ValueError`를 던지고, 오류 메시지에 입력값(`repr`)을 포함한다.
   - 빈 문자열, 공백만 있는 문자열
   - 음수(`"-5m"`)
   - 단위 중복(`"1h1h"`)
   - 단위 순서 뒤바뀜(`"30m1h"`)
   - 단위 없는 숫자(`"90"`)
   - 모르는 단위(`"5d"`)
   - 대문자 단위(`"1H"`)
   - 중간 공백(`"1h 30m"`)
3. `tests/test_durations.py`에 `unittest`로 테스트를 만든다.
   - 정상 입력 5개 이상.
   - 위 2번의 오류 입력 **8가지 모두를 각각** 검증한다. 오류 종류뿐 아니라 메시지에 입력값이 들어 있는지도 확인한다.
4. 모듈과 함수에 독스트링을 쓴다. 독스트링에 허용 형식과 오류 조건을 적는다.

### M2. 프리셋 저장

1. `src/presets.py`에 `save_presets(path, presets: dict[str, str])`와 `load_presets(path) -> dict[str, int]`를 만든다.
   - `presets`는 이름 → 시간 문자열(`"25m"`)이다. 저장할 때 `parse_duration`으로 검증하고, 잘못된 값이 있으면 `ValueError`를 던진다(파일은 건드리지 않는다).
   - `load_presets`는 이름 → 초 단위 정수를 돌려준다.
   - 저장 형식은 CSV(UTF-8, 1행 헤더 `name,duration`, 값은 시간 문자열)다. 사람이 엑셀로 직접 여는 것이 가장 중요한 기준이므로 JSON/SQLite보다 CSV를 택한다. (자체 결정: 합의)
2. `tests/test_presets.py`에 `unittest`로 테스트를 만든다. 저장 후 불러오기가 같은 값을 주는지, 잘못된 값, 파일이 없을 때, 이름이 중복될 때를 확인한다. 임시 폴더를 쓴다.

### M3. 시간 계산과 출력

1. `src/durations.py`에 `total_minutes(text: str) -> int`를 만든다. `parse_duration(text)`의 결과를 분 단위로 **내림**한 값이다. 오류 입력은 `parse_duration`과 같은 `ValueError`다. 예: `"1h30m"` → 90, `"59s"` → 0.
2. `src/durations.py`에 `format_duration(seconds: int) -> str`를 만든다. 초 단위 정수를 사람이 읽는 문자열로 바꾼다. `0` 이상만 받고 음수는 `ValueError`다. **출력 형식은 `1h30m`처럼 `parse_duration`이 읽는 형식이다. 0초는 `0s`로 쓴다. (자체 결정: 합의)**
   - `parse_duration(format_duration(n)) == n`이 모든 `n >= 0`에서 성립해야 한다(왕복). 이것이 출력 형식 선택의 가장 중요한 기준이다.
3. 각 함수의 테스트를 `tests/test_durations.py`에 추가한다. `format_duration`은 왕복 성질을 여러 값(0, 59, 60, 3600, 5400, 86399 등)으로 확인한다.

## 제약

- 표준 라이브러리만 쓴다. 외부 패키지를 설치하지 않는다.
- 패키지 구성: `src/__init__.py`, `tests/__init__.py`를 두고 테스트에서 `from src.durations import parse_duration`으로 가져온다.
- 테스트 실행: `python3 -m unittest discover -s tests -t .`

## 미해결 의사결정

- 없음. (사이클 14에 시간 출력 형식 합의 A를 M3에 반영했다.)
