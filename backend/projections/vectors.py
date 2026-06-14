from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session
from sqlite_vec import serialize_float32

from backend.db.models import Entry
from backend.enrichment.embeddings import embed_text


def _source_text(entry: Entry) -> str:
    """What we embed: body + category + tag names, so search hits metadata too."""
    parts = [entry.body_md or ""]
    if entry.category:
        parts.append(entry.category)
    if entry.tags:
        parts.append(" ".join(t.name for t in entry.tags))
    return "\n".join(p for p in parts if p).strip()


def upsert_entry_vector(session: Session, entry: Entry) -> None:
    """Re-embed and store. vec0 has no UPSERT, so delete-then-insert."""
    blob = serialize_float32(embed_text(_source_text(entry)))
    session.execute(text("DELETE FROM vec_entries WHERE entry_id = :id"), {"id": entry.id})
    session.execute(
        text("INSERT INTO vec_entries(entry_id, embedding) VALUES (:id, :emb)"),
        {"id": entry.id, "emb": blob},
    )


def delete_entry_vector(session: Session, entry_id: int) -> None:
    session.execute(text("DELETE FROM vec_entries WHERE entry_id = :id"), {"id": entry_id})


def search(
    session: Session, query: str, k: int = 10, entry_type: str | None = None
) -> list[tuple[int, float]]:
    """KNN over embeddings. Returns [(entry_id, distance), ...] nearest first.

    Type filter uses overscan-then-filter: vec0 KNN won't combine cleanly with a
    JOIN-side WHERE, so fetch more, filter by Entry.type in Python, trim to k.
    """
    blob = serialize_float32(embed_text(query))
    limit = k * 4 if entry_type else k
    rows = session.execute(
        text(
            "SELECT entry_id, distance FROM vec_entries "
            "WHERE embedding MATCH :q ORDER BY distance LIMIT :limit"
        ),
        {"q": blob, "limit": limit},
    ).all()

    if not entry_type:
        return [(r[0], r[1]) for r in rows]

    ids = [r[0] for r in rows]
    if not ids:
        return []
    stmt = text(
        "SELECT id FROM entries WHERE id IN :ids AND type = :t"
    ).bindparams(bindparam("ids", expanding=True))
    keep = {row[0] for row in session.execute(stmt, {"ids": ids, "t": entry_type}).all()}
    return [(r[0], r[1]) for r in rows if r[0] in keep][:k]
