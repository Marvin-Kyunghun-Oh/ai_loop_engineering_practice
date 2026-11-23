"""FastAPI 앱 진입점. `uv run uvicorn rss_wiki.main:app --host 127.0.0.1 --port 8000`"""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .config import Settings
from .db import init_db
from .pipeline.llm import ClaudeCLI
from .scheduler import CycleController, build_scheduler
from .web.routes import router


def _setup_logging(settings: Settings) -> None:
    settings.log_path.parent.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger("rss_wiki")
    root.setLevel(logging.INFO)
    if not any(isinstance(h, logging.FileHandler) and h.baseFilename == str(settings.log_path.resolve())
               for h in root.handlers):
        fh = logging.FileHandler(settings.log_path, encoding="utf-8")
        fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
        root.addHandler(fh)
        root.addHandler(logging.StreamHandler())  # stderr


def create_app(settings: Settings | None = None, *, llm=None, cycle_runner=None) -> FastAPI:
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        _setup_logging(settings)
        init_db(settings.db_path)  # CREATE TABLE IF NOT EXISTS
        kwargs = {"runner": cycle_runner} if cycle_runner else {}
        app.state.controller = CycleController(
            settings, llm or ClaudeCLI(settings.claude_command), **kwargs)
        scheduler = None
        if settings.enable_scheduler:
            scheduler = build_scheduler(app.state.controller, asyncio.get_running_loop())
            scheduler.start()
        app.state.scheduler = scheduler
        try:
            yield
        finally:
            if scheduler:
                scheduler.shutdown(wait=False)

    app = FastAPI(title="RSS Wiki", lifespan=lifespan)
    app.state.settings = settings
    app.include_router(router)
    return app


app = create_app()
