"""Draft-board screenshot import: vision model (OpenRouter) -> strict JSON -> fuzzy match to our pool.

The model only transcribes what is on the image. Every name is matched against the player pool; the
user reviews and confirms before anything is applied.
"""
from __future__ import annotations

import json
import re
from difflib import SequenceMatcher

from . import config
from .config import Settings
from .llm import _post
from .players import Player
from .sources.common import norm_name

EXTRACT_SCHEMA = {
    "name": "draft_board",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "board_type": {"type": "string", "description": "grid (teams as columns, rounds as rows) or list (picks in order)"},
            "picks": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "pick_no": {"type": ["integer", "null"], "description": "overall pick number if shown"},
                        "round": {"type": ["integer", "null"]},
                        "column": {"type": ["integer", "null"], "description": "1-based column index in a grid board"},
                        "player": {"type": "string", "description": "player name exactly as shown"},
                        "position": {"type": ["string", "null"]},
                        "nfl_team": {"type": ["string", "null"]},
                        "fantasy_team": {"type": ["string", "null"], "description": "drafting team name/column header if shown"},
                    },
                    "required": ["pick_no", "round", "column", "player", "position", "nfl_team", "fantasy_team"],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["board_type", "picks"],
        "additionalProperties": False,
    },
}

SYSTEM = (
    "You transcribe fantasy football draft boards from screenshots. Return every drafted player cell you can read, "
    "exactly as written (abbreviated names are fine), with pick number, round, column, position, NFL team and the "
    "fantasy team/column header when visible. Do not guess names that are not legible; omit unreadable cells. "
    "Respond as JSON matching the schema."
)


def extract(settings: Settings, image_data_url: str, timeout: float = 45.0) -> dict | None:
    if not settings.openrouter_api_key:
        return None
    body = {
        "model": settings.openrouter_vision_model,
        "max_tokens": 4000,
        "temperature": 0.0,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": [
                {"type": "text", "text": "Transcribe this draft board."},
                {"type": "image_url", "image_url": {"url": image_data_url}},
            ]},
        ],
        "response_format": {"type": "json_schema", "json_schema": EXTRACT_SCHEMA},
    }
    data = _post(settings, body, timeout)
    if not data:
        return None
    try:
        txt = data["choices"][0]["message"]["content"].strip()
        txt = re.sub(r"^```(?:json)?|```$", "", txt, flags=re.M).strip()
        return json.loads(txt)
    except Exception:
        return None


def _initial_last(name: str) -> tuple[str | None, str]:
    """'J. Gibbs' -> ('j', 'gibbs'); 'Jahmyr Gibbs' -> ('j', 'gibbs'); 'Gibbs' -> (None, 'gibbs')."""
    parts = [p for p in re.sub(r"[^A-Za-z' .-]", " ", name).split() if p]
    parts = [p for p in parts if p.lower().strip(".") not in ("jr", "sr", "ii", "iii", "iv")]
    if not parts:
        return None, ""
    if len(parts) == 1:
        return None, norm_name(parts[0])
    return parts[0][0].lower(), norm_name(parts[-1])


def match_player(text: str, players: list[Player], position: str | None = None, nfl_team: str | None = None) -> list[tuple[Player, float]]:
    """Return candidate players with confidence, best first."""
    q = norm_name(text)
    ini, last = _initial_last(text)
    pos = (position or "").upper().replace("DST", "DEF").replace("D/ST", "DEF") or None
    if pos and pos not in config.POSITIONS:
        pos = None
    team = (nfl_team or "").upper() or None
    scored = []
    for p in players:
        if pos and p.pos != pos:
            continue
        pn = norm_name(p.name)
        _, plast = _initial_last(p.name)
        s = SequenceMatcher(None, q, pn).ratio()
        if last and plast == last:
            s = max(s, 0.86 if ini is None else (0.95 if p.name[0].lower() == ini else 0.6))
        if team and p.team == team:
            s += 0.04
        if p.pos == "DEF" and (last in (p.team or "").lower() or q in norm_name(p.name)):
            s = max(s, 0.9)
        if s >= 0.6:
            scored.append((p, min(1.0, s)))
    scored.sort(key=lambda x: (-x[1], x[0].adp))
    return scored[:3]


def resolve(extracted: dict, players: list[Player], drafted_ids: set[str], team_names: dict[int, str]) -> list[dict]:
    """Turn extracted cells into proposed picks with match status, ordered by pick number when known."""
    rows = []
    name_to_slot = {norm_name(v): k for k, v in team_names.items()}
    for cell in extracted.get("picks", []):
        name = (cell.get("player") or "").strip()
        if not name:
            continue
        pick_no = cell.get("pick_no")
        rnd, col = cell.get("round"), cell.get("column")
        if pick_no is None and rnd and col and 1 <= col <= config.NUM_TEAMS:
            pick_no = (rnd - 1) * config.NUM_TEAMS + (col if rnd % 2 == 1 else config.NUM_TEAMS - col + 1)
        team = None
        ft = cell.get("fantasy_team")
        if ft:
            key = norm_name(ft)
            team = name_to_slot.get(key)
            if team is None:
                best = max(((SequenceMatcher(None, key, k).ratio(), s) for k, s in name_to_slot.items()), default=(0, None))
                if best[0] >= 0.8:
                    team = best[1]
        if team is None and pick_no:
            team = config.team_on_clock(pick_no)
        cands = match_player(name, players, cell.get("position"), cell.get("nfl_team"))
        status, chosen, conf = "unknown", None, 0.0
        if cands:
            chosen, conf = cands[0]
            if chosen.id in drafted_ids:
                status = "already_drafted"
            elif conf >= 0.85 and (len(cands) == 1 or cands[1][1] < conf - 0.08):
                status = "ok"
            else:
                status = "ambiguous"
        rows.append({
            "text": name, "position": cell.get("position"), "nfl_team": cell.get("nfl_team"), "fantasy_team": ft,
            "pick_no": pick_no, "round": rnd, "column": col, "team": team, "status": status, "confidence": round(conf, 2),
            "player_id": chosen.id if chosen else None, "player_name": chosen.name if chosen else None,
            "candidates": [{"id": p.id, "name": p.name, "pos": p.pos, "team": p.team, "confidence": round(c, 2)} for p, c in cands],
        })
    rows.sort(key=lambda r: (r["pick_no"] is None, r["pick_no"] or 0))
    return rows
