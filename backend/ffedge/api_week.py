"""Phase 1 endpoints: weekly dashboard, rosters, lineup optimizer, streaming, page import, Yahoo sync."""
from __future__ import annotations

import time

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from . import config, draft_state, lineup, llm, rosters, streaming, variance, vision, weekly
from .sync import yahoo

router = APIRouter()
_STATE = {"week_cache": {}, "variance": None}


def _st():
    from .api import st
    return st()


def _variance():
    if _STATE["variance"] is None:
        _STATE["variance"], _ = variance.load()
    return _STATE["variance"]


def week_rows(week: int | None = None, force: bool = False) -> tuple[int, dict, dict]:
    s = _st()
    wk = week or weekly.current_week()
    cached = _STATE["week_cache"].get(wk)
    if cached and not force and time.time() - cached["at"] < 3 * 3600 and cached["pool_built"] == s.meta.get("built_at"):
        return wk, cached["rows"], cached["meta"]
    rows, meta = weekly.build_week(wk, s.players, _variance(), force=force)
    _STATE["week_cache"][wk] = {"rows": rows, "meta": meta, "at": time.time(), "pool_built": s.meta.get("built_at")}
    return wk, rows, meta


def _brief(pid: str, rows: dict, slot: str | None = None) -> dict:
    s = _st()
    p = s.by_id.get(pid)
    r = rows.get(pid)
    d = {"id": pid, "name": p.name if p else pid, "pos": p.pos if p else "?", "team": p.team if p else None, "slot": slot,
         "season_pts": p.pts if p else 0, "vorp": p.vorp if p else 0, "bye": p.bye if p else None,
         "injury": {"code": p.injury.get("code"), "label": p.injury.get("label"), "ir_eligible": p.injury.get("ir_eligible"), "flag": p.injury.get("flag"), "return_week": p.injury.get("return_week")} if p else {},
         "stash_value": p.__dict__.get("stash_value", 0) if p else 0}
    if r:
        d.update(r.to_dict())
    else:
        d.update({"mean": 0.0, "sd": 0.0, "on_bye": False, "opp": None})
    return d


def _players_for_lineup(team: int, rows: dict) -> list[dict]:
    out = []
    for r in rosters.roster(team):
        b = _brief(r["player_id"], rows, r["slot"])
        if r["slot"] == "IR":
            continue
        out.append({"id": b["id"], "pos": b["pos"], "name": b["name"], "mean": 0.0 if b.get("on_bye") else b["mean"], "sd": b["sd"], "slot": r["slot"]})
    return out


def _current_lineup(team: int, rows: dict) -> list[dict]:
    ps = _players_for_lineup(team, rows)
    starters = [p for p in ps if p["slot"] in lineup.SLOT_NAMES]
    if len(starters) < len(lineup.SLOT_NAMES) // 2:  # slots not set yet -> mean-optimal
        return list(lineup.best_by_mean(ps).values())
    return starters


def _opponent_slot(week: int) -> int | None:
    name = config.MY_SCHEDULE.get(week)
    if not name:
        return None
    for slot, n in config.TEAM_NAMES.items():
        if n.lower() == name.lower():
            return slot
    return None


