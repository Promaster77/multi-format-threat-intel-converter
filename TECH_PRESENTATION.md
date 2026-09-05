# Tech Presentation — SIH-26154 (5 slides, ~2.5 min)

> Speaker pacing target: **~30 s per slide**. Total ~2:30.
> Replace `[YOUR TEAM NAME]` on slide 1 before exporting.

---

## Slide 1 — Title & Problem

**Title:** SIH-26154 — Multi-Format Content Converter
**Subtitle:** Team [YOUR TEAM NAME] · Smart India Hackathon 2026

**Body**
- Raw threat intel → 7 communication formats manually
- Slow, inconsistent, expertise-heavy
- Need: one source, many compliant outputs

**Speaker (30 s)**
"Every SOC, CERT, and intel team we spoke to spends hours turning a single advisory into a LinkedIn post, an exec briefing, a tweet thread, a slide deck, and more — and they do it differently each time. We're going to show you a platform that does all of that from one source, in seconds, with full audit trail."

---

## Slide 2 — Architecture

**Title:** Architecture

**Body**
- React 18 + Tailwind (single HTML, no build step) →
- FastAPI (Python 3.12, async handlers) →
- SQLite (local) + MiniMax API
- Pipeline: **Normalize → asyncio.gather generators → Pydantic v2 validation → persist**
- Job states: `pending → running → completed | partial_failure | failed`

**Speaker (30 s)**
"Frontend is a single React file — open it in a browser, no Node build. Backend is FastAPI. The user submits a source; we normalise it, fan out to the selected generators in parallel with asyncio.gather, validate every response against a strict Pydantic schema, and persist each artefact. Job state moves through pending, running, and lands on one of three terminal states."

---

## Slide 3 — Key Features

**Title:** Key Features

**Body**
- **One source, seven outputs** generated simultaneously
- **Strict Pydantic v2 validation** — malformed AI output is caught, retried, then saved as raw + error
- **Full provenance** — every artefact stores `source_id`, `job_id`, `model_id`, params, timestamp
- **Resilient** — partial failures are saved, not lost; one-click retry on failed artefacts
- **Redacted logging** — source text and API keys never appear in logs (status code, model, tokens only)

**Speaker (30 s)**
"What makes this production-shaped, not just a demo: every output is validated against a strict schema; if the model misbehaves we retry and otherwise save the raw response and the error, so we never lose work. Every artefact carries full provenance. And our logs are redacted by design — the API key and the source text never leave the app, only status codes and token counts do."

---

## Slide 4 — Demo Highlights

**Title:** Demo Highlights

**Body**
- Paste a CERT-In advisory (Load Sample prefills it)
- Select Advisory + Executive Summary + LinkedIn Post
- One **Run Conversion** → real-time status polling (`pending → running → …`)
- Formatted outputs: structured advisory, exec briefing, social post — not raw JSON
- Graceful failure: red badge + **Retry this artefact** button → status moves to `completed` / `partial_failure`

**Speaker (30 s)**
"Here's the flow. We paste a CERT-In advisory, pick three formats, hit run. The frontend polls every two seconds. Each artefact card opens formatted — bullets, lists, hashtags — not a JSON blob. If anything fails, we get a red badge and a retry button; one click, and we either finish or we land on partial failure with everything that did succeed preserved."

---

## Slide 5 — Impact & Future

**Title:** Impact & Future

**Body**
- **Impact**
  - Hours of manual rewriting → seconds
  - Consistency across all formats from one normalised source
  - Audit trail satisfies compliance and post-incident review
- **Scalability & Future**
  - New format = new generator module + schema (no router / DB migration)
  - Future: multi-tenant auth, on-premise LLM deployment, vector recall over prior advisories

**Speaker (30 s)**
"From hours to seconds, with one consistent voice across every channel. Adding a new output type is a one-file change — write a generator, drop in the schema, register it. From here we go to multi-tenant auth, on-prem LLM deployment for classified environments, and retrieval over prior advisories so each new artefact inherits institutional voice."

---

## Export checklist
- [ ] Replace `[YOUR TEAM NAME]` on slide 1
- [ ] Add the team logo top-right (optional)
- [ ] Export as PDF **and** PPTX for the submission portal
- [ ] Trim speaker track to ≤ 2:30 before recording the voice-over