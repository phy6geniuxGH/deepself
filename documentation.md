# deepself — Code Documentation

Detailed reference for modules, classes, functions, and the HTTP API. Architecture and
conventions live in [AGENTS.md](AGENTS.md); this file is the per-symbol reference.

Last updated: 2026-06-15 (Phase 0).

---

## backend/config.py

### `class Settings(BaseSettings)`
App-wide configuration. Reads env vars prefixed `DEEPSELF_` and an optional `.env` file.

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| `base_dir` | `Path` | repo root | derived from `__file__` |
| `data_dir` | `Path` | `base_dir/data` | |
| `db_path` | `Path` | `data_dir/deepself.db` | |
| `pkm_dir` | `Path` | `data_dir/pkm` | generated markdown |
| `embedding_model` | `str` | `sentence-transformers/all-MiniLM-L6-v2` | |
| `embedding_dim` | `int` | `384` | must match model + `vec_entries` width |
| `host` | `str` | `127.0.0.1` | |
| `port` | `int` | `8080` | |
| `storage_secret` | `str` | `dev-deepself-change-me` | nicegui storage signing key |

- **`db_url` (property) → str** — `sqlite:///<db_path>` for SQLAlchemy.
- **`ensure_dirs() → None`** — create `data_dir` + `pkm_dir` if missing.

### `get_settings() → Settings`
`@lru_cache` singleton accessor. Use everywhere instead of constructing `Settings()`.

---

## backend/db/engine.py

- **`engine`** — module-level SQLAlchemy `Engine` (SQLite, `check_same_thread=False`).
- **`_on_connect(dbapi_conn, _record)`** — `@event.listens_for(engine, "connect")`: loads the
  sqlite-vec extension and runs `PRAGMA foreign_keys=ON` for every new connection.
- **`SessionLocal`** — `sessionmaker` (`autoflush=False`, `expire_on_commit=False`).
- **`get_session() → Iterator[Session]`** — generator dependency for FastAPI; yields a session,
  commits on success, rolls back on exception, always closes.
- **`ensure_vec_table() → None`** — idempotent `CREATE VIRTUAL TABLE IF NOT EXISTS vec_entries
  USING vec0(entry_id INTEGER PRIMARY KEY, embedding FLOAT[embedding_dim])`. Not managed by
  Alembic.

---

## backend/db/models.py

### Enums (`str, enum.Enum`)
- **`EntryType`** — `journal`, `idea`. *(grows per aspect)*
- **`SourceType`** — `manual`, `csv`, `xlsx`, `derived`.
- **`IdeaStatus`** — `new`, `reviewing`, `pursuing`, `archived`.

### `class Base(DeclarativeBase)`
SQLAlchemy 2.0 declarative base.

### `class Entry(Base)` — table `entries` (the spine)
| Column | Type | Notes |
|--------|------|-------|
| `id` | int PK | |
| `type` | `EntryType` | indexed |
| `source` | `SourceType` | default `manual` |
| `occurred_at` | datetime | when it happened; indexed; default now (UTC) |
| `created_at` | datetime | when recorded; default now (UTC) |
| `category` | str? | indexed; links to a Field of Focus (future) |
| `body_md` | text | free-text / markdown |
| `meta` | JSON? | loose type-specific fields |

Relationships: `tags` (m2m via `entry_tags`), `journal_detail` (1-1, cascade),
`idea_detail` (1-1, cascade).

### `class Tag(Base)` — `tags`
`id`, `name` (unique, indexed); `entries` back-ref.

### `class EntryTag(Base)` — `entry_tags`
Association rows: `entry_id`, `tag_id` (composite PK, `ondelete=CASCADE`).

### `class JournalDetail(Base)` — `journal_details`
`entry_id` PK/FK, `mood: str?`, `sentiment: float?`, `entry` back-ref.

### `class IdeaDetail(Base)` — `idea_details`
`entry_id` PK/FK, `status: IdeaStatus` (default `new`, indexed), `field_id: int?`
(placeholder; real FK added when the Field table exists), `entry` back-ref.