def _recommendations(week: int, rows: dict, opt: dict, cur_eval: dict, my_players: list[dict], cur_lineup: list[dict], stream: dict, slots_set: bool) -> list[dict]:
    recs = []
    best_ids = {p["id"] for p in opt["lineup"].values()}
    cur_starters = {p["id"] for p in cur_lineup}
    ins = [pid for pid in best_ids if pid not in cur_starters]
    outs = [pid for pid in cur_starters if pid not in best_ids]
    if not slots_set:
        recs.append({
            "kind": "lineup", "headline": "Record your starting lineup", "number": round(opt["eval"]["win_prob"] * 100, 1), "unit": "win prob %",
            "secondary": f"{opt['eval']['mean']:.1f} projected", "confidence": "High",
            "rationale": "Slots are not set yet, so the dashboard assumes the max-win-probability lineup. Apply it here and set the same lineup in Yahoo.",
            "action": "apply_lineup",
        })
    elif ins or outs:
        dwin = opt["eval"]["win_prob"] - cur_eval["win_prob"]
        dmean = opt["eval"]["mean"] - cur_eval["mean"]
        names_in = ", ".join(_brief(i, rows)["name"] for i in ins)
        names_out = ", ".join(_brief(o, rows)["name"] for o in outs)
        headline = f"Start {names_in} over {names_out}" if ins and outs else (f"Start {names_in} (open slot)" if ins else f"Bench {names_out}")
        recs.append({
            "kind": "lineup", "headline": headline, "number": round(dwin * 100, 1), "unit": "win prob pts",
            "secondary": f"{dmean:+.1f} projected", "confidence": "High" if dwin > 0.04 else "Medium" if dwin > 0.015 else "Low",
            "rationale": f"{opt['posture'].capitalize()} this week: the sim picks the lineup that maximizes P(win) ({opt['eval']['win_prob']:.0%}), not just projected mean.",
            "action": "apply_lineup",
        })
    # streaming
    for pos in ("DEF", "K"):
        cand = stream.get(pos) or []
        mine = [c for c in cand if c["mine"]]
        avail = [c for c in cand if c["available"]]
        my_best = max((_brief(p["id"], rows)["mean"] for p in my_players if p["pos"] == pos), default=0.0)
        if avail and avail[0]["mean"] - my_best >= 1.5:
            a = avail[0]
            recs.append({
                "kind": "stream", "headline": f"Stream {pos}: add {a['name']}", "number": round(a["mean"] - my_best, 1), "unit": "projected pts",
                "secondary": f"{a['mean']} vs your best {my_best:.1f}", "confidence": "Medium" if a["mean"] - my_best < 3 else "High",
                "rationale": a["mechanism"], "action": "add", "player_id": a["id"],
            })
    # IR choreography
    for p in my_players:
        b = _brief(p["id"], rows)
        if b["injury"].get("ir_eligible") and p["slot"] != "IR":
            recs.append({"kind": "ir", "headline": f"Move {b['name']} to IR", "number": 1, "unit": "bench slot freed",
                         "secondary": f"{b['injury'].get('label')} · back wk {b['injury'].get('return_week') or '?'}", "confidence": "High",
                         "rationale": "IR-eligible by Yahoo status; parking him keeps a live roster spot open for a claim.", "action": "move_ir", "player_id": p["id"]})
    for p in my_players:
        b = _brief(p["id"], rows)
        if p["slot"] in lineup.SLOT_NAMES and b.get("on_bye"):
            recs.append({"kind": "bye", "headline": f"{b['name']} is on bye in slot {p['slot']}", "number": 0, "unit": "pts", "secondary": "",
                         "confidence": "High", "rationale": "A starter on bye scores zero.", "action": "apply_lineup"})
    return recs


@router.get("/api/week")
def week(week_no: int | None = None):
    s = _st()
    wk, rows, meta = week_rows(week_no)
    my = config.MY_SLOT
    opp_slot = _opponent_slot(wk)
    my_players = _players_for_lineup(my, rows)
    opp_players = _players_for_lineup(opp_slot, rows) if opp_slot else []
    opp_lineup = _current_lineup(opp_slot, rows) if opp_slot else []
    cur_lineup = _current_lineup(my, rows)
    slots_set = sum(1 for p in my_players if p["slot"] in lineup.SLOT_NAMES) >= len(lineup.SLOT_NAMES) // 2
    owner = rosters.owner_of()
    stream = {pos: streaming.rank(rows, pos, owner, my, limit=8) for pos in ("K", "DEF")}
    if not my_players:
        return {"week": wk, "empty": True, "opponent": {"slot": opp_slot, "name": config.MY_SCHEDULE.get(wk)}, "streaming": stream,
                "message": "No roster yet. Seed it from the draft board (Roster tab) or import a roster screenshot."}
    opt = lineup.optimize(my_players, opp_lineup)
    cur_eval = lineup.evaluate(cur_lineup, opp_lineup)
    recs = _recommendations(wk, rows, opt, cur_eval, my_players, cur_lineup, stream, slots_set)
    return {
        "week": wk, "empty": False, "my_team": config.MY_TEAM_NAME,
        "opponent": {"slot": opp_slot, "name": config.MY_SCHEDULE.get(wk), "lineup": [_brief(p["id"], rows, p.get("slot")) for p in opp_lineup], "eval": {"mean": cur_eval["opp_mean"], "sd": cur_eval["opp_sd"]}},
        "current": {"lineup": [_brief(p["id"], rows, p.get("slot")) for p in cur_lineup], "eval": cur_eval},
        "optimized": {"lineup": {slot: _brief(p["id"], rows, lineup.KEY_TO_SLOT.get(slot, slot)) for slot, p in opt["lineup"].items()}, "slot_keys": lineup.SLOT_KEYS, "eval": opt["eval"], "posture": opt["posture"], "n_candidates": opt["n_candidates"],
                      "mean_eval": opt["mean_eval"]},
        "roster": [_brief(r["player_id"], rows, r["slot"]) for r in rosters.roster(my)],
        "recommendations": recs, "streaming": stream, "meta": {"projections": meta, "sources": "Sleeper weekly (Rotowire) + nflverse Vegas lines + 2025 variance"},
    }


