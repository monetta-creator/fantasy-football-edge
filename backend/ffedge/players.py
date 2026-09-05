"""Build the unified player pool: match across sources, blend raw stats, score, attach ADP + injuries."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime

import numpy as np

from . import config
from .adp_model import sigma_for
from .scoring import score, score_breakdown
from .sources import espn, injuries, schedule, sleeper, yahoo_public
from .sources.common import norm_name

PROJ_WEIGHTS = {"espn": 0.5, "sleeper": 0.5}
ADP_WEIGHTS = {"yahoo": 0.6, "sleeper": 0.2, "espn": 0.2}
DEFAULT_GAMES = 17.0
UNDRAFTED_ADP = 200.0

# Yahoo status codes -> plain label
STATUS_LABELS = {
    "Q": "Questionable", "D": "Doubtful", "O": "Out", "IR": "IR", "IR-R": "IR (designated to return)",
    "IR-LT": "IR (long term)", "PUP-R": "PUP", "PUP-P": "PUP", "NFI-R": "NFI", "NFI-A": "NFI",
    "SUSP": "Suspended", "NA": "Inactive", "DNR": "Did not report",
}


@dataclass
class Player:
    id: str
    name: str
    pos: str
    team: str | None
    stats: dict[str, float]
    pts: float
    games: float
    ppg: float
    adp: float
    adp_sigma: float
    adp_sources: dict[str, float]
    proj_sources: dict[str, float]  # per-source points under league scoring
    proj_spread: float
    yahoo_rank: float | None
    yahoo_id: str | None
    espn_id: int | None
    sleeper_id: str | None
    bye: int | None
    injury: dict
    outlook: str = ""
    breakdown: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = self.__dict__.copy()
        d["stats"] = {k: round(v, 1) for k, v in self.stats.items()}
        return d


def _blend_stats(parts: dict[str, dict[str, float]]) -> dict[str, float]:
    """Weighted average per stat over sources that provide a non-empty stat line."""
    keys = set()
    for st in parts.values():
        keys.update(st.keys())
    out = {}
    for k in keys:
        num = 0.0
        den = 0.0
        for src, st in parts.items():
            if k in st:
                w = PROJ_WEIGHTS.get(src, 0.5)
                num += w * st[k]
                den += w
        if den > 0:
            out[k] = num / den
    return out


def _return_week(return_date: str | None) -> int | None:
    if not return_date:
        return None
    try:
        d = date.fromisoformat(return_date[:10])
    except ValueError:
        return None
    w1 = date.fromisoformat(config.WEEK1_TUESDAY)
    wk = (d - w1).days // 7 + 1
    return int(max(1, min(config.REG_SEASON_WEEKS + 1, wk)))


def _injury(yrow: dict | None, erow: dict | None, srow: dict | None, ir_plus: bool) -> dict:
    ystatus = (yrow or {}).get("status")
    efs = (erow or {}).get("fantasy_status")
    estatus = (erow or {}).get("status")
    sstatus = (srow or {}).get("injury_status")
    # Best-guess Yahoo-style code
    code = ystatus
    if not code and efs:
        code = {"QUESTIONABLE": "Q", "DOUBTFUL": "D", "OUT": "O", "RESERVE-CEL": "SUSP"}.get(efs, efs)
    if not code and sstatus:
        code = {"Questionable": "Q", "Doubtful": "D", "Out": "O", "IR": "IR", "PUP": "PUP-R", "Sus": "SUSP", "NA": "NA"}.get(sstatus, sstatus)
    eligible_set = set(config.IR_ELIGIBLE_STATUSES) | (config.IR_PLUS_EXTRA if ir_plus else set())
    rw = _return_week((erow or {}).get("return_date"))
    if rw is None and code in ("IR", "IR-R", "PUP-R", "PUP-P", "NFI-R", "NFI-A"):
        rw = 5
    elif rw is None and code == "O":
        rw = 2
    elif rw is None and code == "SUSP":
        rw = 4
    injured = bool(code and code not in ("Q", None))
    return {
        "code": code,
        "label": STATUS_LABELS.get(code, code) if code else None,
        "yahoo_status": ystatus,
        "espn_status": estatus,
        "espn_fantasy_status": efs,
        "sleeper_status": sstatus,
        "type": (erow or {}).get("type") or (yrow or {}).get("injury_note") or (srow or {}).get("injury_body_part"),
        "return_date": (erow or {}).get("return_date"),
        "return_week": rw if injured else None,
        "comment": (erow or {}).get("comment"),
        "ir_eligible": bool(code in eligible_set),
        "flag": injured,
    }


def build_pool(force: bool = False, ir_plus: bool = False, max_players: int = 480) -> tuple[list[Player], dict]:
    s_rows, s_meta = sleeper.load(force=force)
    e_rows, e_meta = espn.load(force=force)
    y_rows, y_meta = yahoo_public.load(force=force)
    inj, i_meta = injuries.load(force=force)
    sched, sc_meta = schedule.load(force=force)

    by_key: dict[str, dict] = {}
    for r in s_rows:
        by_key.setdefault(r["key"], {})["sleeper"] = r
    for r in e_rows:
        by_key.setdefault(r["key"], {})["espn"] = r
    for r in y_rows:
        by_key.setdefault(r["key"], {})["yahoo"] = r

    # Second pass: name-only fallback match for keys that exist in only one source (team mismatch is
    # irrelevant since key ignores team for non-DEF; nothing to do here beyond DEF which keys by team).

    players: list[Player] = []
    for key, srcs in by_key.items():
        e = srcs.get("espn")
        s = srcs.get("sleeper")
        y = srcs.get("yahoo")
        base = e or s or y
        pos = base["pos"]
        name = (e or y or s)["name"]
        team = (e or s or y).get("team")
        parts = {}
        if e and e.get("stats"):
            parts["espn"] = e["stats"]
        if s and s.get("stats"):
            parts["sleeper"] = s["stats"]
        if not parts:
            continue
        stats = _blend_stats(parts)
        pts = score(stats)
        if pts <= 0:
            continue
        proj_sources = {src: score(st) for src, st in parts.items()}
        spread = float(max(proj_sources.values()) - min(proj_sources.values())) if len(proj_sources) > 1 else 0.0
        games = (e or {}).get("games") or DEFAULT_GAMES
        games = float(min(max(games, 1.0), DEFAULT_GAMES))
        adp_sources = {}
        if y and y.get("adp"):
            adp_sources["yahoo"] = float(y["adp"])
        if s and s.get("adp"):
            adp_sources["sleeper"] = float(s["adp"])
        if e and e.get("adp"):
            adp_sources["espn"] = float(e["adp"])
        if adp_sources:
            num = sum(ADP_WEIGHTS[k] * v for k, v in adp_sources.items())
            den = sum(ADP_WEIGHTS[k] for k in adp_sources)
            adp = num / den
            adp_spread = min(max(adp_sources.values()) - min(adp_sources.values()), 60.0)
        elif y and y.get("yahoo_rank"):
            adp = float(y["yahoo_rank"]) * 1.05
            adp_spread = 10.0
        else:
            adp = UNDRAFTED_ADP
            adp_spread = 20.0
        inj_row = inj.get(f"{pos}:{norm_name(name)}") if pos != "DEF" else None
        if inj_row is None and pos == "K":
            inj_row = inj.get(f"PK:{norm_name(name)}")
        bye = (y or {}).get("bye")
        if bye is None and team and team in sched["byes"] and sched["byes"][team]:
            bye = sched["byes"][team][0]
        p = Player(
            id=key, name=name, pos=pos, team=team, stats=stats, pts=pts, games=games,
            ppg=round(pts / games, 2), adp=round(adp, 1), adp_sigma=round(sigma_for(adp, adp_spread), 2),
            adp_sources=adp_sources, proj_sources=proj_sources, proj_spread=round(spread, 1),
            yahoo_rank=(y or {}).get("yahoo_rank"), yahoo_id=(y or {}).get("yahoo_id"),
            espn_id=(e or {}).get("espn_id"), sleeper_id=(s or {}).get("sleeper_id"), bye=bye,
            injury=_injury(y, inj_row, s, ir_plus), outlook=(e or {}).get("outlook") or "",
            breakdown=score_breakdown(stats),
        )
        players.append(p)

    # Keep the draft-relevant pool: sort by a mix of ADP and points so both market and model views survive.
    players.sort(key=lambda p: (p.adp, -p.pts))
    by_pts = sorted(players, key=lambda p: -p.pts)
    keep = set(p.id for p in players[:max_players]) | set(p.id for p in by_pts[:max_players])
    # always keep all K and DEF with points
    keep |= {p.id for p in players if p.pos in ("K", "DEF")}
    players = [p for p in players if p.id in keep]
    players.sort(key=lambda p: (p.adp, -p.pts))
    meta = {
        "sleeper": s_meta, "espn": e_meta, "yahoo": y_meta, "injuries": i_meta, "schedule": sc_meta,
        "counts": {"sleeper": len(s_rows), "espn": len(e_rows), "yahoo": len(y_rows), "pool": len(players)},
        "built_at": datetime.now().isoformat(timespec="seconds"),
    }
    return players, meta
