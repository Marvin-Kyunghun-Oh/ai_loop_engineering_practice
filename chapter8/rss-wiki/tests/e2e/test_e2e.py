"""RSS Wiki E2E 테스트. 각 테스트 이름의 TC 번호는 docs/QA_TC.md와 대응한다."""
import threading
import time

import pytest

AI_FEED = "/ai.xml"
DB_FEED = "/db.xml"


def seed(site):
    site.feeds[AI_FEED] = [("AI 에이전트 입문", "ai1"), ("AI 코딩 도구 비교", "ai2")]
    site.feeds[DB_FEED] = [("DB 인덱스 설계", "db1")]


def cats(server):
    c = server.db()
    try:
        return {r["name"]: r["id"] for r in c.execute("SELECT id, name FROM categories WHERE merged_into_id IS NULL")}
    finally:
        c.close()


def q(server, sql, *args):
    c = server.db()
    try:
        return [dict(r) for r in c.execute(sql, args)]
    finally:
        c.close()


# ---------- A. 기동 ----------
def test_tc_a1_startup_empty_state(server):
    assert server.controller is not None and server.app.state.scheduler.running
    r = server.client.get("/")
    assert r.status_code == 200 and "아직 카테고리가 없습니다" in r.text
    for path in ("/feeds", "/categories/manage", "/search", "/logs"):
        assert server.client.get(path).status_code == 200, path
    assert server.settings.db_path.exists()


def test_tc_a2_scheduler_hourly_cron(server):
    job = server.app.state.scheduler.get_jobs()[0]
    f = {x.name: str(x) for x in job.trigger.fields}
    assert f["hour"] == "*" and f["minute"] == "0"


# ---------- B. 피드 관리 ----------
def test_tc_b1_add_duplicate_invalid_feed(server, site):
    url = site.url(AI_FEED)
    server.add_feed(url)
    assert url in server.client.get("/feeds").text
    assert server.client.post("/feeds/add", data={"url": url}).status_code == 409
    assert server.client.post("/feeds/add", data={"url": "not-a-url"}).status_code == 400
    assert server.client.post("/feeds/add", data={"url": "ftp://x/y"}).status_code == 400
    assert len(q(server, "SELECT id FROM feeds")) == 1


def test_tc_b2_toggle_and_delete_feed(server, site):
    seed(site)
    server.add_feed(site.url(AI_FEED))
    server.run_cycle()
    assert len(q(server, "SELECT id FROM articles")) == 2
    fid = q(server, "SELECT id FROM feeds")[0]["id"]
    assert server.client.post(f"/feeds/{fid}/toggle").status_code == 303
    assert q(server, "SELECT is_active FROM feeds")[0]["is_active"] == 0
    site.feeds[AI_FEED].append(("AI 새 글", "ai3"))
    server.run_cycle()
    assert len(q(server, "SELECT id FROM articles")) == 2  # 비활성 피드는 수집 제외
    server.client.post(f"/feeds/{fid}/toggle")
    assert q(server, "SELECT is_active FROM feeds")[0]["is_active"] == 1
    assert server.client.post(f"/feeds/{fid}/delete").status_code == 303
    assert q(server, "SELECT id FROM articles") == []  # CASCADE
    assert server.client.post("/feeds/9999/delete").status_code == 404


# ---------- C. 수집 → 요약 → 위키 (핵심 시나리오) ----------
def test_tc_c1_full_pipeline_happy_path(server, site, claude_log):
    seed(site)
    server.add_feed(site.url(AI_FEED))
    server.add_feed(site.url(DB_FEED))
    server.run_cycle()

    arts = q(server, "SELECT * FROM articles ORDER BY id")
    assert len(arts) == 3 and all(a["status"] == "ok" for a in arts)
    assert all(a["llm_summary"] and a["primary_category_id"] for a in arts)
    # 본문 추출(TC-C2): RSS 발췌가 아니라 원문 본문이 저장돼야 한다
    assert all(len(a["extracted_content"]) > 300 and "짧은 발췌" not in a["extracted_content"] for a in arts)
    assert set(cats(server)) == {"LLM 에이전트", "데이터베이스"}
    # 카테고리당 위키 재구성 1회 (AI 글 2개는 1회로 묶임)
    rebuilds = claude_log("rebuild")
    assert sorted(r["category"] for r in rebuilds) == ["LLM 에이전트", "데이터베이스"]
    assert len(claude_log("summarize")) == 3

    home = server.client.get("/").text
    assert "LLM 에이전트" in home and "데이터베이스" in home and home.count("새 업데이트") == 2

    cid = cats(server)["LLM 에이전트"]
    page = server.client.get(f"/categories/{cid}").text
    assert "<h2>한줄 요약</h2>" in page and "AI 에이전트 입문" in page and "AI 코딩 도구 비교" in page
    assert site.url("/a/ai1") in page  # 원문 링크
    # 방문 후 읽음 처리: 해당 카테고리만 배지 해제
    assert server.client.get("/").text.count("새 업데이트") == 1
    assert q(server, "SELECT has_unread_updates u FROM wiki_pages WHERE category_id=?", cid)[0]["u"] == 0


