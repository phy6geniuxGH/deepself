from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, field_validator

T = TypeVar("T")


class ORMModel(BaseModel):
    """Read models build straight from SQLAlchemy objects."""
    model_config = ConfigDict(from_attributes=True)


class SearchHit(BaseModel, Generic[T]):
    """A semantic-search result: the entry plus its distance (lower = closer)."""
    distance: float
    entry: T


def split_tags(v) -> list[str]:
    """CSV cell 'a, b ,c' -> ['a','b','c']. Pass through real lists."""
    if v is None or v == "":
        return []
    if isinstance(v, list):
        return [str(t).strip() for t in v if str(t).strip()]
    return [t.strip() for t in str(v).split(",") if t.strip()]
