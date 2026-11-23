import pytest

from rss_wiki.config import Settings
from rss_wiki.db import connect, init_db


@pytest.fixture
def settings(tmp_path):
    return Settings(db_path=tmp_path / "data" / "t.db", log_path=tmp_path / "data" / "logs" / "t.log",
                    enable_scheduler=False)


@pytest.fixture
def conn(settings):
    init_db(settings.db_path)
    c = connect(settings.db_path)
    yield c
    c.close()