def test_tc_c3_no_duplicate_on_second_cycle(server, site, claude_log):
    seed(site)
    server.add_feed(site.url(AI_FEED))
    server.run_cycle()
    n_sum, n_reb = len(claude_log("summarize")), len(claude_log("rebuild"))
    server.run_cycle()
    assert len(q(server, "SELECT id FROM articles")) == 2
    assert len(claude_log("summarize")) == n_sum and len(claude_log("rebuild")) == n_reb  # LLM 재호출 없음


def test_tc_c4_incremental_rebuild_only_affected_category(server, site, claude_log):
    seed(site)
    server.add_feed(site.url(AI_FEED))
    server.add_feed(site.url(DB_FEED))
    server.run_cycle()
    cid = cats(server)["LLM 에이전트"]
    server.client.get(f"/categories/{cid}")  # 읽음 처리
    before = len(claude_log("rebuild"))

    site.feeds[AI_FEED].append(("AI 메모리 설계", "ai3"))
    server.run_cycle()
    new = claude_log("rebuild")[before:]
    assert len(new) == 1 and new[0]["category"] == "LLM 에이전트" and new[0]["new"] == ["AI 메모리 설계"]
    wiki = q(server, "SELECT * FROM wiki_pages WHERE category_id=?", cid)[0]
    assert "AI 메모리 설계" in wiki["content_markdown"] and wiki["has_unread_updates"] == 1
    assert "AI 에이전트 입문" in wiki["content_markdown"]  # 이전 링크 유지


def test_tc_c5_manual_fetch_409_while_running(server, site, monkeypatch):
    seed(site)
    server.add_feed(site.url(DB_FEED))
    monkeypatch.setenv("FAKE_CLAUDE_DELAY", "1.5")
    assert server.client.post("/api/fetch").status_code == 202
    time.sleep(0.3)
    r = server.client.post("/api/fetch")
    assert r.status_code == 409 and r.json()["status"] == "busy"
    server.wait_idle()
    assert server.client.post("/api/fetch").status_code == 202
    server.wait_idle()


def test_tc_c6_fetch_now_button(server, site):
    seed(site)
    server.add_feed(site.url(DB_FEED))
    r = server.client.post("/fetch-now")
    assert r.status_code == 303 and r.headers["location"] == "/feeds"
    server.wait_idle()
    assert len(q(server, "SELECT id FROM articles")) == 1


# ---------- D. 실패 처리 ----------
def test_tc_d1_feed_http_error_isolated_and_logged(server, site):
    seed(site)
    site.statuses[DB_FEED] = 500
    server.add_feed(site.url(DB_FEED))
    server.add_feed(site.url(AI_FEED))
    server.run_cycle()
    assert len(q(server, "SELECT id FROM articles")) == 2  # 정상 피드는 처리됨
    assert q(server, "SELECT is_active FROM feeds ORDER BY id")[0]["is_active"] == 1  # 자동 비활성화 없음
    fails = q(server, "SELECT * FROM job_logs WHERE status='failed' AND job_type='fetch_feed'")
    assert len(fails) >= 1 and fails[0]["error_message"]
    assert "failed" in server.client.get("/logs").text


