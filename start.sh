#!/usr/bin/env bash
# Boot the full SIH-26154 demo + open a fresh Cloudflare quick tunnel.
# Usage: ./start.sh
# Result: prints a new https://*.trycloudflare.com URL when ready.
#
# Stop everything with: ./stop.sh   (or: lsof -ti tcp:8000,8080,9000 | xargs kill -9)

set -euo pipefail
cd "$(dirname "$0")"

CFD="$(pwd)/cloudflared"
LOG_DIR="$(pwd)/.run"
mkdir -p "$LOG_DIR"

cleanup_old() {
  echo "→ killing anything already on :8000 / :8080 / :9000"
  for p in 8000 8080 9000; do
    pid=$(lsof -ti tcp:$p -sTCP:LISTEN 2>/dev/null || true)
    [ -n "$pid" ] && kill -9 $pid 2>/dev/null || true
  done
  sleep 1
}

cleanup_old

echo "→ starting backend (FastAPI) on :8000"
cd backend
[ -d .venv ] || python3 -m venv .venv
source .venv/bin/activate
pip install -q -r requirements.txt
rm -f sih_demo.db
uvicorn main:app --port 8000 --log-level info > "$LOG_DIR/backend.log" 2>&1 &
echo "  pid=$!  log=$LOG_DIR/backend.log"

echo "→ starting demo sidecar (always-500) on :9000"
uvicorn fake_server:app --port 9000 --log-level warning > "$LOG_DIR/sidecar.log" 2>&1 &
echo "  pid=$!  log=$LOG_DIR/sidecar.log"
cd ..

echo "→ starting single-origin frontend + API proxy on :8080"
python3 serve.py > "$LOG_DIR/serve.log" 2>&1 &
echo "  pid=$!  log=$LOG_DIR/serve.log"

echo "→ waiting for backend health"
for i in 1 2 3 4 5 6 7 8 9 10; do
  if curl -s -o /dev/null --max-time 1 http://localhost:8000/; then
    echo "  backend up"
    break
  fi
  sleep 1
done

if [ ! -x "$CFD" ]; then
  echo "✗ cloudflared not found at $CFD"
  echo "  re-download with:"
  echo "  curl -sL -o cloudflared https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-darwin-amd64.tgz && tar -xzf cloudflared.tgz && rm cloudflared.tgz && chmod +x cloudflared"
  exit 1
fi

echo "→ opening Cloudflare quick tunnel"
echo
echo "  ┌─────────────────────────────────────────────────────────────────┐"
echo "  │  waiting for tunnel URL...                                       │"
echo "  │  (look below — copy the https://*.trycloudflare.com line)        │"
echo "  └─────────────────────────────────────────────────────────────────┘"
echo
"$CFD" tunnel --url http://localhost:8080 --no-autoupdate 2>&1 | tee "$LOG_DIR/tunnel.log"