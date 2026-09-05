"""Value of stashing an injured player in an IR slot: weighted return-week surplus over replacement."""
from __future__ import annotations

from . import config
from .players import Player

RISK = {"IR-R": 0.85, "IR": 0.7, "IR-LT": 0.4, "PUP-R": 0.7, "PUP-P": 0.7, "NFI-R": 0.7, "NFI-A": 0.7,
        "O": 0.9, "SUSP": 0.95, "CEL": 0.8, "NA": 0.45, "DNR": 0.3, "D": 0.9}


def week_weight(w: int) -> float:
    if w in config.PLAYOFF_WEEKS:
        return 1.5
    if w >= 8:
        return 1.0
    return 0.5


def stash_value(p: Player, repl_ppg: float) -> float:
    """Sum over weeks from expected return through week 17 of weight(w) * (ppg - repl_ppg), times return risk."""
    inj = p.injury or {}
    rw = inj.get("return_week")
    if not inj.get("flag") or rw is None:
        return 0.0
    rw = max(1, int(rw))
    surplus = max(0.0, p.ppg - repl_ppg)
    if surplus <= 0:
        return 0.0
    total = 0.0
    for w in range(rw, config.PLAYOFF_WEEKS[-1] + 1):
        if p.bye and w == p.bye:
            continue
        total += week_weight(w) * surplus
    return round(total * RISK.get(inj.get("code"), 0.7), 1)


def rank_stash(players: list[Player], limit: int = 40) -> list[dict]:
    rows = []
    for p in players:
        sv = p.__dict__.get("stash_value", 0.0)
        if not p.injury.get("flag") or sv <= 0:
            continue
        rows.append({
            "id": p.id, "name": p.name, "pos": p.pos, "team": p.team, "pts": p.pts, "ppg": p.ppg,
            "adp": p.adp, "vorp": p.__dict__.get("vorp"), "stash_value": sv,
            "status": p.injury.get("code"), "label": p.injury.get("label"), "type": p.injury.get("type"),
            "return_week": p.injury.get("return_week"), "return_date": p.injury.get("return_date"),
            "ir_eligible": p.injury.get("ir_eligible"), "comment": p.injury.get("comment"), "bye": p.bye,
        })
    rows.sort(key=lambda r: -r["stash_value"])
    return rows[:limit]
