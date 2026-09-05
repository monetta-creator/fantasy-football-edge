"""2026 NFL schedule from nflverse/nfldata (bye weeks, playoff-week opponents)."""
from __future__ import annotations

import csv
import io

import httpx

from .. import config
from .cache import cached_json
from .common import norm_team

URL = "https://github.com/nflverse/nfldata/raw/master/data/games.csv"


def _fetch() -> list[dict]:
    r = httpx.get(URL, timeout=90, follow_redirects=True)
    r.raise_for_status()
    rows = []
    for x in csv.DictReader(io.StringIO(r.text)):
        if x.get("season") == str(config.SEASON) and x.get("game_type") == "REG":
            rows.append({
                "week": int(x["week"]), "home": norm_team(x["home_team"]), "away": norm_team(x["away_team"]),
                "gameday": x.get("gameday"), "spread_line": x.get("spread_line"), "total_line": x.get("total_line"),
            })
    return rows


def load(force: bool = False) -> tuple[dict, dict]:
    games, meta = cached_json("schedule", _fetch, ttl_seconds=7 * 24 * 3600, force=force)
    teams = sorted({g["home"] for g in games} | {g["away"] for g in games})
    weeks = sorted({g["week"] for g in games})
    byes = {}
    opp = {}
    for t in teams:
        playing = {}
        for g in games:
            if g["home"] == t:
                playing[g["week"]] = g["away"]
            elif g["away"] == t:
                playing[g["week"]] = f"@{g['home']}"
        byes[t] = [w for w in weeks if w not in playing]
        opp[t] = playing
    return {"byes": byes, "opponents": opp, "weeks": weeks}, meta
