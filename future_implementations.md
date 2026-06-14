# deepself — Future Implementations (Full Scaffold Plan)

> Status: **Phase 0 (MVP) built; remaining phases planned.** This records the full 8-aspect
> architecture so the vertical-slice MVP can fan out into it later. You direct whether to follow
> or change each part. Items below are tagged ✅ done / ⬜ planned.
>
> Last updated: 2026-06-15

## Role & boundary

- **deepself** = data ingestion + storage layer for personal life data.
- **AOSSBrain** (separate app) = agentic reasoning over that data.
- Decision: deepself uses LLM/NLP **ingestion-side only** (write-time enrichment: embeddings, auto-tag, summarize, entity extraction). Querying / chat / agentic reasoning is AOSSBrain's job, consuming deepself's `/api/*` + vector index.

## Core architectural decisions

| Area | Decision | Why |
|------|----------|-----|
| Process model | Single FastAPI process; nicegui mounted via `ui.run_with(fastapi_app)` | One server. `/api/*` for AOSSBrain, nicegui pages for UI. nicegui is itself FastAPI-based, so don't run two. |
| Source of truth | **SQLite** | Single authoritative store. |
| Vectors | **sqlite-vec** (vectors inside the same SQLite file) | One store, one backup, no extra process. |
| PKM | Markdown wiki under `data/pkm/`, **derived** from SQLite | Regenerable projection, never authoritative → no 3-way sync drift. |
| ORM | SQLAlchemy 2.0 (typed `Mapped[]`/`DeclarativeBase`) + separate Pydantic schemas | Mature docs/community vs newer SQLModel. Two classes per table (DB model + API schema) accepted as the tradeoff. |
| Migrations | Alembic | Schema evolves across 8 aspects. |
| Embeddings | `sentence-transformers` (local HF, e.g. all-MiniLM-L6-v2) | Local, free, offline. |
| Optional LLM | LMStudio (primary) / ollama (option) / Claude\|GPT\|Gemini (cloud) via adapter | Swappable enrichment backend; off by default for privacy. |
| Ingestion | Manual entry + csv/xlsx upload, both → pydantic/pandera validation → Entry spine | One validation path, two input modes. |

## The Entry spine (key idea)

All 8 aspects share a timestamped, tagged, categorized, free-text + structured shape. So one core table; specialized tables FK to it.

```
Entry
  id            PK
  type          enum (journal | idea | routine_log | finance | fitness | food |
                      activity | purchase | learning | build | creation | calendar | note)
  source        enum (manual | csv | xlsx | derived)
  occurred_at   datetime   # when it happened
  created_at    datetime   # when recorded
  category      str | null # links to Field of Focus
  body_md       text       # free-text / markdown
  meta          json       # type-specific loose fields

Tag (id, name)            # many-to-many with Entry via EntryTag
```

Every Entry → markdown projection + embedding, uniformly. Specialized tables below hang typed columns off an Entry.

## Aspect-by-aspect scaffold

### 1. Daily Journal
- `Entry(type=journal)` + optional `JournalDetail(entry_id, mood, sentiment_score)`.
- Enrichment: sentiment + auto-tags + summary at write-time. *(sentiment column exists but not yet populated — Phase 5)*
- ✅ **Built (Phase 0).**

### 2. Routines
- `Routine(id, name, cadence[daily|weekly|monthly|annual], schedule_spec, field_id, active)`
- `Entry(type=routine_log)` + `RoutineLog(entry_id, routine_id, completed, notes)`
- Generates expected occurrences; logs completion.

### 3. Important data input (structured records)
All FK an `Entry` for body/tags; typed columns live in their table.
- `FinanceRecord(entry_id, direction[income|expense], amount, currency, account, payee, category)`
- `FitnessRecord(entry_id, metric, value, unit)`
- `FoodLog(entry_id, item, meal, calories, protein, carbs, fat, qty, unit)`
- `ActivityLog(entry_id, activity, duration_min)`
- `PurchaseLog(entry_id, item, is_consumable, cost, qty, vendor)`
- Primary csv/xlsx upload targets — each gets a schema in the import registry.

