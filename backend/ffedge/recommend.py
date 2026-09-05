"""Draft recommendations: candidate evaluation via Monte Carlo lookahead, scarcity, rationale."""
from __future__ import annotations

import time
from math import sqrt

import numpy as np

from . import config
from .adp_model import p_gone_by
from .draft_sim import DraftSim, lineup_value
from .players import Player
from .vorp import POS_NAMES, Arrays

POS_WORD = {"QB": "QB", "RB": "RB", "WR": "WR", "TE": "TE", "K": "kicker", "DEF": "defense"}


def mechanism(p: Player, info: dict) -> str:
    st = p.stats
    rank = info["replacement_rank"].get(p.pos)
    repl = p.__dict__.get("repl_pts", 0)
    if p.pos == "QB":
        return (f"6-pt passing TDs: {st.get('pass_td', 0):.0f} projected TDs = {6 * st.get('pass_td', 0):.0f} pts; "
                f"{p.vorp:+.0f} vs the waiver-level QB ({repl:.0f} pts).")
    if p.pos == "RB":
        return (f"Full PPR: {st.get('rec', 0):.0f} catches + {st.get('rush_yd', 0):.0f} rush yds; "
                f"{p.vorp:+.0f} vs waiver RB ({repl:.0f} pts), and only 1 RB slot means RBs mostly compete for flex.")
    if p.pos == "WR":
        return (f"Full PPR: {st.get('rec', 0):.0f} catches = {st.get('rec', 0):.0f} pts alone; four WR/TE-eligible slots; "
                f"{p.vorp:+.0f} vs waiver WR ({repl:.0f} pts).")
    if p.pos == "TE":
        return (f"Full PPR TE: {st.get('rec', 0):.0f} catches, W/R/T-eligible; {p.vorp:+.0f} vs waiver TE ({repl:.0f} pts).")
    if p.pos == "K":
        return f"50+ yd FGs score 5: {st.get('fg_50p', 0):.0f} projected; {p.vorp:+.0f} vs streaming kicker."
    if p.pos == "DEF":
        pa = st.get("dst_pa_0", 0) * 0 + st.get("dst_pa_1_6", 0) * 3.5 + st.get("dst_pa_7_13", 0) * 10 + st.get("dst_pa_14_20", 0) * 17 + st.get("dst_pa_21_27", 0) * 24 + st.get("dst_pa_28_34", 0) * 31 + st.get("dst_pa_35p", 0) * 38
        g = max(1.0, sum(v for k, v in st.items() if k.startswith("dst_pa_")))
        return f"Points-allowed dominates DST scoring: ~{pa / g:.0f} PA/game projected; {p.vorp:+.0f} vs streaming defense."
    return ""


def confidence(margin: float, se: float) -> str:
    if margin >= 6 and margin > 2.0 * se:
        return "High"
    if margin >= 2.5 and margin > 1.0 * se:
        return "Medium"
    return "Low"


