"""FastAPI app for the draft assistant (Phase 0)."""
from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from . import config, draft_state, llm, vision
from .adp_model import p_gone_by
from .draft_sim import DraftSim
from .ir_stash import rank_stash
from .players import build_pool
from .recommend import Recommender
from .vorp import compute as compute_vorp


class AppState:
    def __init__(self):
        self.settings = config.load_settings()
        self.lock = threading.Lock()
        self.rec_cache: dict[str, dict] = {}
        self.pick_analysis_cache: dict | None = None
        self.executor = ThreadPoolExecutor(max_workers=1)
        self.llm_executor = ThreadPoolExecutor(max_workers=2)
        self.players = []
        self.meta = {}
        self.ready = False
        self.error = None
        self.load()

    def load(self, force: bool = False):
        try:
            players, meta = build_pool(force=force, ir_plus=self.settings.ir_plus)
            arr, info = compute_vorp(players)
            sim = DraftSim(arr)
            rec = Recommender(players, arr, info, sim)
            with self.lock:
                self.players, self.meta, self.arr, self.info, self.sim, self.rec = players, meta, arr, info, sim, rec
                self.by_id = {p.id: p for p in players}
                self.rec_cache = {}
                self.pick_analysis_cache = None
                self.ready = True
                self.error = None
        except Exception as e:  # keep serving stale data if refresh fails
            self.error = str(e)
            if not self.ready:
                raise

    @staticmethod
    def sig(picks: list[dict]) -> str:
        return ",".join(f"{p['pick_no']}:{p['player_id']}:{p['team']}" for p in picks)

    def recommend_for(self, picks: list[dict]) -> dict:
        key = self.sig(picks)
        cached = self.rec_cache.get(key)
        if cached:
            return cached
        with self.lock:
            cached = self.rec_cache.get(key)
            if cached:
                return cached
            out = self.rec.recommend(picks, n_sims=self.settings.sim_count)
            self.rec_cache[key] = out
        if not out.get("done") and llm.available(self.settings):
            self.llm_executor.submit(self._enrich, out)
        return out

    def _enrich(self, out: dict):
        rec = out["recommended"]
        facts = {
            "player": f"{rec['name']} ({rec['pos']}, {rec['team']})",
            "league scoring": "full PPR, 6-pt passing TD, 1 pt per 25 pass yds, 1 RB slot, 2 WR, TE, W/R, W/R/T flex, 3 bench, 6 IR, 12 teams",
            "projected points (league scoring)": rec["pts"],
            "VORP vs waiver replacement": rec["vorp"],
            "consensus ADP": rec["adp"],
            "my current pick": out["decision_pick"],
            "my next pick": out.get("next_pick"),
            "P(gone by my next pick)": rec.get("p_gone_by_next"),
            "advantage over runner-up (sim roster value)": out["margin"],
            "mechanism": rec["mechanism"],
        }
        names = [c["name"] for c in out.get("all_candidates", [])] + [rec["name"]]
        text = llm.rationale(self.settings, facts, names)
        if text:
            out["rationale_llm"] = text

    def precompute(self):
        picks = draft_state.get_picks()
        try:
            self.recommend_for(picks)
        except Exception as e:
            self.error = f"precompute: {e}"


