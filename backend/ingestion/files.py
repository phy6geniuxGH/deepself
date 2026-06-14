from dataclasses import dataclass, field
from io import BytesIO

import pandas as pd
from sqlalchemy.orm import Session

from backend.db.models import Entry, SourceType
from backend.ingestion.registry import get_spec


@dataclass
class ImportResult:
    entries: list[Entry] = field(default_factory=list)
    errors: list[dict] = field(default_factory=list)   # {"row": int, "error": str}

    @property
    def ok(self) -> int:
        return len(self.entries)


def _read_table(content: bytes, filename: str) -> tuple[pd.DataFrame, SourceType]:
    name = filename.lower()
    if name.endswith(".csv"):
        return pd.read_csv(BytesIO(content)), SourceType.csv
    if name.endswith((".xlsx", ".xls")):
        return pd.read_excel(BytesIO(content)), SourceType.xlsx
    raise ValueError("unsupported file type; use .csv or .xlsx")


def import_file(session: Session, aspect: str, content: bytes, filename: str) -> ImportResult:
    """Parse csv/xlsx -> validate each row -> persist. Bad rows collected, not fatal."""
    spec = get_spec(aspect)
    df, source = _read_table(content, filename)
    result = ImportResult()

    for i, raw in df.iterrows():
        rowdict = raw.where(pd.notna(raw), None).to_dict()   # NaN -> None
        try:
            row = spec.csv_schema(**rowdict)                  # validate
            payload = spec.create_schema(**row.model_dump())  # -> create model
            entry = spec.creator(session, payload, source)    # persist
            result.entries.append(entry)
        except Exception as e:
            result.errors.append({"row": int(i) + 2, "error": str(e)})  # +2: header + 1-index
    return result