class Recommender:
    def __init__(self, players: list[Player], arr: Arrays, info: dict, sim: DraftSim):
        self.players = players
        self.by_id = {p.id: p for p in players}
        self.arr = arr
        self.info = info
        self.sim = sim

    # ---- board -----------------------------------------------------------------------------
    def board(self, picks: list[dict], team_names: dict[int, str]) -> dict:
        n = len(picks)
        total = config.NUM_TEAMS * config.ROUNDS
        cur = n + 1
        mine = config.my_picks()
        my_next = [k for k in mine if k >= cur]
        on_clock = config.team_on_clock(cur) if cur <= total else None
        drafted = set(p["player_id"] for p in picks)
        my_ids = [p["player_id"] for p in picks if p["team"] == config.MY_SLOT]
        roster = self.my_roster(my_ids)
        return {
            "pick_no": cur if cur <= total else None,
            "round": config.round_of(cur) if cur <= total else None,
            "total_picks": total,
            "on_clock_team": on_clock,
            "on_clock_name": team_names.get(on_clock) if on_clock else None,
            "is_me": on_clock == config.MY_SLOT,
            "my_next_picks": my_next[:4],
            "picks_until_me": (my_next[0] - cur) if my_next else None,
            "picks": [{**p, "player": self.brief(p["player_id"]), "team_name": team_names.get(p["team"])} for p in picks],
            "my_roster": roster,
            "teams": team_names,
            "drafted_count": len(drafted),
            "team_rosters": self.team_rosters(picks, team_names),
        }

    def brief(self, pid: str) -> dict:
        p = self.by_id.get(pid)
        if not p:
            return {"id": pid, "name": pid, "pos": "?", "team": None}
        return {"id": p.id, "name": p.name, "pos": p.pos, "team": p.team, "pts": p.pts, "vorp": p.vorp, "adp": p.adp,
                "bye": p.bye, "injury": {"code": p.injury.get("code"), "label": p.injury.get("label"), "ir_eligible": p.injury.get("ir_eligible")}}

    def team_rosters(self, picks: list[dict], team_names: dict[int, str]) -> list[dict]:
        out = []
        for t in range(1, config.NUM_TEAMS + 1):
            ps = [self.brief(p["player_id"]) for p in picks if p["team"] == t]
            counts = {}
            for b in ps:
                counts[b["pos"]] = counts.get(b["pos"], 0) + 1
            out.append({"slot": t, "name": team_names.get(t), "players": ps, "counts": counts})
        return out

    def my_roster(self, my_ids: list[str]) -> dict:
        ps = [self.by_id[i] for i in my_ids if i in self.by_id]
        pos_list = [p.pos for p in ps]
        val_list = [max(0.0, p.vorp) for p in ps]
        ir_list = [bool(p.injury.get("ir_eligible")) for p in ps]
        score, assign = lineup_value(pos_list, val_list, ir_list)
        slots = [{"slot": s, "elig": list(e), "player": None} for s, e in config.ROSTER_SLOTS]
        slots += [{"slot": "BN", "elig": ["QB", "RB", "WR", "TE", "K", "DEF"], "player": None} for _ in range(config.BENCH_SLOTS)]
        ir = []
        used = set()
        for a in assign:
            b = self.brief(ps[a["i"]].id)
            if a["slot"] == "IR":
                ir.append(b)
                continue
            for j, s in enumerate(slots):
                if j in used:
                    continue
                if s["slot"] == a["slot"]:
                    s["player"] = b
                    used.add(j)
                    break
            else:
                if a["slot"] in ("BN", "X"):
                    ir.append({**b, "overflow": True})
        needs = [s["slot"] for s in slots if s["player"] is None and s["slot"] != "BN"]
        proj = sum(self.by_id[i].pts for i in my_ids if i in self.by_id and self.by_id[i].pos not in ())
        return {"slots": slots, "ir": ir, "needs": needs, "score": round(score, 1), "count": len(ps),
                "starter_pts": round(sum((s["player"] or {}).get("pts", 0) for s in slots[: config.STARTER_COUNT]), 1)}

    # ---- recommendations ---------------------------------------------------------------------
    def candidates(self, picks: list[dict], decision_pick: int, limit: int = 6) -> list[int]:
        drafted = set(p["player_id"] for p in picks)
        my_ids = [p["player_id"] for p in picks if p["team"] == config.MY_SLOT]
        my_counts = {}
        for i in my_ids:
            p = self.by_id.get(i)
            if p:
                my_counts[p.pos] = my_counts.get(p.pos, 0) + 1
        rnd = config.round_of(decision_pick)
        avail = [i for i, pid in enumerate(self.arr.ids) if pid not in drafted]
        # need-weighted value for candidate selection
        from .draft_sim import NEED_TABLE, MY_CAPS
        from .vorp import POS_INDEX

        def cval(i):
            pos = self.arr.pos[i]
            c = my_counts.get(pos, 0)
            if c >= MY_CAPS[POS_INDEX[pos]]:
                return -1e9
            if pos in ("K", "DEF") and rnd < config.ROUNDS - 3:
                return -1e9
            return float(max(self.arr.myval[i], 0.0) * NEED_TABLE[POS_INDEX[pos], min(c, 9)] + 1e-3 * self.arr.pts[i])

        avail.sort(key=lambda i: -cval(i))
        chosen = [i for i in avail[:limit] if cval(i) > -1e8]
        # ensure the best available at each skill position is considered
        for pos in ("QB", "RB", "WR", "TE"):
            best = next((i for i in avail if self.arr.pos[i] == pos and cval(i) > -1e8), None)
            if best is not None and best not in chosen:
                chosen.append(best)
        if rnd >= config.ROUNDS - 3:
            for pos in ("K", "DEF"):
                best = next((i for i in avail if self.arr.pos[i] == pos and cval(i) > -1e8), None)
                if best is not None and best not in chosen:
                    chosen.append(best)
        return chosen[: limit + 6]

    def recommend(self, picks: list[dict], n_sims: int = 300, seed: int = 11) -> dict:
        t0 = time.time()
        n = len(picks)
        cur = n + 1
        mine = config.my_picks()
        my_next = [k for k in mine if k >= cur]
        if not my_next:
            return {"done": True, "computed_ms": 0}
        decision_pick = my_next[0]
        after = [k for k in mine if k > decision_pick]
        next_pick = after[0] if after else None
        next_pick2 = after[1] if len(after) > 1 else None
        cands = self.candidates(picks, decision_pick)
        results = []
        for i in cands:
            r = self.sim.run(picks, forced={decision_pick: i}, n_sims=n_sims, seed=seed)
            results.append((i, r))
        results.sort(key=lambda x: -x[1].roster_score_mean)
        best_i, best_r = results[0]
        se = [r.roster_score_std / sqrt(r.n_sims) for _, r in results]
        margin = results[0][1].roster_score_mean - (results[1][1].roster_score_mean if len(results) > 1 else 0)
        se_diff = sqrt(se[0] ** 2 + (se[1] ** 2 if len(se) > 1 else 0)) * 0.7  # common random numbers reduce variance
        conf = confidence(margin, se_diff)
        avail_next = best_r.avail_at_next

        def cand_row(i, r, rank):
            p = self.by_id[self.arr.ids[i]]
            gone = None
            if avail_next is not None and next_pick is not None:
                gone = float(1.0 - avail_next[i]) if i != best_i else float(1.0 - self._avail_if_skipped(picks, decision_pick, i, results))
            p_avail_now = 1.0 if decision_pick == cur else 1.0 - p_gone_by(p.adp, p.adp_sigma, cur, decision_pick)
            return {
                "rank": rank, "id": p.id, "name": p.name, "pos": p.pos, "team": p.team, "pts": p.pts, "ppg": p.ppg,
                "vorp": p.vorp, "vols": p.vols, "adp": p.adp, "yahoo_rank": p.yahoo_rank, "bye": p.bye,
                "roster_score": round(r.roster_score_mean, 1), "roster_score_se": round(r.roster_score_std / sqrt(r.n_sims), 1),
                "delta_vs_best": round(r.roster_score_mean - best_r.roster_score_mean, 1),
                "p_gone_by_next": gone, "next_pick": next_pick, "p_available_at_decision": round(p_avail_now, 3),
                "injury": p.injury, "proj_spread": p.proj_spread, "mechanism": mechanism(p, self.info),
                "stash_value": p.__dict__.get("stash_value", 0.0),
            }

        rows = [cand_row(i, r, k + 1) for k, (i, r) in enumerate(results)]
        rec = rows[0]
        scarcity = self.scarcity(picks, best_r, next_pick, next_pick2)
        rationale = self.rationale_text(rec, scarcity, next_pick, decision_pick == cur)
        return {
            "done": False,
            "pick_no": cur, "decision_pick": decision_pick, "is_me": decision_pick == cur, "next_pick": next_pick, "next_pick2": next_pick2,
            "round": config.round_of(decision_pick),
            "recommended": rec, "alternatives": rows[1:5], "all_candidates": rows,
            "confidence": conf, "margin": round(margin, 1), "rationale": rationale,
            "scarcity": scarcity, "n_sims": n_sims, "computed_ms": int((time.time() - t0) * 1000),
            "likely_available_next": self.likely_available(best_r, next_pick),
        }

    def _avail_if_skipped(self, picks, decision_pick, i, results) -> float:
        # availability of the recommended player at my next pick if I take the runner-up instead
        for j, r in results[1:2]:
            if r.avail_at_next is not None:
                return float(r.avail_at_next[i])
        return 0.0

    def likely_available(self, r, next_pick, limit: int = 10) -> list[dict]:
        if r.avail_at_next is None or next_pick is None:
            return []
        av = r.avail_at_next
        order = np.argsort(-(self.arr.myval * np.clip(av, 0, 1)))
        out = []
        for i in order[:60]:
            if av[i] < 0.25:
                continue
            p = self.by_id[self.arr.ids[i]]
            out.append({"id": p.id, "name": p.name, "pos": p.pos, "team": p.team, "pts": p.pts, "vorp": p.vorp, "adp": p.adp,
                        "p_available": round(float(av[i]), 2)})
            if len(out) >= limit:
                break
        return out

    def scarcity(self, picks, r, next_pick, next_pick2) -> list[dict]:
        drafted = set(p["player_id"] for p in picks)
        out = []
        for pos in POS_NAMES:
            avail = [p for p in self.players if p.pos == pos and p.id not in drafted]
            if not avail:
                continue
            best = max(avail, key=lambda p: p.pts)
            nxt = r.best_pos_at_next.get(pos, {})
            nxt2 = r.best_pos_at_next2.get(pos, {})
            out.append({
                "pos": pos, "best_now": {"id": best.id, "name": best.name, "pts": best.pts, "vorp": best.vorp},
                "expected_best_at_next": round(nxt.get("pts", 0.0), 1) if nxt else None,
                "expected_best_at_next2": round(nxt2.get("pts", 0.0), 1) if nxt2 else None,
                "dropoff_to_next": round(best.pts - nxt.get("pts", 0.0), 1) if nxt else None,
                "next_pick": next_pick, "next_pick2": next_pick2,
                "replacement_pts": self.info["replacement_pts"].get(pos),
            })
        return out

    def rationale_text(self, rec: dict, scarcity: list[dict], next_pick, on_clock: bool) -> str:
        sc = next((s for s in scarcity if s["pos"] == rec["pos"]), None)
        parts = [rec["mechanism"]]
        if next_pick and rec.get("p_gone_by_next") is not None:
            parts.append(f"Gone by #{next_pick} in {rec['p_gone_by_next']:.0%} of sims")
            if sc and sc.get("dropoff_to_next") is not None:
                parts[-1] += f"; the best {POS_WORD[rec['pos']]} left at #{next_pick} projects {sc['dropoff_to_next']:.0f} pts lower."
            else:
                parts[-1] += "."
        if not on_clock:
            parts.append(f"Available at your pick with {rec['p_available_at_decision']:.0%} probability.")
        inj = rec.get("injury") or {}
        if inj.get("flag"):
            parts.append(f"Injury: {inj.get('label')} ({inj.get('type')}), expected back week {inj.get('return_week')}; {'IR-eligible' if inj.get('ir_eligible') else 'not IR-eligible'}.")
        return " ".join(parts)

    # ---- pre-draft pick 4 comparison ---------------------------------------------------------
    def pick_analysis(self, pick_no: int = config.MY_SLOT, n_sims: int = 300, seed: int = 11, limit: int = 8) -> dict:
        by_adp = sorted(range(len(self.arr.ids)), key=lambda i: self.arr.adp[i])[:limit]
        by_val = sorted(range(len(self.arr.ids)), key=lambda i: -self.arr.myval[i])[:limit]
        cands = []
        for i in by_adp + by_val:
            if i not in cands and self.arr.pos[i] in ("QB", "RB", "WR", "TE"):
                cands.append(i)
        rows = []
        for i in cands:
            r = self.sim.run([], forced={pick_no: i}, n_sims=n_sims, seed=seed)
            p = self.by_id[self.arr.ids[i]]
            rows.append({
                "id": p.id, "name": p.name, "pos": p.pos, "team": p.team, "pts": p.pts, "vorp": p.vorp, "adp": p.adp,
                "p_available": round(1.0 - p_gone_by(p.adp, p.adp_sigma, 1, pick_no), 2),
                "roster_score": round(r.roster_score_mean, 1), "se": round(r.roster_score_std / sqrt(n_sims), 1),
                "board_at_next": self.likely_available(r, config.my_picks()[1], limit=8),
                "best_pos_at_next": {k: round(v["pts"], 0) for k, v in r.best_pos_at_next.items()},
                "best_pos_at_next2": {k: round(v["pts"], 0) for k, v in r.best_pos_at_next2.items()},
                "injury": p.injury,
            })
        rows.sort(key=lambda x: -x["roster_score"])
        base = rows[0]["roster_score"] if rows else 0
        for r in rows:
            r["delta"] = round(r["roster_score"] - base, 1)
        return {"pick_no": pick_no, "next_picks": config.my_picks()[1:3], "candidates": rows, "n_sims": n_sims}
