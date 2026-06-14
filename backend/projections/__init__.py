"""One-call projection of an Entry into its derived views (vectors + markdown)."""

from sqlalchemy.orm import Session

from backend.db.models import Entry
from backend.projections import markdown, vectors


def project_entry(session: Session, entry: Entry) -> None:
    """After create/update: refresh embedding + markdown file. Call post-flush (id set)."""
    vectors.upsert_entry_vector(session, entry)
    markdown.write_entry(entry)


def remove_entry(session: Session, entry: Entry) -> None:
    """Before/at delete: drop embedding + markdown file."""
    vectors.delete_entry_vector(session, entry.id)
    markdown.delete_entry(entry)
