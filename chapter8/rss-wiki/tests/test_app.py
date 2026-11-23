import asyncio
import time

import pytest
from fastapi.testclient import TestClient

from rss_wiki.config import Settings
from rss_wiki.main import create_app
from rss_wiki.pipeline.cycle import CycleBusy, CycleReport
from rss_wiki.scheduler import CycleController, build_scheduler


def slow_runner(delay=0.4):
    calls = []

    async def runner(db_path, llm, *, lock):
        calls.append(1)
        await asyncio.sleep(delay)
        return CycleReport(feeds_ok=1)

    runner.calls = calls
    return runner


def test_lifespan_creates_db_and_log(settings, tmp_path):
    with TestClient(create_app(settings, llm=object(), cycle_runner=slow_runner())):
        assert settings.db_path.exists()
    assert settings.log_path.exists()


def test_api_fetch_202_then_409_while_running(settings):
    runner = slow_runner(0.4)
    with TestClient(create_app(settings, llm=object(), cycle_runner=runner)) as client:
        assert client.post("/api/fetch").status_code == 202
        r = client.post("/api/fetch")
        assert r.status_code == 409 and r.json()["status"] == "busy"
        time.sleep(0.8)
        assert client.post("/api/fetch").status_code == 202
    assert len(runner.calls) == 2


def test_controller_survives_runner_exception(settings):
    async def boom(db_path, llm, *, lock):
        raise RuntimeError("실패")

    async def go():
        c = CycleController(settings, llm=None, runner=boom)
        assert c.try_start() is True
        await c.wait_idle()
        assert c.running is False and "RuntimeError" in c.last_error
        assert c.try_start() is True  # 실패 후에도 다시 시작 가능
        await c.wait_idle()

    asyncio.run(go())


def test_controller_busy_from_cycle_lock_is_swallowed(settings):
    async def busy(db_path, llm, *, lock):
        raise CycleBusy("x")

    async def go():
        c = CycleController(settings, llm=None, runner=busy)
        c.try_start()
        await c.wait_idle()
        assert c.running is False and c.last_error is None

    asyncio.run(go())


def test_scheduler_registers_hourly_cron_and_trigger_starts_cycle(settings):
    runner = slow_runner(0.05)

    async def go():
        loop = asyncio.get_running_loop()
        c = CycleController(settings, llm=None, runner=runner)
        sched = build_scheduler(c, loop)
        pending = sched._pending_jobs[0][0]
        fields = {f.name: str(f) for f in pending.trigger.fields}
        assert fields["hour"] == "*" and fields["minute"] == "0"
        assert pending.max_instances == 1 and pending.coalesce
        # 스케줄러 스레드가 호출하는 함수를 다른 스레드에서 실행해 루프로 넘어오는지 확인
        await asyncio.to_thread(pending.func)
        await asyncio.sleep(0.01)
        assert c.running or runner.calls
        await c.wait_idle()
        assert len(runner.calls) == 1

    asyncio.run(go())


def test_scheduler_started_only_when_enabled(settings):
    on = Settings(db_path=settings.db_path, log_path=settings.log_path, enable_scheduler=True)
    with TestClient(create_app(on, llm=object(), cycle_runner=slow_runner())) as client:
        assert client.app.state.scheduler.running
        assert client.app.state.scheduler.get_job("fetch_cycle") is not None
    with TestClient(create_app(settings, llm=object(), cycle_runner=slow_runner())) as client:
        assert client.app.state.scheduler is None


def test_fetch_status_endpoint_idle_running_done(settings):
    runner = slow_runner(0.5)
    with TestClient(create_app(settings, llm=object(), cycle_runner=runner)) as client:
        st = client.get("/api/fetch/status")
        assert st.status_code == 200 and st.headers["cache-control"] == "no-store"
        assert st.json() == {"running": False, "last_error": None, "last_report": None}
        client.post("/api/fetch")
        assert client.get("/api/fetch/status").json()["running"] is True
        time.sleep(0.9)
        done = client.get("/api/fetch/status").json()
        assert done["running"] is False and done["last_report"]["feeds_ok"] == 1


def test_fetch_status_reports_error(settings):
    async def boom(db_path, llm, *, lock):
        raise RuntimeError("실패했어요")

    with TestClient(create_app(settings, llm=object(), cycle_runner=boom)) as client:
        client.post("/api/fetch")
        time.sleep(0.3)
        st = client.get("/api/fetch/status").json()
        assert st["running"] is False and "RuntimeError" in st["last_error"]


def test_every_page_has_status_banner_and_poller(settings):
    with TestClient(create_app(settings, llm=object(), cycle_runner=slow_runner())) as client:
        for path in ("/", "/feeds", "/categories/manage", "/search", "/logs"):
            html = client.get(path).text
            assert 'id="fetch-status"' in html and "/api/fetch/status" in html and 'id="fetch-btn"' in html, path
