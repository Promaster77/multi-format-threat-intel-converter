# Demo Script — SIH-26154 (2 minutes)

Record the screen at **1280×720**, browser window only. No microphone narration is required — on-screen captions are enough — but speak over the steps if audio is available. Total runtime target: **120 seconds**.

---

### 0:00 – 0:08  · Cold open
- Screen-record the **header**: "SIH-26154 | Multi-Format Content Converter" in blue.
- Voice-over / caption: *"This is SIH-26154. We convert raw threat intel into 7 communication formats."*

### 0:08 – 0:18  · Load the sample
- Click **Load Sample** in the top-right.
- Cursor highlights the populated **Source Text** area — a realistic CERT-In RCE advisory (CVE-2026-10421, XYZ-VPN).

### 0:18 – 0:28  · Pick the deliverables
- In the **Outputs** panel, tick **Advisory**, **Executive Summary**, **LinkedIn Post**. The header updates to "(3 selected)".
- Briefly sweep the **Parameters** panel: Audience = technical, Tone = urgent, Objective = alert.

### 0:28 – 0:40  · Run
- Click the blue **Run Conversion** button.
- Show the **Job status badge** flip from grey `pending` → blue `running` while the frontend polls `GET /jobs/{id}` every 2 s.

### 0:40 – 1:10  · Reveal the three artefacts
- Highlight each card in turn:
  1. **Advisory** — Severity, Affected Systems, IOCs, Action items rendered as a clean list (not raw JSON).
  2. **Executive Summary** — Risk level, Business impact, Recommendations, Decision needed.
  3. **LinkedIn Post** — Hook, body, hashtags, CTA.
- Demonstrate the **Copy JSON** button on one card (small "Copied" toast optional).

### 1:10 – 1:30  · The audit-trail pitch
- Cut to the backend terminal running `uvicorn` and show the redacted log lines (`status=200 model=… tokens=…` — **no prompt text, no API key**).
- Open `http://localhost:8000/docs` to show the FastAPI schema for `POST /jobs` and `GET /jobs/{id}`.
- Voice-over / caption: *"All from the same source, validated, with full audit trail."*

### 1:30 – 1:50  · Failure & retry
- Trigger a failure (e.g. temporarily unset `MINIMAX_API_KEY` and rerun, or point `MINIMAX_API_URL` at a 500-returning endpoint).
- Show the **red `failed` badge** on one artefact card and the **Retry this artefact** button.
- Click it — status flips back to `running`, and on completion the job badge becomes **yellow `partial_failure`** (or `completed` if everything succeeds on retry).
- End on the green/yellow badge so the resilience story is visible.

### 1:50 – 2:00  · Close
- Return to the header. Caption: *"One source. Seven formats. Zero manual rewriting."*
- Fade out.

---

## Recording tips
- **Don't** show `.env` contents or the API key.
- **Do** show one `uvicorn` log line so the redacted-logging story is visible.
- Keep the cursor visible and slow — this is a 2-minute demo, not a screencast tutorial.
- Total under 120 s; trim any silent gaps before exporting.