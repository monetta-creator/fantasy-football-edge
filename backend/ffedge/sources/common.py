"""Name/team normalization shared by all sources."""
from __future__ import annotations

import re

SUFFIXES = {"jr", "sr", "ii", "iii", "iv", "v"}

TEAM_ALIASES = {
    "WSH": "WAS", "LA": "LAR", "JAC": "JAX", "OAK": "LV", "SD": "LAC", "STL": "LAR",
}

ESPN_PRO_TEAMS = {
    1: "ATL", 2: "BUF", 3: "CHI", 4: "CIN", 5: "CLE", 6: "DAL", 7: "DEN", 8: "DET", 9: "GB",
    10: "TEN", 11: "IND", 12: "KC", 13: "LV", 14: "LAR", 15: "MIA", 16: "MIN", 17: "NE", 18: "NO",
    19: "NYG", 20: "NYJ", 21: "PHI", 22: "ARI", 23: "PIT", 24: "LAC", 25: "SF", 26: "SEA", 27: "TB",
    28: "WAS", 29: "CAR", 30: "JAX", 33: "BAL", 34: "HOU",
}

TEAM_NAMES = {
    "ARI": "Cardinals", "ATL": "Falcons", "BAL": "Ravens", "BUF": "Bills", "CAR": "Panthers",
    "CHI": "Bears", "CIN": "Bengals", "CLE": "Browns", "DAL": "Cowboys", "DEN": "Broncos",
    "DET": "Lions", "GB": "Packers", "HOU": "Texans", "IND": "Colts", "JAX": "Jaguars",
    "KC": "Chiefs", "LV": "Raiders", "LAC": "Chargers", "LAR": "Rams", "MIA": "Dolphins",
    "MIN": "Vikings", "NE": "Patriots", "NO": "Saints", "NYG": "Giants", "NYJ": "Jets",
    "PHI": "Eagles", "PIT": "Steelers", "SF": "49ers", "SEA": "Seahawks", "TB": "Buccaneers",
    "TEN": "Titans", "WAS": "Commanders",
}
NICK_TO_ABBR = {v.lower(): k for k, v in TEAM_NAMES.items()}
CITY_TO_ABBR = {
    "arizona": "ARI", "atlanta": "ATL", "baltimore": "BAL", "buffalo": "BUF", "carolina": "CAR",
    "chicago": "CHI", "cincinnati": "CIN", "cleveland": "CLE", "dallas": "DAL", "denver": "DEN",
    "detroit": "DET", "green bay": "GB", "houston": "HOU", "indianapolis": "IND", "jacksonville": "JAX",
    "kansas city": "KC", "las vegas": "LV", "los angeles chargers": "LAC", "los angeles rams": "LAR",
    "miami": "MIA", "minnesota": "MIN", "new england": "NE", "new orleans": "NO", "new york giants": "NYG",
    "new york jets": "NYJ", "philadelphia": "PHI", "pittsburgh": "PIT", "san francisco": "SF",
    "seattle": "SEA", "tampa bay": "TB", "tennessee": "TEN", "washington": "WAS",
}


def norm_team(t: str | None) -> str | None:
    if not t:
        return None
    t = t.upper().strip()
    return TEAM_ALIASES.get(t, t)


def norm_name(name: str) -> str:
    s = name.lower()
    s = s.replace("d/st", "").replace("dst", "")
    s = re.sub(r"[^a-z ]", "", s)
    parts = [p for p in s.split() if p not in SUFFIXES]
    return "".join(parts)


def player_key(name: str, pos: str, team: str | None = None) -> str:
    if pos == "DEF":
        return f"DEF:{norm_team(team) or norm_name(name)}"
    return f"{pos}:{norm_name(name)}"
