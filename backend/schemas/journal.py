from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from backend.schemas.common import ORMModel, split_tags


class JournalCreate(BaseModel):
    body_md: str
    occurred_at: datetime | None = None      # default now() set in service
    category: str | None = None
    mood: str | None = None
    tags: list[str] = Field(default_factory=list)


class JournalRead(ORMModel):
    id: int
    occurred_at: datetime
    created_at: datetime
    category: str | None
    body_md: str
    mood: str | None = None
    sentiment: float | None = None
    tags: list[str] = Field(default_factory=list)

    @field_validator("tags", mode="before")
    @classmethod
    def _tagnames(cls, v):
        # ORM gives Tag objects; expose names
        return [t.name if hasattr(t, "name") else t for t in (v or [])]

    @classmethod
    def from_entry(cls, e) -> "JournalRead":
        d = e.journal_detail
        return cls(
            id=e.id, occurred_at=e.occurred_at, created_at=e.created_at,
            category=e.category, body_md=e.body_md,
            mood=d.mood if d else None, sentiment=d.sentiment if d else None,
            tags=[t.name for t in e.tags],
        )


class JournalCSVRow(BaseModel):
    """One row of an uploaded journal csv/xlsx."""
    occurred_at: datetime | None = None
    body_md: str
    mood: str | None = None
    category: str | None = None
    tags: list[str] = Field(default_factory=list)

    _split = field_validator("tags", mode="before")(split_tags)
