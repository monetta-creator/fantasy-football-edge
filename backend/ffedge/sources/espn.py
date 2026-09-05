"""ESPN fantasy public API: raw stat projections (all positions), ADP, injury status, games."""
from __future__ import annotations

import json

import httpx

from .. import config
from .cache import cached_json
from .common import ESPN_PRO_TEAMS, player_key

URL = "https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/{season}/segments/0/leaguedefaults/3?view=kona_player_info"
POS = {1: "QB", 2: "RB", 3: "WR", 4: "TE", 5: "K", 16: "DEF"}

# ESPN stat id -> canonical (offense)
OFF_MAP = {
    "3": "pass_yd", "4": "pass_td", "20": "pass_int", "19": "pass_2pt",
    "24": "rush_yd", "25": "rush_td", "26": "rush_2pt",
    "53": "rec", "42": "rec_yd", "43": "rec_td", "44": "rec_2pt",
    "72": "fum_lost",
}
K_MAP = {"80": "fg_0_39", "77": "fg_40_49", "74": "fg_50p", "86": "xp_made"}
DST_MAP = {
    "99": "dst_sack", "95": "dst_int", "96": "dst_fum_rec", "105": "dst_td", "98": "dst_safety", "97": "dst_blk",
    "89": "dst_pa_0", "90": "dst_pa_1_6", "91": "dst_pa_7_13",
}


def _fetch(limit: int = 700) -> list[dict]:
    flt = {
        "players": {
            "limit": limit,
            "sortDraftRanks": {"sortPriority": 100, "sortAsc": True, "value": "PPR"},
            "filterStatsForTopScoringPeriodIds": {"value": 2, "additionalValue": [f"00{config.SEASON}", f"10{config.SEASON}"]},
        }
    }
    r = httpx.get(URL.format(season=config.SEASON), headers={"X-Fantasy-Filter": json.dumps(flt)}, timeout=90)
    r.raise_for_status()
    players = r.json().get("players", [])
    out = []
    for e in players:
        p = e.get("player") or {}
        proj = None
        for s in p.get("stats", []):
            if s.get("seasonId") == config.SEASON and s.get("statSourceId") == 1 and s.get("statSplitTypeId") == 0:
                proj = s
                break
        out.append({
            "id": p.get("id"),
            "fullName": p.get("fullName"),
            "defaultPositionId": p.get("defaultPositionId"),
            "proTeamId": p.get("proTeamId"),
            "injuryStatus": p.get("injuryStatus"),
            "injured": p.get("injured"),
            "adp": (p.get("ownership") or {}).get("averageDraftPosition"),
            "percentOwned": (p.get("ownership") or {}).get("percentOwned"),
            "stats": (proj or {}).get("stats"),
            "appliedTotal": (proj or {}).get("appliedTotal"),
            "seasonOutlook": (p.get("seasonOutlook") or "")[:600],
        })
    return out


def load(force: bool = False) -> tuple[list[dict], dict]:
    raw, meta = cached_json("espn_projections", _fetch, force=force)
    rows = []
    for p in raw:
        pos = POS.get(p.get("defaultPositionId"))
        if not pos:
            continue
        team = ESPN_PRO_TEAMS.get(p.get("proTeamId"))
        st = p.get("stats") or {}
        stats: dict[str, float] = {}
        if pos in ("QB", "RB", "WR", "TE"):
            for k, ck in OFF_MAP.items():
                if k in st:
                    stats[ck] = float(st[k])
            ret = float(st.get("101", 0) or 0) + float(st.get("102", 0) or 0)
            if ret:
                stats["ret_td"] = ret
        elif pos == "K":
            for k, ck in K_MAP.items():
                if k in st:
                    stats[ck] = float(st[k])
        elif pos == "DEF":
            for k, ck in DST_MAP.items():
                if k in st:
                    stats[ck] = float(st[k])
            # ESPN buckets 14-17 (92) and 18-21 (121) straddle Yahoo's 14-20 / 21-27 boundary.
            b_14_17 = float(st.get("92", 0) or 0)
            b_18_21 = float(st.get("121", 0) or 0)
            stats["dst_pa_14_20"] = b_14_17 + 0.75 * b_18_21
            stats["dst_pa_21_27"] = 0.25 * b_18_21 + float(st.get("122", 0) or 0)
            stats["dst_pa_28_34"] = float(st.get("123", 0) or 0)
            stats["dst_pa_35p"] = float(st.get("124", 0) or 0) + float(st.get("125", 0) or 0)
        games = st.get("210")
        name = p.get("fullName") or ""
        if pos == "DEF":
            name = f"{team} D/ST"
        rows.append({
            "source": "espn",
            "espn_id": p.get("id"),
            "key": player_key(name, pos, team),
            "name": name,
            "pos": pos,
            "team": team,
            "stats": stats if st else {},
            "games": float(games) if games else None,
            "adp": p.get("adp") if p.get("adp") and 0 < p.get("adp") <= 300 else None,
            "percent_owned": p.get("percentOwned"),
            "injury_status": p.get("injuryStatus"),
            "pts_source": p.get("appliedTotal"),
            "outlook": p.get("seasonOutlook"),
        })
    return rows, meta
