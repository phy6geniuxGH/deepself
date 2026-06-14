"""Test fixtures. Point the app at a throwaway DB + pkm dir BEFORE importing backend."""

import os
import tempfile
from pathlib import Path

import pytest

_TMP = Path(tempfile.mkdtemp(prefix="deepself-test-"))
os.environ["DEEPSELF_DATA_DIR"] = str(_TMP)
os.environ["DEEPSELF_DB_PATH"] = str(_TMP / "test.db")
os.environ["DEEPSELF_PKM_DIR"] = str(_TMP / "pkm")

# imported only after env is set, so engine binds the temp DB
from backend.db.engine import SessionLocal, engine, ensure_vec_table  # noqa: E402
from backend.db.models import Base  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _schema():
    Base.metadata.create_all(engine)
    ensure_vec_table()
    yield


@pytest.fixture
def session():
    s = SessionLocal()
    try:
        yield s
        s.commit()
    finally:
        s.close()
