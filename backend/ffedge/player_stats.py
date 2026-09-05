"""Derived per-player statistics for the detail page: rates, trends, consistency, position ranks."""
from __future__ import annotations

import statistics

from .players import Player

BOOM = 25.0
BUST = 8.0
STARTABLE = {"QB": 18.0, "RB": 12.0, "WR": 12.0, "TE": 9.0, "K": 8.0, "DEF": 7.0}


def _avg(xs):
    xs = [x for x in xs if x is not None]
    return round(statistics.fmean(xs), 2) if xs else None


def rates_2025(pos: str, weeks: list[dict]) -> dict:
    """Per-game rates from last season's weekly rows (stats + extra)."""
    if not weeks:
        return {}
    g = len(weeks)
    S = lambda k: sum(float(w.get("stats", {}).get(k, 0) or 0) for w in weeks)  # noqa: E731
    E = lambda k: sum(float(w.get("extra", {}).get(k, 0) or 0) for w in weeks)  # noqa: E731
    out: dict[str, float | None] = {"games": g}
    if pos == "QB":
        att, cmp_, py, ptd, pint, ry, rtd, car = E("attempts"), E("completions"), S("pass_yd"), S("pass_td"), S("pass_int"), S("rush_yd"), S("rush_td"), E("carries")
        out.update({"pass_att_per_game": round(att / g, 1), "comp_pct": round(100 * cmp_ / att, 1) if att else None, "yds_per_att": round(py / att, 2) if att else None,
                    "pass_yds_per_game": round(py / g, 1), "pass_td_rate_pct": round(100 * ptd / att, 2) if att else None, "int_rate_pct": round(100 * pint / att, 2) if att else None,
                    "rush_yds_per_game": round(ry / g, 1), "rush_td": rtd, "carries_per_game": round(car / g, 1)})
    elif pos in ("RB", "WR", "TE"):
        tg, rec, ry, rtd, car, ruy, rutd = E("targets"), S("rec"), S("rec_yd"), S("rec_td"), E("carries"), S("rush_yd"), S("rush_td")
        out.update({"targets_per_game": round(tg / g, 1), "receptions_per_game": round(rec / g, 1), "catch_pct": round(100 * rec / tg, 1) if tg else None,
                    "yds_per_target": round(ry / tg, 2) if tg else None, "yds_per_rec": round(ry / rec, 1) if rec else None, "rec_yds_per_game": round(ry / g, 1),
                    "rec_td": rtd, "carries_per_game": round(car / g, 1), "yds_per_carry": round(ruy / car, 2) if car else None, "rush_yds_per_game": round(ruy / g, 1), "rush_td": rutd,
                    "touches_per_game": round((rec + car) / g, 1), "td_per_game": round((rtd + rutd) / g, 2)})
    elif pos == "K":
        fgm = S("fg_0_19") + S("fg_20_29") + S("fg_30_39") + S("fg_40_49") + S("fg_50p")
        att = E("fg_att")
        out.update({"fg_made_per_game": round(fgm / g, 2), "fg_pct": round(100 * fgm / att, 1) if att else None, "fg_50plus": S("fg_50p"), "xp_per_game": round(S("xp_made") / g, 2), "long": max((float(w.get("extra", {}).get("fg_long", 0) or 0) for w in weeks), default=None)})
    elif pos == "DEF":
        out.update({"sacks_per_game": round(S("dst_sack") / g, 2), "takeaways_per_game": round((S("dst_int") + S("dst_fum_rec")) / g, 2), "def_td": S("dst_td") + S("dst_ret_td"),
                    "pts_allowed_per_game": _avg([w.get("stats", {}).get("pa") for w in weeks])})
    return out


def consistency(pos: str, weeks: list[dict]) -> dict:
    if not weeks:
        return {}
    pts = [w["pts"] for w in weeks]
    thr = STARTABLE.get(pos, 10.0)
    last4 = pts[-4:]
    first_half = pts[: max(1, len(pts) // 2)]
    second_half = pts[len(pts) // 2:]
    rolling = []
    for i in range(len(weeks)):
        win = pts[max(0, i - 2): i + 1]
        rolling.append({"week": weeks[i]["week"], "avg3": round(statistics.fmean(win), 2)})
    return {
        "startable_threshold": thr, "startable_pct": round(100 * sum(1 for x in pts if x >= thr) / len(pts)), "boom_pct": round(100 * sum(1 for x in pts if x >= BOOM) / len(pts)),
        "bust_pct": round(100 * sum(1 for x in pts if x < BUST) / len(pts)), "best": max(pts), "worst": min(pts), "median": round(statistics.median(pts), 1),
        "last4_avg": round(statistics.fmean(last4), 2), "first_half_avg": round(statistics.fmean(first_half), 2), "second_half_avg": round(statistics.fmean(second_half), 2) if second_half else None,
        "trend": ("up" if second_half and statistics.fmean(second_half) > statistics.fmean(first_half) * 1.1 else "down" if second_half and statistics.fmean(second_half) < statistics.fmean(first_half) * 0.9 else "flat"),
        "rolling": rolling,
    }


def position_ranks(p: Player, players: list[Player], hist_table: dict) -> dict:
    same = [q for q in players if q.pos == p.pos]
    by_pts = sorted(same, key=lambda q: -q.pts)
    by_vorp = sorted(same, key=lambda q: -q.vorp)
    by_adp = sorted(same, key=lambda q: q.adp)
    hp = hist_table.get("players") or {}
    last = sorted([(k, v["mean"]) for k, v in hp.items() if k.startswith(p.pos + ":") and v.get("games", 0) >= 6], key=lambda kv: -kv[1])
    rank_2025 = next((i + 1 for i, (k, _) in enumerate(last) if k == p.id), None)
    return {
        "proj_rank": next((i + 1 for i, q in enumerate(by_pts) if q.id == p.id), None), "vorp_rank": next((i + 1 for i, q in enumerate(by_vorp) if q.id == p.id), None),
        "adp_rank": next((i + 1 for i, q in enumerate(by_adp) if q.id == p.id), None), "rank_2025_ppg": rank_2025, "n_pos": len(same), "n_2025": len(last),
    }
