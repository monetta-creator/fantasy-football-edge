"""Yahoo public (read-only, unauthenticated) player list: Yahoo rank, average pick, status, bye.

This is what opponents see in the Yahoo draft room, so it is the primary opponent model.
"""
from __future__ import annotations

import time

import httpx

from .. import config
from .cache import cached_json
from .common import norm_team, player_key

URL = (
    "https://pub-api-ro.fantasysports.yahoo.com/fantasy/v2/game/nfl/players;"
    "position=ALL;start={start};count=100;sort=OR;sort_type=season;sort_season={season};"
    "out=draft_analysis,ranks;ranks=season?format=json_f"
)
POS_MAP = {"QB": "QB", "RB": "RB", "WR": "WR", "TE": "TE", "K": "K", "DEF": "DEF"}


def _fetch(pages: int = 9) -> list[dict]:
    out = []
    for i in range(pages):
        url = URL.format(start=i * 100, season=config.SEASON)
        r = httpx.get(url, timeout=60, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        players = r.json()["fantasy_content"]["game"]["players"]
        if not players:
            break
        for e in players:
            p = e["player"]
            out.append({
                "yahoo_id": p.get("player_id"),
                "name": p.get("name", {}).get("full"),
                "display_position": p.get("display_position"),
                "team": p.get("editorial_team_abbr"),
                "status": p.get("status"),
                "status_full": p.get("status_full"),
                "injury_note": p.get("injury_note"),
                "bye": (p.get("bye_weeks") or {}).get("week"),
                "draft_analysis": p.get("draft_analysis"),
                "ranks": p.get("player_ranks"),
                "percent_owned": (p.get("percent_owned") or {}).get("value"),
            })
        time.sleep(0.4)
    return out


def _f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def load(force: bool = False) -> tuple[list[dict], dict]:
    raw, meta = cached_json("yahoo_public", _fetch, force=force)
    rows = []
    for p in raw:
        dp = (p.get("display_position") or "").split(",")[0]
        pos = POS_MAP.get(dp)
        if not pos:
            continue
        team = norm_team(p.get("team"))
        da = p.get("draft_analysis") or {}
        rank = None
        for r in p.get("ranks") or []:
            pr = r.get("player_rank", {})
            if pr.get("rank_type") == "S" and str(pr.get("rank_season")) == str(config.SEASON):
                rank = _f(pr.get("rank_value"))
        name = p.get("name") or ""
        rows.append({
            "source": "yahoo",
            "yahoo_id": p.get("yahoo_id"),
            "key": player_key(name, pos, team),
            "name": name,
            "pos": pos,
            "team": team,
            "yahoo_rank": rank,
            "adp": _f(da.get("average_pick")),
            "percent_drafted": _f(da.get("percent_drafted")),
            "status": p.get("status"),
            "status_full": p.get("status_full"),
            "injury_note": p.get("injury_note"),
            "bye": int(p["bye"]) if p.get("bye") and str(p["bye"]).isdigit() else None,
        })
    return rows, meta