### 4. Fields of Focus
- `Field(id, name, description, priority, status[active|paused|done], parent_id)`
- Referenced by `Entry.category` and `Routine.field_id`. The categorization backbone.

### 5. Idea Dumps
- `Entry(type=idea)` + `IdeaDetail(entry_id, status[new|reviewing|pursuing|archived], field_id)`
- Quick capture; review queue; promote to a Field/project.
- ✅ **Built (Phase 0).**

### 6. Personal Knowledge Monitoring (PKM / self-wiki)
- `WikiPage(id, slug, title, body_md, auto_generated)` + `WikiLink(src, dst)` for backlinks.
- `data/pkm/` markdown projection generated from Entries + WikiPages.
- Grows automatically: entities/tags extracted at ingestion become wiki nodes.

### 7. Calendar
- `Entry(type=calendar)` + `CalendarEvent(entry_id, title, start, end, all_day, kind[event|task|activity])`
- `Task(entry_id, status[todo|doing|done], due_at, priority)`
- nicegui calendar view; tasks/events/activities plotted.

### 8. Productivity (Daily Learning / Builds / Creation)
- `Entry(type in [learning|build|creation])` + `ProductivityLog(entry_id, kind, artifact_url, duration_min)`
- Daily logging + streaks/rollups.

## Proposed folder layout

Single process: nicegui mounts on FastAPI. `backend/` = server-side, `frontend/` = nicegui UI, root `main.py` = entrypoint wiring both. Run from repo root.

```
deepself_app/
  main.py                  # entrypoint: build FastAPI app + nicegui mount + lifespan
  backend/
    config.py              # settings (pydantic-settings, .env)
    db/
      engine.py            # SQLAlchemy engine, load sqlite-vec extension
      models.py            # SQLAlchemy 2.0 models: Entry spine + specialized tables
      migrations/          # alembic
    schemas/               # pydantic IO models + csv import schemas
    ingestion/
      manual.py            # manual entry -> validate -> persist
      files.py             # csv/xlsx -> validate -> persist
      registry.py          # per-type import schema registry
    enrichment/
      embeddings.py        # sentence-transformers
      llm.py               # LMStudio/ollama/cloud adapter (off by default)
      tagging.py           # auto-tag, sentiment, entity extraction
    projections/
      markdown.py          # Entry/WikiPage -> data/pkm/*.md
      vectors.py           # Entry -> sqlite-vec upsert
    api/                   # FastAPI routers, one per aspect
    aspects/               # domain logic per aspect
  frontend/
    pages/                 # nicegui pages, one per aspect
    components/            # shared nicegui widgets
  data/
    deepself.db            # SQLite (incl. sqlite-vec vectors)
    pkm/                   # generated markdown wiki
  tests/
  requirements.txt
  CLAUDE.md
```

## Phasing

- ✅ **Phase 0 (MVP / vertical slice):** Entry spine + storage + Journal + Idea Dumps, end-to-end: manual + csv/xlsx ingestion, embeddings → sqlite-vec, markdown projection, FastAPI routes, nicegui pages, tests, docs. **Done 2026-06-15.**
- ⬜ **Phase 1:** Fields of Focus (categorization backbone) + PKM wiki generation.
- ⬜ **Phase 2:** Important data input (finance/fitness/food/activity/purchase) — heavy csv schemas.
- ⬜ **Phase 3:** Calendar + Tasks.
- ⬜ **Phase 4:** Routines + Productivity logging + rollups/streaks.
- ⬜ **Phase 5:** Optional LLM enrichment adapters (LMStudio/ollama/cloud) + AOSSBrain-facing API hardening.
  - Not yet built but deferred from Phase 0: journal **sentiment** enrichment (column exists, unused), auth/multi-user, `.gitignore` for `data/`, post-commit projection ordering.

## Open questions to revisit
- Auth/multi-user? (assumed single-user local for now)
- AOSSBrain ↔ deepself API contract (REST now; consider events/webhooks later)
- Backup/export strategy (SQLite file + pkm/ dir)
