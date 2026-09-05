# Architecture — SIH-26154 Multi-Format Content Converter

## System Diagram

```
┌────────────────────────┐         HTTP/JSON          ┌──────────────────────────┐
│  React 18 + Tailwind   │  ───────────────────────▶  │   FastAPI (uvicorn)      │
│  Single index.html     │  ◀───────────────────────  │   main.py                │
│  (browser, no build)   │      polling every 2 s     │  ┌────────────────────┐  │
└────────────────────────┘                            │  │ /sources, /jobs    │  │
                                                     │  │ /jobs/{id}/retry   │  │
                                                     │  └────────────────────┘  │
                                                     │            │             │
                                                     │            ▼             │
                                                     │  ┌────────────────────┐  │
                                                     │  │ asyncio.gather     │  │
                                                     │  │ 7 generators       │  │
                                                     │  └────────────────────┘  │
                                                     │      │       │           │
                                          ┌──────────┴───────┐   │   ┌────────┴────────┐
                                          │ SQLite (local)   │   │   │ MiniMax API     │
                                          │ sources, jobs,   │   │   │ (json_schema,   │
                                          │ artefacts        │   │   │  retry/backoff) │
                                          └──────────────────┘   │   └─────────────────┘
                                                                │
                                                       Pydantic v2 schemas
                                                       validate every artefact
```

## Data Flow

1. **Source submit** — `POST /sources` with `raw_text`. Server strips control characters and collapses whitespace → stores `raw_text` + `normalized_text`. Returns `source_id`.
2. **Job create** — `POST /jobs` with `source_id`, `output_types[]`, `tone`, `audience`. Server validates source, creates a `Job` row with status `pending`, then schedules `asyncio.create_task(_run_job(...))`.
3. **Parallel generation** — `_run_job` flips status to `running` and calls `asyncio.gather(*[_run_one(t, ...) for t in output_types])`. Each `_run_one` invokes its generator (`generate_advisory`, `generate_infographic`, …), which builds a focused prompt + JSON Schema and calls `ai_client.generate_structured(...)`.
4. **Persistence + status** — every result lands as an `Artefact` row: success → `content_json`; failure → `error_msg` + `raw_output`. Job status is recomputed and `completed_at` is set.
5. **Polling** — the frontend polls `GET /jobs/{id}` every 2 s until status is `completed`, `partial_failure`, or `failed`, then renders the artefact cards.
6. **Retry** — `POST /jobs/{id}/retry` re-runs only artefacts with non-null `error_msg` and recomputes the job status.

## Job State Machine

```
        ┌─────────┐  create    ┌─────────┐  gather done   ┌────────────┐
  →  →  │ pending │ ─────────▶ │ running │ ──────────────▶ │ completed  │
        └─────────┘            └─────────┘                 └────────────┘
                                       │ all failed              ▲ some ok
                                       ▼                         │
                                 ┌──────────┐         ┌─────────────────────┐
                                 │  failed  │         │  partial_failure    │
                                 └──────────┘         └─────────────────────┘
                                          retry ──────────────────┘
```

Transitions are explicit in `main.py::_run_job`. Retry path uses `POST /jobs/{id}/retry` and rewrites only `error_msg IS NOT NULL` rows.

## Why SQLite

- **Zero-config** — single file (`sih_demo.db`) created on first boot, no server, no credentials.
- **Hackathon-fit** — ideal for a local demo: fast, reliable, and easy to inspect.
- **Sync SQLAlchemy 2.0** — runs inside async FastAPI handlers without adding `aiosqlite` to the dependency budget. Async DB is unnecessary when the bottleneck is the LLM call, not the database.

## Why Pydantic Validation

- **Defense in depth** — the LLM is asked to return JSON in a strict `json_schema`, but we still validate with Pydantic v2 before persisting; malformed AI output is caught, retried (max 2), then stored as `raw_output + error_msg` rather than corrupting the artefact table.
- **Stable API contracts** — request/response models (`SourceCreate`, `JobCreate`, `JobOut`, `ArtefactOut`) prevent the frontend from breaking on internal changes.
- **Generated JSON Schema** — `Pydantic.model_json_schema()` is reused as the prompt's schema, so the model is asked for exactly the shape we validate against.

## Security

- **Redacted logging** — only `status_code`, `model`, and `tokens_used` are ever logged. Source text and the API key are excluded from all log calls.
- **Env-driven secrets** — `MINIMAX_API_KEY` read via `pydantic-settings`; never committed, never logged.
- **No hardcoded keys** — the `.env` path is supported but `.env` itself is not in version control.
- **Local-only data** — sources and artefacts stay in the local SQLite file; nothing is uploaded to a remote store by the platform itself.

## Scalability — Add a New Output Type in 3 Steps

1. Add a generator function + JSON Schema in `backend/generators.py` and register it in the `GENERATORS` dict.
2. Add a label/checkbox in `frontend/index.html` (and, if desired, a `FormattedContent` branch for nicer rendering).
3. (Optional) Extend the Pydantic output model in `backend/models.py` if the new type needs stronger validation.

No router or DB migration changes are required — the schema in `artefacts` already stores arbitrary JSON content keyed by `output_type`.