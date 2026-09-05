"""Vegas consistency check and scaling: compare our projected team scoring with implied team totals."""
from __future__ import annotations

from . import config
from .weekly import WeekRow

FACTOR_MIN, FACTOR_MAX = 0.85, 1.15
ALPHA = 0.5  # projection scales with (implied / projected) ** ALPHA


def team_projection_points(rows: dict[str, WeekRow]) -> dict[str, dict]:
    """Projected NFL points per team from our weekly player projections (TDs + FG + XP; rec TDs == pass TDs)."""
    out: dict[str, dict] = {}
    for r in rows.values():
        if not r.team or r.on_bye or r.mean <= 0:
            continue
        t = out.setdefault(r.team, {"pass_td": 0.0, "rush_td": 0.0, "fg": 0.0, "xp": 0.0, "players": 0})
        st = r.stats or {}
        if r.pos == "QB":
            t["pass_td"] += float(st.get("pass_td", 0) or 0)
        if r.pos in ("QB", "RB", "WR", "TE"):
            t["rush_td"] += float(st.get("rush_td", 0) or 0)
            t["players"] += 1
        if r.pos == "K":
            t["fg"] += sum(float(st.get(k, 0) or 0) for k in ("fg_0_19", "fg_20_29", "fg_30_39", "fg_0_39", "fg_40_49", "fg_50p"))
            t["xp"] += float(st.get("xp_made", 0) or 0)
    for t in out.values():
        t["proj_points"] = round(6 * (t["pass_td"] + t["rush_td"]) + 3 * t["fg"] + t["xp"], 1)
    return out


def consistency(rows: dict[str, WeekRow], lines: dict[str, dict]) -> list[dict]:
    """Per team: Vegas implied total vs our projected points, the scaling factor applied, and a flag."""
    proj = team_projection_points(rows)
    out = []
    for team, v in lines.items():
        p = proj.get(team)
        if not p or p["players"] < 3:
            continue
        implied = float(v.get("implied") or 0)
        ratio = implied / p["proj_points"] if p["proj_points"] > 0 else 1.0
        factor = min(FACTOR_MAX, max(FACTOR_MIN, ratio ** ALPHA))
        flag = "high" if ratio < 0.85 else "low" if ratio > 1.15 else "ok"
        out.append({"team": team, "opp": v.get("opp"), "home": v.get("home"), "implied": round(implied, 1), "proj_points": p["proj_points"], "ratio": round(ratio, 3),
                    "factor": round(factor, 3), "flag": flag, "pass_td": round(p["pass_td"], 2), "rush_td": round(p["rush_td"], 2), "fg": round(p["fg"], 2)})
    out.sort(key=lambda x: x["ratio"])
    return out


def apply_vegas_scaling(rows: dict[str, WeekRow], lines: dict[str, dict]) -> list[dict]:
    """Scale skill-player means toward Vegas (in place). Returns the consistency table."""
    table = consistency(rows, lines)
    factors = {t["team"]: t["factor"] for t in table}
    for r in rows.values():
        if r.pos in ("QB", "RB", "WR", "TE") and r.team in factors and not r.on_bye and r.mean > 0:
            f = factors[r.team]
            if abs(f - 1.0) > 0.005:
                r.mean = round(r.mean * f, 2)
                r.sd = round(r.sd * f, 2)
                r.note = (r.note + "; " if r.note else "") + f"Vegas scaling ×{f:.2f}"
            r.vegas = {**(r.vegas or {}), "factor": f}
    return table
