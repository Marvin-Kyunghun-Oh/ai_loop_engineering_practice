"""위키 페이지 증분 재구성 (PRD §8.2)."""
from __future__ import annotations

import re
import sqlite3
from pathlib import Path

from jinja2 import Environment, StrictUndefined

from .. import config
from ..db import log_job, utcnow
from .llm import LLMError

PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "wiki_rebuild.txt"
_env = Environment(undefined=StrictUndefined, keep_trailing_newline=True, autoescape=False)
_REQUIRED_SECTIONS = ("## 한줄 요약", "## 핵심 내용")
_ORDER = "ORDER BY COALESCE(published_at, fetched_at) DESC, id DESC"


def one_line(summary: str | None, limit: int = 80) -> str:
    first = re.split(r"(?<=[.!?。])\s", (summary or "").strip(), maxsplit=1)[0]
    return first if len(first) <= limit else first[: limit - 1] + "…"


def _rows(conn, sql, args=()):
    return [dict(r) for r in conn.execute(sql, args)]


def _ok_count(conn: sqlite3.Connection, category_id: int) -> int:
    return conn.execute(
        "SELECT COUNT(*) c FROM articles WHERE primary_category_id=? AND status='ok'",
        (category_id,)).fetchone()["c"]


def build_rebuild_prompt(
    conn: sqlite3.Connection, category_id: int, new_article_ids: list[int] | None = None,
    char_limit: int = config.WIKI_INPUT_CHAR_LIMIT,
) -> str:
    """입력이 상한을 넘으면 existing_recent_articles를 10→5→3→0개로 줄인다(new_articles는 항상 전부)."""
    cat = conn.execute("SELECT name FROM categories WHERE id=?", (category_id,)).fetchone()
    wiki = conn.execute("SELECT content_markdown, articles_count_at_rebuild FROM wiki_pages "
                        "WHERE category_id=?", (category_id,)).fetchone()
    previous = wiki["content_markdown"] if wiki else ""
    base = "primary_category_id=? AND status='ok'"

    if new_article_ids is None:  # 이전 재구성 이후 늘어난 만큼을 최신 글로 간주(실패한 재구성 보완)
        n = max(0, _ok_count(conn, category_id) - (wiki["articles_count_at_rebuild"] if wiki else 0))
        new_ids = [r["id"] for r in conn.execute(
            f"SELECT id FROM articles WHERE {base} ORDER BY id DESC LIMIT ?", (category_id, n))]
    else:
        new_ids = list(new_article_ids)
    marks = ",".join("?" * len(new_ids)) or "NULL"
    new_articles = _rows(
        conn, f"SELECT title, url, llm_summary, published_at FROM articles "
              f"WHERE {base} AND id IN ({marks}) {_ORDER}", (category_id, *new_ids))

    first_build = not previous
    steps = [config.WIKI_FIRST_BUILD_ARTICLES if first_build else config.WIKI_RECENT_STEPS[0],
             *config.WIKI_RECENT_STEPS[1:]]
    template = _env.from_string(PROMPT_PATH.read_text(encoding="utf-8"))
    prompt = ""
    for limit in steps:
        if first_build:  # 최초 빌드: 전체 글 중 최신 N개
            recent = _rows(conn, f"SELECT title, published_at, llm_summary FROM articles WHERE {base} "
                                 f"{_ORDER} LIMIT ?", (category_id, limit))
        else:
            recent = _rows(conn, f"SELECT title, published_at, llm_summary FROM articles "
                                 f"WHERE {base} AND id NOT IN ({marks}) {_ORDER} LIMIT ?",
                           (category_id, *new_ids, limit))
        for a in recent:
            a["one_line"] = one_line(a["llm_summary"])
        prompt = template.render(category_name=cat["name"], previous_wiki_markdown=previous,
                                 new_articles=new_articles, existing_recent_articles=recent)
        if len(prompt) <= char_limit:
            break
    return prompt


def clean_markdown(text: str) -> str:
    text = text.strip()
    m = re.match(r"^```(?:markdown|md)?\s*\n(.*)\n```$", text, re.S)
    return (m.group(1) if m else text).strip()


def validate_markdown(text: str) -> None:
    if not text.startswith("# ") or any(s not in text for s in _REQUIRED_SECTIONS):
        raise ValueError("위키 Markdown 구조가 올바르지 않음")


async def rebuild_category(
    conn: sqlite3.Connection, llm, category_id: int, new_article_ids: list[int] | None = None,
    char_limit: int = config.WIKI_INPUT_CHAR_LIMIT,
) -> bool:
    """카테고리의 위키 페이지를 다시 만든다. 성공하면 has_unread_updates=1. 실패하면 기존 페이지를 유지한다."""
    started = utcnow()
    count = _ok_count(conn, category_id)
    if count == 0:
        return False
    prompt = build_rebuild_prompt(conn, category_id, new_article_ids, char_limit)
    attempts = 1
    try:
        resp = await llm.complete_text(prompt)
        attempts = resp.attempts
        markdown = clean_markdown(resp.value)
        validate_markdown(markdown)
    except LLMError as e:
        log_job(conn, "rebuild_wiki", category_id, "failed", error=str(e), attempts=e.attempts,
                started_at=started)
        return False
    except ValueError as e:
        log_job(conn, "rebuild_wiki", category_id, "failed", error=str(e), attempts=attempts,
                started_at=started)
        return False

    conn.execute(
        """INSERT INTO wiki_pages(category_id, content_markdown, last_rebuilt_at,
                                  articles_count_at_rebuild, has_unread_updates)
           VALUES (?,?,?,?,1)
           ON CONFLICT(category_id) DO UPDATE SET content_markdown=excluded.content_markdown,
             last_rebuilt_at=excluded.last_rebuilt_at,
             articles_count_at_rebuild=excluded.articles_count_at_rebuild, has_unread_updates=1""",
        (category_id, markdown, utcnow(), count))
    conn.commit()
    log_job(conn, "rebuild_wiki", category_id, "ok", attempts=attempts, started_at=started)
    return True
