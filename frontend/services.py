"""In-process service layer for the nicegui UI.

Each call opens a short-lived session, does the work, commits, and returns plain
pydantic models (not ORM objects) so the UI never touches a detached session.
"""

from contextlib import contextmanager

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend import projections
from backend.db.engine import SessionLocal
from backend.db.models import Entry, EntryType, IdeaDetail, IdeaStatus
from backend.ingestion import manual
from backend.ingestion.files import import_file
from backend.projections import vectors
from backend.schemas.idea import IdeaCreate, IdeaRead
from backend.schemas.journal import JournalCreate, JournalRead


@contextmanager
def _session():
    s = SessionLocal()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()


# --- journal ---
def create_journal(body_md: str, mood: str | None, tags_csv: str | None) -> JournalRead:
    data = JournalCreate(
        body_md=body_md,
        mood=mood or None,
        tags=[t.strip() for t in (tags_csv or "").split(",") if t.strip()],
    )
    with _session() as s:
        e = manual.create_journal(s, data)
        projections.project_entry(s, e)
        return JournalRead.from_entry(e)


def list_journals(limit: int = 100) -> list[JournalRead]:
    with _session() as s:
        stmt = (
            select(Entry)
            .where(Entry.type == EntryType.journal)
            .order_by(Entry.occurred_at.desc())
            .limit(limit)
        )
        return [JournalRead.from_entry(e) for e in s.scalars(stmt).all()]


def search_journals(q: str, k: int = 10) -> list[tuple[JournalRead, float]]:
    with _session() as s:
        hits = vectors.search(s, q, k=k, entry_type=EntryType.journal.value)
        found = {e.id: e for e in s.scalars(select(Entry).where(Entry.id.in_([h[0] for h in hits]))).all()}
        return [(JournalRead.from_entry(found[i]), d) for i, d in hits if i in found]


def delete_journal(entry_id: int) -> None:
    with _session() as s:
        e = s.get(Entry, entry_id)
        if e and e.type == EntryType.journal:
            projections.remove_entry(s, e)
            s.delete(e)


def import_journal(content: bytes, filename: str) -> dict:
    with _session() as s:
        res = import_file(s, "journal", content, filename)
        for e in res.entries:
            projections.project_entry(s, e)
        return {"imported": res.ok, "errors": res.errors}


# --- idea ---
def create_idea(body_md: str, tags_csv: str | None) -> IdeaRead:
    data = IdeaCreate(
        body_md=body_md,
        tags=[t.strip() for t in (tags_csv or "").split(",") if t.strip()],
    )
    with _session() as s:
        e = manual.create_idea(s, data)
        projections.project_entry(s, e)
        return IdeaRead.from_entry(e)


def list_ideas(status: IdeaStatus | None = None, limit: int = 100) -> list[IdeaRead]:
    with _session() as s:
        stmt = select(Entry).where(Entry.type == EntryType.idea)
        if status is not None:
            stmt = stmt.join(IdeaDetail).where(IdeaDetail.status == status)
        stmt = stmt.order_by(Entry.occurred_at.desc()).limit(limit)
        return [IdeaRead.from_entry(e) for e in s.scalars(stmt).all()]


def set_idea_status(entry_id: int, status: IdeaStatus) -> None:
    with _session() as s:
        e = s.get(Entry, entry_id)
        if e and e.type == EntryType.idea:
            e.idea_detail.status = status


def delete_idea(entry_id: int) -> None:
    with _session() as s:
        e = s.get(Entry, entry_id)
        if e and e.type == EntryType.idea:
            projections.remove_entry(s, e)
            s.delete(e)


def import_idea(content: bytes, filename: str) -> dict:
    with _session() as s:
        res = import_file(s, "idea", content, filename)
        for e in res.entries:
            projections.project_entry(s, e)
        return {"imported": res.ok, "errors": res.errors}
