import pytest
from fastapi.testclient import TestClient

from rss_wiki.db import connect
from rss_wiki.main import create_app

WIKI = "# AI\n\n## 한줄 요약\n핵심 <script>alert(1)</script> [나쁜](javascript:alert(1)) [좋은](https://ok.com)\n"


@pytest.fixture
def client(settings):
    with TestClient(create_app(settings, llm=object()), follow_redirects=False) as c:
        yield c


@pytest.fixture
def db(client, settings):
    conn = connect(settings.db_path)
    conn.execute("INSERT INTO feeds(id, url, title) VALUES (1, 'http://f', '내 피드')")
    conn.commit()
    yield conn
    conn.close()


def cat(db, id, name, parent=None, merged=None, unread=None, md=""):
    db.execute("INSERT INTO categories(id, name, parent_id, merged_into_id) VALUES (?,?,?,?)",
               (id, name, parent, merged))
    if unread is not None:
        db.execute("INSERT INTO wiki_pages(category_id, content_markdown, has_unread_updates, last_rebuilt_at) "
                   "VALUES (?,?,?, '2026-11-22T00:00:00+00:00')", (id, md, unread))
    db.commit()


def art(db, id, cat_id, title="글", status="ok"):
    db.execute("INSERT INTO articles(id, feed_id, url, title, llm_summary, primary_category_id, status, published_at) "
               "VALUES (?,1,?,?,?,?,?, '2026-11-22T09:00:00+00:00')",
               (id, f"https://a.com/{id}", title, f"요약{id}", cat_id, status))
    db.commit()


def test_empty_index(client):
    assert "아직 카테고리가 없습니다" in client.get("/").text


def test_index_shows_only_top_level_unread_first(client, db):
    cat(db, 1, "가나다", unread=0)
    cat(db, 2, "라마바", unread=1)
    cat(db, 3, "숨은리프", parent=1, unread=0)
    cat(db, 4, "병합됨", merged=1)
    html = client.get("/").text
    assert "숨은리프" not in html and "병합됨" not in html
    assert html.index("라마바") < html.index("가나다")  # 안읽음 상단
    assert html.count("새 업데이트") == 1


def test_index_root_badge_when_child_unread(client, db):
    cat(db, 1, "루트", unread=0)
    cat(db, 2, "리프", parent=1, unread=1)
    art(db, 1, 2)
    html = client.get("/").text
    assert "새 업데이트" in html and "하위 1개" in html and "글 1개" in html


def test_category_page_renders_wiki_safely_and_lists_articles(client, db):
    cat(db, 1, "AI", unread=1, md=WIKI)
    art(db, 1, 1, "첫 글")
    art(db, 2, 1, "실패한 글", status="failed")
    r = client.get("/categories/1")
    assert r.status_code == 200
    assert "<script>alert(1)</script>" not in r.text and "&lt;script&gt;" in r.text
    assert 'href="javascript:' not in r.text and 'href="https://ok.com"' in r.text
    assert 'href="https://a.com/1"' in r.text and "첫 글" in r.text and "실패한 글" not in r.text
    assert "내 피드" in r.text and "요약1" in r.text


def test_visit_marks_read(client, db):
    cat(db, 1, "AI", unread=1, md="# AI\n\n## 한줄 요약\nx")
    r = client.get("/categories/1")
    assert "새 업데이트" not in r.text
    row = db.execute("SELECT has_unread_updates, last_seen_at FROM wiki_pages").fetchone()
    assert row["has_unread_updates"] == 0 and row["last_seen_at"]
    assert "새 업데이트" not in client.get("/").text


def test_parent_page_lists_children_and_their_articles(client, db):
    cat(db, 1, "루트", unread=0, md="# 루트\n\n## 한줄 요약\nx")
    cat(db, 2, "리프", parent=1, unread=1)
    art(db, 1, 2, "리프 글")
    html = client.get("/categories/1").text
    assert 'href="/categories/2"' in html and "하위 카테고리" in html and "리프 글" in html
    leaf = client.get("/categories/2").text
    assert "← 루트" in leaf
    assert db.execute("SELECT has_unread_updates FROM wiki_pages WHERE category_id=2").fetchone()[0] == 0


def test_category_without_wiki_placeholder(client, db):
    cat(db, 1, "새 주제")
    assert "아직 위키 페이지가 만들어지지 않았습니다" in client.get("/categories/1").text


def test_merged_redirects_and_missing_404(client, db):
    cat(db, 1, "대상", unread=0)
    cat(db, 2, "원본", merged=1)
    r = client.get("/categories/2")
    assert r.status_code == 307 and r.headers["location"] == "/categories/1"
    assert client.get("/categories/999").status_code == 404
