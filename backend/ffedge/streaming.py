"""Weekly K and DST streaming ranks from Vegas implied totals and weekly projections."""
from __future__ import annotations

from .weekly import WeekRow


def rank(week_rows: dict[str, WeekRow], pos: str, owner_of: dict[str, int], my_team: int, limit: int = 12) -> list[dict]:
    rows = []
    for r in week_rows.values():
        if r.pos != pos or r.on_bye:
            continue
        owner = owner_of.get(r.id)
        v = r.vegas or {}
        if pos == "DEF":
            mech = f"Opponent implied total {v.get('opp_implied', '?')} (spread {v.get('spread', '?'):+}); {r.note}"
        else:
            mech = f"Team implied total {v.get('implied', '?')}; {r.stats.get('fg_50p', 0):.2f} expected 50+ FGs (5 pts each)"
        rows.append({"id": r.id, "name": r.name, "team": r.team, "opp": r.opp, "mean": round(r.mean, 1), "floor": round(max(0, r.mean - 1.28 * r.sd), 1),
                     "ceiling": round(r.mean + 1.28 * r.sd, 1), "owner": owner, "mine": owner == my_team, "available": owner is None, "mechanism": mech,
                     "opp_implied": v.get("opp_implied"), "implied": v.get("implied"), "gameday": v.get("gameday")})
    rows.sort(key=lambda x: -x["mean"])
    return rows[:limit]
