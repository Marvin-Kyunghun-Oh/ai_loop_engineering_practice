"""설정 로더: TOML 파일 + 기본값."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, fields
from pathlib import Path

HOST = "127.0.0.1"  # 고정. 설정 키로 받지 않는다.
DEFAULT_CONFIG_NAME = "rss-wiki.toml"

_PATH_FIELDS = ("wiki_dir", "db_path", "log_dir")
_INT_FIELDS = (
    "port",
    "first_fetch_limit",
    "max_per_run",
    "content_max_chars",
    "http_timeout_sec",
    "claude_timeout_sec",
)


@dataclass(frozen=True)
class Settings:
    wiki_dir: Path = Path("wiki")
    db_path: Path = Path("rss-wiki.db")
    log_dir: Path = Path("logs")
    port: int = 8000
    first_fetch_limit: int = 10
    max_per_run: int = 50
    content_max_chars: int = 12000
    http_timeout_sec: int = 20
    claude_timeout_sec: int = 120
    claude_path: str = "claude"
    claude_model: str | None = None


def load_settings(path: Path | None = None) -> Settings:
    if path is not None:
        path = Path(path)
        if not path.is_file():
            raise FileNotFoundError(f"설정 파일을 찾을 수 없습니다: {path}")
        config_file: Path | None = path
    else:
        candidate = Path.cwd() / DEFAULT_CONFIG_NAME
        config_file = candidate if candidate.is_file() else None

    data: dict = {}
    if config_file is not None:
        raw_bytes = config_file.read_bytes()
        if raw_bytes.startswith(b"\xef\xbb\xbf"):
            raise ValueError(
                f"설정 파일 {config_file}이(가) UTF-8 BOM으로 시작합니다. "
                "UTF-8(BOM 없음)으로 저장하세요."
            )
        try:
            data = tomllib.loads(raw_bytes.decode("utf-8"))
        except UnicodeDecodeError as e:
            raise ValueError(
                f"설정 파일 {config_file}을(를) UTF-8로 읽을 수 없습니다. "
                "UTF-8(BOM 없음)으로 저장하세요."
            ) from e
        except tomllib.TOMLDecodeError as e:
            raise ValueError(f"설정 파일 {config_file}을(를) 파싱할 수 없습니다: {e}") from e
        base = config_file.resolve().parent
        where = f" (설정 파일: {config_file})"
    else:
        base = Path.cwd().resolve()
        where = ""

    known = {f.name for f in fields(Settings)}
    unknown = sorted(set(data) - known)
    if unknown:
        raise ValueError(f"알 수 없는 설정 키: {', '.join(unknown)}{where}")

    kwargs: dict = {}
    defaults = Settings()
    for key, value in data.items():
        if key in _INT_FIELDS:
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(f"설정 {key}는 양의 정수여야 합니다: {value!r}{where}")
            if key == "port" and value > 65535:
                raise ValueError(f"설정 port는 1~65535여야 합니다: {value!r}{where}")
        elif key in ("claude_path", "claude_model"):
            if not isinstance(value, str) or not value:
                raise ValueError(
                    f"설정 {key}는 비어 있지 않은 문자열이어야 합니다: {value!r}{where}"
                )
        kwargs[key] = value
    for key in _PATH_FIELDS:
        raw = kwargs.get(key, getattr(defaults, key))
        if not isinstance(raw, (str, Path)) or not str(raw):
            raise ValueError(f"설정 {key}는 경로 문자열이어야 합니다: {raw!r}{where}")
        p = Path(raw).expanduser()
        kwargs[key] = (p if p.is_absolute() else base / p).resolve()
    return Settings(**kwargs)