def test_tc_d2_llm_failure_marks_article_failed_and_continues(server, site, claude_log):
    site.feeds[AI_FEED] = [("AI LLMFAIL 글", "f1"), ("AI 정상 글", "ok1")]
    server.add_feed(site.url(AI_FEED))
    server.run_cycle()
    rows = {a["title"]: a for a in q(server, "SELECT * FROM articles")}
    assert rows["AI LLMFAIL 글"]["status"] == "failed" and rows["AI 정상 글"]["status"] == "ok"
    assert claude_log("summarize").count("AI LLMFAIL 글") == 4  # 최초 1 + 재시도 3
    # 실패 글은 카테고리 화면·검색에 노출되지 않는다
    cid = cats(server)["LLM 에이전트"]
    assert "AI LLMFAIL 글" not in server.client.get(f"/categories/{cid}").text
    assert "AI LLMFAIL 글" not in server.client.get("/search", params={"q": "LLMFAIL"}).text
    assert any(r["job_type"] == "summarize" for r in q(server, "SELECT * FROM job_logs WHERE status='failed'"))


def test_tc_d3_json_in_code_fence_is_accepted(server, site):
    site.feeds[AI_FEED] = [("AI FENCE 글", "fe1")]
    server.add_feed(site.url(AI_FEED))
    server.run_cycle()
    assert q(server, "SELECT status FROM articles")[0]["status"] == "ok"


def test_tc_d4_article_page_404_falls_back_to_rss_summary(server, site):
    site.feeds[AI_FEED] = [("AI 본문없음", "gone1")]
    site.statuses["/a/gone1"] = 404
    server.add_feed(site.url(AI_FEED))
    server.run_cycle()
    a = q(server, "SELECT * FROM articles")[0]
    assert a["status"] == "ok" and "짧은 발췌" in (a["extracted_content"] or "")


def test_tc_d5_dead_feed_url_does_not_crash(server):
    server.add_feed("http://127.0.0.1:1/never.xml")
    server.run_cycle()
    assert server.client.get("/").status_code == 200
    assert q(server, "SELECT is_active FROM feeds")[0]["is_active"] == 1


# ---------- E. 검색 ----------
def test_tc_e1_search_hits_highlight_and_misses(server, site):
    seed(site)
    server.add_feed(site.url(AI_FEED))
    server.run_cycle()
    r = server.client.get("/search", params={"q": "kubernetes"})
    assert r.status_code == 200 and "<mark>" in r.text and "AI 에이전트 입문" in r.text
    r = server.client.get("/search", params={"q": "에이전트"})
    assert "AI <mark>에이전트</mark> 입문" in r.text  # 제목이 하이라이트로 쪼개짐(정상)
    assert "AI 에이전트 입문" not in server.client.get("/search", params={"q": "zzzqqq"}).text


@pytest.mark.parametrize("bad", ['"', "AND OR NOT", "a*(", "'; DROP TABLE articles;--", "<script>alert(1)</script>", "   ", "\\"])
def test_tc_e2_search_special_chars_safe(server, site, bad):
    seed(site)
    server.add_feed(site.url(AI_FEED))
    server.run_cycle()
    r = server.client.get("/search", params={"q": bad})
    assert r.status_code == 200
    assert "<script>alert(1)</script>" not in r.text
    assert len(q(server, "SELECT id FROM articles")) == 2


# ---------- F. 카테고리 편집 ----------
def test_tc_f1_rename_category(server, site):
    seed(site)
    server.add_feed(site.url(AI_FEED))
    server.run_cycle()
    cid = cats(server)["LLM 에이전트"]
    assert server.client.post(f"/categories/{cid}/rename", data={"name": "에이전트 연구"}).status_code == 303
    assert "에이전트 연구" in server.client.get("/").text
    assert q(server, "SELECT is_user_edited e FROM categories WHERE id=?", cid)[0]["e"] == 1
    assert server.client.post(f"/categories/{cid}/rename", data={"name": "  "}).status_code == 400


def test_tc_f2_merge_moves_articles_and_rebuilds_target(server, site, claude_log):
    seed(site)
    server.add_feed(site.url(AI_FEED))
    server.add_feed(site.url(DB_FEED))
    server.run_cycle()
    c = cats(server)
    src, tgt = c["데이터베이스"], c["LLM 에이전트"]
    before = len(claude_log("rebuild"))
    assert server.client.post(f"/categories/{src}/merge", data={"target_id": tgt}).status_code == 303
    server.wait_idle()
    assert q(server, "SELECT COUNT(*) n FROM articles WHERE primary_category_id=?", tgt)[0]["n"] == 3
    assert q(server, "SELECT id FROM wiki_pages WHERE category_id=?", src) == []
    home = server.client.get("/").text
    assert "데이터베이스" not in home and "LLM 에이전트" in home and "글 3개" in home
    assert server.client.get(f"/categories/{src}", follow_redirects=True).url.path == f"/categories/{tgt}"
    assert len(claude_log("rebuild")) > before
    assert server.client.post(f"/categories/{tgt}/merge", data={"target_id": tgt}).status_code == 400


