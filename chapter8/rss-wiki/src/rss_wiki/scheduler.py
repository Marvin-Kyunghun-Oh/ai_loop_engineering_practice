"""APScheduler 등록과 수집 사이클 제어 (PRD §7.1, §14).

스케줄러는 BackgroundScheduler(별도 스레드)이고, 사이클 자체는 FastAPI 이벤트 루프에서 실행해
전역 asyncio.Lock으로 중복 실행을 막는다.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Awaitable, Callable

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from . import config
from .config import Settings
from .db import connect
from .pipeline.cycle import CycleBusy, CycleReport, run_cycle
from .pipeline.rebuilder import rebuild_category

log = logging.getLogger("rss_wiki.scheduler")
CycleRunner = Callable[..., Awaitable[CycleReport]]


class CycleController:
    """수집 사이클을 백그라운드 태스크로 시작·추적한다. 반드시 이벤트 루프 안에서 호출한다."""

    def __init__(self, settings: Settings, llm, runner: CycleRunner = run_cycle):
        self.settings = settings
        self.llm = llm
        self._loop = asyncio.get_running_loop()  # 다른 스레드(동기 엔드포인트)에서도 이 루프로 작업을 넘긴다
        self.lock = asyncio.Lock()
        self.rebuild_lock = asyncio.Lock()  # 수동 재구성(병합 등)끼리 직렬화
        self.running = False
        self.last_report: CycleReport | None = None
        self.last_error: str | None = None
        self._runner = runner
        self._tasks: set[asyncio.Task] = set()

    def try_start(self) -> bool:
        """실행 중이면 False. 아니면 태스크를 만들고 True."""
        if self.running:
            return False
        self.running = True
        task = asyncio.get_running_loop().create_task(self._run())
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return True

    def status(self) -> dict:
        """화면 폴링용 상태. last_report는 가장 최근에 끝난 사이클 결과(없으면 None)."""
        r = self.last_report
        return {
            "running": self.running,
            "last_error": self.last_error,
            "last_report": None if r is None else {
                "feeds_ok": r.feeds_ok, "feeds_failed": r.feeds_failed, "new_articles": r.new_articles,
                "summarized": r.summarized, "summarize_failed": r.summarize_failed,
                "categories_rebuilt": len(r.categories_rebuilt), "rebuild_failed": len(r.rebuild_failed)},
        }

    async def _run(self) -> None:
        try:
            self.last_report = await self._runner(self.settings.db_path, self.llm, lock=self.lock)
            self.last_error = None
            log.info("수집 사이클 완료: %s", self.last_report)
        except CycleBusy:
            log.info("이미 실행 중이라 건너뜀")
        except Exception as e:  # 사이클 실패가 앱을 죽이지 않게 한다
            self.last_error = f"{type(e).__name__}: {e}"
            log.exception("수집 사이클 실패")
        finally:
            self.running = False

    def schedule_rebuild(self, category_id: int, new_article_ids: list[int] | None = None) -> None:
        """카테고리 위키를 백그라운드에서 다시 만든다(예: 병합 직후). 어느 스레드에서 불러도 된다."""
        self._loop.call_soon_threadsafe(self._spawn_rebuild, category_id, new_article_ids)

    def _spawn_rebuild(self, category_id: int, new_article_ids: list[int] | None) -> None:
        task = self._loop.create_task(self._rebuild(category_id, new_article_ids))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _rebuild(self, category_id: int, new_article_ids: list[int] | None) -> None:
        async with self.rebuild_lock:
            conn = connect(self.settings.db_path)
            try:
                await rebuild_category(conn, self.llm, category_id, new_article_ids)
            except Exception:
                log.exception("카테고리 %s 재구성 실패", category_id)
            finally:
                conn.close()

    async def wait_idle(self) -> None:
        while self._tasks:
            await asyncio.gather(*list(self._tasks), return_exceptions=True)


def build_scheduler(controller: CycleController, loop: asyncio.AbstractEventLoop) -> BackgroundScheduler:
    """매시 정각(`hour='*', minute=0`)에 사이클을 시작하는 스케줄러를 만든다 (아직 start 전)."""

    def trigger() -> None:
        async def start():
            controller.try_start()

        asyncio.run_coroutine_threadsafe(start(), loop)

    scheduler = BackgroundScheduler()
    scheduler.add_job(trigger, CronTrigger(**config.FETCH_CRON), id="fetch_cycle",
                      max_instances=1, coalesce=True, replace_existing=True)
    return scheduler
