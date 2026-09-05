"""Last season's weekly results (nflverse) under league scoring: per-player weekly series, sd, and a
position-level CV fallback. Also feeds the player detail chart. Cached in data/cache/history_<season>.json."""
from __future__ import annotations

import csv
import io
import statistics

import httpx

from . import config
from .scoring import pa_buckets_from_mean, score
from .sources.cache import cached_json
from .sources.common import norm_name, norm_team

PLAYER_URL = "https://github.com/nflverse/nflverse-data/releases/download/stats_player/stats_player_week_{season}.csv"
TEAM_URL = "https://github.com/nflverse/nflverse-data/releases/download/stats_team/stats_team_week_{season}.csv"
GAMES_URL = "https://github.com/nflverse/nfldata/raw/master/data/games.csv"

COLS = {
    "passing_yards": "pass_yd", "passing_tds": "pass_td", "passing_interceptions": "pass_int", "passing_2pt_conversions": "pass_2pt",
    "rushing_yards": "rush_yd", "rushing_tds": "rush_td", "rushing_2pt_conversions": "rush_2pt",
    "receptions": "rec", "receiving_yards": "rec_yd", "receiving_tds": "rec_td", "receiving_2pt_conversions": "rec_2pt",
    "special_teams_tds": "ret_td",
}
FUM_COLS = ["sack_fumbles_lost", "rushing_fumbles_lost", "receiving_fumbles_lost"]
K_COLS = {"fg_made_0_19": "fg_0_19", "fg_made_20_29": "fg_20_29", "fg_made_30_39": "fg_30_39", "fg_made_40_49": "fg_40_49", "pat_made": "xp_made"}
ADV = ["passing_epa", "rushing_epa", "receiving_epa", "receiving_air_yards", "receiving_yards_after_catch", "passing_air_yards", "passing_yards_after_catch",
       "target_share", "air_yards_share", "wopr", "racr", "rushing_first_downs", "receiving_first_downs", "passing_first_downs"]
EXTRA = {"QB": ["attempts", "completions", "carries"] + ADV, "RB": ["carries", "targets"] + ADV, "WR": ["targets", "carries"] + ADV, "TE": ["targets", "carries"] + ADV, "K": ["fg_att", "fg_long"]}
# Position-level weekly CV fallbacks (medians from 2025 weekly stats).
POS_CV = {"QB": 0.47, "RB": 0.57, "WR": 0.58, "TE": 0.63, "K": 0.5, "DEF": 0.7}
MIN_GAMES = 6


