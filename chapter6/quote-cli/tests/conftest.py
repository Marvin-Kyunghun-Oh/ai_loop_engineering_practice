# 공통 픽스처: 실제 quotes.db / quotes.json 을 건드리지 않도록 임시 폴더를 가리키게 한다.
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import main  # noqa: E402


@pytest.fixture
def db(tmp_path, monkeypatch):
    # 임시 DB + 존재하지 않는 시드 경로 -> 빈 DB로 시작
    monkeypatch.setattr(main, "DB_FILE", tmp_path / "test.db")
    monkeypatch.setattr(main, "QUOTES_FILE", tmp_path / "no-seed.json")
    return tmp_path / "test.db"
