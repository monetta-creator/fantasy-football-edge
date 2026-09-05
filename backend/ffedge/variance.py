"""Weekly scoring variance from last season's nflverse weekly stats, under league scoring.

Produces per-player weekly point standard deviation (players with >= 6 games) and a position-level
fallback (coefficient of variation). Cached in data/cache/variance_<season>.json.
"""
from __future__ import annotations

import csv
import io
import statistics

import httpx

from . import config
from .scoring import score
from .sources.cache import cached_json
from .sources.common import norm_name

URL = "https://github.com/nflverse/nflverse-data/releases/download/stats_player/stats_player_week_{season}.csv"

COLS = {
    "passing_yards": "pass_yd", "passing_tds": "pass_td", "passing_interceptions": "pass_int", "passing_2pt_conversions": "pass_2pt",
    "rushing_yards": "rush_yd", "rushing_tds": "rush_td", "rushing_2pt_conversions": "rush_2pt",
    "receptions": "rec", "receiving_yards": "rec_yd", "receiving_tds": "rec_td", "receiving_2pt_conversions": "rec_2pt",
    "special_teams_tds": "ret_td",
}
FUM_COLS = ["sack_fumbles_lost", "rushing_fumbles_lost", "receiving_fumbles_lost"]
# Position-level weekly CV fallbacks (sd / mean) from typical NFL week-to-week spread.
POS_CV = {"QB": 0.47, "RB": 0.57, "WR": 0.58, "TE": 0.63, "K": 0.5, "DEF": 0.7}  # medians from 2025 weekly stats
MIN_GAMES = 6


def _fetch(season: int) -> dict:
    r = httpx.get(URL.format(season=season), timeout=120, follow_redirects=True)
    r.raise_for_status()
    per_player: dict[str, list[float]] = {}
    names: dict[str, str] = {}
    for row in csv.DictReader(io.StringIO(r.text)):
        if row.get("season_type") != "REG" or row.get("position") not in ("QB", "RB", "WR", "TE"):
            continue
        st = {}
        for c, k in COLS.items():
            v = row.get(c)
            if v not in (None, "", "NA"):
                st[k] = float(v)
        st["fum_lost"] = sum(float(row.get(c) or 0) for c in FUM_COLS)
        pts = score(st)
        key = f"{row['position']}:{norm_name(row['player_display_name'])}"
        per_player.setdefault(key, []).append(pts)
        names[key] = row["player_display_name"]
    out = {}
    for key, pts in per_player.items():
        if len(pts) >= MIN_GAMES:
            m = statistics.fmean(pts)
            sd = statistics.pstdev(pts)
            out[key] = {"games": len(pts), "mean": round(m, 2), "sd": round(sd, 2), "cv": round(sd / m, 3) if m > 0 else None, "name": names[key]}
    return {"season": season, "players": out}


def load(season: int = config.SEASON - 1, force: bool = False) -> tuple[dict, dict]:
    return cached_json(f"variance_{season}", lambda: _fetch(season), ttl_seconds=30 * 24 * 3600, force=force)


def weekly_sd(player_key: str, pos: str, weekly_mean: float, table: dict) -> float:
    """Weekly point sd for a player: last season's own sd scaled to this week's mean, else position CV."""
    rec = (table.get("players") or {}).get(player_key)
    cv = POS_CV.get(pos, 0.6)
    if rec and rec.get("cv"):
        cv = 0.7 * rec["cv"] + 0.3 * POS_CV.get(pos, 0.6)  # shrink toward the position prior
    return max(1.5, cv * max(weekly_mean, 1.0))
