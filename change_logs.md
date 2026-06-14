# Change Log

All notable changes to deepself. Format loosely follows [Keep a Changelog]; dates are ISO.

## [0.1.0] — 2026-06-15 — Phase 0 (MVP vertical slice)

First working end-to-end slice: **Entry spine + Daily Journal + Idea Dumps**, manual and
file ingestion, semantic search, markdown PKM, API + UI in one process.

### Added
- **Project scaffolding** — `backend/` + `frontend/` split, single-process design
  (FastAPI + nicegui mounted via `ui.run_with`); `requirements.txt`.
- **Config** — `backend/config.py`: pydantic-settings `Settings` (`DEEPSELF_` env prefix),
  paths, embedding model/dim, server host/port, `storage_secret`, `db_url`, `ensure_dirs`.
- **Database** — `backend/db/engine.py`: SQLAlchemy 2.0 engine, per-connection sqlite-vec
  load + `PRAGMA foreign_keys=ON`, `get_session` dependency, idempotent `ensure_vec_table`
  (vec0 virtual table, 384-dim).
- **Models** — `backend/db/models.py`: Entry spine + `Tag`/`EntryTag` (m2m) +
  `JournalDetail`/`IdeaDetail` (1-1); enums `EntryType`, `SourceType`, `IdeaStatus`.
- **Migrations** — Alembic initialized at `backend/db/migrations/`; `env.py` wired to
  `Settings.db_url` + `Base.metadata` with `render_as_batch=True`; baseline migration
  (`entries`, `tags`, `entry_tags`, `journal_details`, `idea_details`).
- **Schemas** — `backend/schemas/`: `Create` / `Read` / `CSVRow` per aspect; `ORMModel`,
  generic `SearchHit`, `split_tags`; `Read.from_entry(...)` classmethods.
- **Ingestion** — `backend/ingestion/`: `manual.create_journal/create_idea` +
  `get_or_create_tags`; registry-driven `import_file` for csv/xlsx with per-row,
  non-fatal validation (`ImportResult`).
- **Embeddings** — `backend/enrichment/embeddings.py`: lazy `sentence-transformers`
  singleton, L2-normalized `embed_text` / `embed_batch`, blank→zero-vector, dim assertion.
- **Projections** — `backend/projections/`: `vectors.py` (upsert/delete/KNN search with
  overscan type-filter), `markdown.py` (`data/pkm/<type>/<id>.md` + YAML frontmatter),
  `project_entry` / `remove_entry` orchestrators.
- **API** — `backend/api/`: `journal` + `idea` routers (create/list/get/delete/search/upload;
  idea status filter + PATCH status), aggregated under `/api`.
- **Frontend** — `frontend/services.py` (in-process service layer returning session-safe
  Read models); nicegui pages for Home, Journal, Idea Dumps; shared nav `page_header`.
- **Entrypoint** — `main.py`: FastAPI app, startup lifespan (migrations + vec table),
  API mount, page registration, `ui.run_with`.
- **Tests** — `tests/`: temp-DB `conftest`, ingestion tests (manual/csv/dedup/errors),
  projection tests (markdown, vector ranking, cleanup). 8 passing.
- **Docs** — `AGENTS.md`, `CLAUDE.md` (shim), `README.md`, `documentation.md`,
  `future_implementations.md` (8-aspect roadmap), `LICENSE` (MIT), this change log.

### Decisions
- deepself scope = ingestion + storage only; LLM/NLP **ingestion-side only**. Reasoning is
  AOSSBrain's job.
- **SQLite = source of truth**; markdown + sqlite-vec are derived, regenerable projections.
- Vectors stored in **sqlite-vec** inside the same SQLite file (no extra service).
- **SQLAlchemy 2.0** chosen over SQLModel (maturity/docs).
- Single process (UI in-process to backend), folders for code separation only.

### Notes
- First request needing embeddings downloads the ~80MB MiniLM model once.
- LICENSE copyright holder set to "Francis Dela Cruz" — update if incorrect.
