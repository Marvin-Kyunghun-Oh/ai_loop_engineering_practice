from __future__ import annotations

from pathlib import Path
from typing import Iterator

import re
from datetime import datetime, timezone

from markdown_it import MarkdownIt
from markupsafe import escape
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from ..db import connect

TEMPLATES_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
router = APIRouter()


def localtime(value: str | None) -> str:
    """DB의 UTC 시각(sqlite `YYYY-MM-DD HH:MM:SS` 또는 ISO8601)을 로컬 타임존으로 표시한다."""
    if not value:
        return ""
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        return value
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone().strftime("%Y-%m-%d %H:%M")


templates.env.filters["localtime"] = localtime

_md = MarkdownIt("commonmark", {"html": False})  # LLM이 만든 원시 HTML은 이스케이프, javascript: 링크는 차단


def render_markdown(text: str) -> str:
    return _md.render(text or "")


def get_conn(request: Request) -> Iterator:
    conn = connect(request.app.state.settings.db_path)
    try:
        yield conn
    finally:
        conn.close()


@router.post("/api/fetch")
async def api_fetch(request: Request):
    """수동 수집 트리거. 이미 실행 중이면 409."""
    if not request.app.state.controller.try_start():
        return JSONResponse({"status": "busy", "detail": "이미 수집이 진행 중입니다"}, status_code=409)
    return JSONResponse({"status": "started"}, status_code=202)


@router.get("/api/fetch/status")
async def api_fetch_status(request: Request):
    """수집 진행 상태(화면이 폴링한다)."""
    return JSONResponse(request.app.state.controller.status(), headers={"Cache-Control": "no-store"})


def render(request: Request, name: str, status_code: int = 200, **ctx):
    return templates.TemplateResponse(request, name, ctx, status_code=status_code)


@router.post("/fetch-now")
async def fetch_now(request: Request):
    """UI의 'Fetch now' 버튼. 시작 여부와 무관하게 피드 화면으로 돌아간다."""
    request.app.state.controller.try_start()
    return RedirectResponse("/feeds", status_code=303)


# ---- 피드 관리 ----
def _feeds_page(request: Request, conn, status_code: int = 200, error: str | None = None):
    feeds = conn.execute("SELECT * FROM feeds ORDER BY id").fetchall()
    return render(request, "feeds.html", status_code, feeds=feeds, error=error)


@router.get("/feeds", response_class=HTMLResponse)
def feeds_page(request: Request, conn=Depends(get_conn)):
    return _feeds_page(request, conn)


@router.post("/feeds/add")
def feeds_add(request: Request, url: str = Form(...), conn=Depends(get_conn)):
    url = url.strip()
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.netloc:
        return _feeds_page(request, conn, 400, "http(s) URL을 입력하세요.")
    if conn.execute("SELECT 1 FROM feeds WHERE url=?", (url,)).fetchone():
        return _feeds_page(request, conn, 409, "이미 구독 중인 피드입니다.")
    conn.execute("INSERT INTO feeds(url) VALUES (?)", (url,))
    conn.commit()
    return RedirectResponse("/feeds", status_code=303)


def _require_feed(conn, feed_id: int):
    if conn.execute("SELECT 1 FROM feeds WHERE id=?", (feed_id,)).fetchone() is None:
        raise HTTPException(404, "피드를 찾을 수 없습니다")


@router.post("/feeds/{feed_id}/toggle")
def feeds_toggle(feed_id: int, conn=Depends(get_conn)):
    _require_feed(conn, feed_id)
    conn.execute("UPDATE feeds SET is_active = 1 - is_active WHERE id=?", (feed_id,))
    conn.commit()
    return RedirectResponse("/feeds", status_code=303)


@router.post("/feeds/{feed_id}/delete")
def feeds_delete(feed_id: int, conn=Depends(get_conn)):
    _require_feed(conn, feed_id)
    conn.execute("DELETE FROM feeds WHERE id=?", (feed_id,))  # ON DELETE CASCADE로 articles도 삭제
    conn.commit()
    return RedirectResponse("/feeds", status_code=303)


