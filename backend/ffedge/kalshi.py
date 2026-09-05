"""Kalshi public market data (no key needed): NFL game winners, totals/spreads/team-total ladders,
anytime TD, player yardage and fantasy-point ladders, season win totals. Read-only, cached 3 h."""
from __future__ import annotations

import re
from datetime import date, timedelta

import httpx

from . import config
from .sources.cache import cached_json
from .sources.common import norm_name, norm_team

BASE = "https://api.elections.kalshi.com/trade-api/v2"
TEAM_FIX = {"JAC": "JAX", "LA": "LAR", "WSH": "WAS"}
SERIES = {
    "game": "KXNFLGAME", "total": "KXNFLTOTAL", "spread": "KXNFLSPREAD", "team_total": "KXNFLTEAMTOTAL",
    "anytime_td": "KXNFLANYTD", "pass_yds": "KXNFLPASSYDS", "rush_yds": "KXNFLRSHYDS", "rec_yds": "KXNFLRECYDS", "ff_pts": "KXNFLFFPTS",
}
MONTHS = {m: i for i, m in enumerate(["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"], 1)}


def _fetch_series(series_ticker: str, status: str = "open", max_pages: int = 10) -> list[dict]:
    out, cursor = [], None
    for _ in range(max_pages):
        params = {"series_ticker": series_ticker, "status": status, "limit": 200}
        if cursor:
            params["cursor"] = cursor
        r = httpx.get(f"{BASE}/markets", params=params, timeout=30)
        r.raise_for_status()
        d = r.json()
        out += d.get("markets", [])
        cursor = d.get("cursor")
        if not cursor:
            break
    return out


def _price(m: dict) -> float | None:
    """Mid of yes bid/ask in probability, else last price."""
    b, a = m.get("yes_bid"), m.get("yes_ask")
    if b is not None and a is not None and a > 0:
        return (float(b) + float(a)) / 200.0
    lp = m.get("last_price")
    return float(lp) / 100.0 if lp is not None else None


def _event(ticker: str) -> tuple[str | None, str | None, date | None]:
    """'KXNFLGAME-26SEP13BUFHOU-HOU' -> (away, home, date)."""
    m = re.match(r"^[A-Z0-9]+-(\d{2})([A-Z]{3})(\d{2})([A-Z]{2,3})([A-Z]{2,3})", ticker)
    if not m:
        return None, None, None
    yy, mon, dd, t1, t2 = m.groups()
    try:
        d = date(2000 + int(yy), MONTHS[mon], int(dd))
    except Exception:
        d = None
    return norm_team(TEAM_FIX.get(t1, t1)), norm_team(TEAM_FIX.get(t2, t2)), d


def ladder_stats(points: list[tuple[float, float]]) -> dict | None:
    """From (strike, P(over strike)) pairs -> implied median and mean."""
    pts = sorted((s, p) for s, p in points if p is not None)
    if len(pts) < 2:
        return None
    # median: where P(over) crosses 0.5 (linear interpolation)
    med = None
    for (s1, p1), (s2, p2) in zip(pts, pts[1:]):
        if p1 >= 0.5 >= p2 and p1 != p2:
            med = s1 + (p1 - 0.5) / (p1 - p2) * (s2 - s1)
            break
    if med is None:
        med = pts[0][0] if pts[0][1] < 0.5 else pts[-1][0]
    # mean ~ integral of survival function over the ladder range + edges
    step = (pts[-1][0] - pts[0][0]) / (len(pts) - 1)
    mean = pts[0][0] - step / 2 + sum(p for _, p in pts) * step
    return {"median": round(med, 2), "mean": round(mean, 2), "strikes": len(pts)}


