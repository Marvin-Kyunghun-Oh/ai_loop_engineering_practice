from rss_wiki import config
from rss_wiki.config import Settings


def test_operating_constants_match_prd():
    assert config.FETCH_CRON == {"hour": "*", "minute": 0}
    assert config.FEED_CONCURRENCY == 5
    assert config.FEED_FETCH_TIMEOUT == 30
    assert config.EXTRACT_TIMEOUT == 20
    assert config.CLAUDE_TIMEOUT == 120
    assert config.LLM_MAX_RETRIES == 3 and config.LLM_BACKOFF_SECONDS == (2, 4, 8)
    assert config.WIKI_INPUT_CHAR_LIMIT == 100_000
    assert config.WIKI_RECENT_STEPS == (10, 5, 3, 0)
    assert config.WIKI_FIRST_BUILD_ARTICLES == 20
    assert (config.HOST, config.PORT) == ("127.0.0.1", 8000)


def test_default_paths_and_command():
    s = Settings()
    assert str(s.db_path) == "data/rss-wiki.db"
    assert str(s.log_path) == "data/logs/rss-wiki.log"
    assert s.claude_command == ("claude", "-p", "--output-format", "text")
