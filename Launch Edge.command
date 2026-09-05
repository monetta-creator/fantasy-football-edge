#!/usr/bin/env bash
# Double-click in Finder to launch the app. Starts backend (:8000) + frontend (:3000), opens the browser.
# Close this Terminal window or press Ctrl+C to stop everything.
cd "$(dirname "$0")" || exit 1
export PATH="/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin:$PATH"
LOG=data/logs; mkdir -p "$LOG"

if ! curl -s localhost:8000/api/health >/dev/null 2>&1 && ! curl -s -o /dev/null localhost:3000 2>/dev/null; then
  echo "▶ Edge — starting…"
else
  echo "▶ Edge is already running. Opening the browser."
  open "http://localhost:3000/draft"
  exit 0
fi

# One-time setup if needed
if [ ! -f .env ]; then cp .env.example .env; echo "Created .env from .env.example (add OPENROUTER_API_KEY there for LLM features)."; fi
if [ ! -x backend/.venv/bin/uvicorn ]; then
  echo "Installing Python deps (first run)…"
  (cd backend && uv venv --python 3.12 .venv >/dev/null && uv pip install -q -e ".[dev]") || { echo "Python setup failed. Is uv installed? (brew install uv)"; read -r -p "Press Enter to close"; exit 1; }
fi
if [ ! -d frontend/node_modules ]; then
  echo "Installing frontend deps (first run)…"
  (cd frontend && npm install --silent) || { echo "npm install failed. Is Node installed? (brew install node)"; read -r -p "Press Enter to close"; exit 1; }
fi

cleanup() {
  trap - INT TERM EXIT
  echo; echo "Stopping Edge…"
  pkill -P $$ 2>/dev/null
  pkill -f "uvicorn ffedge.api:app" 2>/dev/null; pkill -f "next dev" 2>/dev/null; pkill -f "next-server" 2>/dev/null
  for i in 1 2 3 4 5; do pgrep -f "uvicorn ffedge.api:app|next dev|next-server" >/dev/null || break; sleep 1; done
  pkill -9 -f "uvicorn ffedge.api:app" 2>/dev/null; pkill -9 -f "next dev" 2>/dev/null; pkill -9 -f "next-server" 2>/dev/null
  echo "Stopped."
  exit 0
}
trap cleanup INT TERM HUP EXIT

(cd backend && exec .venv/bin/uvicorn ffedge.api:app --host 127.0.0.1 --port 8000) >"$LOG/backend.log" 2>&1 &
BACK=$!
(cd frontend && exec npm run dev -- -p 3000) >"$LOG/frontend.log" 2>&1 &
FRONT=$!

echo -n "Loading projections"
for i in $(seq 1 60); do
  if curl -s localhost:8000/api/health 2>/dev/null | grep -q '"ready":true' && curl -s -o /dev/null localhost:3000 2>/dev/null; then echo; break; fi
  echo -n "."; sleep 1
done
if ! curl -s localhost:8000/api/health 2>/dev/null | grep -q '"ready":true'; then
  echo; echo "Backend did not come up. Last log lines:"; tail -20 "$LOG/backend.log"; read -r -p "Press Enter to close"; exit 1
fi
open "http://localhost:3000/draft"
echo "✓ Edge is running at http://localhost:3000/draft"
echo "  Logs: $LOG/backend.log, $LOG/frontend.log"
echo "  Leave this window open. Ctrl+C or close it to stop."
echo
tail -f "$LOG/backend.log" &
wait "$BACK"
