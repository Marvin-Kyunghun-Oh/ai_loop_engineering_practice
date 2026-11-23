"""base.html의 수집 상태 스크립트를 node로 실행해 동작을 검증한다(브라우저 대신 최소 DOM 흉내). node가 없으면 건너뛴다."""
import json
import re
import shutil
import subprocess

import pytest
from fastapi.testclient import TestClient

from rss_wiki.main import create_app

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node 필요")

HARNESS = r"""
const script = %(script)s, scenario = %(scenario)s;
const els = {};
const mk = () => ({hidden: true, className: "", innerHTML: "", disabled: false, listeners: {},
                   addEventListener(n, f) { this.listeners[n] = f; }});
["fetch-status", "fetch-btn", "fetch-form"].forEach(id => els[id] = mk());
const store = Object.assign({}, scenario.storage || {});
const out = {reloads: 0, fetches: 0, timers: []};
const responses = scenario.responses.slice();
const sandbox = {
  document: {getElementById: id => els[id]},
  sessionStorage: {getItem: k => (k in store ? store[k] : null), setItem: (k, v) => { store[k] = String(v); },
                   removeItem: k => { delete store[k]; }},
  location: {reload() { out.reloads++; }},
  fetch: () => { out.fetches++; const r = responses.length > 1 ? responses.shift() : responses[0];
                 return r === "FAIL" ? Promise.reject(new Error("x")) : Promise.resolve({json: () => Promise.resolve(r)}); },
  setTimeout: (f, ms) => { out.timers.push(ms); out.next = f; return 1; },
  clearTimeout() {},
};
new Function(...Object.keys(sandbox), script)(...Object.values(sandbox));
(async () => {
  const flush = () => new Promise(r => setImmediate(r));
  await flush(); await flush();
  for (let i = 0; i < (scenario.ticks || 0); i++) { const f = out.next; out.next = null; if (f) f(); await flush(); await flush(); }
  if (scenario.submit) els["fetch-form"].listeners.submit();
  console.log(JSON.stringify({...out, store, box: {cls: els["fetch-status"].className, html: els["fetch-status"].innerHTML,
    hidden: els["fetch-status"].hidden}, btnDisabled: els["fetch-btn"].disabled}));
})();
"""

IDLE = {"running": False, "last_error": None,
        "last_report": {"feeds_ok": 2, "feeds_failed": 0, "new_articles": 3, "summarized": 3,
                        "summarize_failed": 0, "categories_rebuilt": 2, "rebuild_failed": 0}}
RUN = {"running": True, "last_error": None, "last_report": None}


@pytest.fixture(scope="module")
def script(tmp_path_factory):
    from rss_wiki.config import Settings
    d = tmp_path_factory.mktemp("js")
    s = Settings(db_path=d / "a.db", log_path=d / "a.log", enable_scheduler=False)
    with TestClient(create_app(s, llm=object())) as c:
        html = c.get("/feeds").text
    return re.findall(r"<script>(.*?)</script>", html, re.S)[-1]


def run(script, **scenario):
    code = HARNESS % {"script": json.dumps(script), "scenario": json.dumps(scenario)}
    r = subprocess.run(["node", "-e", code], capture_output=True, text=True, timeout=20)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_idle_page_does_nothing(script):
    o = run(script, responses=[IDLE])
    assert o["reloads"] == 0 and o["box"]["hidden"] is True and o["btnDisabled"] is False


def test_running_shows_banner_disables_button_and_keeps_polling(script):
    o = run(script, responses=[RUN])
    assert "수집 중" in o["box"]["html"] and o["box"]["cls"] == "busy" and o["btnDisabled"] is True
    assert o["reloads"] == 0 and o["timers"] == [2000] and o["store"]["rssWikiFetch"] == "pending"


def test_reloads_exactly_once_when_cycle_finishes(script):
    o = run(script, responses=[RUN, RUN, IDLE], ticks=2)
    assert o["reloads"] == 1 and o["fetches"] == 3
    assert o["store"]["rssWikiFetch"].startswith("done:ok|수집 완료: 새 글 3개, 요약 3개, 위키 갱신 2개")


def test_fast_cycle_finished_before_first_poll_still_reloads(script):
    o = run(script, storage={"rssWikiFetch": "pending"}, responses=[IDLE])  # 눌렀는데 이미 끝난 경우
    assert o["reloads"] == 1


def test_result_message_shown_after_reload_and_no_reload_loop(script):
    o = run(script, storage={"rssWikiFetch": "done:ok|수집 완료: 새 글 3개"}, responses=[IDLE])
    assert o["reloads"] == 0 and "수집 완료: 새 글 3개" in o["box"]["html"] and o["box"]["hidden"] is False
    assert "rssWikiFetch" not in o["store"]


def test_failure_counts_are_shown_as_error(script):
    bad = {**IDLE, "last_report": {**IDLE["last_report"], "summarize_failed": 2}}
    o = run(script, storage={"rssWikiFetch": "pending"}, responses=[bad])
    assert o["store"]["rssWikiFetch"].startswith("done:err|") and "실패 2건" in o["store"]["rssWikiFetch"]


def test_cycle_error_is_shown_and_escaped(script):
    err = {"running": False, "last_error": "<b>Boom</b>", "last_report": None}
    o = run(script, storage={"rssWikiFetch": "pending"}, responses=[err])
    assert "<b>" not in o["store"]["rssWikiFetch"] and "수집 실패" in o["store"]["rssWikiFetch"]


def test_submit_marks_pending(script):
    o = run(script, responses=[IDLE], submit=True)
    assert o["store"]["rssWikiFetch"] == "pending"


def test_server_unreachable_retries_quietly(script):
    o = run(script, responses=["FAIL"])
    assert o["reloads"] == 0 and o["timers"] == [5000] and o["box"]["hidden"] is True
