import enum
from datetime import datetime, timezone

from sqlalchemy import (
    JSON, DateTime, Enum, Float, ForeignKey, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import (
    DeclarativeBase, Mapped, mapped_column, relationship,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


# --- enums (grow as aspects added) ---
class EntryType(str, enum.Enum):
    journal = "journal"
    idea = "idea"


class SourceType(str, enum.Enum):
    manual = "manual"
    csv = "csv"
    xlsx = "xlsx"
    derived = "derived"


class IdeaStatus(str, enum.Enum):
    new = "new"
    reviewing = "reviewing"
    pursuing = "pursuing"
    archived = "archived"


# --- association: Entry <-> Tag ---
class EntryTag(Base):
    __tablename__ = "entry_tags"
    entry_id: Mapped[int] = mapped_column(
        ForeignKey("entries.id", ondelete="CASCADE"), primary_key=True
    )
    tag_id: Mapped[int] = mapped_column(
        ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True
    )


class Tag(Base):
    __tablename__ = "tags"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    entries: Mapped[list["Entry"]] = relationship(
        secondary="entry_tags", back_populates="tags"
    )


# --- core spine ---
class Entry(Base):
    __tablename__ = "entries"
    id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[EntryType] = mapped_column(Enum(EntryType), index=True)
    source: Mapped[SourceType] = mapped_column(
        Enum(SourceType), default=SourceType.manual
    )
    occurred_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    category: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    body_md: Mapped[str] = mapped_column(Text, default="")
    meta: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    tags: Mapped[list[Tag]] = relationship(
        secondary="entry_tags", back_populates="entries"
    )
    journal_detail: Mapped["JournalDetail | None"] = relationship(
        back_populates="entry", cascade="all, delete-orphan", uselist=False
    )
    idea_detail: Mapped["IdeaDetail | None"] = relationship(
        back_populates="entry", cascade="all, delete-orphan", uselist=False
    )


# --- specialized (one-to-one off Entry) ---
class JournalDetail(Base):
    __tablename__ = "journal_details"
    entry_id: Mapped[int] = mapped_column(
        ForeignKey("entries.id", ondelete="CASCADE"), primary_key=True
    )
    mood: Mapped[str | None] = mapped_column(String(32), nullable=True)
    sentiment: Mapped[float | None] = mapped_column(Float, nullable=True)
    entry: Mapped[Entry] = relationship(back_populates="journal_detail")


class IdeaDetail(Base):
    __tablename__ = "idea_details"
    entry_id: Mapped[int] = mapped_column(
        ForeignKey("entries.id", ondelete="CASCADE"), primary_key=True
    )
    status: Mapped[IdeaStatus] = mapped_column(
        Enum(IdeaStatus), default=IdeaStatus.new, index=True
    )
    field_id: Mapped[int | None] = mapped_column(nullable=True)  # FK added when Field table exists
    entry: Mapped[Entry] = relationship(back_populates="idea_detail")
