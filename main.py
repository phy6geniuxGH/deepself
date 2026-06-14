"""deepself entrypoint.

Single process: FastAPI serves /api/* (AOSSBrain-facing); nicegui serves the UI
pages mounted on the same app. Launch with:

    .venv/bin/uvicorn main:app --reload

Startup runs Alembic migrations + ensures the sqlite-vec table exists.
"""

from contextlib import asynccontextmanager

from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from nicegui import ui

from backend.api import api_router
from backend.config import get_settings
from backend.db.engine import ensure_vec_table

settings = get_settings()


def _run_migrations() -> None:
    cfg = Config(str(settings.base_dir / "alembic.ini"))
    command.upgrade(cfg, "head")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings.ensure_dirs()
    _run_migrations()        # ORM tables up to date
    ensure_vec_table()       # sqlite-vec virtual table (outside Alembic)
    yield


app = FastAPI(title="deepself", lifespan=lifespan)
app.include_router(api_router)

# importing this package registers all @ui.page routes
import frontend.pages  # noqa: E402,F401

# mount nicegui onto the FastAPI app (same process, shared event loop)
ui.run_with(app, storage_secret=settings.storage_secret, title="deepself")
