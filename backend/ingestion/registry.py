from collections.abc import Callable
from dataclasses import dataclass

from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.db.models import Entry, EntryType, SourceType
from backend.ingestion import manual
from backend.schemas.idea import IdeaCreate, IdeaCSVRow
from backend.schemas.journal import JournalCreate, JournalCSVRow


@dataclass(frozen=True)
class AspectSpec:
    entry_type: EntryType
    csv_schema: type[BaseModel]      # validates one file row
    create_schema: type[BaseModel]   # canonical create payload
    creator: Callable[[Session, BaseModel, SourceType], Entry]


REGISTRY: dict[str, AspectSpec] = {
    "journal": AspectSpec(EntryType.journal, JournalCSVRow, JournalCreate, manual.create_journal),
    "idea": AspectSpec(EntryType.idea, IdeaCSVRow, IdeaCreate, manual.create_idea),
}


def get_spec(aspect: str) -> AspectSpec:
    try:
        return REGISTRY[aspect]
    except KeyError:
        raise ValueError(f"unknown aspect '{aspect}'. known: {list(REGISTRY)}")
