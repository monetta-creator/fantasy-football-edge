"""League constants for Yahoo league 872372 ("Marian Prayers"), 2026 season.

Everything numeric about the league lives here so models never hard-code rules.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
CACHE_DIR = DATA_DIR / "cache"
DB_PATH = DATA_DIR / "ffedge.db"

import json as _json

SEASON = 2026
LEAGUE_ID = 872372

# League facts live in data/league.json (owner-verified); the constants below are the fallback.
_LEAGUE: dict = {}
try:
    _LEAGUE = _json.loads((DATA_DIR / "league.json").read_text())
except Exception:
    _LEAGUE = {}

NUM_TEAMS = int(_LEAGUE.get("num_teams", 12))
MY_SLOT = int(_LEAGUE.get("my_slot", 5))  # 1-based draft slot
TEAM_NAMES: dict[int, str] = {int(k): v for k, v in (_LEAGUE.get("teams") or {}).items()}
MY_TEAM_NAME = _LEAGUE.get("my_team", "Me")
MY_SCHEDULE: dict[int, str] = {int(k): v for k, v in (_LEAGUE.get("my_schedule") or {}).items()}
REG_SEASON_WEEKS = 18  # NFL weeks
FANTASY_REG_WEEKS = 14  # fantasy regular season: weeks 1-14
PLAYOFF_WEEKS = (15, 16, 17)
WEEK1_TUESDAY = "2026-09-08"  # fantasy week 1 begins (Tue before Thu kickoff 09-10)

# ---- Scoring (Yahoo settings, verified by owner) ----
OFFENSE_SCORING: dict[str, float] = {
    "pass_yd": 1 / 25,
    "pass_td": 6.0,
    "pass_int": -1.0,
    "pass_2pt": 2.0,
    "rush_yd": 1 / 10,
    "rush_td": 6.0,
    "rush_2pt": 2.0,
    "rec": 1.0,
    "rec_yd": 1 / 10,
    "rec_td": 6.0,
    "rec_2pt": 2.0,
    "ret_td": 6.0,
    "fum_lost": -2.0,
    "off_fum_ret_td": 6.0,
}
KICKER_SCORING: dict[str, float] = {
    "fg_0_19": 3.0,
    "fg_20_29": 3.0,
    "fg_30_39": 3.0,
    "fg_0_39": 3.0,  # combined bucket some sources provide
    "fg_40_49": 4.0,
    "fg_50p": 5.0,
    "xp_made": 1.0,
}
DST_SCORING: dict[str, float] = {
    "dst_sack": 1.0,
    "dst_int": 2.0,
    "dst_fum_rec": 2.0,
    "dst_td": 6.0,
    "dst_safety": 2.0,
    "dst_blk": 2.0,
    "dst_ret_td": 6.0,
    "dst_xp_ret": 2.0,
}
# points allowed buckets -> points, keyed by canonical stat (games in bucket)
DST_POINTS_ALLOWED: dict[str, float] = {
    "dst_pa_0": 10.0,
    "dst_pa_1_6": 7.0,
    "dst_pa_7_13": 4.0,
    "dst_pa_14_20": 1.0,
    "dst_pa_21_27": 0.0,
    "dst_pa_28_34": -1.0,
    "dst_pa_35p": -4.0,
}

# ---- Roster ----
POSITIONS = ("QB", "RB", "WR", "TE", "K", "DEF")
# slot name -> eligible positions
ROSTER_SLOTS: list[tuple[str, tuple[str, ...]]] = [
    ("QB", ("QB",)),
    ("WR", ("WR",)),
    ("WR", ("WR",)),
    ("RB", ("RB",)),
    ("TE", ("TE",)),
    ("W/R", ("WR", "RB")),
    ("W/R/T", ("WR", "RB", "TE")),
    ("K", ("K",)),
    ("DEF", ("DEF",)),
]
BENCH_SLOTS = int(_LEAGUE.get("bench_slots", 6))
IR_SLOTS = int(_LEAGUE.get("ir_slots", 6))
STARTER_COUNT = len(ROSTER_SLOTS)
DRAFTABLE = STARTER_COUNT + BENCH_SLOTS
ROUNDS = int(_LEAGUE.get("rounds", DRAFTABLE))  # Yahoo drafts one round per non-IR roster spot

# Yahoo statuses that can occupy an IR slot. "O" (Out) is only eligible if the
# league uses IR+ slots; the owner should confirm the slot label in Yahoo.
IR_ELIGIBLE_STATUSES = {"IR", "IR-R", "IR-LT", "PUP-R", "PUP-P", "NFI-R", "NFI-A", "SUSP", "COVID-19", "DNR", "NA"}
IR_PLUS_EXTRA = {"O"}


def my_picks(slot: int = MY_SLOT, teams: int = NUM_TEAMS, rounds: int = ROUNDS) -> list[int]:
    """Overall pick numbers for a slot in a snake draft (1-based)."""
    out = []
    for r in range(1, rounds + 1):
        if r % 2 == 1:
            out.append((r - 1) * teams + slot)
        else:
            out.append((r - 1) * teams + (teams - slot + 1))
    return out


def team_on_clock(pick_no: int, teams: int = NUM_TEAMS) -> int:
    """1-based team slot that owns overall pick `pick_no`."""
    r = (pick_no - 1) // teams + 1
    i = (pick_no - 1) % teams
    return i + 1 if r % 2 == 1 else teams - i


def round_of(pick_no: int, teams: int = NUM_TEAMS) -> int:
    return (pick_no - 1) // teams + 1


@dataclass
class Settings:
    openrouter_api_key: str | None = None
    openrouter_model: str = "google/gemini-3.8-flash"
    openrouter_vision_model: str = "google/gemini-3.8-flash"
    openrouter_reasoning_effort: str = "minimal"  # "" to omit the reasoning parameter
    odds_api_key: str | None = None
    yahoo_client_id: str | None = None
    yahoo_client_secret: str | None = None
    sim_count: int = 200
    ir_plus: bool = False
    extra: dict = field(default_factory=dict)


def load_settings() -> Settings:
    import os

    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
    return Settings(
        openrouter_api_key=os.getenv("OPENROUTER_API_KEY") or None,
        openrouter_model=os.getenv("OPENROUTER_MODEL") or "google/gemini-3.8-flash",
        openrouter_vision_model=os.getenv("OPENROUTER_VISION_MODEL") or "google/gemini-3.8-flash",
        openrouter_reasoning_effort=os.getenv("OPENROUTER_REASONING_EFFORT", "minimal"),
        odds_api_key=os.getenv("ODDS_API_KEY") or None,
        yahoo_client_id=os.getenv("YAHOO_CLIENT_ID") or None,
        yahoo_client_secret=os.getenv("YAHOO_CLIENT_SECRET") or None,
        sim_count=int(os.getenv("SIM_COUNT", "200")),
        ir_plus=os.getenv("IR_PLUS", str(_LEAGUE.get("ir_plus", False))).lower() in ("1", "true", "yes"),
    )
