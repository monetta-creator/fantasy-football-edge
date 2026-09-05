"""Weekly projections under league scoring: Sleeper weekly raw stats + Vegas implied totals + variance.

Output rows carry mean and sd of weekly points so the lineup optimizer can simulate.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

import httpx

from . import config
from .players import Player
from .scoring import pa_buckets_from_mean, score
from .sources import schedule as schedule_src
from .sources.cache import cached_json
from .sources.common import norm_team, player_key
from .variance import weekly_sd

WEEK_URL = (
    "https://api.sleeper.com/projections/nfl/{season}/{week}?season_type=regular"
    "&position[]=QB&position[]=RB&position[]=WR&position[]=TE&position[]=K&position[]=DEF&order_by=pts_ppr"
)
STATE_URL = "https://api.sleeper.app/v1/state/nfl"
OFF_MAP = {
    "pass_yd": "pass_yd", "pass_td": "pass_td", "pass_int": "pass_int", "pass_2pt": "pass_2pt",
    "rush_yd": "rush_yd", "rush_td": "rush_td", "rush_2pt": "rush_2pt",
    "rec": "rec", "rec_yd": "rec_yd", "rec_td": "rec_td", "rec_2pt": "rec_2pt", "fum_lost": "fum_lost",
}
LEAGUE_AVG_TEAM_TOTAL = 22.5
PA_BLEND_VEGAS = 0.5  # weight on the Vegas opponent implied total vs Sleeper's pts_allow


def current_week() -> int:
    try:
        st, _ = cached_json("sleeper_state", lambda: httpx.get(STATE_URL, timeout=20).json(), ttl_seconds=3600)
        wk = int(st.get("week") or 1)
        return max(1, min(config.REG_SEASON_WEEKS, wk))
    except Exception:
        w1 = date.fromisoformat(config.WEEK1_TUESDAY)
        return max(1, min(config.REG_SEASON_WEEKS, (date.today() - w1).days // 7 + 1))


def _fetch_week(week: int) -> list[dict]:
    r = httpx.get(WEEK_URL.format(season=config.SEASON, week=week), timeout=60)
    r.raise_for_status()
    out = []
    for p in r.json():
        pl = p.get("player") or {}
        pos = pl.get("position")
        if pos not in config.POSITIONS:
            continue
        st = p.get("stats") or {}
        if not st:
            continue
        team = norm_team(p.get("team") or pl.get("team"))
        name = f"{team} D/ST" if pos == "DEF" else f"{pl.get('first_name', '')} {pl.get('last_name', '')}".strip()
        out.append({"key": player_key(name, pos, team), "name": name, "pos": pos, "team": team, "opp": norm_team(p.get("opponent")), "stats": st})
    return out


def canonical_stats(pos: str, st: dict) -> dict[str, float]:
    out: dict[str, float] = {}
    if pos in ("QB", "RB", "WR", "TE"):
        for k, ck in OFF_MAP.items():
            if k in st:
                out[ck] = float(st[k])
        ret = float(st.get("def_kr_td", 0) or 0) + float(st.get("pr_td", 0) or 0)
        if ret:
            out["ret_td"] = ret
    elif pos == "K":
        buckets = 0.0
        for k, ck in {"fgm_0_19": "fg_0_19", "fgm_20_29": "fg_20_29", "fgm_30_39": "fg_30_39", "fgm_40_49": "fg_40_49", "fgm_50p": "fg_50p"}.items():
            if k in st:
                out[ck] = float(st[k])
                buckets += float(st[k])
        fgm = float(st.get("fgm", 0) or 0)
        if "fgm_50p" not in st and fgm > buckets:
            out["fg_50p"] = round(fgm - buckets, 3)  # Sleeper omits the 50+ bucket; it is the remainder
        out["xp_made"] = float(st.get("xpm", 0) or 0)
    elif pos == "DEF":
        out["dst_sack"] = float(st.get("sack", 0) or 0)
        out["dst_int"] = float(st.get("int", 0) or 0)
        out["dst_fum_rec"] = float(st.get("fum_rec", 0) or 0)
        out["dst_td"] = float(st.get("def_td", 0) or 0)
        out["dst_ret_td"] = max(float(st.get("st_td", 0) or 0), float(st.get("def_kr_td", 0) or 0) + float(st.get("def_pr_td", 0) or 0))
        out["dst_safety"] = float(st.get("safe", 0) or 0)
        out["dst_blk"] = float(st.get("blk_kick", 0) or 0)
    return out


def vegas(week: int) -> dict[str, dict]:
    """team -> {opp, home, spread, total, implied, opp_implied} from the nflverse schedule (closing lines when present)."""
    games, _ = cached_json("schedule", lambda: schedule_src._fetch(), ttl_seconds=7 * 24 * 3600)
    out = {}
    for g in games:
        if g["week"] != week:
            continue
        try:
            spread = float(g.get("spread_line") or 0)  # positive = home favored
            total = float(g.get("total_line") or 0)
        except ValueError:
            spread, total = 0.0, 0.0
        if total <= 0:
            total = 2 * LEAGUE_AVG_TEAM_TOTAL
        home_imp = total / 2 + spread / 2
        away_imp = total / 2 - spread / 2
        out[g["home"]] = {"opp": g["away"], "home": True, "spread": spread, "total": total, "implied": round(home_imp, 2), "opp_implied": round(away_imp, 2), "gameday": g.get("gameday")}
        out[g["away"]] = {"opp": g["home"], "home": False, "spread": -spread, "total": total, "implied": round(away_imp, 2), "opp_implied": round(home_imp, 2), "gameday": g.get("gameday")}
    return out


@dataclass
class WeekRow:
    id: str
    name: str
    pos: str
    team: str | None
    opp: str | None
    mean: float
    sd: float
    on_bye: bool
    stats: dict = field(default_factory=dict)
    vegas: dict = field(default_factory=dict)
    note: str = ""

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name, "pos": self.pos, "team": self.team, "opp": self.opp, "mean": round(self.mean, 2), "sd": round(self.sd, 2),
                "on_bye": self.on_bye, "vegas": self.vegas, "note": self.note, "floor": round(max(0.0, self.mean - 1.28 * self.sd), 1), "ceiling": round(self.mean + 1.28 * self.sd, 1)}


def build_week(week: int, players: list[Player], variance_table: dict, force: bool = False) -> tuple[dict[str, WeekRow], dict]:
    raw, meta = cached_json(f"sleeper_week_{config.SEASON}_{week}", lambda: _fetch_week(week), ttl_seconds=3 * 3600, force=force)
    by_key = {r["key"]: r for r in raw}
    lines = vegas(week)
    out: dict[str, WeekRow] = {}
    for p in players:
        r = by_key.get(p.id)
        v = lines.get(p.team or "", {})
        if r is None:
            on_bye = bool(p.bye == week) or not v
            out[p.id] = WeekRow(p.id, p.name, p.pos, p.team, v.get("opp"), 0.0, 0.0, on_bye, {}, v, "bye" if on_bye else "no projection")
            continue
        st = canonical_stats(p.pos, r["stats"])
        note = ""
        if p.pos == "DEF":
            pa_sleeper = float(r["stats"].get("pts_allow") or LEAGUE_AVG_TEAM_TOTAL)
            pa = pa_sleeper if not v else (1 - PA_BLEND_VEGAS) * pa_sleeper + PA_BLEND_VEGAS * v["opp_implied"]
            st.update(pa_buckets_from_mean(pa, 1.0))
            note = f"opp implied {v.get('opp_implied', '?')} pts; blended PA {pa:.1f}"
        elif p.pos == "K" and v:
            scale = (v["implied"] / LEAGUE_AVG_TEAM_TOTAL) ** 0.5
            st = {k: val * (0.6 + 0.4 * scale) for k, val in st.items()}
            note = f"team implied {v['implied']} pts"
        mean = score(st)
        sd = weekly_sd(p.id, p.pos, mean, variance_table)
        out[p.id] = WeekRow(p.id, p.name, p.pos, p.team, r.get("opp") or v.get("opp"), mean, sd, False, st, v, note)
    # Vegas consistency: scale skill players toward implied team totals; keep the table for the dashboard
    from .market import apply_vegas_scaling
    meta["consistency"] = apply_vegas_scaling(out, lines)
    meta["week"] = week
    meta["vegas_games"] = len(lines) // 2
    return out, meta