### `_utcnow() → datetime`
Timezone-aware UTC now; used as column default.

---

## backend/schemas/

### common.py
- **`ORMModel(BaseModel)`** — base for Read models; `from_attributes=True`.
- **`SearchHit(BaseModel, Generic[T])`** — `{distance: float, entry: T}` search result wrapper.
- **`split_tags(v) → list[str]`** — coerce a CSV cell `"a, b, c"` (or a real list) into a clean
  tag list; used as a pre-validator on CSV row schemas.

### journal.py
- **`JournalCreate`** — `body_md`, `occurred_at?`, `category?`, `mood?`, `tags: list[str]`.
- **`JournalRead(ORMModel)`** — `id, occurred_at, created_at, category, body_md, mood,
  sentiment, tags`. Validator maps `Tag` objects → names.
  - **`from_entry(e) → JournalRead`** (classmethod) — build from an ORM `Entry` (+ its
    `journal_detail`). Safe to return after session close.
- **`JournalCSVRow`** — one uploaded row: `occurred_at?`, `body_md`, `mood?`, `category?`,
  `tags` (split from string).

### idea.py
- **`IdeaCreate`** — `body_md`, `occurred_at?`, `category?`, `status: IdeaStatus=new`, `tags`.
- **`IdeaRead(ORMModel)`** — `id, occurred_at, created_at, category, body_md, status, tags`.
  - **`from_entry(e) → IdeaRead`** (classmethod) — build from ORM `Entry` (+ `idea_detail`).
- **`IdeaCSVRow`** — `occurred_at?`, `body_md`, `category?`, `status=new`, `tags`.

---

## backend/ingestion/

### manual.py
- **`get_or_create_tags(session, names) → list[Tag]`** — reuse existing tags by name, create
  missing; case-insensitive dedup, order-stable.
- **`create_journal(session, data: JournalCreate, source=manual) → Entry`** — build `Entry`
  (`type=journal`) + `JournalDetail` + tags, `flush()` (assigns id), return.
- **`create_idea(session, data: IdeaCreate, source=manual) → Entry`** — same for `type=idea`
  + `IdeaDetail`.

### registry.py
- **`AspectSpec`** (frozen dataclass) — `entry_type`, `csv_schema`, `create_schema`, `creator`.
- **`REGISTRY: dict[str, AspectSpec]`** — `"journal"`, `"idea"`. Add an aspect here.
- **`get_spec(aspect) → AspectSpec`** — lookup; raises `ValueError("unknown aspect ...")`.

### files.py
- **`ImportResult`** (dataclass) — `entries: list[Entry]`, `errors: list[dict]`,
  `ok` (property = count of entries).
- **`_read_table(content, filename) → (DataFrame, SourceType)`** — read `.csv` (pandas) or
  `.xlsx/.xls` (openpyxl); raises `ValueError` on unsupported type.
- **`import_file(session, aspect, content, filename) → ImportResult`** — per row: NaN→None,
  validate via `csv_schema`, map to `create_schema`, persist via `creator`; collects per-row
  errors (`row` = spreadsheet line number) without aborting.

---

## backend/enrichment/embeddings.py

- **`_model()`** — `@lru_cache(1)` lazy `SentenceTransformer` load; asserts model dim ==
  `settings.embedding_dim`.
- **`embed_text(text) → list[float]`** — one string → 384-float L2-normalized vector; blank →
  zero vector (no model call).
- **`embed_batch(texts) → list[list[float]]`** — batch encode; blanks map to zero vectors,
  positions preserved.

---

## backend/projections/

### vectors.py
- **`_source_text(entry) → str`** — text embedded = body + category + tag names.
- **`upsert_entry_vector(session, entry) → None`** — embed + store; delete-then-insert (vec0
  has no UPSERT).
- **`delete_entry_vector(session, entry_id) → None`** — remove the entry's vector.
- **`search(session, query, k=10, entry_type=None) → list[(entry_id, distance)]`** — KNN nearest
  first. With `entry_type`, overscans `k*4` then filters by `Entry.type`, trims to `k`.

