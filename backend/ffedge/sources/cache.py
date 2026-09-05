"""Tiny JSON file cache with TTL for external sources."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Callable

from .. import config


def cached_json(name: str, fetch: Callable[[], Any], ttl_seconds: int = 6 * 3600, force: bool = False) -> tuple[Any, dict]:
    """Return (data, meta). meta = {fetched_at, age_s, from_cache, error}."""
    config.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = config.CACHE_DIR / f"{name}.json"
    now = time.time()
    if path.exists() and not force:
        try:
            blob = json.loads(path.read_text())
            age = now - blob.get("fetched_at", 0)
            if age < ttl_seconds:
                return blob["data"], {"fetched_at": blob["fetched_at"], "age_s": age, "from_cache": True, "error": None}
        except Exception:
            pass
    try:
        data = fetch()
        path.write_text(json.dumps({"fetched_at": now, "data": data}))
        return data, {"fetched_at": now, "age_s": 0, "from_cache": False, "error": None}
    except Exception as e:  # fall back to stale cache if any
        if path.exists():
            blob = json.loads(path.read_text())
            return blob["data"], {"fetched_at": blob["fetched_at"], "age_s": now - blob["fetched_at"], "from_cache": True, "error": str(e)}
        raise


def cache_meta(name: str) -> dict | None:
    path = config.CACHE_DIR / f"{name}.json"
    if not path.exists():
        return None
    try:
        blob = json.loads(path.read_text())
        return {"fetched_at": blob.get("fetched_at"), "age_s": time.time() - blob.get("fetched_at", 0)}
    except Exception:
        return None