def test_tc_f3_parent_two_level_rules(server, site):
    seed(site)
    server.add_feed(site.url(AI_FEED))
    server.add_feed(site.url(DB_FEED))
    server.run_cycle()
    c = cats(server)
    ai, db = c["LLM 에이전트"], c["데이터베이스"]
    assert server.client.post(f"/categories/{db}/parent", data={"parent_id": ai}).status_code == 303
    home = server.client.get("/").text
    assert "하위 1개" in home and 'href="/categories/%d"' % db not in home  # 최상위만 노출
    assert "데이터베이스" in server.client.get(f"/categories/{ai}").text  # 드릴다운
    assert server.client.post(f"/categories/{ai}/parent", data={"parent_id": db}).status_code == 400  # 3단계 방지
    assert server.client.post(f"/categories/{ai}/parent", data={"parent_id": ai}).status_code == 400
    assert server.client.post(f"/categories/{db}/parent", data={"parent_id": ""}).status_code == 303
    assert 'href="/categories/%d"' % db in server.client.get("/").text


# ---------- G. 보안/견고성 ----------
def test_tc_g1_xss_in_title_is_escaped(server, site):
    site.feeds[AI_FEED] = [("AI <script>alert(1)</script> 글", "xss1")]
    server.add_feed(site.url(AI_FEED))
    server.run_cycle()
    cid = cats(server)["LLM 에이전트"]
    for path in (f"/categories/{cid}", "/search?q=script", "/logs"):
        assert "<script>alert(1)</script>" not in server.client.get(path).text, path


def test_tc_g2_unknown_paths(server):
    assert server.client.get("/categories/99999").status_code == 404
    assert server.client.get("/categories/abc").status_code == 422
    assert server.client.get("/nope").status_code == 404


def test_tc_g3_concurrent_reads_during_cycle(server, site, monkeypatch):
    seed(site)
    server.add_feed(site.url(AI_FEED))
    monkeypatch.setenv("FAKE_CLAUDE_DELAY", "0.4")
    server.client.post("/api/fetch")
    codes = []

    def hit():
        import httpx
        with httpx.Client(base_url=str(server.client.base_url), timeout=15) as c:
            for p in ("/", "/feeds", "/logs", "/search?q=ai"):
                codes.append(c.get(p).status_code)

    ts = [threading.Thread(target=hit) for _ in range(4)]
    [t.start() for t in ts]; [t.join() for t in ts]
    server.wait_idle()
    assert set(codes) == {200}


# ---------- H. 영속성 ----------
def test_tc_h1_data_survives_restart(server, site, tmp_path):
    from .conftest import Server
    seed(site)
    server.add_feed(site.url(AI_FEED))
    server.run_cycle()
    settings = server.settings
    server.stop()
    s2 = Server(settings)
    try:
        assert "LLM 에이전트" in s2.client.get("/").text
        assert len(q(s2, "SELECT id FROM articles")) == 2
        s2.run_cycle()
        assert len(q(s2, "SELECT id FROM articles")) == 2  # 재기동 후에도 중복 없음
    finally:
        s2.stop()


# ---------- I. 수집 상태 표시 ----------
def test_tc_i1_status_endpoint_tracks_real_cycle(server, site, monkeypatch):
    seed(site)
    server.add_feed(site.url(AI_FEED))
    assert server.client.get("/api/fetch/status").json()["running"] is False
    monkeypatch.setenv("FAKE_CLAUDE_DELAY", "0.8")
    server.client.post("/fetch-now")
    assert server.client.get("/api/fetch/status").json()["running"] is True  # 303 직후에 이미 진행 중
    assert 'id="fetch-status"' in server.client.get("/feeds").text
    server.wait_idle()
    st = server.client.get("/api/fetch/status").json()
    assert st["running"] is False and st["last_error"] is None
    assert st["last_report"]["new_articles"] == 2 and st["last_report"]["categories_rebuilt"] == 1