class SeedIn(BaseModel):
    replace: bool = False


@router.post("/api/rosters/seed-from-draft")
def seed(body: SeedIn):
    picks = draft_state.get_picks()
    if not picks:
        raise HTTPException(400, "draft board is empty")
    n = rosters.seed_from_draft(picks, replace=body.replace)
    _STATE["week_cache"] = {}
    return {"rows": n}


@router.get("/api/rosters")
def all_rosters():
    wk, rows, _ = week_rows()
    names = draft_state.get_team_names()
    out = []
    for t, ps in rosters.all_rosters().items():
        out.append({"slot": t, "name": names.get(t), "players": [_brief(p["player_id"], rows, p["slot"]) for p in ps]})
    return {"week": wk, "teams": out}


class MoveIn(BaseModel):
    player_id: str
    slot: str
    team: int | None = None


class AddIn(BaseModel):
    player_id: str
    team: int | None = None
    slot: str = "BN"
    drop_player_id: str | None = None


class DropIn(BaseModel):
    player_id: str
    team: int | None = None


@router.post("/api/roster/move")
def move(body: MoveIn):
    try:
        rosters.move(body.team or config.MY_SLOT, body.player_id, body.slot)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"ok": True}


@router.post("/api/roster/add")
def add(body: AddIn):
    s = _st()
    if body.player_id not in s.by_id:
        raise HTTPException(404, "unknown player")
    team = body.team or config.MY_SLOT
    try:
        if body.drop_player_id:
            rosters.drop(team, body.drop_player_id)
        rosters.add(team, body.player_id, body.slot)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"ok": True}


@router.post("/api/roster/drop")
def drop(body: DropIn):
    rosters.drop(body.team or config.MY_SLOT, body.player_id)
    return {"ok": True}


class LineupIn(BaseModel):
    assignments: dict[str, str]


@router.post("/api/roster/apply-lineup")
def apply_lineup(body: LineupIn):
    rosters.set_lineup(config.MY_SLOT, body.assignments)
    return {"ok": True}


@router.post("/api/roster/apply-optimized")
def apply_optimized():
    wk, rows, _ = week_rows()
    opp_slot = _opponent_slot(wk)
    my_players = _players_for_lineup(config.MY_SLOT, rows)
    opp_lineup = _current_lineup(opp_slot, rows) if opp_slot else []
    opt = lineup.optimize(my_players, opp_lineup)
    assignments = {p["id"]: lineup.KEY_TO_SLOT.get(slot, slot) for slot, p in opt["lineup"].items()}
    # keep IR players on IR
    for r in rosters.roster(config.MY_SLOT):
        if r["slot"] == "IR":
            assignments[r["player_id"]] = "IR"
    rosters.set_lineup(config.MY_SLOT, assignments)
    return {"ok": True, "assignments": assignments, "win_prob": opt["eval"]["win_prob"]}


@router.get("/api/free-agents")
def free_agents(pos: str = "ALL", limit: int = 60, sort: str = "week"):
    s = _st()
    wk, rows, _ = week_rows()
    owner = rosters.owner_of()
    out = []
    for p in s.players:
        if p.id in owner:
            continue
        if pos != "ALL" and p.pos != pos:
            continue
        out.append(_brief(p.id, rows))
    key = {"week": lambda r: -r["mean"], "season": lambda r: -r["vorp"], "stash": lambda r: -r["stash_value"]}.get(sort, lambda r: -r["mean"])
    out.sort(key=key)
    return {"week": wk, "players": out[:limit], "rostered": len(owner)}


@router.get("/api/roster/log")
def roster_log():
    return rosters.log()


# ---- Screenshot page import ------------------------------------------------------------------
class ImportPageIn(BaseModel):
    image: str


@router.post("/api/import-page")
def import_page(body: ImportPageIn):
    s = _st()
    if not llm.available(s.settings):
        raise HTTPException(400, "OPENROUTER_API_KEY not set")
    if not body.image.startswith("data:image/"):
        raise HTTPException(400, "image must be a data URL")
    ex = vision.extract_page(s.settings, body.image)
    if ex is None:
        raise HTTPException(502, "vision model returned nothing usable")
    rows = vision.resolve_page(ex, s.players, draft_state.get_team_names())
    return {"page_type": ex.get("page_type"), "fantasy_team": ex.get("fantasy_team"), "rows": rows, "model": s.settings.openrouter_vision_model}


class ApplyPageIn(BaseModel):
    team: int
    mode: str = "replace"  # replace | merge | transactions
    rows: list[dict]


