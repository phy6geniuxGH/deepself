# deepself

Personal-life **data ingestion + storage** layer. Capture journals, ideas, routines,
finances, fitness, and more — by typing or by uploading csv/xlsx — into one queryable
store with semantic search and an auto-growing markdown knowledge base.

deepself is the storage/ingestion half of a larger personal "second brain". The reasoning
half (**AOSSBrain**, a separate agentic app) consumes deepself's API and vector index.
deepself itself uses local NLP only at ingestion time (embeddings) — it does not chat or
reason over your data.

> **Status:** Phase 0 (MVP) complete — **Daily Journal** + **Idea Dumps** end-to-end.
> The full 8-aspect roadmap lives in [future_implementations.md](future_implementations.md).

## Features (Phase 0)

- **Entry spine** — one core data model all aspects share (timestamp, tags, category,
  free-text/markdown body) with typed per-aspect detail tables.
- **Two ingestion modes** — manual entry in the UI, or bulk upload of `.csv` / `.xlsx`
  with per-row validation (bad rows reported, not fatal).
- **Semantic search** — local `sentence-transformers` embeddings stored in **sqlite-vec**
  (inside the same SQLite file), L2-normalized for cosine-like ranking.
- **Markdown PKM** — every entry is also projected to `data/pkm/<type>/<id>.md` with YAML
  frontmatter; derived from SQLite and fully regenerable.
- **API + UI in one process** — FastAPI (`/api/*`, `/docs`) for programmatic access;
  [nicegui](https://nicegui.io) pages for humans. Mounted on a single server.

## Tech stack

Python · FastAPI · nicegui · SQLAlchemy 2.0 + Alembic · SQLite + sqlite-vec ·
sentence-transformers (Hugging Face) · pandas/openpyxl · pydantic v2.

## Quick start

```bash
# 1. install (torch is large; first install is slow)
.venv/bin/python -m pip install -r requirements.txt

# 2. apply migrations (also run automatically at app startup)
.venv/bin/alembic upgrade head

# 3. run
.venv/bin/uvicorn main:app --reload
```

Open http://127.0.0.1:8080 for the UI, or http://127.0.0.1:8080/docs for the API.
First request that needs embeddings downloads the ~80MB model once.

## Tests

```bash
.venv/bin/python -m pytest tests/ -q
```

## Configuration

All settings live in `backend/config.py` (pydantic-settings). Override any field with an
env var prefixed `DEEPSELF_` or a `.env` file, e.g.:

```env
DEEPSELF_PORT=9000
DEEPSELF_STORAGE_SECRET=replace-me-in-production
```

## Project layout

```
backend/    config, db (models + engine + migrations), schemas,
            ingestion, enrichment (embeddings), projections, api
frontend/   nicegui pages + in-process service layer
main.py     entrypoint: FastAPI + nicegui mount + startup migrations
data/       deepself.db (SQLite + vectors) and pkm/ (generated markdown)
tests/      pytest smoke tests
```

See [AGENTS.md](AGENTS.md) for architecture details and [documentation.md](documentation.md)
for the API/class reference.

## License

MIT — see [LICENSE](LICENSE).
