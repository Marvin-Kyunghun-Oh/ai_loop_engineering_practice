"""E2E 하네스: 로컬 RSS/원문 HTTP 서버 + 가짜 claude CLI + 실제 uvicorn 서버(스레드) + httpx 클라이언트."""
import json
import socket
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import httpx
import pytest
import uvicorn

from rss_wiki import config
from rss_wiki.config import Settings
from rss_wiki.main import create_app

FAKE_CLAUDE = Path(__file__).with_name("fake_claude.py")


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def article_html(title: str, body_marker: str) -> str:
    paras = "".join(
        f"<p>{body_marker} 단락 {i}. 이 글은 {title}에 관한 충분히 긴 본문입니다. "
        f"추출기가 본문으로 인식하도록 문장을 여러 개 이어 붙입니다. kubernetes orchestration 설명이 이어집니다. "
        f"독자는 이 단락을 통해 주제의 배경과 세부 사항을 이해할 수 있습니다.</p>" for i in range(1, 8))
    return f"<html><head><title>{title}</title></head><body><nav>menu</nav><article><h1>{title}</h1>{paras}</article></body></html>"


class Site:
    """가변 상태를 가진 가짜 웹사이트. feeds[path] = [(title, slug), ...], statuses[path] = HTTP 상태."""

    def __init__(self):
        self.feeds: dict[str, list[tuple[str, str]]] = {}
        self.statuses: dict[str, int] = {}
        self.hits: list[str] = []
        self.port = free_port()
        site = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_GET(self):
                site.hits.append(self.path)
                status = site.statuses.get(self.path, 200)
                if status != 200:
                    self.send_response(status); self.end_headers(); return
                if self.path in site.feeds:
                    items = "".join(
                        f"<item><title>{t}</title><link>http://127.0.0.1:{site.port}/a/{slug}</link>"
                        f"<description>짧은 발췌 {slug}</description>"
                        f"<pubDate>Mon, 05 Jan 2026 10:00:00 GMT</pubDate></item>" for t, slug in site.feeds[self.path])
                    body = (f"<?xml version='1.0' encoding='UTF-8'?><rss version='2.0'><channel>"
                            f"<title>테스트 피드 {self.path}</title>{items}</channel></rss>").encode()
                    ctype = "application/rss+xml"
                elif self.path.startswith("/a/"):
                    slug = self.path[3:]
                    title = next((t for f in site.feeds.values() for t, s in f if s == slug), slug)
                    body, ctype = article_html(title, f"[{slug}]").encode(), "text/html; charset=utf-8"
                else:
                    self.send_response(404); self.end_headers(); return
                self.send_response(200)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        self.httpd = ThreadingHTTPServer(("127.0.0.1", self.port), H)
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def url(self, path: str) -> str:
        return f"http://127.0.0.1:{self.port}{path}"

    def close(self):
        self.httpd.shutdown()


class Server:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.port = free_port()
        self.app = create_app(settings)
        self.server = uvicorn.Server(uvicorn.Config(self.app, host="127.0.0.1", port=self.port, log_level="warning"))
        self.thread = threading.Thread(target=self.server.run, daemon=True)
        self.thread.start()
        for _ in range(100):
            if self.server.started:
                break
            time.sleep(0.05)
        assert self.server.started, "서버 기동 실패"
        self.client = httpx.Client(base_url=f"http://127.0.0.1:{self.port}", follow_redirects=False, timeout=15)

    @property
    def controller(self):
        return self.app.state.controller

    def run_cycle(self, timeout=60):
        """수동 수집을 트리거하고 끝날 때까지 기다린다."""
        r = self.client.post("/api/fetch")
        assert r.status_code == 202, r.text
        self.wait_idle(timeout)

    def wait_idle(self, timeout=60):
        end = time.time() + timeout
        time.sleep(0.1)
        while self.controller.running and time.time() < end:
            time.sleep(0.05)
        assert not self.controller.running, "수집 사이클이 끝나지 않음"
        time.sleep(0.1)  # 재구성 태스크(병합 등) 정리 여유

    def add_feed(self, url: str):
        r = self.client.post("/feeds/add", data={"url": url})
        assert r.status_code == 303, r.text

    def db(self):
        from rss_wiki.db import connect
        return connect(self.settings.db_path)

    def stop(self):
        self.client.close()
        self.server.should_exit = True
        self.thread.join(10)


@pytest.fixture(autouse=True)
def _fast_backoff(monkeypatch):
    # trafilatura는 기본적으로 127.0.0.1 등 비공개 주소를 SSRF 보호로 차단한다. 로컬 모의 서버 테스트용으로만 끈다.
    from trafilatura.settings import DEFAULT_CONFIG
    old = DEFAULT_CONFIG.get("DEFAULT", "SSRF_PROTECTION")
    DEFAULT_CONFIG.set("DEFAULT", "SSRF_PROTECTION", "off")
    monkeypatch.setattr(config, "LLM_BACKOFF_SECONDS", (0.01, 0.01, 0.01))
    yield
    DEFAULT_CONFIG.set("DEFAULT", "SSRF_PROTECTION", old)
    return
    monkeypatch.setattr(config, "LLM_BACKOFF_SECONDS", (0.01, 0.01, 0.01))


@pytest.fixture
def claude_log(tmp_path, monkeypatch):
    path = tmp_path / "claude_calls.jsonl"
    monkeypatch.setenv("FAKE_CLAUDE_LOG", str(path))

    def calls(kind=None):
        if not path.exists():
            return []
        rows = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines()]
        return [r["detail"] for r in rows if kind is None or r["kind"] == kind]

    return calls


@pytest.fixture
def site():
    s = Site()
    yield s
    s.close()


def make_settings(tmp_path) -> Settings:
    return Settings(db_path=tmp_path / "data" / "e2e.db", log_path=tmp_path / "data" / "logs" / "e2e.log",
                    claude_command=(sys.executable, str(FAKE_CLAUDE)), enable_scheduler=True)


@pytest.fixture
def server(tmp_path, claude_log):
    s = Server(make_settings(tmp_path))
    yield s
    s.stop()
