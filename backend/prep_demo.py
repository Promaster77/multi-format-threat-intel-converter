"""One-shot helper that creates a deterministic failure job for demo recording.

Usage:
    python prep_demo.py              # uses localhost:8000
    API=http://myhost:8000 python prep_demo.py

Creates a job with two outputs: 'advisory' (succeeds) and 'linkedin'
(forced to fail via the always-500 sidecar on :9000). The job lands in
state 'partial_failure' with one red-badged artefact ready for the
Retry button to be recorded.

Sidecar must be running on :9000 (fake_server.py).
"""
from __future__ import annotations

import json
import os
import time
import urllib.request

API = os.getenv("API", "http://localhost:8000")
SOURCE_TEXT = (
    "CVE-2026-10421: critical unauth RCE in XYZ-VPN SSL-VPN 9.2-9.7. "
    "Patch 9.7.1 in 24h. IOCs: 198.51.100.7, 203.0.113.42, "
    "/admin/sslvpn_tmp_login. Reference: vendor advisory V-2026-10421."
)


def post(path: str, body: dict) -> dict:
    req = urllib.request.Request(
        f"{API}{path}",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def get(path: str) -> dict:
    with urllib.request.urlopen(f"{API}{path}", timeout=30) as r:
        return json.loads(r.read())


def main() -> None:
    print(f"→ POST {API}/sources")
    src = post("/sources", {"raw_text": SOURCE_TEXT})
    sid = src["source_id"]
    print(f"  source_id={sid}")

    print(f"→ POST {API}/jobs (linkedin forced to fail)")
    j = post("/jobs", {
        "source_id": sid,
        "output_types": ["advisory", "linkedin"],
        "tone": "urgent",
        "audience": "technical",
        "force_failure_for": ["linkedin"],
    })
    jid = j["job_id"]
    print(f"  job_id={jid}")

    print("→ polling until terminal (max 30 s)...")
    for _ in range(15):
        time.sleep(2)
        job = get(f"/jobs/{jid}")
        print(f"  status={job['status']}  artefacts={[(a['output_type'],a['status']) for a in job['artefacts']]}")
        if job["status"] in ("completed", "failed", "partial_failure"):
            print("\nDEMO STATE READY.")
            print(f"Open http://localhost:3000 and either:")
            print(f"  • paste job_id={jid} into the URL bar, OR")
            print(f"  • re-submit this source (the source_id is {sid}).")
            print("Then click 'Retry failed' to show the recovery path.")
            return
    print("Timed out waiting for terminal state.")


if __name__ == "__main__":
    main()