"""Three-option decision at my pick: deterministic reasons plus a bull case and a bear case per candidate.

Every sentence here is built from numbers the models computed; nothing comes from the language model.
"""
from __future__ import annotations

from math import sqrt

from . import config
from .player_stats import consistency
from .players import Player
from .recommend import confidence

POS_LABEL = {"QB": "QB", "RB": "RB", "WR": "WR", "TE": "TE", "K": "kicker", "DEF": "defense"}
SRC_LABEL = {"espn": "ESPN", "sleeper": "Sleeper"}
N_OPTIONS = 3
MAX_CLAUSES = 4  # per bull / bear case


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


def _ranks(p: Player, players: list[Player], drafted: set[str]):
    """(rank among available at position, next-best at position, VORP rank among available, ADP rank among available)."""
    same_pos = sorted([q for q in players if q.pos == p.pos and q.id not in drafted], key=lambda q: -q.pts)
    rank_pos = next((i + 1 for i, q in enumerate(same_pos) if q.id == p.id), None)
    nxt = next((q for q in same_pos if q.id != p.id), None)
    by_vorp = sorted([q for q in players if q.id not in drafted], key=lambda q: -q.vorp)
    vrank = next((i + 1 for i, q in enumerate(by_vorp) if q.id == p.id), None)
    by_adp = sorted([q for q in players if q.id not in drafted], key=lambda q: q.adp)
    arank = next((i + 1 for i, q in enumerate(by_adp) if q.id == p.id), None)
    return rank_pos, nxt, vrank, arank


def _drops(rec: dict) -> tuple[dict, dict, str | None]:
    sc = {s["pos"]: s for s in rec.get("scarcity", [])}
    drops = {k: (v.get("dropoff_to_next") or 0) for k, v in sc.items() if k in ("QB", "RB", "WR", "TE")}
    biggest = max(drops, key=drops.get) if drops else None
    return sc, drops, biggest


def _pair_confidence(c: dict, other: dict, rec: dict, best: dict, runner: dict) -> str:
    """The card-level confidence is A vs B; any other pair gets the same rule on its own standard errors."""
    if {c["id"], other["id"]} == {best["id"], runner["id"]}:
        return rec.get("confidence", "Low")
    se = sqrt((c.get("roster_score_se") or 0) ** 2 + (other.get("roster_score_se") or 0) ** 2)
    return confidence(abs(c["roster_score"] - other["roster_score"]), se)


def reasons_for(c: dict, best: dict, runner: dict, rec: dict, picks: list[dict], by_id: dict[str, Player], players: list[Player], hist: dict | None) -> list[dict]:
    p = by_id[c["id"]]
    drafted = {x["player_id"] for x in picks}
    counts = _my_counts(picks, by_id)
    next_pick = rec.get("next_pick")
    rank_pos, nxt, vrank, arank = _ranks(p, players, drafted)
    out: list[dict] = []

    # 1. Value vs replacement and vs next-best at position
    txt = f"{p.vorp:+.0f} VORP: {p.pts:.0f} projected vs {p.__dict__.get('repl_pts', 0):.0f} for the best {POS_LABEL[p.pos]} left on waivers after the draft."
    if rank_pos:
        txt += f" #{rank_pos} of available {p.pos}s"
        if nxt:
            txt += f", {p.pts - nxt.pts:+.0f} pts vs the next one ({nxt.name}, {nxt.pts:.0f})."
    out.append({"kind": "value", "text": txt, "good": p.vorp > 0})

    # 2. Scarcity / drop-off at my next pick
    sc, drops, biggest = _drops(rec)
    s = sc.get(p.pos)
    if s and s.get("dropoff_to_next") is not None and next_pick:
        txt = f"Best {p.pos} still there at your next pick (#{next_pick}) projects {s['expected_best_at_next']:.0f}, a drop of {s['dropoff_to_next']:.0f} pts."
        if biggest == p.pos:
            txt += " That is the steepest drop-off of any position right now."
        else:
            txt += f" ({biggest} drops more: {drops[biggest]:.0f}.)"
        out.append({"kind": "scarcity", "text": txt, "good": biggest == p.pos})

    # 3. Availability at my next pick, and (looking ahead) at the decision pick itself
    pg = c.get("p_gone_by_next")
    if pg is not None and next_pick:
        if pg >= 0.6:
            out.append({"kind": "availability", "text": f"Gone before #{next_pick} in {pg:.0%} of simulated drafts. It is now or never.", "good": True})
        else:
            out.append({"kind": "availability", "text": f"Still available at #{next_pick} in {1 - pg:.0%} of simulated drafts; you could take another option now and hope he lasts.", "good": False})
    if c.get("conditional") and c.get("p_available_at_decision") is not None:
        pa = c["p_available_at_decision"]
        out.append({"kind": "availability", "text": f"On the board at #{rec['decision_pick']} in {pa:.0%} of simulated drafts. The roster value below counts only those drafts, so it answers \"if he is there, is he the pick?\"", "good": pa >= 0.5})

    # 4. Roster fit
    slot = _slot_for(p.pos, counts)
    have = ", ".join(f"{v} {k}" for k, v in sorted(counts.items())) or "nobody yet"
    out.append({"kind": "fit", "text": f"Would be your {slot}. Drafted so far: {have}.", "good": "bench" not in slot and "unnecessary" not in slot})

    # 5. Simulation outcome: A is compared with B, everyone else with A
    other = runner if c["id"] == best["id"] else best
    d = c["roster_score"] - other["roster_score"]
    n_used = c.get("n_sims_used") or rec.get("n_sims")
    where = f"across {n_used} simulated drafts" + (" in which he was still there" if c.get("conditional") and n_used != rec.get("n_sims") else "")
    out.append({"kind": "simulation", "text": f"Final-roster value {c['roster_score']:.0f} ± {c['roster_score_se']} {where}, {d:+.1f} vs {other['name']}. Confidence in the gap: {_pair_confidence(c, other, rec, best, runner)}.", "good": d >= 0})

    # 6. Scoring mechanism
    out.append({"kind": "scoring", "text": c.get("mechanism", ""), "good": True})

    # 7. Market view
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


