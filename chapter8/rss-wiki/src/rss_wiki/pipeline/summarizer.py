"""개별 글 요약·분류 (PRD §7.2, §8.1)."""
from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from jinja2 import Environment, StrictUndefined

from ..db import log_job, utcnow
from .fetcher import FeedEntry
from .llm import LLMError

PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "article_summarize.txt"
_env = Environment(undefined=StrictUndefined, keep_trailing_newline=True, autoescape=False)
_HANGUL = re.compile(r"[가-힣]")


class SummaryFormatError(ValueError):
    pass


@dataclass
class SummarizeOutcome:
    article_id: int | None
    status: str  # 'ok' | 'failed' | 'duplicate'
    category_id: int | None = None
    error: str | None = None


def detect_language(text: str) -> str:
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return "기타"
    return "ko" if len(_HANGUL.findall(text)) / len(letters) > 0.3 else "en"


def resolve_category(conn: sqlite3.Connection, name: str) -> int:
    """이름으로 카테고리를 찾고(병합된 카테고리는 대상으로 이동), 없으면 만든다."""
    name = name.strip()
    row = conn.execute("SELECT id, merged_into_id FROM categories WHERE name=?", (name,)).fetchone()
    seen: set[int] = set()
    while row is not None and row["merged_into_id"] is not None and row["id"] not in seen:
        seen.add(row["id"])
        row = conn.execute("SELECT id, merged_into_id FROM categories WHERE id=?",
                           (row["merged_into_id"],)).fetchone()
    if row is not None:
        return row["id"]
    cur = conn.execute("INSERT INTO categories(name) VALUES (?)", (name,))
    return cur.lastrowid


def build_prompt(conn: sqlite3.Connection, entry: FeedEntry, content: str) -> str:
    cats = conn.execute(
        "SELECT name, description FROM categories WHERE merged_into_id IS NULL ORDER BY id").fetchall()
    return _env.from_string(PROMPT_PATH.read_text(encoding="utf-8")).render(
        existing_categories=[dict(c) for c in cats], title=entry.title, url=entry.url,
        detected_language=detect_language(content), content=content)


def _validate(data: dict) -> tuple[str, str, str | None]:
    summary, cat = data.get("summary"), data.get("category_name")
    if not isinstance(summary, str) or not summary.strip():
        raise SummaryFormatError("summary 누락")
    if not isinstance(cat, str) or not cat.strip():
        raise SummaryFormatError("category_name 누락")
    lang = data.get("language_detected")
    return summary.strip(), cat.strip(), lang if isinstance(lang, str) else None


async def summarize_article(
    conn: sqlite3.Connection, llm, *, feed_id: int, entry: FeedEntry,
    content: str, raw_summary: str | None = None,
) -> SummarizeOutcome:
    """글을 요약·분류해 저장한다. 실패하면 `status='failed'` 레코드를 남겨 다음 사이클의 재수집을 막는다."""
    started = utcnow()
    attempts, error = 1, None
    try:
        resp = await llm.complete_json(build_prompt(conn, entry, content))
        attempts = resp.attempts
        summary, cat_name, lang = _validate(resp.value)
    except LLMError as e:
        attempts, error = e.attempts, str(e)
    except SummaryFormatError as e:
        error = f"LLM 응답 형식 오류: {e}"

    if error is not None:
        cur = conn.execute(
            """INSERT OR IGNORE INTO articles(feed_id, url, title, author, published_at, raw_summary,
                   extracted_content, status) VALUES (?,?,?,?,?,?,?, 'failed')""",
            (feed_id, entry.url, entry.title, entry.author, entry.published_at,
             entry.raw_summary, content))
        conn.commit()
        log_job(conn, "summarize", cur.lastrowid or entry.url, "failed",
                error=error, attempts=attempts, started_at=started)
        return SummarizeOutcome(cur.lastrowid or None, "failed", error=error)

    category_id = resolve_category(conn, cat_name)
    cur = conn.execute(
        """INSERT OR IGNORE INTO articles(feed_id, url, title, author, published_at, raw_summary,
               extracted_content, llm_summary, primary_category_id, language, status)
           VALUES (?,?,?,?,?,?,?,?,?,?, 'ok')""",
        (feed_id, entry.url, entry.title, entry.author, entry.published_at, entry.raw_summary,
         content, summary, category_id, lang or detect_language(content)))
    conn.commit()
    if cur.rowcount == 0:
        return SummarizeOutcome(None, "duplicate")
    log_job(conn, "summarize", cur.lastrowid, "ok", attempts=attempts, started_at=started)
    return SummarizeOutcome(cur.lastrowid, "ok", category_id)
