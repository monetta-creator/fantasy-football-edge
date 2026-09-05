"""Two-option decision with detailed, deterministic reasons for each candidate at my pick."""
from __future__ import annotations

from . import config
from .players import Player

POS_LABEL = {"QB": "QB", "RB": "RB", "WR": "WR", "TE": "TE", "K": "kicker", "DEF": "defense"}


def _my_counts(picks: list[dict], by_id: dict[str, Player]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for p in picks:
        if p["team"] == config.MY_SLOT and p["player_id"] in by_id:
            pos = by_id[p["player_id"]].pos
            counts[pos] = counts.get(pos, 0) + 1
    return counts


def _slot_for(pos: str, counts: dict[str, int]) -> str:
    n = counts.get(pos, 0)
    if pos == "QB":
        return "QB starter" if n == 0 else "backup QB (bench)"
    if pos == "TE":
        return "TE starter" if n == 0 else "TE2 (W/R/T flex or bench)"
    if pos == "RB":
        return ["RB starter", "RB2 (W/R flex)", "RB3 (W/R/T flex)"][n] if n < 3 else f"RB{n + 1} (bench depth)"
    if pos == "WR":
        return ["WR1 starter", "WR2 starter", "WR3 (W/R flex)", "WR4 (W/R/T flex)"][n] if n < 4 else f"WR{n + 1} (bench depth)"
    if pos in ("K", "DEF"):
        return f"{POS_LABEL[pos]} starter" if n == 0 else f"second {POS_LABEL[pos]} (unnecessary)"
    return pos


def reasons_for(c: dict, other: dict, rec: dict, picks: list[dict], by_id: dict[str, Player], players: list[Player], hist: dict | None) -> list[dict]:
    p = by_id[c["id"]]
    drafted = {x["player_id"] for x in picks}
    counts = _my_counts(picks, by_id)
    next_pick = rec.get("next_pick")
    out: list[dict] = []

    # 1. Value vs replacement and vs next-best at position
    same_pos = sorted([q for q in players if q.pos == p.pos and q.id not in drafted], key=lambda q: -q.pts)
    rank_pos = next((i + 1 for i, q in enumerate(same_pos) if q.id == p.id), None)
    nxt = next((q for q in same_pos if q.id != p.id), None)
    txt = f"{p.vorp:+.0f} VORP: {p.pts:.0f} projected vs {p.__dict__.get('repl_pts', 0):.0f} for the best {POS_LABEL[p.pos]} left on waivers after the draft."
    if rank_pos:
        txt += f" #{rank_pos} of available {p.pos}s"
        if nxt:
            txt += f", {p.pts - nxt.pts:+.0f} pts vs the next one ({nxt.name}, {nxt.pts:.0f})."
    out.append({"kind": "value", "text": txt, "good": p.vorp > 0})

    # 2. Scarcity / drop-off at my next pick
    sc = {s["pos"]: s for s in rec.get("scarcity", [])}
    s = sc.get(p.pos)
    if s and s.get("dropoff_to_next") is not None and next_pick:
        drops = {k: v.get("dropoff_to_next") or 0 for k, v in sc.items() if k in ("QB", "RB", "WR", "TE")}
        biggest = max(drops, key=drops.get) if drops else None
        txt = f"Best {p.pos} still there at your next pick (#{next_pick}) projects {s['expected_best_at_next']:.0f}, a drop of {s['dropoff_to_next']:.0f} pts."
        if biggest == p.pos:
            txt += " That is the steepest drop-off of any position right now."
        else:
            txt += f" ({biggest} drops more: {drops[biggest]:.0f}.)"
        out.append({"kind": "scarcity", "text": txt, "good": biggest == p.pos})

    # 3. Availability
    pg = c.get("p_gone_by_next")
    if pg is not None and next_pick:
        if pg >= 0.6:
            out.append({"kind": "availability", "text": f"Gone before #{next_pick} in {pg:.0%} of simulated drafts. It is now or never.", "good": True})
        else:
            out.append({"kind": "availability", "text": f"Still available at #{next_pick} in {1 - pg:.0%} of simulated drafts; you could take the other option now and hope he lasts.", "good": False})

    # 4. Roster fit
    slot = _slot_for(p.pos, counts)
    have = ", ".join(f"{v} {k}" for k, v in sorted(counts.items())) or "nobody yet"
    out.append({"kind": "fit", "text": f"Would be your {slot}. Drafted so far: {have}.", "good": "bench" not in slot and "unnecessary" not in slot})

    # 5. Simulation outcome
    d = c["roster_score"] - other["roster_score"]
    out.append({"kind": "simulation", "text": f"Final-roster value {c['roster_score']:.0f} ± {c['roster_score_se']} across {rec.get('n_sims')} simulated drafts, {d:+.1f} vs {other['name']}. Confidence in the gap: {rec.get('confidence')}.", "good": d >= 0})

    # 6. Scoring mechanism
    out.append({"kind": "scoring", "text": c.get("mechanism", ""), "good": True})

    # 7. Market view
    by_vorp = sorted([q for q in players if q.id not in drafted], key=lambda q: -q.vorp)
    vrank = next((i + 1 for i, q in enumerate(by_vorp) if q.id == p.id), None)
    by_adp = sorted([q for q in players if q.id not in drafted], key=lambda q: q.adp)
    arank = next((i + 1 for i, q in enumerate(by_adp) if q.id == p.id), None)
    if vrank and arank:
        verdict = "the market undervalues him" if arank - vrank >= 5 else "the market overvalues him" if vrank - arank >= 5 else "market and model agree"
        yr = f"Yahoo rank {p.yahoo_rank:.0f}" if p.yahoo_rank else "no Yahoo rank"
        out.append({"kind": "market", "text": f"ADP {p.adp:.1f} ({yr}): #{arank} among available by ADP vs #{vrank} by our VORP, so {verdict}.", "good": arank >= vrank})

    # 8. Risks: injury, bye overlap, source disagreement, games, volatility
    inj = p.injury or {}
    if inj.get("flag") or inj.get("code") == "Q":
        out.append({"kind": "risk", "text": f"Status {inj.get('label') or inj.get('code')}{(' · ' + inj['type']) if inj.get('type') else ''}{(' · expected back week ' + str(inj['return_week'])) if inj.get('return_week') else ''}{' · IR-eligible, would not use a bench slot' if inj.get('ir_eligible') else ''}.", "good": bool(inj.get("ir_eligible"))})
    if p.games and p.games < 16.5:
        out.append({"kind": "risk", "text": f"Projected for only {p.games:.0f} games ({p.ppg:.1f} per game when active).", "good": False})
    mine = [by_id[x["player_id"]] for x in picks if x["team"] == config.MY_SLOT and x["player_id"] in by_id]
    same_bye = [q.name for q in mine if q.bye == p.bye and q.pos in ("QB", "RB", "WR", "TE")]
    if same_bye:
        out.append({"kind": "risk", "text": f"Bye week {p.bye} overlaps with {', '.join(same_bye)}.", "good": False})
    elif p.bye:
        out.append({"kind": "risk", "text": f"Bye week {p.bye}; no overlap with your roster.", "good": True})
    if p.proj_spread and p.proj_spread > 40:
        srcs = " vs ".join(f"{k} {v:.0f}" for k, v in p.proj_sources.items())
        out.append({"kind": "risk", "text": f"Sources disagree by {p.proj_spread:.0f} pts ({srcs}).", "good": False})
    else:
        srcs = " and ".join(f"{k} {v:.0f}" for k, v in p.proj_sources.items())
        if len(p.proj_sources) > 1:
            out.append({"kind": "sources", "text": f"Sources agree: {srcs}.", "good": True})
    if hist and hist.get("games"):
        cv = (hist.get("sd") or 0) / hist["mean"] if hist.get("mean") else None
        vol = "volatile" if cv and cv > 0.65 else "steady" if cv and cv < 0.45 else "typical"
        out.append({"kind": "history", "text": f"2025: {hist['mean']:.1f} pts/game over {hist['games']} games under this scoring, weekly sd {hist['sd']:.1f} ({vol} week to week).", "good": vol != "volatile"})
    return out


def decide(rec: dict, picks: list[dict], by_id: dict[str, Player], players: list[Player], hist_table: dict) -> dict:
    cands = rec.get("all_candidates", [])[:2]
    if len(cands) < 2:
        return {"error": "not enough candidates"}
    a, b = cands
    options = []
    sc = {x["pos"]: x for x in rec.get("scarcity", [])}
    for c, other in ((a, b), (b, a)):
        h = (hist_table.get("players") or {}).get(c["id"])
        s_pos = sc.get(c["pos"]) or {}
        options.append({**c, "reasons": reasons_for(c, other, rec, picks, by_id, players, h), "history": ({"games": h["games"], "mean": h["mean"], "sd": h["sd"]} if h else None),
                        "wait_cost": s_pos.get("dropoff_to_next"), "wait_best": s_pos.get("expected_best_at_next")})
    return {
        "pick_no": rec["pick_no"], "decision_pick": rec["decision_pick"], "is_me": rec["is_me"], "next_pick": rec.get("next_pick"), "round": rec.get("round"),
        "options": options, "margin": rec["margin"], "confidence": rec["confidence"], "n_sims": rec.get("n_sims"), "computed_ms": rec.get("computed_ms"),
        "my_picks_so_far": [{"id": x["player_id"], "name": by_id[x["player_id"]].name, "pos": by_id[x["player_id"]].pos} for x in picks if x["team"] == config.MY_SLOT and x["player_id"] in by_id],
        "drafted_count": len(picks),
    }