def _sentence(parts: list[str]) -> str:
    parts = [x.strip() for x in parts if x and x.strip()][:MAX_CLAUSES]
    if not parts:
        return ""
    s = "; ".join(parts)
    return s[0].upper() + s[1:] + "."


_SUFFIX = {"jr", "jr.", "sr", "sr.", "ii", "iii", "iv", "v"}


def _last(name: str) -> str:
    """Surname for short references: 'Brian Thomas III' -> 'Thomas', 'Puka Nacua' -> 'Nacua'."""
    parts = [x for x in name.split() if x.lower() not in _SUFFIX] or name.split()
    return parts[-1]


def bull_bear(c: dict, best: dict, runner: dict, rec: dict, p: Player, hist: dict | None, players: list[Player], picks: list[dict], by_id: dict[str, Player]) -> dict:
    """Strongest case for and against the pick, as two short deterministic sentences built from the same facts."""
    drafted = {x["player_id"] for x in picks}
    rank_pos, nxt, vrank, arank = _ranks(p, players, drafted)
    sc, drops, biggest = _drops(rec)
    drop = (sc.get(p.pos) or {}).get("dropoff_to_next")
    next_pick = rec.get("next_pick")
    cons = consistency(p.pos, hist["weeks"]) if hist and hist.get("weeks") else {}
    cv = (hist["sd"] / hist["mean"]) if hist and hist.get("mean") and hist.get("sd") is not None else None
    srcs = p.proj_sources or {}
    hi = max(srcs.items(), key=lambda kv: kv[1]) if len(srcs) > 1 else None
    lo = min(srcs.items(), key=lambda kv: kv[1]) if len(srcs) > 1 else None
    is_best = c["id"] == best["id"]
    other = runner if is_best else best
    d = c["roster_score"] - other["roster_score"]
    conf = _pair_confidence(c, other, rec, best, runner)
    inj = p.injury or {}

    bull: list[str] = []
    if is_best and conf in ("Medium", "High"):
        bull.append(f"wins the simulation by {d:+.1f} roster value over {_last(other['name'])} ({conf} confidence)")
    if vrank == 1:
        bull.append("highest VORP on the board")
    elif rank_pos == 1 and nxt:
        bull.append(f"best {p.pos} left, {p.pts - nxt.pts:+.0f} pts over {nxt.name}")
    if hi and hi[1] - p.pts >= 5:
        bull.append(f"{SRC_LABEL.get(hi[0], hi[0])} projects {hi[1]:.0f} ({hi[1] - p.pts:+.0f} vs the blend)")
    if drop is not None and next_pick and drop >= 15:
        bull.append(("steepest cliff on the board: " if biggest == p.pos else "") + f"{p.pos} drops {drop:.0f} pts by #{next_pick}")
    if vrank and arank and arank - vrank >= 3:
        bull.append(f"market has him #{arank}, model #{vrank}")
    if cons and cons.get("boom_pct", 0) >= 25:
        bull.append(f"2025 ceiling: best week {cons['best']:.1f}, 25+ pts in {cons['boom_pct']}% of games")
    if cv is not None and cv < 0.45:
        bull.append(f"steady in 2025 (sd {hist['sd']:.1f} on {hist['mean']:.1f} per game)")
    if not inj.get("code"):
        bull.append("no injury flag")
    if len(srcs) > 1 and p.proj_spread <= 15:
        bull.append(f"sources agree within {p.proj_spread:.0f} pts")

    bear: list[str] = []
    if inj.get("code"):
        t = str(inj.get("label") or inj["code"])
        if inj.get("type"):
            t += f" ({str(inj['type']).lower()})"
        if inj.get("return_week"):
            t += f", expected back week {inj['return_week']}"
        elif inj.get("return_date"):
            t += f", return date {inj['return_date'][5:10].replace('-', '/')}"
        bear.append(t)
    if lo and p.pts - lo[1] >= 5:
        bear.append(f"{SRC_LABEL.get(lo[0], lo[0])} projects only {lo[1]:.0f} ({lo[1] - p.pts:+.0f} vs the blend)")
    if p.games and p.games < 16.5:
        bear.append(f"projected for only {p.games:.0f} games")
    pg = c.get("p_gone_by_next")
    if pg is not None and next_pick and pg < 0.6:
        bear.append(f"still there at #{next_pick} in {1 - pg:.0%} of sims, so you could wait")
    if biggest and biggest != p.pos and drop is not None and drops[biggest] - drop >= 10:
        bear.append(f"{biggest} cliff is steeper ({drops[biggest]:.0f} vs {drop:.0f})")
    if vrank and arank and vrank - arank >= 3:
        bear.append(f"model has him #{vrank}, market #{arank}")
    if is_best and conf == "Low":
        bear.append(f"edge over {_last(other['name'])} is {d:+.1f}, within simulation noise (SE {c.get('roster_score_se')})")
    if not is_best:
        bear.append(f"trails {_last(best['name'])} by {abs(d):.1f} roster value in the sims ({conf} confidence)")
    if cons and cons.get("bust_pct", 0) >= 10:
        bear.append(f"2025 floor: worst week {cons['worst']:.1f}, under 8 pts in {cons['bust_pct']}% of games")
    if cv is not None and cv > 0.65:
        bear.append(f"volatile in 2025 (sd {hist['sd']:.1f} on {hist['mean']:.1f} per game)")
    repl = p.__dict__.get("repl_pts") or 0
    if p.pts and repl / p.pts >= 0.6:
        bear.append(f"deep position: the waiver {POS_LABEL[p.pos]} projects {repl:.0f}")
    if p.proj_spread and p.proj_spread > 40 and not (lo and p.pts - lo[1] >= 5):
        bear.append(f"sources {p.proj_spread:.0f} pts apart")
    mine = [by_id[x["player_id"]] for x in picks if x["team"] == config.MY_SLOT and x["player_id"] in by_id]
    same_bye = [q.name for q in mine if q.bye == p.bye and q.pos in ("QB", "RB", "WR", "TE")]
    if same_bye:
        bear.append(f"bye week {p.bye} overlaps with {', '.join(_last(n) for n in same_bye)}")
    return {"bull": _sentence(bull) or "Nothing beyond the numbers below.", "bear": _sentence(bear) or "Nothing flagged: healthy, sources agree, bye clear."}


