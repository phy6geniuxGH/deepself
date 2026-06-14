from backend.db.models import EntryType, IdeaStatus, SourceType
from backend.ingestion import manual
from backend.ingestion.files import import_file
from backend.schemas.idea import IdeaCreate
from backend.schemas.journal import JournalCreate


def test_manual_journal_creates_entry_detail_tags(session):
    e = manual.create_journal(
        session,
        JournalCreate(body_md="Morning run", mood="great", tags=["fitness", "fitness", "Health"]),
    )
    assert e.id is not None
    assert e.type == EntryType.journal
    assert e.source == SourceType.manual
    assert e.journal_detail.mood == "great"
    # dedup is case-insensitive -> fitness + Health
    assert {t.name for t in e.tags} == {"fitness", "Health"}


def test_manual_idea_defaults_status_new(session):
    e = manual.create_idea(session, IdeaCreate(body_md="Build a CLI"))
    assert e.type == EntryType.idea
    assert e.idea_detail.status == IdeaStatus.new


def test_tags_reused_across_entries(session):
    a = manual.create_journal(session, JournalCreate(body_md="a", tags=["shared"]))
    b = manual.create_journal(session, JournalCreate(body_md="b", tags=["shared"]))
    session.flush()
    assert a.tags[0].id == b.tags[0].id  # same Tag row, not duplicated


def test_csv_import_good_and_bad_rows(session):
    csv = (
        b"body_md,mood,tags\n"
        b'Ran today,good,"fitness,health"\n'
        b"Read a book,calm,reading\n"
        b",sad,empty\n"  # blank body_md -> validation error
    )
    result = import_file(session, "journal", csv, "entries.csv")
    assert result.ok == 2
    assert len(result.errors) == 1
    assert result.errors[0]["row"] == 4  # header + 1-indexed data row
    # tags split from the csv cell
    first = result.entries[0]
    assert {t.name for t in first.tags} == {"fitness", "health"}
    assert first.source == SourceType.csv


def test_import_unknown_aspect_raises(session):
    try:
        import_file(session, "nope", b"body_md\nx\n", "x.csv")
        assert False, "expected ValueError"
    except ValueError as e:
        assert "unknown aspect" in str(e)