STATE: AppState | None = None
app = FastAPI(title="ffedge", version="0.2.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
SCHEDULER = None


def st() -> AppState:
    global STATE
    if STATE is None:
        STATE = AppState()
        STATE.executor.submit(STATE.precompute)
    return STATE


@app.on_event("startup")
def _startup():
    st()
    global SCHEDULER
    try:
        from apscheduler.schedulers.background import BackgroundScheduler

        from . import api_week

        SCHEDULER = BackgroundScheduler(daemon=True)
        SCHEDULER.add_job(lambda: st().load(force=True), "interval", hours=6, id="refresh_pool")
        SCHEDULER.add_job(lambda: api_week.week_rows(force=True), "interval", hours=3, id="refresh_week")
        SCHEDULER.start()
    except Exception as e:  # scheduler is a convenience; never block startup
        st().error = f"scheduler: {e}"


from . import api_week  # noqa: E402

app.include_router(api_week.router)


class PickIn(BaseModel):
    player_id: str
    team: int | None = None


class TeamsIn(BaseModel):
    names: dict[int, str]


class RefreshIn(BaseModel):
    force: bool = True


class ImportIn(BaseModel):
    image: str  # data URL (image/jpeg or image/png, base64)


class BulkPick(BaseModel):
    player_id: str
    team: int | None = None


class BulkIn(BaseModel):
    picks: list[BulkPick]


@app.get("/api/health")
def health():
    s = st()
    return {"ok": True, "ready": s.ready, "error": s.error}


@app.get("/api/meta")
def meta():
    s = st()
    return {
        "season": config.SEASON, "league_id": config.LEAGUE_ID, "teams": config.NUM_TEAMS, "my_slot": config.MY_SLOT,
        "rounds": config.ROUNDS, "my_picks": config.my_picks(), "sources": s.meta, "replacement": s.info,
        "llm": {"enabled": llm.available(s.settings), "model": s.settings.openrouter_model if llm.available(s.settings) else None},
        "sim_count": s.settings.sim_count, "ir_plus": s.settings.ir_plus, "error": s.error,
        "roster_slots": [{"slot": n, "elig": list(e)} for n, e in config.ROSTER_SLOTS], "bench": config.BENCH_SLOTS, "ir": config.IR_SLOTS,
    }


@app.get("/api/board")
def board():
    s = st()
    picks = draft_state.get_picks()
    return s.rec.board(picks, draft_state.get_team_names())


@app.get("/api/recommend")
def recommend():
    s = st()
    picks = draft_state.get_picks()
    return s.recommend_for(picks)


@app.get("/api/players")
def players(q: str = "", pos: str = "ALL", available: bool = True, limit: int = 300, sort: str = "vorp"):
    s = st()
    picks = draft_state.get_picks()
    drafted = {p["player_id"]: p for p in picks}
    cur = len(picks) + 1
    mine = [k for k in config.my_picks() if k >= cur]
    decision = mine[0] if mine else None
    nxt = mine[1] if len(mine) > 1 else None
    qn = q.lower().replace("'", "").replace(".", "").strip()
    rows = []
    for p in s.players:
        if available and p.id in drafted:
            continue
        if pos != "ALL" and p.pos != pos:
            continue
        if qn and qn not in p.name.lower().replace("'", "").replace(".", "") and qn not in (p.team or "").lower():
            continue
        d = drafted.get(p.id)
        rows.append({
            "id": p.id, "name": p.name, "pos": p.pos, "team": p.team, "pts": p.pts, "ppg": p.ppg, "vorp": p.vorp, "vols": p.vols,
            "adp": p.adp, "adp_sigma": p.adp_sigma, "yahoo_rank": p.yahoo_rank, "bye": p.bye, "games": p.games,
            "injury": {"code": p.injury.get("code"), "label": p.injury.get("label"), "type": p.injury.get("type"),
                       "return_week": p.injury.get("return_week"), "ir_eligible": p.injury.get("ir_eligible"), "flag": p.injury.get("flag")},
            "stash_value": p.__dict__.get("stash_value", 0.0), "proj_spread": p.proj_spread,
            "p_gone_by_decision": round(p_gone_by(p.adp, p.adp_sigma, cur, decision), 3) if decision and decision > cur else 0.0,
            "p_gone_by_next": round(p_gone_by(p.adp, p.adp_sigma, cur, nxt), 3) if nxt else None,
            "drafted": ({"pick_no": d["pick_no"], "team": d["team"]} if d else None),
        })
    keyf = {"vorp": lambda r: -r["vorp"], "pts": lambda r: -r["pts"], "adp": lambda r: r["adp"], "stash": lambda r: -r["stash_value"]}.get(sort, lambda r: -r["vorp"])
    rows.sort(key=keyf)
    return {"decision_pick": decision, "next_pick": nxt, "players": rows[:limit]}


@app.get("/api/players/{player_id}")
def player(player_id: str):
    s = st()
    p = s.by_id.get(player_id)
    if not p:
        raise HTTPException(404, "unknown player")
    d = p.to_dict()
    d["breakdown"] = p.breakdown
    return d


@app.post("/api/pick")
def pick(body: PickIn):
    s = st()
    if body.player_id not in s.by_id:
        raise HTTPException(404, "unknown player")
    try:
        r = draft_state.add_pick(body.player_id, body.team)
    except ValueError as e:
        raise HTTPException(400, str(e))
    s.executor.submit(s.precompute)
    return r


@app.post("/api/undo")
def undo():
    s = st()
    r = draft_state.undo()
    s.executor.submit(s.precompute)
    return r or {}


@app.post("/api/reset")
def reset():
    s = st()
    draft_state.reset()
    s.executor.submit(s.precompute)
    return {"ok": True}


@app.put("/api/teams")
def teams(body: TeamsIn):
    draft_state.set_team_names(body.names)
    return draft_state.get_team_names()


@app.get("/api/pick-analysis")
def pick_analysis(pick: int = config.MY_SLOT):
    s = st()
    if pick == config.MY_SLOT and s.pick_analysis_cache:
        return s.pick_analysis_cache
    out = s.rec.pick_analysis(pick_no=pick, n_sims=s.settings.sim_count)
    if pick == config.MY_SLOT:
        s.pick_analysis_cache = out
    return out


@app.get("/api/ir-stash")
def ir_stash():
    s = st()
    picks = draft_state.get_picks()
    drafted = {p["player_id"] for p in picks}
    rows = rank_stash(s.players, limit=60)
    for r in rows:
        r["drafted"] = r["id"] in drafted
    return {"rows": rows, "ir_plus": s.settings.ir_plus}


@app.post("/api/refresh")
def refresh(body: RefreshIn):
    s = st()
    s.load(force=body.force)
    s.executor.submit(s.precompute)
    return {"ok": True, "error": s.error, "counts": s.meta.get("counts")}


@app.post("/api/import-screenshot")
def import_screenshot(body: ImportIn):
    """Vision model transcribes a draft-board photo; names are matched to the pool; nothing is applied."""
    s = st()
    if not llm.available(s.settings):
        raise HTTPException(400, "OPENROUTER_API_KEY not set; screenshot import needs a vision model")
    if not body.image.startswith("data:image/"):
        raise HTTPException(400, "image must be a data URL")
    extracted = vision.extract(s.settings, body.image)
    if extracted is None:
        raise HTTPException(502, "vision model returned nothing usable")
    picks = draft_state.get_picks()
    drafted = {p["player_id"] for p in picks}
    rows = vision.resolve(extracted, s.players, drafted, draft_state.get_team_names())
    return {"board_type": extracted.get("board_type"), "model": s.settings.openrouter_vision_model, "rows": rows,
            "next_pick_no": len(picks) + 1, "ok": sum(1 for r in rows if r["status"] == "ok"),
            "ambiguous": sum(1 for r in rows if r["status"] == "ambiguous"), "unknown": sum(1 for r in rows if r["status"] == "unknown")}


@app.post("/api/picks/bulk")
def picks_bulk(body: BulkIn):
    """Apply confirmed picks in order. Stops at the first error and reports how many were applied."""
    s = st()
    applied, errors = [], []
    for bp in body.picks:
        if bp.player_id not in s.by_id:
            errors.append(f"unknown player {bp.player_id}")
            continue
        try:
            applied.append(draft_state.add_pick(bp.player_id, bp.team))
        except ValueError as e:
            errors.append(f"{bp.player_id}: {e}")
    s.executor.submit(s.precompute)
    return {"applied": applied, "errors": errors}


@app.get("/api/log")
def log():
    with draft_state.conn() as c:
        return [dict(r) for r in c.execute("SELECT id, ts, kind, detail FROM action_log ORDER BY id DESC LIMIT 200")]
