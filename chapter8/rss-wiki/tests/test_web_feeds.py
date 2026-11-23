import pytest
from fastapi.testclient import TestClient

from rss_wiki.db import connect
from rss_wiki.main import create_app
from rss_wiki.web.routes import localtime


@pytest.fixture
def client(settings):
    with TestClient(create_app(settings, llm=object()), follow_redirects=False) as c:
        yield c


def feeds(settings):
    conn = connect(settings.db_path)
    try:
        return [dict(r) for r in conn.execute("SELECT * FROM feeds ORDER BY id")]
    finally:
        conn.close()


def test_empty_list(client):
    r = client.get("/feeds")
    assert r.status_code == 200 and "구독 중인 피드가 없습니다" in r.text and "Fetch now" in r.text


def test_add_lists_and_redirects(client, settings):
    r = client.post("/feeds/add", data={"url": " https://a.com/rss "})
    assert r.status_code == 303 and r.headers["location"] == "/feeds"
    assert [f["url"] for f in feeds(settings)] == ["https://a.com/rss"]
    assert "https://a.com/rss" in client.get("/feeds").text


def test_duplicate_is_409(client, settings):
    client.post("/feeds/add", data={"url": "https://a.com/rss"})
    r = client.post("/feeds/add", data={"url": "https://a.com/rss"})
    assert r.status_code == 409 and "이미 구독 중" in r.text
    assert len(feeds(settings)) == 1


@pytest.mark.parametrize("bad", ["not-a-url", "ftp://a.com/x", "https://"])
def test_invalid_url_400(client, settings, bad):
    assert client.post("/feeds/add", data={"url": bad}).status_code == 400
    assert feeds(settings) == []


def test_toggle(client, settings):
    client.post("/feeds/add", data={"url": "https://a.com/rss"})
    assert client.post("/feeds/1/toggle").status_code == 303
    assert feeds(settings)[0]["is_active"] == 0 and "활성화" in client.get("/feeds").text
    client.post("/feeds/1/toggle")
    assert feeds(settings)[0]["is_active"] == 1


def test_delete_cascades_articles(client, settings):
    client.post("/feeds/add", data={"url": "https://a.com/rss"})
    conn = connect(settings.db_path)
    conn.execute("INSERT INTO articles(feed_id, url, title) VALUES (1, 'https://a.com/1', 't')")
    conn.commit()
    assert client.post("/feeds/1/delete").status_code == 303
    assert feeds(settings) == []
    assert conn.execute("SELECT COUNT(*) c FROM articles").fetchone()["c"] == 0
    conn.close()


def test_unknown_feed_404(client):
    assert client.post("/feeds/99/toggle").status_code == 404
    assert client.post("/feeds/99/delete").status_code == 404


def test_html_escaped(client):
    client.post("/feeds/add", data={"url": "https://a.com/rss?x=<script>"})
    html = client.get("/feeds").text
    assert "x=<script>" not in html and "x=&lt;script&gt;" in html  # 페이지 자체 <script>(상태 폴러)와 구분


def test_fetch_now_redirects(client):
    r = client.post("/fetch-now")
    assert r.status_code == 303 and r.headers["location"] == "/feeds"


def test_localtime_filter():
    assert localtime(None) == "" and localtime("garbage") == "garbage"
    from datetime import datetime, timezone
    expected = datetime(2026, 11, 22, 9, 0, tzinfo=timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M")
    assert localtime("2026-11-22 09:00:00") == expected
    assert localtime("2026-11-22T09:00:00+00:00") == expected