def decide(rec: dict, picks: list[dict], by_id: dict[str, Player], players: list[Player], hist_table: dict) -> dict:
    cands = rec.get("all_candidates", [])
    if len(cands) < 2:
        return {"error": "not enough candidates"}
    best, runner = cands[0], cands[1]
    hp = hist_table.get("players") or {}
    sc = {x["pos"]: x for x in rec.get("scarcity", [])}
    options = []
    for c in cands[:N_OPTIONS]:
        h = hp.get(c["id"])
        p = by_id[c["id"]]
        s_pos = sc.get(c["pos"]) or {}
        options.append({**c, "reasons": reasons_for(c, best, runner, rec, picks, by_id, players, h),
                        **bull_bear(c, best, runner, rec, p, h, players, picks, by_id),
                        "history": ({"games": h["games"], "mean": h["mean"], "sd": h["sd"]} if h else None),
                        "wait_cost": s_pos.get("dropoff_to_next"), "wait_best": s_pos.get("expected_best_at_next")})
    others = [{"id": c["id"], "name": c["name"], "pos": c["pos"], "roster_score": c["roster_score"], "delta_vs_best": c["delta_vs_best"],
               "p_available_at_decision": c.get("p_available_at_decision")} for c in cands[N_OPTIONS:]]
    return {
        "pick_no": rec["pick_no"], "decision_pick": rec["decision_pick"], "is_me": rec["is_me"], "next_pick": rec.get("next_pick"), "round": rec.get("round"),
        "lookahead": bool(rec.get("lookahead")), "options": options, "others": others, "unlikely_available": rec.get("unlikely_available", []),
        "margin": rec["margin"], "confidence": rec["confidence"], "n_sims": rec.get("n_sims"), "computed_ms": rec.get("computed_ms"),
        "my_picks_so_far": [{"id": x["player_id"], "name": by_id[x["player_id"]].name, "pos": by_id[x["player_id"]].pos} for x in picks if x["team"] == config.MY_SLOT and x["player_id"] in by_id],
        "drafted_count": len(picks),
    }
