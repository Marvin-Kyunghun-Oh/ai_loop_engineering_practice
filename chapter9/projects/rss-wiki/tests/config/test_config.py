import tomllib
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from rss_wiki.config import HOST, Settings, load_settings


def test_defaults_without_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    s = load_settings()
    assert isinstance(s, Settings)
    assert s.port == 8000
    assert s.first_fetch_limit == 10
    assert s.max_per_run == 50
    assert s.content_max_chars == 12000
    assert s.http_timeout_sec == 20
    assert s.claude_timeout_sec == 120
    assert s.claude_path == "claude"
    assert s.claude_model is None
    assert s.wiki_dir == (tmp_path / "wiki").resolve()
    assert s.db_path == (tmp_path / "rss-wiki.db").resolve()
    assert s.log_dir == (tmp_path / "logs").resolve()
    assert HOST == "127.0.0.1"


def test_cwd_file_is_found(tmp_path, monkeypatch):
    (tmp_path / "rss-wiki.toml").write_text("port = 9000\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert load_settings().port == 9000


def test_toml_overrides(tmp_path):
    p = tmp_path / "c.toml"
    p.write_text('port = 9001\nclaude_model = "haiku"\nmax_per_run = 5\n', encoding="utf-8")
    s = load_settings(p)
    assert s.port == 9001
    assert s.claude_model == "haiku"
    assert s.max_per_run == 5
    assert s.first_fetch_limit == 10


def test_relative_paths_resolve_to_config_dir(tmp_path, monkeypatch):
    cfg_dir = tmp_path / "conf"
    cfg_dir.mkdir()
    other = tmp_path / "other"
    other.mkdir()
    monkeypatch.chdir(other)
    p = cfg_dir / "c.toml"
    p.write_text('wiki_dir = "vault/wiki"\ndb_path = "x.db"\n', encoding="utf-8")
    s = load_settings(p)
    assert s.wiki_dir == (cfg_dir / "vault" / "wiki").resolve()
    assert s.db_path == (cfg_dir / "x.db").resolve()
    assert s.log_dir == (cfg_dir / "logs").resolve()


def test_absolute_path_kept(tmp_path):
    target = tmp_path / "abs_wiki"
    p = tmp_path / "c.toml"
    p.write_text(f"wiki_dir = '{target}'\n", encoding="utf-8")
    assert load_settings(p).wiki_dir == target.resolve()


INT_KEYS = [
    "port",
    "first_fetch_limit",
    "max_per_run",
    "content_max_chars",
    "http_timeout_sec",
    "claude_timeout_sec",
]


@pytest.mark.parametrize("key", INT_KEYS)
@pytest.mark.parametrize("value", ["0", "-1", '"80"', "1.5", "true"])
def test_invalid_int_raises(tmp_path, key, value):
    p = tmp_path / "c.toml"
    p.write_text(f"{key} = {value}\n", encoding="utf-8")
    with pytest.raises(ValueError, match=key):
        load_settings(p)


def test_port_range(tmp_path):
    p = tmp_path / "c.toml"
    p.write_text("port = 65536\n", encoding="utf-8")
    with pytest.raises(ValueError, match="port"):
        load_settings(p)
    p.write_text("port = 65535\n", encoding="utf-8")
    assert load_settings(p).port == 65535


@pytest.mark.parametrize("key", ["claude_path", "claude_model"])
@pytest.mark.parametrize("value", ['""', "3"])
def test_invalid_str_raises(tmp_path, key, value):
    p = tmp_path / "c.toml"
    p.write_text(f"{key} = {value}\n", encoding="utf-8")
    with pytest.raises(ValueError, match=key):
        load_settings(p)


@pytest.mark.parametrize("key", ["wiki_dir", "db_path", "log_dir"])
def test_invalid_path_raises(tmp_path, key):
    p = tmp_path / "c.toml"
    p.write_text(f"{key} = 5\n", encoding="utf-8")
    with pytest.raises(ValueError, match=key):
        load_settings(p)


def test_broken_toml_mentions_path(tmp_path):
    p = tmp_path / "broken.toml"
    p.write_text("port = = 1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="broken.toml") as ei:
        load_settings(p)
    assert isinstance(ei.value.__cause__, tomllib.TOMLDecodeError)


def test_errors_mention_config_path(tmp_path):
    p = tmp_path / "named.toml"
    p.write_text("port = 0\n", encoding="utf-8")
    with pytest.raises(ValueError, match="named.toml"):
        load_settings(p)
    p.write_text("prot = 1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="named.toml"):
        load_settings(p)


def test_cp949_file_rejected(tmp_path):
    p = tmp_path / "cp.toml"
    p.write_bytes('wiki_dir = "위키"'.encode("cp949"))
    with pytest.raises(ValueError, match="cp.toml") as ei:
        load_settings(p)
    assert isinstance(ei.value.__cause__, UnicodeDecodeError)
    assert "UTF-8" in str(ei.value)


def test_bom_file_rejected(tmp_path):
    p = tmp_path / "bom.toml"
    p.write_bytes(b"\xef\xbb\xbf" + b"port = 9000\n")
    with pytest.raises(ValueError, match="bom.toml") as ei:
        load_settings(p)
    assert "BOM" in str(ei.value)


def test_tilde_expanded(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    p = tmp_path / "c.toml"
    p.write_text('wiki_dir = "~/w"\n', encoding="utf-8")
    assert load_settings(p).wiki_dir == (Path.home() / "w").resolve()
    assert Path.home().resolve() == home.resolve()


def test_empty_path_raises(tmp_path):
    p = tmp_path / "c.toml"
    p.write_text('wiki_dir = ""\n', encoding="utf-8")
    with pytest.raises(ValueError, match="wiki_dir"):
        load_settings(p)


@pytest.mark.parametrize("line", ['claude_path = ""', "db_path = 5"])
def test_field_errors_mention_config_path(tmp_path, line):
    p = tmp_path / "where.toml"
    p.write_text(line + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="where.toml"):
        load_settings(p)


def test_unknown_key_raises(tmp_path):
    p = tmp_path / "c.toml"
    p.write_text("prot = 1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="prot"):
        load_settings(p)


def test_host_key_rejected(tmp_path):
    p = tmp_path / "c.toml"
    p.write_text('host = "0.0.0.0"\n', encoding="utf-8")
    with pytest.raises(ValueError, match="host"):
        load_settings(p)


def test_explicit_missing_path(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_settings(tmp_path / "nope.toml")


def test_settings_frozen():
    with pytest.raises(FrozenInstanceError):
        Settings().port = 1  # type: ignore[misc]
