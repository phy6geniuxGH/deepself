from collections.abc import Iterator

import sqlite_vec
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from backend.config import get_settings

settings = get_settings()

# check_same_thread=False: nicegui/FastAPI touch the DB from multiple threads.
engine: Engine = create_engine(
    settings.db_url,
    echo=False,
    connect_args={"check_same_thread": False},
)


@event.listens_for(engine, "connect")
def _on_connect(dbapi_conn, _record):
    """Runs for every new connection: load sqlite-vec + enable FK enforcement."""
    dbapi_conn.enable_load_extension(True)
    sqlite_vec.load(dbapi_conn)
    dbapi_conn.enable_load_extension(False)
    dbapi_conn.execute("PRAGMA foreign_keys=ON")  # SQLite ignores FKs unless ON


SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_session() -> Iterator[Session]:
    """FastAPI dependency / context use. One session per request."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def ensure_vec_table() -> None:
    """Idempotent: create the sqlite-vec virtual table (not managed by Alembic)."""
    settings.ensure_dirs()
    with engine.connect() as conn:
        conn.execute(
            text(
                f"""
                CREATE VIRTUAL TABLE IF NOT EXISTS vec_entries
                USING vec0(
                    entry_id INTEGER PRIMARY KEY,
                    embedding FLOAT[{settings.embedding_dim}]
                )
                """
            )
        )
        conn.commit()
