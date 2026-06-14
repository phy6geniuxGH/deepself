# AGENTS.md

Guidance for AI agents (Claude Code et al.) and developers working in this repository.
`CLAUDE.md` is a thin shim that points here — this file is the source of truth.

## What this project is

**deepself** = the *data ingestion + storage* layer for personal life data. It complements
**AOSSBrain** (a separate agentic app) which does the reasoning. Hard boundary:

- deepself uses LLM/NLP **ingestion-side only** (write-time: embeddings, later auto-tag /
  summarize / entity-extract). It does **not** do querying/chat/agentic reasoning.
- AOSSBrain consumes deepself's `/api/*` + vector index.

Keep that boundary. Do not add chat/agent loops to deepself.

## Commands

```bash
# install
.venv/bin/python -m pip install -r requirements.txt

# run the app (FastAPI + nicegui, one process)
.venv/bin/uvicorn main:app --reload        # http://127.0.0.1:8080  + /docs

# tests
.venv/bin/python -m pytest tests/ -q
.venv/bin/python -m pytest tests/test_ingestion.py::test_csv_import_good_and_bad_rows   # single test

# migrations (Alembic manages ORM tables)
.venv/bin/alembic revision --autogenerate -m "msg"   # after changing models; REVIEW the script
.venv/bin/alembic upgrade head
.venv/bin/alembic downgrade -1
```

Always run from repo root so `backend` / `frontend` import correctly.

## Architecture (the big picture)

### Entry spine — one core table, not 8 silos
All aspects share a timestamped/tagged/categorized/free-text shape. So:
`Entry` (core) + specialized **one-to-one** detail tables hanging off it
(`JournalDetail`, `IdeaDetail`, …) + `Tag` many-to-many. Adding an aspect = a new
detail table + enum value, not a new parallel stack. See `backend/db/models.py`.

### Three stores, one source of truth
- **SQLite** = authoritative.
- **markdown** (`data/pkm/`) and **sqlite-vec** vectors are **derived projections**,
  regenerable from SQLite. Never treat them as authoritative.
- `backend/projections/project_entry(session, entry)` rebuilds both for an entry;
  `remove_entry(...)` drops both. Call `project_entry` after every create/update.

### Single process
`backend/` = server-side, `frontend/` = nicegui UI, root `main.py` = entrypoint that
builds the FastAPI app, mounts the API router, imports `frontend.pages` (registers
`@ui.page` routes), and calls `ui.run_with(app)`. The UI talks to the backend
**in-process** via `frontend/services.py` — no HTTP hop.

### Ingestion is registry-driven
`backend/ingestion/registry.py::REGISTRY` maps an aspect name → its CSV schema, create
schema, and creator function. Both manual entry and csv/xlsx upload funnel through
pydantic validation into the same Entry spine. **Add an aspect = one REGISTRY line**
(+ its schemas + a `create_*` in `manual.py`).

### Embeddings
`backend/enrichment/embeddings.py` — local `sentence-transformers`, lazy singleton load.
Vectors are L2-normalized so sqlite-vec L2 distance ranks like cosine.
`settings.embedding_dim` **must** equal the model's real dim **and** the `vec_entries`
table width — they're created together. Change model → change dim → recreate the table.

## Conventions & gotchas (easy to get wrong)

- **sqlite-vec + FK pragma load per connection** — `engine.py` has a `@event.listens_for
  (engine, "connect")` hook that loads the extension and runs `PRAGMA foreign_keys=ON`.
  SQLite silently ignores FKs and won't know the extension otherwise.
- **`vec_entries` is OUTSIDE Alembic** — it's a `vec0` virtual table; autogenerate can't
  see it and would try to drop it. It's created idempotently by `ensure_vec_table()` at
  startup. Don't add it to migrations.
- **Migrations use `render_as_batch=True`** (set in `migrations/env.py`) — required because
  SQLite can't `ALTER TABLE` for most changes; batch mode rebuilds the table.
- **Read models via `from_entry`** — `JournalRead.from_entry(e)` / `IdeaRead.from_entry(e)`
  build plain pydantic from an ORM Entry so callers are safe after the session closes
  (no detached-instance errors). The API and the UI services both use these.
- **Search type-filter overscans** — `vectors.search(..., entry_type=...)` fetches `k*4`
  then filters by type in Python, because vec0 KNN doesn't combine cleanly with a JOIN-side
  WHERE.
- **`session.flush()` not `commit()` in ingestion** — `manual.create_*` flush to get
  `entry.id`; the surrounding `get_session` dependency / `_session()` context commits once.
- **CSV import is non-fatal per row** — `ImportResult` collects `{row, error}` for bad rows
  (row number = spreadsheet line). One bad row doesn't kill the upload.

## Where things live

| Concern | Path |
|---------|------|
| Config / settings | `backend/config.py` (`get_settings()`, env prefix `DEEPSELF_`) |
| DB engine + session + vec table | `backend/db/engine.py` |
| ORM models + enums | `backend/db/models.py` |
| Migrations | `backend/db/migrations/` + `alembic.ini` |
| Pydantic schemas (IO + CSV) | `backend/schemas/` |
| Ingestion (manual / files / registry) | `backend/ingestion/` |
| Embeddings | `backend/enrichment/embeddings.py` |
| Projections (vectors / markdown) | `backend/projections/` |
| API routers | `backend/api/` (mounted under `/api`) |
| UI services + pages | `frontend/services.py`, `frontend/pages/` |
| Entrypoint | `main.py` |
| Roadmap (all 8 aspects) | `future_implementations.md` |

## Status

Phase 0 (MVP vertical slice) is complete: Entry spine + Journal + Idea Dumps, end-to-end.
See `future_implementations.md` for the full 8-aspect plan and what remains.
