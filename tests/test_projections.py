"""Projection tests. These load the real embedding model (slow first run)."""

from backend import projections
from backend.ingestion import manual
from backend.projections import markdown, vectors
from backend.schemas.journal import JournalCreate


def test_markdown_written_with_frontmatter(session):
    e = manual.create_journal(
        session, JournalCreate(body_md="Hello world body", mood="ok", tags=["x"])
    )
    projections.project_entry(session, e)
    path = markdown.entry_path(e)
    assert path.exists()
    text = path.read_text()
    assert "Hello world body" in text
    assert "type: journal" in text
    assert "mood: ok" in text


def test_vector_search_ranks_relevant_first(session):
    hike = manual.create_journal(
        session, JournalCreate(body_md="I love hiking mountains and trails outdoors")
    )
    money = manual.create_journal(
        session, JournalCreate(body_md="Quarterly budget spreadsheet and finance review")
    )
    projections.project_entry(session, hike)
    projections.project_entry(session, money)
    session.flush()

    hits = vectors.search(session, "outdoor trekking in nature", k=5, entry_type="journal")
    assert hits, "expected at least one hit"
    assert hits[0][0] == hike.id  # hiking entry ranks above finance


def test_remove_entry_clears_markdown(session):
    e = manual.create_journal(session, JournalCreate(body_md="to be deleted"))
    projections.project_entry(session, e)
    assert markdown.entry_path(e).exists()
    projections.remove_entry(session, e)
    assert not markdown.entry_path(e).exists()
