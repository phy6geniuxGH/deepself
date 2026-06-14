from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from backend.db.models import IdeaStatus
from backend.schemas.common import ORMModel, split_tags


class IdeaCreate(BaseModel):
    body_md: str
    occurred_at: datetime | None = None
    category: str | None = None
    status: IdeaStatus = IdeaStatus.new
    tags: list[str] = Field(default_factory=list)


class IdeaRead(ORMModel):
    id: int
    occurred_at: datetime
    created_at: datetime
    category: str | None
    body_md: str
    status: IdeaStatus
    tags: list[str] = Field(default_factory=list)

    @field_validator("tags", mode="before")
    @classmethod
    def _tagnames(cls, v):
        return [t.name if hasattr(t, "name") else t for t in (v or [])]

    @classmethod
    def from_entry(cls, e) -> "IdeaRead":
        d = e.idea_detail
        return cls(
            id=e.id, occurred_at=e.occurred_at, created_at=e.created_at,
            category=e.category, body_md=e.body_md,
            status=d.status if d else IdeaStatus.new,
            tags=[t.name for t in e.tags],
        )


class IdeaCSVRow(BaseModel):
    occurred_at: datetime | None = None
    body_md: str
    category: str | None = None
    status: IdeaStatus = IdeaStatus.new
    tags: list[str] = Field(default_factory=list)

    _split = field_validator("tags", mode="before")(split_tags)
