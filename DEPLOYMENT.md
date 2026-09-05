# Deployment plan (parked 2026-09-05; revisit after the draft)

Status: not started. The app runs locally via `Launch Edge.command`. Owner has a Vercel Pro account and the repo
is already visible to Vercel (`monetta-creator/fantasy-football-edge`, detected as `backend · fastapi` and `frontend · nextjs`).

## Decision so far

Frontend on Vercel, backend on a small always-on host. Do not port the backend to Vercel serverless functions.

Why: the backend keeps state that serverless discards on every invocation: SQLite (`data/ffedge.db`: draft board,
rosters), the JSON source cache (`data/cache/`), the in-memory player pool and week cache, the props blend, and the
in-process APScheduler. Rebuilding that per cold start means several seconds of fetching before the first answer, and
the scheduler cannot exist at all. Porting would require Postgres + Blob/KV + Vercel Cron in place of all of that
(about a day of work) for no gain over a ~$5/month box.

## Target shape

1. **Frontend on Vercel.** Production gated by Deployment Protection (Pro): password or Vercel login, so the app is
   private without building auth. `/api/*` rewrites go through a Next.js route handler that forwards to `BACKEND_URL`
   and adds an `X-Edge-Key` header from an env var.
2. **Backend on Fly.io or Railway** (~$5/month) with a persistent volume mounted at `data/`. The scheduler keeps running
   with the laptop closed. Backend rejects requests without the shared secret. Env vars: `OPENROUTER_API_KEY`,
   `OPENROUTER_MODEL`, `OPENROUTER_VISION_MODEL`, `ODDS_API_KEY`, `YAHOO_CLIENT_ID/SECRET` (when approved), `EDGE_KEY`.
3. **Vercel Cron** (Pro: any frequency) hitting Next routes that forward to the backend:
   - Sunday 09:00 ET: `POST /api/odds/refresh` (props pull, ~90 credits of the 500/month free tier)
   - every 3 h: projections/injuries refresh (already scheduled in-process; cron is a backup)
   - Tuesday 06:00 ET: waiver-window check (Phase 2, once transactions can be read)

## What Vercel Pro unlocks that matters here

- Deployment Protection on production (the main reason to use Pro).
- Cron at sub-daily frequency (Hobby allows once per day).
- Fluid compute / long durations (up to 800 s) if sims or vision calls ever move into Vercel functions.
- Marketplace storage with free tiers (Neon Postgres, Upstash KV, Blob) if we ever go all-in on Vercel.
- Logs, analytics, preview deployments (nice, not decisive).

## Work list when we resume

- [ ] `backend/Dockerfile` (python 3.12-slim, uv install, uvicorn on 0.0.0.0:8000) and `fly.toml` or Railway config with a volume at `/app/data`
- [ ] `EDGE_KEY` check middleware in `backend/ffedge/api.py` (skip when unset for local use)
- [ ] `frontend/src/app/api/[...path]/route.ts` proxy that forwards to `BACKEND_URL` with the key; remove the dev rewrite when `BACKEND_URL` is set
- [ ] `frontend/vercel.json` with the cron entries above
- [ ] README: deploy steps (two account clicks, env vars, volume)
- [ ] Verify: cold start time, scheduler survives restarts, SQLite on the volume, props pull via cron spends one batch of credits only

## Alternative kept on file

All-in on Vercel: FastAPI as Vercel Python functions, state in Neon Postgres, caches in Blob, scheduler replaced by Cron.
Only worth it if the backend host becomes a hassle.
