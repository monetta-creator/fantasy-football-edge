"""ESPN injuries feed: status, fantasy designation, return date, beat-writer comment."""
from __future__ import annotations

import httpx

from .cache import cached_json
from .common import norm_name

URL = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/injuries"


def _fetch() -> list[dict]:
    r = httpx.get(URL, timeout=60)
    r.raise_for_status()
    out = []
    for t in r.json().get("injuries", []):
        for i in t.get("injuries", []):
            a = i.get("athlete") or {}
            d = i.get("details") or {}
            out.append({
                "name": a.get("displayName"),
                "pos": (a.get("position") or {}).get("abbreviation"),
                "team": t.get("displayName"),
                "status": i.get("status"),
                "fantasy_status": ((d.get("fantasyStatus") or {}).get("abbreviation")),
                "type": d.get("type"),
                "detail": d.get("detail"),
                "return_date": d.get("returnDate"),
                "comment": (i.get("longComment") or i.get("shortComment") or "")[:700],
                "date": i.get("date"),
            })
    return out


def load(force: bool = False) -> tuple[dict[str, dict], dict]:
    """Return {pos:normname -> injury row}, keeping the most recent per player."""
    raw, meta = cached_json("espn_injuries", _fetch, ttl_seconds=3 * 3600, force=force)
    out: dict[str, dict] = {}
    for r in raw:
        if not r.get("name") or not r.get("pos"):
            continue
        k = f"{r['pos']}:{norm_name(r['name'])}"
        prev = out.get(k)
        if prev is None or (r.get("date") or "") > (prev.get("date") or ""):
            out[k] = r
    return out, meta
