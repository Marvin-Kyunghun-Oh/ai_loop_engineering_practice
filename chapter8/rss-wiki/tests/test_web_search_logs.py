import pytest
from fastapi.testclient import TestClient

from rss_wiki.db import connect
from rss_wiki.main import create_app
from rss_wiki.web.routes import build_fts_query, highlight_html


@pytest.fixture
def client(settings):
    with TestClient(create_app(settings, llm=object()), follow_redirects=False) as c:
        yield c


@pytest.fixture
def db(client, settings):
    conn = connect(settings.db_path)
    conn.execute("INSERT INTO feeds(id, url, title) VALUES (1, 'http://f', '내 피드')")
    conn.execute("INSERT INTO categories(id, name) VALUES (1, 'LLM 에이전트')")
    conn.commit()
    yield conn
    conn.close()


def art(db, id, title, summary=None, content=None, status="ok", cat=1):
    db.execute("INSERT INTO articles(id, feed_id, url, title, llm_summary, extracted_content, status, "
               "primary_category_id, published_at) VALUES (?,1,?,?,?,?,?,?, '2026-11-22T09:00:00+00:00')",
               (id, f"https://a.com/{id}", title, summary, content, status, cat))
    db.commit()


def test_build_fts_query():
    assert build_fts_query("에이전트") == '"에이전트"*'
    assert build_fts_query("llm agent") == '"llm" "agent"*'
    assert build_fts_query('"; DROP -- AND *') == '"DROP" "AND"*'
    assert build_fts_query("!!! ???") is None


def test_highlight_escapes_html_but_keeps_marks():
    assert highlight_html("<b>\x02핵심\x03</b>") == "&lt;b&gt;<mark>핵심</mark>&lt;/b&gt;"


def test_search_matches_title_summary_and_content(client, db):
    art(db, 1, "에이전트 설계", "다른 요약.", "본문")
    art(db, 2, "무관한 제목", "에이전트들의 시스템 요약입니다.", "본문")
    art(db, 3, "또 다른 글", "요약.", "긴 본문에 에이전트가 등장한다")
    art(db, 4, "관련 없는 글", "요약.", "전혀 다른 내용")
    html = client.get("/search", params={"q": "에이전트"}).text
    assert html.count('class="card"') == 3
    for i in (1, 2, 3):
        assert f'href="https://a.com/{i}"' in html
    assert 'href="https://a.com/4"' not in html
    assert "<mark>에이전트</mark> 설계" in html  # 제목 하이라이트
    assert "<mark>에이전트들의</mark>" in html  # 접두 일치한 토큰 전체가 강조됨
    assert 'href="/categories/1"' in html and "LLM 에이전트" in html and "내 피드" in html


def test_unicode61_does_not_match_mid_word(client, db):
    art(db, 1, "제목", "멀티에이전트 시스템.", "본문")  # PRD가 정한 unicode61 토크나이저의 한계
    assert "결과가 없습니다" in client.get("/search", params={"q": "에이전트"}).text


def test_prefix_search_handles_korean_suffix(client, db):
    art(db, 1, "제목", "이 글은 요약입니다.", "본문")
    assert 'class="card"' in client.get("/search", params={"q": "요약"}).text


def test_multiple_words_are_and(client, db):
    art(db, 1, "alpha beta", "x.", "y")
    art(db, 2, "alpha only", "x.", "y")
    html = client.get("/search", params={"q": "alpha beta"}).text
    assert html.count('class="card"') == 1 and "alpha beta" in html


def test_failed_articles_excluded(client, db):
    art(db, 1, "실패한 글", "요약.", "본문", status="failed", cat=None)
    assert "결과가 없습니다" in client.get("/search", params={"q": "실패한"}).text


def test_no_results_empty_and_symbol_queries(client, db):
    assert client.get("/search").status_code == 200
    assert "결과가 없습니다" in client.get("/search", params={"q": "없는단어"}).text
    r = client.get("/search", params={"q": '"; DROP TABLE articles; -- *'})
    assert r.status_code == 200
    assert "검색어를 입력하세요" in client.get("/search", params={"q": "!!!"}).text
    assert db.execute("SELECT COUNT(*) FROM articles").fetchone()[0] == 0  # 테이블 멀쩡


def test_search_output_is_escaped(client, db):
    art(db, 1, "<script>alert(1)</script> 에이전트", "요약.", "본문")
    html = client.get("/search", params={"q": "에이전트"}).text
    assert "<script>alert(1)</script>" not in html and "&lt;script&gt;" in html


def test_search_updates_when_article_updated(client, db):
    art(db, 1, "처음 제목", "요약.", "본문")
    db.execute("UPDATE articles SET title='바뀐제목' WHERE id=1"); db.commit()
    assert 'class="card"' in client.get("/search", params={"q": "바뀐제목"}).text
    assert "결과가 없습니다" in client.get("/search", params={"q": "처음"}).text


def test_logs_empty(client):
    assert "아직 기록이 없습니다" in client.get("/logs").text


def test_logs_latest_200_newest_first_with_escaped_errors(client, db):
    for i in range(205):
        db.execute("INSERT INTO job_logs(job_type, target_ref, status, error_message, attempt_count, started_at) "
                   "VALUES ('fetch_feed', ?, ?, ?, 4, ?)",
                   (str(i), "failed" if i == 204 else "ok", "<b>오류</b>" if i == 204 else None,
                    f"2026-11-22T09:{i // 60:02d}:{i % 60:02d}+00:00"))
    db.commit()
    html = client.get("/logs").text
    assert "최근 200건" in html and html.count("<tr>") == 201  # 헤더 1 + 200건
    assert "&lt;b&gt;오류&lt;/b&gt;" in html and "<b>오류</b>" not in html
    assert html.index("<td>204</td>") < html.index("<td>100</td>")  # 최신순
    assert "<td>4</td>" in html  # 시도 횟수 열
    assert "<td>0</td>" not in html and "<td>4</td><td>" in html  # 가장 오래된 5건(0~4)은 잘려 나감