@router.post("/api/import-page/apply")
def import_page_apply(body: ApplyPageIn):
    s = _st()
    ids = [r["player_id"] for r in body.rows if r.get("player_id") in s.by_id]
    if body.mode == "replace":
        slots = {r["player_id"]: (r.get("slot") or "BN") for r in body.rows if r.get("player_id")}
        rosters.replace_team(body.team, ids, slots)
    elif body.mode == "merge":
        for r in body.rows:
            if r.get("player_id") in s.by_id:
                try:
                    rosters.add(body.team, r["player_id"], r.get("slot") or "BN")
                except ValueError:
                    pass
    elif body.mode == "transactions":
        for r in body.rows:
            pid = r.get("player_id")
            if pid not in s.by_id:
                continue
            t = r.get("team") or body.team
            if r.get("action") in ("add", "waiver", "claim"):
                try:
                    rosters.add(t, pid, "BN")
                except ValueError:
                    pass
            elif r.get("action") == "drop":
                rosters.drop(t, pid)
    _STATE["week_cache"] = {}
    return {"ok": True, "applied": len(ids)}


# ---- Yahoo (dormant until credentials exist) ---------------------------------------------------
def _yahoo():
    s = _st()
    c = yahoo.client_from_settings(s.settings)
    if c is None:
        raise HTTPException(400, "YAHOO_CLIENT_ID/SECRET not set (application pending)")
    return c


@router.get("/api/yahoo/status")
def yahoo_status():
    s = _st()
    c = yahoo.client_from_settings(s.settings)
    return {"configured": c is not None, "connected": bool(c and c.connected()), "read_only": True}


@router.get("/api/yahoo/auth-url")
def yahoo_auth_url():
    return {"url": _yahoo().auth_url()}


class CodeIn(BaseModel):
    code: str


@router.post("/api/yahoo/callback")
def yahoo_callback(body: CodeIn):
    c = _yahoo()
    c.exchange_code(body.code.strip())
    return {"connected": True}


@router.post("/api/yahoo/sync")
def yahoo_sync():
    """Pull rosters from Yahoo and overwrite the roster store (match by name/position/team)."""
    s = _st()
    c = _yahoo()
    if not c.connected():
        raise HTTPException(400, "not connected; run the auth flow")
    teams = c.rosters()
    names = draft_state.get_team_names()
    applied = []
    for t in teams:
        slot = next((k for k, v in names.items() if v.lower() == (t.get("name") or "").lower()), None)
        if slot is None:
            continue
        ids, slots = [], {}
        for pl in t["players"]:
            cands = vision.match_player(pl["name"], s.players, pl.get("pos"), pl.get("team"))
            if cands and cands[0][1] >= 0.85:
                pid = cands[0][0].id
                ids.append(pid)
                slots[pid] = vision.SLOT_ALIASES.get((pl.get("slot") or "BN").upper(), pl.get("slot") or "BN")
        rosters.replace_team(slot, ids, slots)
        applied.append({"team": slot, "players": len(ids)})
    _STATE["week_cache"] = {}
    return {"applied": applied}


@router.get("/api/players/{player_id}/detail")
def player_detail(player_id: str):
    s = _st()
    p = s.by_id.get(player_id)
    if not p:
        raise HTTPException(404, "unknown player")
    wk, rows, _ = week_rows()
    r = rows.get(player_id)
    hist = variance.history(player_id, _variance()) or {}
    owner = rosters.owner_of().get(player_id)
    names = draft_state.get_team_names()
    return {
        "id": p.id, "name": p.name, "pos": p.pos, "team": p.team, "bye": p.bye, "injury": p.injury, "adp": p.adp, "adp_sigma": p.adp_sigma,
        "adp_sources": p.adp_sources, "yahoo_rank": p.yahoo_rank, "proj_sources": p.proj_sources, "proj_spread": p.proj_spread,
        "vorp": p.vorp, "vols": p.vols, "repl_pts": p.__dict__.get("repl_pts"), "stash_value": p.__dict__.get("stash_value", 0.0), "outlook": p.outlook,
        "owner": owner, "owner_name": names.get(owner) if owner else None,
        "season": {"pts": p.pts, "games": p.games, "ppg": p.ppg, "stats": {k: round(v, 1) for k, v in p.stats.items()}, "breakdown": p.breakdown},
        "week": ({"week": wk, **r.to_dict(), "stats": {k: round(v, 2) for k, v in r.stats.items()}} if r else {"week": wk}),
        "history": {"season": config.SEASON - 1, "games": hist.get("games", 0), "mean": hist.get("mean"), "sd": hist.get("sd"), "weeks": hist.get("weeks", [])},
    }
