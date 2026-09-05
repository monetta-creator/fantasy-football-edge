#!/usr/bin/env bash
# Starts backend (FastAPI :8000) and frontend (Next.js :3000) bound to all interfaces so a phone on the same Wi-Fi can connect.
set -euo pipefail
cd "$(dirname "$0")"
IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || echo "localhost")
echo "Backend  -> http://$IP:8000/api/health"
echo "Frontend -> http://$IP:3000/draft   (open this on your phone)"
(cd backend && .venv/bin/uvicorn ffedge.api:app --host 0.0.0.0 --port 8000) &
BACK=$!
trap 'kill $BACK 2>/dev/null' EXIT
cd frontend && npm run dev -- -H 0.0.0.0 -p 3000
