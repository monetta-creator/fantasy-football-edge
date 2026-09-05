"""Optional LLM layer via OpenRouter (open-source models). Explains; never computes.

Design ("forced" calls):
  * every call passes a complete fact sheet (numbers computed by our models);
  * the response is constrained to a strict JSON schema;
  * post-validation rejects any sentence that contains a number not present in the facts,
    names a player not on the allowed list, or exceeds the word limit.
Set OPENROUTER_API_KEY (and optionally OPENROUTER_MODEL) in .env. Short timeout, deterministic fallback.
"""
from __future__ import annotations

import json
import re

import httpx

from .config import Settings

URL = "https://openrouter.ai/api/v1/chat/completions"

RATIONALE_SCHEMA = {
    "name": "draft_rationale",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "rationale": {"type": "string", "description": "One sentence, max 32 words, uses only the given numbers."},
            "numbers_used": {"type": "array", "items": {"type": "number"}},
        },
        "required": ["rationale", "numbers_used"],
        "additionalProperties": False,
    },
}

RATIONALE_SYSTEM = (
    "You write one-sentence fantasy football draft rationales for an expert. Use ONLY the numbers in the fact sheet; "
    "never introduce a statistic, player, or claim that is not in it. Name the mechanism (scoring rule, scarcity, "
    "availability). No praise, no hedging. Max 32 words. Respond as JSON matching the schema."
)


def available(settings: Settings) -> bool:
    return bool(settings.openrouter_api_key)


def _post(settings: Settings, body: dict, timeout: float) -> dict | None:
    try:
        r = httpx.post(
            URL,
            headers={
                "Authorization": f"Bearer {settings.openrouter_api_key}",
                "HTTP-Referer": "http://localhost:3000",
                "X-Title": "ffedge draft assistant",
            },
            json=body,
            timeout=timeout,
        )
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def structured(settings: Settings, system: str, user: str, schema: dict, max_tokens: int = 200, timeout: float = 8.0) -> dict | None:
    """Chat completion constrained to a JSON schema. Returns the parsed object or None."""
    if not settings.openrouter_api_key:
        return None
    body = {
        "model": settings.openrouter_model,
        "max_tokens": max_tokens,
        "temperature": 0.2,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "response_format": {"type": "json_schema", "json_schema": schema},
    }
    data = _post(settings, body, timeout)
    if data is None:
        return None
    try:
        txt = data["choices"][0]["message"]["content"].strip()
        txt = re.sub(r"^```(?:json)?|```$", "", txt.strip(), flags=re.M).strip()
        return json.loads(txt)
    except Exception:
        return None


_NUM = re.compile(r"-?\d+(?:\.\d+)?")


def _numbers_in(text: str) -> list[float]:
    return [float(x) for x in _NUM.findall(text.replace(",", ""))]


def _fact_numbers(facts: dict) -> set[float]:
    out: set[float] = set()
    for v in facts.values():
        if isinstance(v, bool) or v is None:
            continue
        if isinstance(v, (int, float)):
            out.add(round(float(v), 2))
            out.add(round(float(v), 1))
            out.add(round(float(v)))
            if 0 <= float(v) <= 1:  # probabilities may be quoted as percents
                out.add(round(float(v) * 100))
        else:
            for n in _numbers_in(str(v)):
                out.add(round(n, 2)); out.add(round(n, 1)); out.add(round(n))
    return out


def grounded(text: str, facts: dict, allowed_names: list[str], max_words: int = 34) -> bool:
    """True if every number in `text` appears in `facts` and no foreign player name is used."""
    if not text or len(text.split()) > max_words:
        return False
    allowed = _fact_numbers(facts)
    for n in _numbers_in(text):
        if round(n, 2) in allowed or round(n, 1) in allowed or round(n) in allowed:
            continue
        return False
    # crude name guard: any "Firstname Lastname" capitalised pair must be an allowed name
    for m in re.finditer(r"\b([A-Z][a-z'\.]+(?: [A-Z][a-z'\.]+)+)\b", text):
        cand = m.group(1)
        if not any(cand in a or a in cand for a in allowed_names):
            return False
    return True


def rationale(settings: Settings, facts: dict, allowed_names: list[str]) -> str | None:
    """Return a validated one-sentence rationale, or None (caller keeps the deterministic text)."""
    user = "Fact sheet (JSON):\n" + json.dumps(facts, indent=1) + "\n\nWrite the one-sentence rationale."
    obj = structured(settings, RATIONALE_SYSTEM, user, RATIONALE_SCHEMA)
    if not obj or not isinstance(obj.get("rationale"), str):
        return None
    text = obj["rationale"].strip()
    return text if grounded(text, facts, allowed_names) else None
