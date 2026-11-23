"""운영 상수 (PRD §14)와 설정."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

# 수집
FETCH_CRON = {"hour": "*", "minute": 0}  # 매시 정각
FEED_CONCURRENCY = 5
FEED_FETCH_TIMEOUT = 30  # 초
EXTRACT_TIMEOUT = 20  # 초

# Claude CLI
CLAUDE_TIMEOUT = 120  # 초
LLM_MAX_RETRIES = 3
LLM_BACKOFF_SECONDS = (2, 4, 8)

# 위키 재구성
WIKI_INPUT_CHAR_LIMIT = 100_000
WIKI_RECENT_STEPS = (10, 5, 3, 0)  # 입력 초과 시 existing_recent_articles 축소 순서
WIKI_FIRST_BUILD_ARTICLES = 20

# 서버
HOST = "127.0.0.1"
PORT = 8000


@dataclass(frozen=True)
class Settings:
    db_path: Path = Path("./data/rss-wiki.db")
    log_path: Path = Path("./data/logs/rss-wiki.log")
    claude_command: tuple[str, ...] = ("claude", "-p", "--output-format", "text")
    enable_scheduler: bool = True
