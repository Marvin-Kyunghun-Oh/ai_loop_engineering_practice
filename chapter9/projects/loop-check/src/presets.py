"""자주 쓰는 시간을 이름과 함께 CSV 파일에 저장하고 불러오는 모듈.

파일 형식:
- UTF-8 with BOM(`utf-8-sig`)으로 읽고 쓴다. 엑셀에서 한글 이름이 깨지지 않게 하기 위함이다.
- 1행은 헤더 `name,duration`이고 저장할 때 항상 쓴다.
- 이후 행은 `이름,시간 문자열`이다(예: `집중,25m`). 시간 문자열은 `parse_duration` 형식을 따른다.

동작:
- save_presets는 모든 값을 먼저 `parse_duration`으로 검증한다. 잘못된 값이 하나라도 있으면
  ValueError를 던지고 파일을 만들거나 바꾸지 않는다.
- load_presets는 파일이 없으면 빈 dict를 돌려준다. 같은 이름이 두 번 나오면 ValueError를 던진다.
  값은 `parse_duration`으로 초 단위 정수가 된다.
"""

import csv
import os

from src.durations import parse_duration

_ENCODING = "utf-8-sig"
_HEADER = ["name", "duration"]


def save_presets(path: str, presets: dict[str, str]) -> None:
    """프리셋 이름과 시간 문자열을 CSV 파일로 저장한다.

    presets의 모든 값을 `parse_duration`으로 먼저 검증한다. 잘못된 값이 하나라도 있으면
    ValueError를 던지며, 이때 파일은 만들거나 바꾸지 않는다.
    파일이 이미 있으면 내용을 덮어쓴다. 헤더 `name,duration`은 항상 쓴다.
    """
    for name, value in presets.items():
        parse_duration(value)  # 잘못된 값이면 ValueError. 파일은 아직 건드리지 않는다.

    with open(path, "w", encoding=_ENCODING, newline="") as f:
        writer = csv.writer(f)
        writer.writerow(_HEADER)
        for name, value in presets.items():
            writer.writerow([name, value])


def load_presets(path: str) -> dict[str, int]:
    """CSV 파일에서 프리셋을 읽어 이름 → 초 단위 정수 dict로 돌려준다.

    파일이 없으면 빈 dict를 돌려준다.
    같은 이름이 두 번 나오면 ValueError를 던진다.
    헤더에 `name` 또는 `duration` 열이 없거나, 이름이나 시간 값이 빈 행이면 ValueError를 던진다.
    이때 메시지에 열 이름 또는 행 번호를 넣는다. KeyError나 None 전달 오류는 새지 않는다.
    값은 `parse_duration`으로 변환하며, 잘못된 값이면 parse_duration의 ValueError가 그대로 전파된다.
    """
    if not os.path.exists(path):
        return {}

    presets: dict[str, int] = {}
    with open(path, "r", encoding=_ENCODING, newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        for column in _HEADER:
            if column not in fieldnames:
                raise ValueError(f"CSV 헤더에 {column!r} 열이 없음")
        for row in reader:
            row_no = reader.line_num
            name = row.get("name")
            value = row.get("duration")
            if not name:
                raise ValueError(f"프리셋 이름이 비어 있음 (행 {row_no})")
            if not value:
                raise ValueError(f"프리셋 시간 값이 비어 있음 (행 {row_no}, 이름 {name!r})")
            if name in presets:
                raise ValueError(f"프리셋 이름이 중복됨: {name!r} (행 {row_no})")
            presets[name] = parse_duration(value)
    return presets