# ---- 카테고리 편집 / 병합 (/categories/{id} 보다 먼저 선언) ----
def _manage_page(request: Request, conn, status_code: int = 200, error: str | None = None):
    cats = conn.execute(
        """SELECT c.*, p.name AS parent_name,
             (SELECT COUNT(*) FROM articles a WHERE a.primary_category_id=c.id AND a.status='ok') AS article_count,
             (SELECT COUNT(*) FROM categories k WHERE k.parent_id=c.id AND k.merged_into_id IS NULL) AS child_count
           FROM categories c LEFT JOIN categories p ON p.id=c.parent_id
           WHERE c.merged_into_id IS NULL ORDER BY c.name""").fetchall()
    roots = [c for c in cats if c["parent_id"] is None]
    return render(request, "manage.html", status_code, categories=cats, roots=roots, error=error)


def _active_category(conn, category_id: int):
    row = conn.execute("SELECT * FROM categories WHERE id=? AND merged_into_id IS NULL",
                       (category_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "카테고리를 찾을 수 없습니다")
    return row


@router.get("/categories/manage", response_class=HTMLResponse)
def categories_manage(request: Request, conn=Depends(get_conn)):
    return _manage_page(request, conn)


@router.post("/categories/{category_id}/rename")
def categories_rename(category_id: int, request: Request, name: str = Form(...), conn=Depends(get_conn)):
    _active_category(conn, category_id)
    name = name.strip()
    if not name:
        return _manage_page(request, conn, 400, "이름을 입력하세요.")
    if conn.execute("SELECT 1 FROM categories WHERE name=? AND id!=?", (name, category_id)).fetchone():
        return _manage_page(request, conn, 409, f"이미 있는 이름입니다: {name}")
    conn.execute("UPDATE categories SET name=?, is_user_edited=1 WHERE id=?", (name, category_id))
    conn.commit()
    return RedirectResponse("/categories/manage", status_code=303)


@router.post("/categories/{category_id}/merge")
def categories_merge(category_id: int, request: Request, target_id: int = Form(...), conn=Depends(get_conn)):
    """source(category_id)를 target으로 병합: 글 이동 → source 위키 삭제 → target 재구성 트리거."""
    source = _active_category(conn, category_id)
    target = resolve_category(conn, target_id)
    if target is None:
        return _manage_page(request, conn, 404, "병합 대상을 찾을 수 없습니다.")
    if target["id"] == source["id"]:
        return _manage_page(request, conn, 400, "같은 카테고리끼리는 병합할 수 없습니다.")
    sid, tid = source["id"], target["id"]

    # 2단계 계층 유지: 대상이 source의 하위였다면 먼저 source의 자리(상위)로 올린다.
    if target["parent_id"] == sid:
        conn.execute("UPDATE categories SET parent_id=? WHERE id=?", (source["parent_id"], tid))
        target_parent = source["parent_id"]
    else:
        target_parent = target["parent_id"]
    # source의 하위는 대상 아래로(대상이 최상위일 때), 대상이 하위 카테고리면 대상의 상위 아래로 옮긴다.
    new_parent = tid if target_parent is None else target_parent
    conn.execute("UPDATE categories SET parent_id=? WHERE parent_id=? AND id!=?", (new_parent, sid, tid))

    moved = [r["id"] for r in conn.execute(
        "SELECT id FROM articles WHERE primary_category_id=? AND status='ok'", (sid,))]
    conn.execute("UPDATE articles SET primary_category_id=? WHERE primary_category_id=?", (tid, sid))
    conn.execute("DELETE FROM wiki_pages WHERE category_id=?", (sid,))
    # 행은 남긴다: LLM이 옛 이름을 다시 제안해도 대상 카테고리로 연결된다.
    conn.execute("UPDATE categories SET merged_into_id=?, parent_id=NULL WHERE id=?", (tid, sid))
    conn.commit()
    request.app.state.controller.schedule_rebuild(tid, moved)
    return RedirectResponse("/categories/manage", status_code=303)


@router.post("/categories/{category_id}/parent")
def categories_parent(category_id: int, request: Request, parent_id: str = Form(""), conn=Depends(get_conn)):
    cat = _active_category(conn, category_id)
    if parent_id.strip() == "":
        conn.execute("UPDATE categories SET parent_id=NULL WHERE id=?", (category_id,))
        conn.commit()
        return RedirectResponse("/categories/manage", status_code=303)
    try:
        pid = int(parent_id)
    except ValueError:
        return _manage_page(request, conn, 400, "잘못된 상위 카테고리입니다.")
    parent = conn.execute("SELECT * FROM categories WHERE id=? AND merged_into_id IS NULL", (pid,)).fetchone()
    if parent is None:
        return _manage_page(request, conn, 404, "상위 카테고리를 찾을 수 없습니다.")
    if pid == category_id:
        return _manage_page(request, conn, 400, "자기 자신을 상위로 지정할 수 없습니다.")
    if parent["parent_id"] is not None:
        return _manage_page(request, conn, 400, "상위 카테고리는 최상위여야 합니다(2단계까지).")
    if conn.execute("SELECT 1 FROM categories WHERE parent_id=? AND merged_into_id IS NULL",
                    (category_id,)).fetchone():
        return _manage_page(request, conn, 400, "하위 카테고리가 있는 카테고리는 다른 곳의 하위가 될 수 없습니다.")
    conn.execute("UPDATE categories SET parent_id=? WHERE id=?", (pid, category_id))
    conn.commit()
    return RedirectResponse("/categories/manage", status_code=303)


# ---- 카테고리 / 위키 ----
def resolve_category(conn, category_id: int):
    """병합된 카테고리는 최종 대상으로 따라간다. 없으면 None."""
    seen: set[int] = set()
    row = conn.execute("SELECT * FROM categories WHERE id=?", (category_id,)).fetchone()
    while row is not None and row["merged_into_id"] is not None and row["id"] not in seen:
        seen.add(row["id"])
        row = conn.execute("SELECT * FROM categories WHERE id=?", (row["merged_into_id"],)).fetchone()
    return row


@router.get("/", response_class=HTMLResponse)
def index(request: Request, conn=Depends(get_conn)):
    """최상위 카테고리만. 안읽음(본인 또는 하위) 우선 정렬."""
    rows = conn.execute(
        """SELECT c.id, c.name, c.description,
             (SELECT COUNT(*) FROM categories k WHERE k.parent_id=c.id AND k.merged_into_id IS NULL) AS child_count,
             (SELECT COUNT(*) FROM articles a WHERE a.status='ok' AND (a.primary_category_id=c.id OR
                a.primary_category_id IN (SELECT id FROM categories k WHERE k.parent_id=c.id))) AS article_count,
             (COALESCE((SELECT has_unread_updates FROM wiki_pages w WHERE w.category_id=c.id), 0) OR
              EXISTS (SELECT 1 FROM wiki_pages w JOIN categories k ON k.id=w.category_id
                      WHERE k.parent_id=c.id AND k.merged_into_id IS NULL AND w.has_unread_updates=1)) AS unread
           FROM categories c
           WHERE c.parent_id IS NULL AND c.merged_into_id IS NULL
           ORDER BY unread DESC, c.name""").fetchall()
    return render(request, "index.html", categories=rows)


@router.get("/categories/{category_id}", response_class=HTMLResponse)
def category_page(category_id: int, request: Request, conn=Depends(get_conn)):
    if category_id == 0:
        raise HTTPException(404)
    category = resolve_category(conn, category_id)
    if category is None:
        raise HTTPException(404, "카테고리를 찾을 수 없습니다")
    if category["id"] != category_id:
        return RedirectResponse(f"/categories/{category['id']}", status_code=307)
    cid = category["id"]
    wiki = conn.execute("SELECT * FROM wiki_pages WHERE category_id=?", (cid,)).fetchone()
    children = conn.execute(
        """SELECT c.id, c.name, COALESCE(w.has_unread_updates, 0) AS has_unread_updates
           FROM categories c LEFT JOIN wiki_pages w ON w.category_id=c.id
           WHERE c.parent_id=? AND c.merged_into_id IS NULL ORDER BY c.name""", (cid,)).fetchall()
    parent = (conn.execute("SELECT id, name FROM categories WHERE id=?", (category["parent_id"],)).fetchone()
              if category["parent_id"] else None)
    articles = conn.execute(
        """SELECT a.title, a.url, a.llm_summary, a.published_at, a.fetched_at, f.title AS feed_title
           FROM articles a LEFT JOIN feeds f ON f.id=a.feed_id
           WHERE a.status='ok' AND (a.primary_category_id=? OR a.primary_category_id IN
                 (SELECT id FROM categories WHERE parent_id=?))
           ORDER BY COALESCE(a.published_at, a.fetched_at) DESC, a.id DESC LIMIT 200""",
        (cid, cid)).fetchall()
    response = render(request, "category.html", category=category, wiki=wiki,
                      wiki_html=render_markdown(wiki["content_markdown"]) if wiki and wiki["content_markdown"] else "",
                      children=children, parent=parent, articles=articles)
    # 방문하면 읽음 처리 (카테고리 단위)
    conn.execute("UPDATE wiki_pages SET has_unread_updates=0, last_seen_at=datetime('now') "
                 "WHERE category_id=?", (cid,))
    conn.commit()
    return response


# ---- 검색 / 로그 ----
_HL_START, _HL_END = "\x02", "\x03"
SEARCH_LIMIT = 50


def build_fts_query(q: str) -> str | None:
    """사용자 입력을 안전한 FTS5 질의로 바꾼다: 단어별로 따옴표 처리(AND)하고 마지막 단어는 접두 검색(`*`).
    unicode61은 공백·기호 단위로 토큰을 나누므로, 접두 검색으로 한국어 어미 변화를 어느 정도 흡수한다."""
    tokens = re.findall(r"\w+", q, flags=re.UNICODE)
    if not tokens:
        return None
    return " ".join(f'"{t}"' for t in tokens[:-1]) + (" " if len(tokens) > 1 else "") + f'"{tokens[-1]}"*'


def highlight_html(text: str | None) -> str:
    """FTS 마커(\x02/\x03)만 <mark>로 바꾸고 나머지는 모두 이스케이프한다."""
    safe = str(escape(text or ""))
    return safe.replace(_HL_START, "<mark>").replace(_HL_END, "</mark>")


@router.get("/search", response_class=HTMLResponse)
def search(request: Request, q: str = "", conn=Depends(get_conn)):
    q = q.strip()[:200]
    results = []
    fts = build_fts_query(q) if q else None
    if fts:
        rows = conn.execute(
            f"""SELECT a.id, a.url, a.published_at, a.fetched_at, a.primary_category_id AS category_id,
                       c.name AS category_name, f.title AS feed_title,
                       highlight(articles_fts, 0, '{_HL_START}', '{_HL_END}') AS title_hl,
                       snippet(articles_fts, 1, '{_HL_START}', '{_HL_END}', '…', 24) AS sum_snip,
                       snippet(articles_fts, 2, '{_HL_START}', '{_HL_END}', '…', 24) AS body_snip
                FROM articles_fts
                JOIN articles a ON a.id = articles_fts.rowid
                LEFT JOIN categories c ON c.id = a.primary_category_id
                LEFT JOIN feeds f ON f.id = a.feed_id
                WHERE articles_fts MATCH ? AND a.status = 'ok'
                ORDER BY rank LIMIT ?""", (fts, SEARCH_LIMIT)).fetchall()
        for r in rows:
            snippet = r["sum_snip"] if _HL_START in (r["sum_snip"] or "") else (r["body_snip"] or r["sum_snip"])
            results.append({**dict(r), "title_html": highlight_html(r["title_hl"]),
                            "snippet_html": highlight_html(snippet)})
    return render(request, "search.html", q=q, results=results, searched_empty=bool(q) and not fts)


@router.get("/logs", response_class=HTMLResponse)
def logs(request: Request, conn=Depends(get_conn)):
    rows = conn.execute("SELECT * FROM job_logs ORDER BY started_at DESC, id DESC LIMIT 200").fetchall()
    return render(request, "logs.html", logs=rows)
