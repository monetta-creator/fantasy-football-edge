"""Roster store for all 12 teams (SQLite). Seeded from the draft board; kept current by manual moves,
screenshot imports, or the Yahoo client. Slots: QB WR RB TE W/R W/R/T K DEF BN IR."""
from __future__ import annotations

import time

from . import config
from .draft_state import conn

SLOTS = [s for s, _ in config.ROSTER_SLOTS] + ["BN", "IR"]
SCHEMA = """
CREATE TABLE IF NOT EXISTS roster (
  team INTEGER NOT NULL,
  player_id TEXT NOT NULL,
  slot TEXT NOT NULL DEFAULT 'BN',
  updated_at REAL NOT NULL,
  PRIMARY KEY (team, player_id)
);
CREATE TABLE IF NOT EXISTS roster_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts REAL NOT NULL,
  team INTEGER NOT NULL,
  kind TEXT NOT NULL,
  player_id TEXT,
  detail TEXT
);
"""


def _init(c):
    c.executescript(SCHEMA)


def _log(c, team: int, kind: str, player_id: str | None, detail: str = ""):
    c.execute("INSERT INTO roster_log (ts, team, kind, player_id, detail) VALUES (?,?,?,?,?)", (time.time(), team, kind, player_id, detail))


def all_rosters(path=None) -> dict[int, list[dict]]:
    with conn(path) as c:
        _init(c)
        out: dict[int, list[dict]] = {t: [] for t in range(1, config.NUM_TEAMS + 1)}
        for r in c.execute("SELECT team, player_id, slot FROM roster ORDER BY team, slot"):
            out.setdefault(int(r["team"]), []).append({"player_id": r["player_id"], "slot": r["slot"]})
        return out


def roster(team: int, path=None) -> list[dict]:
    return all_rosters(path).get(team, [])


def owner_of(path=None) -> dict[str, int]:
    with conn(path) as c:
        _init(c)
        return {r["player_id"]: int(r["team"]) for r in c.execute("SELECT team, player_id FROM roster")}


def seed_from_draft(picks: list[dict], replace: bool = False, path=None) -> int:
    """Copy the draft board into rosters (everyone on the bench). Returns rows written."""
    with conn(path) as c:
        _init(c)
        if replace:
            c.execute("DELETE FROM roster")
        n = 0
        for p in picks:
            c.execute("INSERT OR IGNORE INTO roster (team, player_id, slot, updated_at) VALUES (?,?,?,?)", (int(p["team"]), p["player_id"], "BN", time.time()))
            n += c.execute("SELECT changes()").fetchone()[0]
        _log(c, config.MY_SLOT, "seed_from_draft", None, f"{n} rows")
        return n


def add(team: int, player_id: str, slot: str = "BN", path=None) -> None:
    with conn(path) as c:
        _init(c)
        owner = c.execute("SELECT team FROM roster WHERE player_id=?", (player_id,)).fetchone()
        if owner and int(owner["team"]) != team:
            raise ValueError(f"player is on team {owner['team']}")
        c.execute("INSERT OR REPLACE INTO roster (team, player_id, slot, updated_at) VALUES (?,?,?,?)", (team, player_id, slot, time.time()))
        _log(c, team, "add", player_id, slot)


def drop(team: int, player_id: str, path=None) -> None:
    with conn(path) as c:
        _init(c)
        c.execute("DELETE FROM roster WHERE team=? AND player_id=?", (team, player_id))
        _log(c, team, "drop", player_id)


def move(team: int, player_id: str, slot: str, path=None) -> None:
    if slot not in SLOTS:
        raise ValueError(f"bad slot {slot}")
    with conn(path) as c:
        _init(c)
        r = c.execute("SELECT 1 FROM roster WHERE team=? AND player_id=?", (team, player_id)).fetchone()
        if not r:
            raise ValueError("player not on this roster")
        c.execute("UPDATE roster SET slot=?, updated_at=? WHERE team=? AND player_id=?", (slot, time.time(), team, player_id))
        _log(c, team, "move", player_id, slot)


def set_lineup(team: int, assignments: dict[str, str], path=None) -> None:
    """assignments: player_id -> slot for every player on the team (unlisted players go to BN)."""
    with conn(path) as c:
        _init(c)
        ids = [r["player_id"] for r in c.execute("SELECT player_id FROM roster WHERE team=?", (team,))]
        for pid in ids:
            slot = assignments.get(pid, "BN")
            c.execute("UPDATE roster SET slot=?, updated_at=? WHERE team=? AND player_id=?", (slot, time.time(), team, pid))
        _log(c, team, "set_lineup", None, str(len(assignments)))


def replace_team(team: int, player_ids: list[str], slots: dict[str, str] | None = None, path=None) -> None:
    """Overwrite a team's roster (used by screenshot/Yahoo sync)."""
    with conn(path) as c:
        _init(c)
        c.execute("DELETE FROM roster WHERE team=?", (team,))
        for pid in player_ids:
            c.execute("INSERT OR REPLACE INTO roster (team, player_id, slot, updated_at) VALUES (?,?,?,?)", (team, pid, (slots or {}).get(pid, "BN"), time.time()))
        _log(c, team, "replace", None, f"{len(player_ids)} players")


def log(limit: int = 100, path=None) -> list[dict]:
    with conn(path) as c:
        _init(c)
        return [dict(r) for r in c.execute("SELECT id, ts, team, kind, player_id, detail FROM roster_log ORDER BY id DESC LIMIT ?", (limit,))]
