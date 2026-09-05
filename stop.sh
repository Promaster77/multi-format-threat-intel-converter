#!/usr/bin/env bash
# Stop everything started.sh launched.
set -euo pipefail

echo "→ killing :8000 / :8080 / :9000"
for p in 8000 8080 9000; do
  pid=$(lsof -ti tcp:$p -sTCP:LISTEN 2>/dev/null || true)
  [ -n "$pid" ] && kill -9 $pid 2>/dev/null && echo "  killed :$p (pid $pid)" || echo "  :$p free"
done

# Also kill the cloudflared process if it's still around.
pkill -f "cloudflared tunnel --url" 2>/dev/null && echo "  killed cloudflared" || true

echo "done."