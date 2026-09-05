"""Sportsbook player props via The Odds API (free tier: 500 credits/month; a market costs 1 credit per event).

Props are the market's weekly projection. We convert lines + prices to component means under league
scoring and blend them with the model projection; the gap is the sanity check.
"""
from __future__ import annotations

import json
import math
import time

import httpx

from . import config
from .config import Settings
from .sources.common import norm_name

BASE = "https://api.the-odds-api.com/v4"
SPORT = "americanfootball_nfl"
MARKETS = ["player_pass_yds", "player_pass_tds", "player_rush_yds", "player_receptions", "player_reception_yds", "player_anytime_td"]
COMPONENT = {"player_pass_yds": "pass_yd", "player_pass_tds": "pass_td", "player_rush_yds": "rush_yd", "player_receptions": "rec", "player_reception_yds": "rec_yd"}
SD_FRAC = {"pass_yd": 0.28, "pass_td": 0.8, "rush_yd": 0.45, "rec": 0.38, "rec_yd": 0.45}
CACHE = config.CACHE_DIR / "odds_week_{season}_{week}.json"


def available(settings: Settings) -> bool:
    return bool(getattr(settings, "odds_api_key", None))


def _ppf(p: float) -> float:
    """Inverse normal CDF (Acklam approximation, adequate for 0.02<p<0.98)."""
    p = min(0.98, max(0.02, p))
    a = [-3.969683028665376e01, 2.209460984245205e02, -2.759285104469687e02, 1.383577518672690e02, -3.066479806614716e01, 2.506628277459239e00]
    b = [-5.447609879822406e01, 1.615858368580409e02, -1.556989798598866e02, 6.680131188771972e01, -1.328068155288572e01]
    q = p - 0.5
    r = q * q
    return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1)


def _implied(price) -> float | None:
    """American or decimal odds -> implied probability (with vig)."""
    if price is None:
        return None
    price = float(price)
    if price > 1.0 and price < 1.01:
        return None
    if -100 < price < 100 and price != 0 and abs(price) < 1.5:  # decimal (rare shape)
        return 1.0 / price
    if price >= 100:
        return 100.0 / (price + 100.0)
    if price <= -100:
        return -price / (-price + 100.0)
    return 1.0 / price if price > 1 else None


