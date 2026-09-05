# Multi-Format Threat-Intel Converter

> My first end-to-end project. Built for **Smart India Hackathon 2026** (problem statement **SIH-26154**).

One source of information → many communication artefacts. Paste a CERT-In advisory, an incident report, a research paper, or a free-form prompt, and the platform turns it into structured deliverables ready to publish: **LinkedIn post, Twitter/X thread, security advisory, infographic content, executive summary, presentation deck, or full video package** — all from the same source, in parallel, validated against strict schemas.

---

## ✨ What it does

```
   ┌──────────┐     ┌────────────┐     ┌──────────────┐
   │  Source  │ ──▶ │  Job (N    │ ──▶ │  Artefacts   │
   │  (paste) │     │  outputs)  │     │  (one per    │
   └──────────┘     └────────────┘     │  output type)│
                                       └──────────────┘
   LinkedIn  ·  Twitter  ·  Advisory  ·  Infographic  ·  Exec Summary  ·  Presentation  ·  Video Package
```

- **One paste, seven outputs.** All generated in parallel via `asyncio.gather`.
- **Strict Pydantic v2 schemas** for every output — malformed model responses are caught, retried, then stored as raw + error so no work is lost.
- **Full audit trail** — every artefact stores `source_id`, `job_id`, `params`, `model_id`, timestamp.
- **Redacted logging** — only `status_code`, `model`, and `tokens_used` are ever logged. Source text and the API key never appear in logs.
- **Resilient** — partial failures are saved; one click on **Retry failed** re-runs only the broken ones.
- **Live AI** — real **MiniMax M3** via OpenRouter, with a deterministic offline mock fallback when no key is set.

---

## 🧱 Tech stack

| Layer | Choice |
|---|---|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2.0, Pydantic v2 |
| Database | SQLite (local file, no setup) |
| AI | MiniMax M3 via OpenRouter, `response_format: json_object`, tenacity retries |
| Frontend | React 18 (plain `createElement`, no build step), Tailwind CSS |
| Optional tunnel | Cloudflare `cloudflared` quick tunnel for a public URL |

**No Docker, no cloud account required, one-command boot.** Total codebase: **~1,500 lines**.

---

## 🚀 Run it locally

### Prerequisites
- Python 3.12+
- A free OpenRouter API key (https://openrouter.ai) — or any MiniMax-compatible endpoint

### Backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env             # then edit .env and add your MINIMAX_API_KEY
uvicorn main:app --port 8000 --reload
```

### Frontend
The frontend is a single static HTML file with vendored React/Tailwind. Two ways to serve it:

```bash
# Option A — open the file directly
open frontend/index.html

# Option B — serve over http (recommended; `file://` blocks fetch)
cd frontend && python3 -m http.server 3000
# then open http://localhost:3000
```

### One-command full stack
A `start.sh` script boots backend + sidecar + frontend + an optional Cloudflare tunnel:

```bash
./start.sh     # boot
./stop.sh      # kill all three ports
```

---

## 🌐 Public demo URL

Want to show the demo from your laptop? `./start.sh` will print a fresh `https://*.trycloudflare.com` URL — share it with anyone, no deployment needed.

---

## 📁 Project layout

```
.
├── backend/
│   ├── main.py            FastAPI app, endpoints, lifespan
│   ├── config.py          pydantic-settings env loader
│   ├── database.py        SQLite engine + Base + get_db()
│   ├── models.py          SQLAlchemy tables + Pydantic v2 schemas
│   ├── ai_client.py       MiniMax HTTP client with tenacity retries
│   ├── generators.py      7 async generators (one per output type)
│   ├── fake_server.py     Demo failure sidecar (always returns 500)
│   ├── prep_demo.py       Helper that creates a deterministic failure job
│   └── requirements.txt
├── frontend/
│   ├── index.html         React 18 + Tailwind, plain createElement
│   └── vendor/            React, ReactDOM, Tailwind (no CDN needed)
├── serve.py               Single-origin static + API proxy
├── start.sh               Boot everything
├── stop.sh                Kill everything
├── .env.example           Template for backend/.env
├── README.md
├── ARCHITECTURE.md
├── DEMO_SCRIPT.md
└── TECH_PRESENTATION.md
```

---

## 🛠 API

| Method | Path | Purpose |
|---|---|---|
| `GET`  | `/`                                  | Health / index |
| `POST` | `/sources`                           | Create + normalize a source |
| `GET`  | `/sources/{id}`                      | Fetch a source |
| `POST` | `/jobs`                              | Create a transformation job (multi-format) |
| `GET`  | `/jobs/{id}`                         | Poll job + all artefacts |
| `POST` | `/jobs/{id}/retry`                   | Re-run only failed artefacts |

Interactive docs at `http://localhost:8000/docs`.

---

## 🐛 Troubleshooting

- **`MiniMax fails, verify API key and rate limits`** — check `cat backend/.env`; the free M3 tier on OpenRouter is throttled (~1 in 3 requests get 429s); the client retries twice with exponential back-off.
- **`fetch` blocked in browser** — open `frontend/index.html` via `python3 -m http.server` instead of double-clicking. `file://` blocks cross-origin fetches.
- **No API key set** — backend boots in deterministic mock mode; the UI is fully testable offline.

---

## 📜 License

MIT — fork it, learn from it, build on it.