### markdown.py
- **`entry_path(entry) → Path`** — `pkm_dir/<type>/<id:06d>.md`.
- **`_frontmatter(entry) → str`** — YAML block (id, type, source, timestamps, category, mood/
  status, tags).
- **`render_entry(entry) → str`** — frontmatter + body.
- **`write_entry(entry) → Path`** — mkdir + write file.
- **`delete_entry(entry) → None`** — unlink (missing-ok).

### __init__.py (orchestrator)
- **`project_entry(session, entry) → None`** — upsert vector + write markdown. Call after every
  create/update (post-flush, id set).
- **`remove_entry(session, entry) → None`** — delete vector + markdown file.

---

## backend/api/  (mounted under `/api`)

Each router has a private `_to_read` (delegates to `Read.from_entry`) and `_get_or_404`.

### journal.py — `/api/journal`
| Method | Path | Body/Query | Returns |
|--------|------|------------|---------|
| POST | `/journal` | `JournalCreate` | `JournalRead` (201) |
| GET | `/journal` | `limit≤200, offset` | `list[JournalRead]` |
| GET | `/journal/search` | `q, k≤50` | `list[SearchHit[JournalRead]]` |
| GET | `/journal/{id}` | | `JournalRead` (404 if missing) |
| DELETE | `/journal/{id}` | | 204 |
| POST | `/journal/upload` | multipart file | `{imported, errors}` |

`/search` is declared before `/{id}` so "search" isn't parsed as an id.

### idea.py — `/api/idea`
Same shape as journal, plus:
| GET | `/idea` | `status?, limit, offset` | `list[IdeaRead]` (status filter) |
| PATCH | `/idea/{id}/status` | `status` | `IdeaRead` |

### __init__.py
- **`api_router`** — `APIRouter(prefix="/api")` including the journal + idea routers.

---

## frontend/

### services.py (in-process layer for the UI)
`_session()` context manager (commit/rollback/close). Functions return plain pydantic
Read models (session-safe):
- Journal: `create_journal(body_md, mood, tags_csv)`, `list_journals(limit=100)`,
  `search_journals(q, k=10) → list[(JournalRead, distance)]`, `delete_journal(id)`,
  `import_journal(content, filename) → {imported, errors}`.
- Idea: `create_idea(body_md, tags_csv)`, `list_ideas(status=None, limit=100)`,
  `set_idea_status(id, status)`, `delete_idea(id)`, `import_idea(content, filename)`.

### components/layout.py
- **`page_header(active)`** — top nav bar (Home / Journal / Ideas), highlights `active`.

### pages/
- **journal.py — `@ui.page("/journal")`** — add form, csv/xlsx upload, semantic search box,
  recent feed (with delete). Uses `@ui.refreshable` blocks.
- **idea.py — `@ui.page("/idea")`** — quick capture, upload, review queue with status filter +
  per-card status dropdown + delete.
- **__init__.py** — imports the page modules (registers routes) and defines
  **`@ui.page("/")`** home.

---

## main.py

- **`_run_migrations()`** — `alembic upgrade head` programmatically via `alembic.ini`.
- **`lifespan(app)`** — async context manager: `ensure_dirs()` → migrations → `ensure_vec_table()`.
- **`app`** — `FastAPI(title="deepself", lifespan=...)`, includes `api_router`, imports
  `frontend.pages`, then `ui.run_with(app, storage_secret=..., title="deepself")`.

Launch: `.venv/bin/uvicorn main:app --reload`.

---

## tests/

- **conftest.py** — sets `DEEPSELF_*` env to a temp dir *before* importing backend; session-wide
  `_schema` fixture (`create_all` + `ensure_vec_table`); function-scoped `session` fixture.
- **test_ingestion.py** — manual create (entry/detail/tags + case-insensitive dedup), idea
  default status, tag reuse, csv good/bad rows, unknown-aspect error.
- **test_projections.py** — markdown written with frontmatter, vector search ranks relevant
  entry first, remove clears markdown. (Loads the real embedding model.)