def _f(v) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _fetch(season: int) -> dict:
    r = httpx.get(PLAYER_URL.format(season=season), timeout=120, follow_redirects=True)
    r.raise_for_status()
    # team weekly carries/attempts for share metrics
    team_tot: dict[tuple[str, int], dict] = {}
    try:
        tt = httpx.get(TEAM_URL.format(season=season), timeout=90, follow_redirects=True)
        tt.raise_for_status()
        for trow in csv.DictReader(io.StringIO(tt.text)):
            if trow.get("season_type") == "REG":
                team_tot[(norm_team(trow["team"]), int(trow["week"]))] = {"carries": _f(trow.get("carries")), "attempts": _f(trow.get("attempts"))}
    except Exception:
        pass
    series: dict[str, list[dict]] = {}
    names: dict[str, str] = {}
    for row in csv.DictReader(io.StringIO(r.text)):
        pos = row.get("position")
        if row.get("season_type") != "REG" or pos not in ("QB", "RB", "WR", "TE", "K"):
            continue
        st: dict[str, float] = {}
        if pos == "K":
            for c, k in K_COLS.items():
                st[k] = _f(row.get(c))
            st["fg_50p"] = _f(row.get("fg_made_50_59")) + _f(row.get("fg_made_60_"))
        else:
            for c, k in COLS.items():
                if row.get(c) not in (None, "", "NA"):
                    st[k] = _f(row.get(c))
            st["fum_lost"] = sum(_f(row.get(c)) for c in FUM_COLS)
        extra = {c: round(_f(row.get(c)), 3) for c in EXTRA.get(pos, []) if row.get(c) not in (None, "", "NA")}
        tt_row = team_tot.get((norm_team(row.get("team")), int(row["week"])))
        if tt_row and pos in ("RB", "QB", "WR", "TE") and tt_row.get("carries"):
            extra["rush_share"] = round(_f(row.get("carries")) / tt_row["carries"], 3)
        key = f"{pos}:{norm_name(row['player_display_name'])}"
        series.setdefault(key, []).append({"week": int(row["week"]), "opp": norm_team(row.get("opponent_team")), "team": norm_team(row.get("team")), "pts": round(score(st), 2), "stats": {k: round(v, 1) for k, v in st.items() if v}, **({"extra": extra} if extra else {})})
        names[key] = row["player_display_name"]
    # DST: team weekly defensive stats + points allowed from game scores
    try:
        games = httpx.get(GAMES_URL, timeout=90, follow_redirects=True).text
        pa: dict[tuple[str, int], float] = {}
        for g in csv.DictReader(io.StringIO(games)):
            if g.get("season") != str(season) or g.get("game_type") != "REG" or not g.get("home_score"):
                continue
            w = int(g["week"])
            pa[(norm_team(g["home_team"]), w)] = _f(g["away_score"])
            pa[(norm_team(g["away_team"]), w)] = _f(g["home_score"])
        tr = httpx.get(TEAM_URL.format(season=season), timeout=90, follow_redirects=True)
        tr.raise_for_status()
        for row in csv.DictReader(io.StringIO(tr.text)):
            if row.get("season_type") != "REG":
                continue
            team = norm_team(row["team"])
            w = int(row["week"])
            st = {
                "dst_sack": _f(row.get("def_sacks")), "dst_int": _f(row.get("def_interceptions")), "dst_fum_rec": _f(row.get("fumble_recovery_opp")),
                "dst_td": _f(row.get("def_tds")), "dst_safety": _f(row.get("def_safeties")), "dst_blk": _f(row.get("def_fg_blocks")) + _f(row.get("def_pat_blocks")) + _f(row.get("def_punt_blocks")),
                "dst_ret_td": _f(row.get("special_teams_tds")),
            }
            allowed = pa.get((team, w))
            if allowed is not None:
                st.update({k: (1.0 if v > 0.5 else 0.0) for k, v in pa_buckets_from_mean(allowed, 1.0, sd=0.01).items()})
                st["pa"] = allowed
            key = f"DEF:{team}"
            series.setdefault(key, []).append({"week": w, "opp": norm_team(row.get("opponent_team")), "team": team, "pts": round(score(st), 2), "stats": {k: round(v, 1) for k, v in st.items() if v}})
            names[key] = f"{team} D/ST"
    except Exception:
        pass
    players = {}
    for key, rows in series.items():
        rows.sort(key=lambda x: x["week"])
        pts = [x["pts"] for x in rows]
        rec = {"games": len(pts), "mean": round(statistics.fmean(pts), 2) if pts else 0.0, "sd": round(statistics.pstdev(pts), 2) if len(pts) > 1 else 0.0, "name": names[key], "weeks": rows}
        rec["cv"] = round(rec["sd"] / rec["mean"], 3) if rec["mean"] > 0 and len(pts) >= MIN_GAMES else None
        players[key] = rec
    return {"season": season, "players": players}


def load(season: int = config.SEASON - 1, force: bool = False) -> tuple[dict, dict]:
    return cached_json(f"history_{season}_v2", lambda: _fetch(season), ttl_seconds=30 * 24 * 3600, force=force)


def history(player_key: str, table: dict) -> dict | None:
    return (table.get("players") or {}).get(player_key)


def weekly_sd(player_key: str, pos: str, weekly_mean: float, table: dict) -> float:
    """Weekly point sd for a player: last season's own sd scaled to this week's mean, else position CV."""
    rec = (table.get("players") or {}).get(player_key)
    cv = POS_CV.get(pos, 0.6)
    if rec and rec.get("cv"):
        cv = 0.7 * rec["cv"] + 0.3 * POS_CV.get(pos, 0.6)  # shrink toward the position prior
    return max(1.5, cv * max(weekly_mean, 1.0))
