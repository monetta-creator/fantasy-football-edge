"""Lineup optimizer with win probability (Monte Carlo over weekly point distributions).

Maximizing P(win) automatically prefers high-variance lineups when trailing and high-floor lineups
when favored; we surface both numbers so the choice is explainable.
"""
from __future__ import annotations

import itertools

import numpy as np

from . import config

SLOT_ELIG = [set(e) for _, e in config.ROSTER_SLOTS]
SLOT_NAMES = [s for s, _ in config.ROSTER_SLOTS]


def _assign(players: list[dict], order: list[int]) -> dict[str, dict] | None:
    """Greedy slot fill in the given priority order (nested eligibility => optimal for that order)."""
    caps = [1] * len(SLOT_ELIG)
    out: dict[str, dict] = {}
    for i in order:
        p = players[i]
        for s in range(len(SLOT_ELIG)):
            if caps[s] and p["pos"] in SLOT_ELIG[s]:
                caps[s] = 0
                out[SLOT_NAMES[s]] = p
                break
    return out


def best_by_mean(players: list[dict]) -> dict[str, dict]:
    order = sorted(range(len(players)), key=lambda i: -players[i]["mean"])
    return _assign(players, order)


def simulate_totals(lineup: list[dict], n: int, rng: np.random.Generator) -> np.ndarray:
    """Per-player truncated-normal draws summed to a weekly total."""
    if not lineup:
        return np.zeros(n)
    means = np.array([p["mean"] for p in lineup])
    sds = np.array([max(p["sd"], 0.5) for p in lineup])
    draws = rng.standard_normal((n, len(lineup))) * sds + means
    return np.clip(draws, -3.0, None).sum(axis=1)


def evaluate(my_lineup: list[dict], opp_lineup: list[dict], n: int = 20000, seed: int = 3) -> dict:
    rng = np.random.default_rng(seed)
    mine = simulate_totals(my_lineup, n, rng)
    opp = simulate_totals(opp_lineup, n, rng)
    return {
        "win_prob": float((mine > opp).mean()), "mean": float(mine.mean()), "sd": float(mine.std()),
        "p10": float(np.percentile(mine, 10)), "p90": float(np.percentile(mine, 90)),
        "opp_mean": float(opp.mean()), "opp_sd": float(opp.std()),
    }


def candidate_lineups(players: list[dict], max_alternates: int = 5) -> list[dict[str, dict]]:
    """Mean-optimal lineup plus variants that swap one starter for a bench alternate."""
    base = best_by_mean(players)
    cands = [base]
    starters = {p["id"] for p in base.values()}
    bench = sorted([p for p in players if p["id"] not in starters and p["mean"] > 0], key=lambda p: -p["mean"])[:max_alternates]
    for slot, starter in base.items():
        for alt in bench:
            if alt["pos"] not in SLOT_ELIG[SLOT_NAMES.index(slot)]:
                continue
            pool = [p for p in players if p["id"] != starter["id"]]
            forced = [i for i, p in enumerate(pool) if p["id"] == alt["id"]]
            order = forced + sorted([i for i in range(len(pool)) if i not in forced], key=lambda i: -pool[i]["mean"])
            lu = _assign(pool, order)
            if lu and {p["id"] for p in lu.values()} != starters:
                cands.append(lu)
    # de-duplicate by player set
    seen, out = set(), []
    for lu in cands:
        key = frozenset(p["id"] for p in lu.values())
        if key not in seen:
            seen.add(key)
            out.append(lu)
    return out


def optimize(players: list[dict], opp_lineup: list[dict], n: int = 20000) -> dict:
    """Return the max-win-probability lineup among candidates, with the mean-optimal for comparison."""
    cands = candidate_lineups(players)
    scored = []
    for lu in cands:
        ev = evaluate(list(lu.values()), opp_lineup, n)
        scored.append((ev, lu))
    scored.sort(key=lambda x: -x[0]["win_prob"])
    best_ev, best = scored[0]
    base_ev, base = next((ev, lu) for ev, lu in scored if lu is cands[0])
    changes = []
    for slot in SLOT_NAMES:
        a, b = base.get(slot), best.get(slot)
        if a and b and a["id"] != b["id"]:
            changes.append({"slot": slot, "out": a, "in": b})
    return {
        "lineup": {s: best[s] for s in SLOT_NAMES if s in best}, "eval": best_ev,
        "mean_lineup": {s: base[s] for s in SLOT_NAMES if s in base}, "mean_eval": base_ev,
        "changes_vs_mean": changes, "n_candidates": len(cands),
        "posture": "favored" if best_ev["win_prob"] >= 0.5 else "underdog",
    }