def _snapshot() -> dict:
    games: dict[str, dict] = {}
    players: dict[str, dict] = {}

    def gkey(away, home):
        return f"{away}@{home}"

    for m in _fetch_series(SERIES["game"]):
        away, home, d = _event(m["ticker"])
        if not away or not home:
            continue
        g = games.setdefault(gkey(away, home), {"away": away, "home": home, "date": d.isoformat() if d else None})
        p = _price(m)
        side = m["ticker"].split("-")[-1]
        side_team = norm_team(TEAM_FIX.get(side, side))
        if p is not None:
            g["p_home" if side_team == home else "p_away"] = round(p, 3)
    for kind in ("total", "spread"):
        ladders: dict[str, list] = {}
        for m in _fetch_series(SERIES[kind]):
            away, home, d = _event(m["ticker"])
            p = _price(m)
            strike = m.get("floor_strike")
            if not away or strike is None or p is None:
                continue
            key = gkey(away, home)
            if kind == "spread":
                side = re.sub(r"\d+$", "", m["ticker"].split("-")[-1])
                side_team = norm_team(TEAM_FIX.get(side, side))
                strike = float(strike) if side_team == home else -float(strike)  # home-perspective margin
                p = p if side_team == home else 1 - p
            ladders.setdefault(key, []).append((float(strike), p))
        for key, pts in ladders.items():
            st = ladder_stats(pts)
            if st:
                games.setdefault(key, {"away": key.split("@")[0], "home": key.split("@")[1], "date": None})[kind] = st
    for m in _fetch_series(SERIES["team_total"]):
        away, home, d = _event(m["ticker"])
        p = _price(m)
        strike = m.get("floor_strike")
        if not away or strike is None or p is None:
            continue
        side = re.sub(r"\d+$", "", m["ticker"].split("-")[-1])
        team = norm_team(TEAM_FIX.get(side, side))
        g = games.setdefault(gkey(away, home), {"away": away, "home": home, "date": d.isoformat() if d else None})
        g.setdefault("team_total_ladder", {}).setdefault(team, []).append((float(strike), p))
    for g in games.values():
        lad = g.pop("team_total_ladder", None)
        if lad:
            g["team_total"] = {t: ladder_stats(v) for t, v in lad.items()}
    # player markets
    for m in _fetch_series(SERIES["anytime_td"]):
        p = _price(m)
        name = m.get("yes_sub_title") or m.get("title", "").replace(" scores a touchdown", "")
        if p is None or not name:
            continue
        away, home, d = _event(m["ticker"])
        players.setdefault(norm_name(name), {"name": name})["anytime_td_p"] = round(p, 3)
        players[norm_name(name)]["game"] = gkey(away, home) if away else None
    for kind in ("pass_yds", "rush_yds", "rec_yds", "ff_pts"):
        ladders: dict[str, list] = {}
        names: dict[str, str] = {}
        for m in _fetch_series(SERIES[kind]):
            p = _price(m)
            strike = m.get("floor_strike")
            name = (m.get("yes_sub_title") or "").split(":")[0].strip() or None
            if p is None or strike is None or not name:
                continue
            # subtitle shapes vary ("Puka Nacua: 75+ yards"); strip the numeric tail
            name = re.sub(r"\s+\d.*$", "", name).strip()
            key = norm_name(name)
            names[key] = name
            ladders.setdefault(key, []).append((float(strike), p))
        for key, pts in ladders.items():
            st = ladder_stats(pts)
            if st:
                players.setdefault(key, {"name": names[key]})[kind] = st
    return {"games": games, "players": players}


def load(force: bool = False) -> tuple[dict, dict]:
    return cached_json("kalshi_nfl", _snapshot, ttl_seconds=3 * 3600, force=force)


def season_wins(force: bool = False) -> tuple[dict, dict]:
    """Expected regular-season wins per team from the KXNFLWINS-<team> ladders (when priced)."""
    def _fetch():
        out = {}
        for abbr in ("ARI", "ATL", "BAL", "BUF", "CAR", "CHI", "CIN", "CLE", "DAL", "DEN", "DET", "GB", "HOU", "IND", "JAC", "KC", "LA", "LAC", "LV", "MIA", "MIN", "NE", "NO", "NYG", "NYJ", "PHI", "PIT", "SEA", "SF", "TB", "TEN", "WAS"):
            try:
                ms = _fetch_series(f"KXNFLWINS-{abbr}", max_pages=1)
            except Exception:
                continue
            pts = [(float(m["floor_strike"]), _price(m)) for m in ms if m.get("floor_strike") is not None and _price(m) is not None]
            st = ladder_stats(pts)
            if st:
                out[norm_team(TEAM_FIX.get(abbr, abbr))] = st
        return out
    return cached_json("kalshi_wins", _fetch, ttl_seconds=24 * 3600, force=force)
