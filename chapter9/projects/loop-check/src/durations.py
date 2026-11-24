"""시간 문자열("1h30m", "90s" 등)을 초 단위 정수로 바꾸는 모듈.

허용 형식:
- 단위는 h(시간), m(분), s(초) 세 가지이며 소문자만 허용한다.
- 단위는 h, m, s 순서로만 쓰고 각각 한 번까지 쓸 수 있다. 일부만 써도 된다.
- 앞뒤 공백은 무시한다. 중간 공백은 허용하지 않는다.
- 음수, 단위 없는 숫자, 모르는 단위, 대문자 단위는 허용하지 않는다.

오류 조건: 위 형식에 맞지 않으면 ValueError를 던지며, 메시지에 입력값(repr)을 포함한다.
"""

import re

_PATTERN = re.compile(r"(?:([0-9]+)h)?(?:([0-9]+)m)?(?:([0-9]+)s)?")


def parse_duration(text: str) -> int:
    """시간 문자열을 초 단위 정수로 변환한다.

    허용 형식: h(시간), m(분), s(초) 단위를 h, m, s 순서로 각각 최대 한 번 쓴다.
    예: "1h30m" -> 5400, "90s" -> 90, "2h" -> 7200, " 45m " -> 2700, "1h1m1s" -> 3661.
    앞뒤 공백은 무시하고 중간 공백은 허용하지 않는다.

    오류 조건: 빈 문자열이나 공백만 있는 문자열, 음수, 단위 중복, 단위 순서 뒤바뀜,
    단위 없는 숫자, 모르는 단위(예: "5d"), 대문자 단위(예: "1H"), 중간 공백이면
    ValueError를 던진다. 오류 메시지에는 입력값(repr)이 들어간다.
    """
    stripped = text.strip()
    if not stripped:
        raise ValueError(f"잘못된 기간 형식: {text!r}")
    match = _PATTERN.fullmatch(stripped)
    if match is None:
        raise ValueError(f"잘못된 기간 형식: {text!r}")
    hours, minutes, seconds = (int(g) if g is not None else 0 for g in match.groups())
    return hours * 3600 + minutes * 60 + seconds


def total_minutes(text: str) -> int:
    """시간 문자열을 분 단위 정수로 바꾼다. 초 단위는 버린다(내림).

    예: "1h30m" -> 90, "59s" -> 0, "1h1m1s" -> 61.
    오류 입력은 parse_duration이 던지는 ValueError를 그대로 전파한다.
    """
    return parse_duration(text) // 60


def format_duration(seconds: int) -> str:
    """초 단위 정수를 parse_duration이 읽는 형식("1h30m" 등)으로 바꾼다.

    0 이상만 받는다. 음수는 ValueError를 던지며 메시지에 입력값(repr)이 들어간다.
    0초는 "0s"로 쓴다. 0이 아닌 단위만 h, m, s 순서로 이어 쓴다.
    예: 0 -> "0s", 60 -> "1m", 3600 -> "1h", 5400 -> "1h30m", 3661 -> "1h1m1s".
    """
    if seconds < 0:
        raise ValueError(f"음수 기간은 허용하지 않는다: {seconds!r}")
    hours, rest = divmod(seconds, 3600)
    minutes, secs = divmod(rest, 60)
    text = ""
    if hours:
        text += f"{hours}h"
    if minutes:
        text += f"{minutes}m"
    if secs:
        text += f"{secs}s"
    return text or "0s"