def fetch_week(settings: Settings, week: int, force: bool = False, ttl_seconds: int = 12 * 3600, max_events: int = 20) -> tuple[dict, dict]:
    """Return ({"players": {normname: {market: {...}}}, "events": [...]}, meta).

    Credits are only spent when force=True (the "Pull props" button or the weekly job). Otherwise the
    cached pull for the week is used however old it is, so page loads never cost anything."""
    path = config.CACHE_DIR / f"odds_week_{config.SEASON}_{week}.json"
    if path.exists() and not force:
        blob = json.loads(path.read_text())
        return blob["data"], {"fetched_at": blob["fetched_at"], "from_cache": True, "credits_remaining": blob.get("credits_remaining"), "error": None}
    if not force:
        return {"players": {}, "events": []}, {"fetched_at": None, "from_cache": False, "credits_remaining": None, "error": "not pulled yet (press Pull props)"}
    if not available(settings):
        if path.exists():
            blob = json.loads(path.read_text())
            return blob["data"], {"fetched_at": blob["fetched_at"], "from_cache": True, "credits_remaining": blob.get("credits_remaining"), "error": "no ODDS_API_KEY"}
        return {"players": {}, "events": []}, {"fetched_at": None, "from_cache": False, "credits_remaining": None, "error": "no ODDS_API_KEY"}
    key = settings.odds_api_key
    ev = httpx.get(f"{BASE}/sports/{SPORT}/events", params={"apiKey": key}, timeout=30)
    ev.raise_for_status()
    # the events feed lists the whole season; keep only this fantasy week's window (Tue..Mon) to protect credits
    from datetime import date, datetime, timedelta, timezone
    w1 = datetime.combine(date.fromisoformat(config.WEEK1_TUESDAY), datetime.min.time(), tzinfo=timezone.utc)
    start = w1 + timedelta(days=7 * (week - 1))
    end = start + timedelta(days=7, hours=12)  # include Monday night (Tue 00:15 UTC)
    events = []
    for e in ev.json():
        try:
            ct = datetime.fromisoformat(e["commence_time"].replace("Z", "+00:00"))
        except Exception:
            continue
        if start <= ct < end:
            events.append(e)
    events = events[:max_events]
    remaining = ev.headers.get("x-requests-remaining")
    players: dict[str, dict] = {}
    kept = []
    for e in events:
        try:
            r = httpx.get(f"{BASE}/sports/{SPORT}/events/{e['id']}/odds", params={"apiKey": key, "regions": "us", "markets": ",".join(MARKETS), "oddsFormat": "american"}, timeout=30)
            if r.status_code != 200:
                continue
            remaining = r.headers.get("x-requests-remaining", remaining)
            data = r.json()
        except Exception:
            continue
        kept.append({"id": e["id"], "home": e.get("home_team"), "away": e.get("away_team"), "commence": e.get("commence_time")})
        # take the first bookmaker that has each market (or average lines across books)
        for bk in data.get("bookmakers", []):
            for m in bk.get("markets", []):
                mk = m.get("key")
                if mk not in MARKETS:
                    continue
                by_player: dict[str, dict] = {}
                for o in m.get("outcomes", []):
                    name = o.get("description") or o.get("name")
                    if not name:
                        continue
                    d = by_player.setdefault(name, {})
                    side = (o.get("name") or "").lower()
                    if mk == "player_anytime_td":
                        if side == "yes":
                            d["yes"] = o.get("price")
                    else:
                        d["line"] = o.get("point")
                        d[side] = o.get("price")
                for name, d in by_player.items():
                    pl = players.setdefault(norm_name(name), {"name": name, "markets": {}, "books": set()})
                    pl["books"].add(bk.get("key"))
                    slot = pl["markets"].setdefault(mk, {"samples": []})
                    slot["samples"].append(d)
    # aggregate samples across books
    for pl in players.values():
        pl["books"] = sorted(pl["books"])
        for mk, slot in pl["markets"].items():
            samples = slot.pop("samples")
            if mk == "player_anytime_td":
                ps = [_implied(s.get("yes")) for s in samples if s.get("yes") is not None]
                ps = [p for p in ps if p]
                if ps:
                    p = sum(ps) / len(ps) / 1.06  # crude vig removal for one-sided market
                    slot.update({"p_td": round(p, 3), "exp_td": round(-math.log(max(1e-6, 1 - p)), 3), "books": len(ps)})
            else:
                lines = [s.get("line") for s in samples if s.get("line") is not None]
                if not lines:
                    continue
                line = sum(lines) / len(lines)
                po = []
                for s in samples:
                    o, u = _implied(s.get("over")), _implied(s.get("under"))
                    if o and u:
                        po.append(o / (o + u))
                p_over = sum(po) / len(po) if po else 0.5
                comp = COMPONENT[mk]
                sd = SD_FRAC[comp] * (line if comp != "pass_td" else 1.0) if comp != "pass_td" else SD_FRAC[comp]
                mean = line + _ppf(p_over) * sd
                slot.update({"line": round(line, 2), "p_over": round(p_over, 3), "mean": round(mean, 2), "books": len(lines)})
    out = {"players": players, "events": kept}
    config.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"fetched_at": time.time(), "credits_remaining": remaining, "data": out}))
    return out, {"fetched_at": time.time(), "from_cache": False, "credits_remaining": remaining, "error": None}


def market_points(pos: str, markets: dict) -> dict:
    """League points implied by the props that exist, plus which components were covered."""
    comps: dict[str, float] = {}
    for mk, d in markets.items():
        if mk in COMPONENT and d.get("mean") is not None:
            comps[COMPONENT[mk]] = d["mean"]
    if markets.get("player_anytime_td", {}).get("exp_td") is not None:
        td = markets["player_anytime_td"]["exp_td"]
        comps["rush_td" if pos == "RB" else "rec_td"] = td  # anytime TD covers rush+rec; attribute to the main channel
    pts = 0.0
    from .scoring import ALL_SCORING
    for k, v in comps.items():
        pts += ALL_SCORING.get(k, 0.0) * v
    return {"components": comps, "points": round(pts, 2), "covered": sorted(comps.keys())}


def blend(row_stats: dict, row_mean: float, pos: str, markets: dict, weight: float = 0.5) -> tuple[float, dict]:
    """Component-wise blend of model stats with market components; returns (new_mean, market_summary)."""
    from .scoring import score

    mp = market_points(pos, markets)
    if not mp["components"]:
        return row_mean, {"available": False}
    st = dict(row_stats)
    for k, v in mp["components"].items():
        st[k] = (1 - weight) * float(st.get(k, 0.0) or 0.0) + weight * v
    new_mean = score(st)
    return new_mean, {"available": True, "points": mp["points"], "components": mp["components"], "covered": mp["covered"], "model_mean_before": round(row_mean, 2), "blended_mean": round(new_mean, 2),
                      "delta_market_vs_model": round(mp["points"] - row_mean, 2), "lines": {mk: {k: v for k, v in d.items() if k in ("line", "p_over", "p_td", "exp_td", "books")} for mk, d in markets.items()}}
