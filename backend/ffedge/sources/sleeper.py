"""Sleeper public API: season projections (Rotowire-sourced raw stats), ADP, players."""
from __future__ import annotations

import httpx

from .. import config
from .cache import cached_json
from .common import norm_team, player_key

PROJ_URL = (
    "https://api.sleeper.com/projections/nfl/{season}?season_type=regular"
    "&position[]=QB&position[]=RB&position[]=WR&position[]=TE&position[]=K&position[]=DEF&order_by=adp_ppr"
)
PLAYERS_URL = "https://api.sleeper.app/v1/players/nfl"
STATE_URL = "https://api.sleeper.app/v1/state/nfl"

# Sleeper stat key -> canonical
STAT_MAP = {
    "pass_yd": "pass_yd", "pass_td": "pass_td", "pass_int": "pass_int", "pass_2pt": "pass_2pt",
    "rush_yd": "rush_yd", "rush_td": "rush_td", "rush_2pt": "rush_2pt",
    "rec": "rec", "rec_yd": "rec_yd", "rec_td": "rec_td", "rec_2pt": "rec_2pt",
    "fum_lost": "fum_lost",
}


def _fetch_projections() -> list[dict]:
    r = httpx.get(PROJ_URL.format(season=config.SEASON), timeout=60)
    r.raise_for_status()
    return r.json()


def _fetch_players() -> dict:
    r = httpx.get(PLAYERS_URL, timeout=120)
    r.raise_for_status()
    data = r.json()
    # trim to fantasy-relevant to keep the cache small
    keep = {}
    for pid, p in data.items():
        if p.get("position") in config.POSITIONS or p.get("fantasy_positions"):
            keep[pid] = {k: p.get(k) for k in (
                "full_name", "first_name", "last_name", "position", "team", "status", "injury_status",
                "injury_body_part", "injury_notes", "injury_start_date", "search_rank", "years_exp", "age",
                "espn_id", "yahoo_id", "depth_chart_order", "practice_description", "news_updated",
            )}
    return keep


def fetch_state() -> dict:
    r = httpx.get(STATE_URL, timeout=20)
    r.raise_for_status()
    return r.json()


def load(force: bool = False) -> tuple[list[dict], dict]:
    """Return (rows, meta). Each row is a partially-normalized player projection."""
    raw, meta = cached_json("sleeper_projections", _fetch_projections, force=force)
    rows = []
    for p in raw:
        pl = p.get("player") or {}
        pos = pl.get("position")
        if pos not in config.POSITIONS:
            continue
        st = p.get("stats") or {}
        stats = {}
        for k, ck in STAT_MAP.items():
            if k in st:
                stats[ck] = float(st[k])
        ret = float(st.get("def_kr_td", 0) or 0) + float(st.get("pr_td", 0) or 0)
        if pos != "DEF" and ret:
            stats["ret_td"] = ret
        if pos in ("K", "DEF"):
            stats = {}  # incomplete on Sleeper: no short FGs, no points-allowed
        team = norm_team(p.get("team") or pl.get("team"))
        if pos == "DEF":
            name = f"{team} D/ST"
        else:
            name = f"{pl.get('first_name','')} {pl.get('last_name','')}".strip()
        rows.append({
            "source": "sleeper",
            "sleeper_id": p.get("player_id"),
            "key": player_key(name, pos, team),
            "name": name,
            "pos": pos,
            "team": team,
            "stats": stats,
            "adp": st.get("adp_ppr") if st.get("adp_ppr") and st.get("adp_ppr") <= 300 else None,
            "adp_half": st.get("adp_half_ppr"),
            "pts_ppr_source": st.get("pts_ppr"),
            "injury_status": pl.get("injury_status"),
            "injury_body_part": pl.get("injury_body_part"),
            "injury_notes": pl.get("injury_notes"),
            "years_exp": pl.get("years_exp"),
            "updated_at": p.get("updated_at"),
        })
    return rows, meta


def load_players(force: bool = False) -> tuple[dict, dict]:
    return cached_json("sleeper_players", _fetch_players, ttl_seconds=24 * 3600, force=force)
