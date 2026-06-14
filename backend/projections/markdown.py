"""Render Entries to markdown files under data/pkm/. Derived, regenerable."""

from pathlib import Path

from backend.config import get_settings
from backend.db.models import Entry

settings = get_settings()


def entry_path(entry: Entry) -> Path:
    return settings.pkm_dir / entry.type.value / f"{entry.id:06d}.md"


def _frontmatter(entry: Entry) -> str:
    fields: list[tuple[str, str]] = [
        ("id", str(entry.id)),
        ("type", entry.type.value),
        ("source", entry.source.value),
        ("occurred_at", entry.occurred_at.isoformat()),
        ("created_at", entry.created_at.isoformat()),
    ]
    if entry.category:
        fields.append(("category", entry.category))
    if entry.journal_detail and entry.journal_detail.mood:
        fields.append(("mood", entry.journal_detail.mood))
    if entry.idea_detail:
        fields.append(("status", entry.idea_detail.status.value))

    lines = ["---"]
    lines += [f"{k}: {v}" for k, v in fields]
    tags = [t.name for t in entry.tags]
    lines.append("tags: [" + ", ".join(tags) + "]")
    lines.append("---")
    return "\n".join(lines)


def render_entry(entry: Entry) -> str:
    return f"{_frontmatter(entry)}\n\n{entry.body_md or ''}\n"


def write_entry(entry: Entry) -> Path:
    path = entry_path(entry)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_entry(entry), encoding="utf-8")
    return path


def delete_entry(entry: Entry) -> None:
    entry_path(entry).unlink(missing_ok=True)
