"""SQLite persistence for the live draft: picks, team names, key/value settings."""
from __future__ import annotations

import sqlite3
import time
from contextlib import contextmanager

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS picks (
  pick_no INTEGER PRIMARY KEY,
  player_id TEXT NOT NULL,
  team INTEGER NOT NULL,
  created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS teams (
  slot INTEGER PRIMARY KEY,
  name TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS kv (
  key TEXT PRIMARY KEY,
  value TEXT
);
CREATE TABLE IF NOT EXISTS action_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts REAL NOT NULL,
  kind TEXT NOT NULL,
  detail TEXT
);
"""


@contextmanager
def conn(path=None):
    path = path or config.DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(str(path))
    c.row_factory = sqlite3.Row
    try:
        c.executescript(SCHEMA)
        yield c
        c.commit()
    finally:
        c.close()


def get_picks(path=None) -> list[dict]:
    with conn(path) as c:
        return [dict(r) for r in c.execute("SELECT pick_no, player_id, team FROM picks ORDER BY pick_no")]


def next_pick_no(path=None) -> int:
    with conn(path) as c:
        r = c.execute("SELECT MAX(pick_no) AS m FROM picks").fetchone()
        return int(r["m"] or 0) + 1


def add_pick(player_id: str, team: int | None = None, path=None) -> dict:
    with conn(path) as c:
        if c.execute("SELECT 1 FROM picks WHERE player_id=?", (player_id,)).fetchone():
            raise ValueError("player already drafted")
        r = c.execute("SELECT MAX(pick_no) AS m FROM picks").fetchone()
        pick_no = int(r["m"] or 0) + 1
        if pick_no > config.NUM_TEAMS * config.ROUNDS:
            raise ValueError("draft is complete")
        team = team or config.team_on_clock(pick_no)
        c.execute("INSERT INTO picks (pick_no, player_id, team, created_at) VALUES (?,?,?,?)", (pick_no, player_id, team, time.time()))
        c.execute("INSERT INTO action_log (ts, kind, detail) VALUES (?,?,?)", (time.time(), "pick", f"{pick_no}:{team}:{player_id}"))
        return {"pick_no": pick_no, "player_id": player_id, "team": team}


def undo(path=None) -> dict | None:
    with conn(path) as c:
        r = c.execute("SELECT pick_no, player_id, team FROM picks ORDER BY pick_no DESC LIMIT 1").fetchone()
        if not r:
            return None
        c.execute("DELETE FROM picks WHERE pick_no=?", (r["pick_no"],))
        c.execute("INSERT INTO action_log (ts, kind, detail) VALUES (?,?,?)", (time.time(), "undo", f"{r['pick_no']}:{r['player_id']}"))
        return dict(r)


def reset(path=None) -> None:
    with conn(path) as c:
        c.execute("DELETE FROM picks")
        c.execute("INSERT INTO action_log (ts, kind, detail) VALUES (?,?,?)", (time.time(), "reset", ""))


def get_team_names(path=None) -> dict[int, str]:
    with conn(path) as c:
        names = {int(r["slot"]): r["name"] for r in c.execute("SELECT slot, name FROM teams")}
    for s in range(1, config.NUM_TEAMS + 1):
        names.setdefault(s, config.TEAM_NAMES.get(s) or ("Me" if s == config.MY_SLOT else f"Team {s}"))
    return names


def set_team_names(names: dict[int, str], path=None) -> None:
    with conn(path) as c:
        for slot, name in names.items():
            c.execute("INSERT INTO teams (slot, name) VALUES (?,?) ON CONFLICT(slot) DO UPDATE SET name=excluded.name", (int(slot), name))


def get_kv(key: str, default=None, path=None):
    with conn(path) as c:
        r = c.execute("SELECT value FROM kv WHERE key=?", (key,)).fetchone()
        return r["value"] if r else default


def set_kv(key: str, value: str, path=None) -> None:
    with conn(path) as c:
        c.execute("INSERT INTO kv (key, value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))
