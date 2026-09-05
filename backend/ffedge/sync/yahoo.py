"""Yahoo Fantasy Sports API client (OAuth2, read-only). Dormant until YAHOO_CLIENT_ID/SECRET exist.

Flow: /api/yahoo/auth-url -> user signs in at Yahoo -> pastes the code (redirect_uri "oob") ->
/api/yahoo/callback exchanges it -> tokens stored in data/yahoo_token.json and refreshed on demand.
All reads are parsed into the same plain dicts the screenshot/manual sync paths produce.
"""
from __future__ import annotations

import base64
import json
import time
from pathlib import Path

import httpx

from .. import config

AUTH_URL = "https://api.login.yahoo.com/oauth2/request_auth"
TOKEN_URL = "https://api.login.yahoo.com/oauth2/get_token"
API = "https://fantasysports.yahooapis.com/fantasy/v2"
TOKEN_PATH = config.DATA_DIR / "yahoo_token.json"


class YahooClient:
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str = "oob", token_path: Path = TOKEN_PATH):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.token_path = token_path
        self.token: dict | None = None
        if token_path.exists():
            try:
                self.token = json.loads(token_path.read_text())
            except Exception:
                self.token = None

    # ---- OAuth ------------------------------------------------------------------------------
    def auth_url(self) -> str:
        return f"{AUTH_URL}?client_id={self.client_id}&redirect_uri={self.redirect_uri}&response_type=code&language=en-us"

    def _basic(self) -> dict:
        raw = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
        return {"Authorization": f"Basic {raw}", "Content-Type": "application/x-www-form-urlencoded"}

    def exchange_code(self, code: str) -> dict:
        r = httpx.post(TOKEN_URL, headers=self._basic(), data={"grant_type": "authorization_code", "redirect_uri": self.redirect_uri, "code": code}, timeout=30)
        r.raise_for_status()
        self._save(r.json())
        return self.token

    def refresh(self) -> dict:
        if not self.token or not self.token.get("refresh_token"):
            raise RuntimeError("no refresh token; run the auth flow")
        r = httpx.post(TOKEN_URL, headers=self._basic(), data={"grant_type": "refresh_token", "redirect_uri": self.redirect_uri, "refresh_token": self.token["refresh_token"]}, timeout=30)
        r.raise_for_status()
        self._save(r.json())
        return self.token

    def _save(self, tok: dict) -> None:
        tok["obtained_at"] = time.time()
        self.token = tok
        self.token_path.parent.mkdir(parents=True, exist_ok=True)
        self.token_path.write_text(json.dumps(tok))

    def connected(self) -> bool:
        return bool(self.token and self.token.get("access_token"))

    def _headers(self) -> dict:
        if not self.token:
            raise RuntimeError("not authorized")
        if time.time() - self.token.get("obtained_at", 0) > self.token.get("expires_in", 3600) - 60:
            self.refresh()
        return {"Authorization": f"Bearer {self.token['access_token']}"}

    def get(self, path: str, retries: int = 3) -> dict:
        """GET with JSON format, token refresh on 401, exponential backoff on 429/5xx."""
        url = f"{API}/{path}{'&' if '?' in path else '?'}format=json"
        delay = 1.0
        for attempt in range(retries):
            r = httpx.get(url, headers=self._headers(), timeout=30)
            if r.status_code == 401 and attempt == 0:
                self.refresh()
                continue
            if r.status_code in (429, 500, 502, 503) and attempt < retries - 1:
                time.sleep(delay)
                delay *= 2
                continue
            r.raise_for_status()
            return r.json()
        raise RuntimeError("yahoo request failed")

    # ---- Keys -------------------------------------------------------------------------------
    def game_key(self) -> str:
        d = self.get("game/nfl")
        return str(d["fantasy_content"]["game"][0]["game_key"])

    def league_key(self) -> str:
        return f"{self.game_key()}.l.{config.LEAGUE_ID}"

    # ---- Reads (parsed to plain dicts) ------------------------------------------------------
    def rosters(self) -> list[dict]:
        lk = self.league_key()
        d = self.get(f"league/{lk}/teams/roster")
        return parse_rosters(d)

    def free_agents(self, start: int = 0, count: int = 25, status: str = "A") -> list[dict]:
        lk = self.league_key()
        d = self.get(f"league/{lk}/players;status={status};start={start};count={count};sort=AR")
        return parse_players(d)

    def transactions(self, count: int = 50) -> list[dict]:
        lk = self.league_key()
        d = self.get(f"league/{lk}/transactions;count={count}")
        return parse_transactions(d)

    def scoreboard(self, week: int | None = None) -> dict:
        lk = self.league_key()
        return self.get(f"league/{lk}/scoreboard" + (f";week={week}" if week else ""))

    def standings(self) -> dict:
        return self.get(f"league/{self.league_key()}/standings")

    def draft_results(self) -> list[dict]:
        d = self.get(f"league/{self.league_key()}/draftresults")
        return parse_draft_results(d)


