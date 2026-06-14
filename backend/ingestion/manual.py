from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.db.models import (
    Entry, EntryType, IdeaDetail, JournalDetail, SourceType, Tag,
)
from backend.schemas.idea import IdeaCreate
from backend.schemas.journal import JournalCreate


def _now() -> datetime:
    return datetime.now(timezone.utc)


def get_or_create_tags(session: Session, names: list[str]) -> list[Tag]:
    """Reuse existing Tag rows by name, create missing ones. Dedup, order-stable."""
    out: list[Tag] = []
    seen: set[str] = set()
    for raw in names:
        name = raw.strip()
        if not name or name.lower() in seen:
            continue
        seen.add(name.lower())
        tag = session.scalar(select(Tag).where(Tag.name == name))
        if tag is None:
            tag = Tag(name=name)
            session.add(tag)
        out.append(tag)
    return out


def create_journal(
    session: Session, data: JournalCreate, source: SourceType = SourceType.manual
) -> Entry:
    entry = Entry(
        type=EntryType.journal,
        source=source,
        occurred_at=data.occurred_at or _now(),
        category=data.category,
        body_md=data.body_md,
    )
    entry.journal_detail = JournalDetail(mood=data.mood)
    entry.tags = get_or_create_tags(session, data.tags)
    session.add(entry)
    session.flush()          # assign entry.id without committing
    return entry


def create_idea(
    session: Session, data: IdeaCreate, source: SourceType = SourceType.manual
) -> Entry:
    entry = Entry(
        type=EntryType.idea,
        source=source,
        occurred_at=data.occurred_at or _now(),
        category=data.category,
        body_md=data.body_md,
    )
    entry.idea_detail = IdeaDetail(status=data.status)
    entry.tags = get_or_create_tags(session, data.tags)
    session.add(entry)
    session.flush()
    return entry