# ---- Parsers (Yahoo's JSON is a list-of-dicts soup; these flatten it) --------------------------
def _flatten(obj) -> dict:
    """Merge Yahoo's [{k:v},{k:v},...] fragments into one dict."""
    out = {}
    if isinstance(obj, dict):
        return obj
    for part in obj or []:
        if isinstance(part, dict):
            out.update(part)
    return out


def _iter_numbered(d: dict):
    for k, v in (d or {}).items():
        if k.isdigit():
            yield v


def parse_player(pl) -> dict:
    p = _flatten(pl[0] if isinstance(pl, list) and pl and isinstance(pl[0], list) else pl)
    name = (p.get("name") or {}).get("full")
    pos = (p.get("display_position") or "").split(",")[0]
    pos = "DEF" if pos == "DEF" else pos
    return {
        "yahoo_id": str(p.get("player_id")), "player_key": p.get("player_key"), "name": name, "pos": pos,
        "team": (p.get("editorial_team_abbr") or "").upper(), "status": p.get("status"), "injury_note": p.get("injury_note"),
        "bye": ((p.get("bye_weeks") or {}).get("week")),
    }


def parse_rosters(d: dict) -> list[dict]:
    teams = []
    league = d["fantasy_content"]["league"]
    tdict = league[1]["teams"]
    for t in _iter_numbered(tdict):
        team = _flatten(t["team"][0])
        roster = t["team"][1]["roster"]["0"]["players"]
        players = []
        for pl in _iter_numbered(roster):
            frag = pl["player"]
            base = parse_player(frag[0])
            sel = _flatten(frag[1]).get("selected_position") if len(frag) > 1 else None
            base["slot"] = _flatten(sel).get("position") if sel else None
            players.append(base)
        teams.append({"team_key": team.get("team_key"), "team_id": int(team.get("team_id", 0)), "name": team.get("name"), "players": players})
    return teams


def parse_players(d: dict) -> list[dict]:
    out = []
    league = d["fantasy_content"]["league"]
    for pl in _iter_numbered(league[1]["players"]):
        out.append(parse_player(pl["player"][0]))
    return out


def parse_transactions(d: dict) -> list[dict]:
    out = []
    league = d["fantasy_content"]["league"]
    for tr in _iter_numbered(league[1]["transactions"]):
        meta = _flatten(tr["transaction"][0])
        players = []
        pd = tr["transaction"][1].get("players") if len(tr["transaction"]) > 1 else None
        for pl in _iter_numbered(pd or {}):
            base = parse_player(pl["player"][0])
            td = _flatten(pl["player"][1]).get("transaction_data") if len(pl["player"]) > 1 else None
            td = td[0] if isinstance(td, list) and td else td
            base["type"] = (td or {}).get("type")
            base["source_type"] = (td or {}).get("source_type")
            base["destination_team_key"] = (td or {}).get("destination_team_key")
            base["source_team_key"] = (td or {}).get("source_team_key")
            players.append(base)
        out.append({"id": meta.get("transaction_id"), "type": meta.get("type"), "status": meta.get("status"), "timestamp": int(meta.get("timestamp", 0)), "players": players})
    return out


def parse_draft_results(d: dict) -> list[dict]:
    out = []
    league = d["fantasy_content"]["league"]
    for dr in _iter_numbered(league[1]["draft_results"]):
        r = dr["draft_result"]
        out.append({"pick": int(r["pick"]), "round": int(r["round"]), "team_key": r["team_key"], "player_key": r.get("player_key")})
    return out


def client_from_settings(settings: config.Settings) -> YahooClient | None:
    if not (settings.yahoo_client_id and settings.yahoo_client_secret):
        return None
    return YahooClient(settings.yahoo_client_id, settings.yahoo_client_secret)
