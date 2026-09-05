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


LAST: dict = {"status": "off", "model": None, "ms": None, "detail": None}


def _record(status: str, model: str | None, ms: float | None, detail: str | None = None) -> None:
    LAST.update({"status": status, "model": model, "ms": None if ms is None else int(ms), "detail": detail})


def structured(settings: Settings, system: str, user: str, schema: dict, max_tokens: int = 1200, timeout: float = 25.0, model: str | None = None) -> dict | None:
    """Chat completion constrained to a JSON schema. Returns the parsed object or None (LAST records why)."""
    if not settings.openrouter_api_key:
        _record("off", None, None, "no OPENROUTER_API_KEY")
        return None
    import time as _t
    t0 = _t.time()
    model = model or settings.openrouter_model
    body = {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": 0.2,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "response_format": {"type": "json_schema", "json_schema": schema},
    }
    if settings.openrouter_reasoning_effort:
        body["reasoning"] = {"effort": settings.openrouter_reasoning_effort}
    data = _post(settings, body, timeout)
    if data is None:
        _record("error", model, (_t.time() - t0) * 1000, "request failed or timed out")
        return None
    if data.get("error"):
        _record("error", model, (_t.time() - t0) * 1000, str(data["error"].get("message", ""))[:160])
        return None
    try:
        txt = (data["choices"][0]["message"].get("content") or "").strip()
        txt = re.sub(r"^```(?:json)?|```$", "", txt.strip(), flags=re.M).strip()
        obj = json.loads(txt)
        _record("ok", model, (_t.time() - t0) * 1000)
        return obj
    except Exception as e:
        _record("error", model, (_t.time() - t0) * 1000, f"unparseable response: {e}")
        return None


_NUM = re.compile(r"-?\d+(?:\.\d+)?")


def _numbers_in(text: str) -> list[float]:
    return [float(x) for x in _NUM.findall(text.replace(",", ""))]


def _fact_numbers(facts: dict) -> set[float]:
    out: set[float] = set()
    for n in _numbers_in(" ".join(str(k) for k in facts.keys())):  # keys like "week 1" or "2025 results" carry numbers too
        out.add(round(n, 2)); out.add(round(n, 1)); out.add(round(n))
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


def grounding_problem(text: str, facts: dict, allowed_names: list[str], max_words: int = 34) -> str | None:
    """None if every number in `text` appears in `facts` and no foreign player name is used; else the reason."""
    if not text:
        return "empty"
    if len(text.split()) > max_words:
        return f"too long ({len(text.split())} words)"
    allowed = _fact_numbers(facts)
    for n in _numbers_in(text):
        if round(n, 2) in allowed or round(n, 1) in allowed or round(n) in allowed:
            continue
        return f"number {n:g} not in facts"
    # name guard: a capitalised multi-word phrase must share a token with an allowed name (catches invented players,
    # tolerates sentence-initial verbs like "Draft Christian McCaffrey")
    allowed_tokens = {t.lower().strip(".'") for a in allowed_names for t in a.split() if len(t) > 2}
    for m in re.finditer(r"\b([A-Z][a-z'\.]+(?: [A-Z][a-z'\.]+)+)\b", text):
        cand = m.group(1)
        toks = {t.lower().strip(".'") for t in cand.split()}
        if any(cand in a or a in cand for a in allowed_names) or (toks & allowed_tokens):
            continue
        return f"name '{cand}' not allowed"
    return None


def grounded(text: str, facts: dict, allowed_names: list[str], max_words: int = 34) -> bool:
    return grounding_problem(text, facts, allowed_names, max_words) is None


def rationale(settings: Settings, facts: dict, allowed_names: list[str]) -> str | None:
    """Return a validated one-sentence rationale, or None (caller keeps the deterministic text)."""
    user = "Fact sheet (JSON):\n" + json.dumps(facts, indent=1) + "\n\nWrite the one-sentence rationale."
    obj = structured(settings, RATIONALE_SYSTEM, user, RATIONALE_SCHEMA)
    if not obj or not isinstance(obj.get("rationale"), str):
        return None
    text = obj["rationale"].strip()
    if grounded(text, facts, allowed_names):
        return text
    _record("rejected", LAST.get("model"), LAST.get("ms"), "sentence used a number or name not in the fact sheet")
    return None


EXPLAIN_SCHEMA = {
    "name": "explanation",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {"explanation": {"type": "string", "description": "2-4 sentences, max 90 words, uses only the given numbers and names."}},
        "required": ["explanation"],
        "additionalProperties": False,
    },
}
EXPLAIN_SYSTEM = (
    "You are an analyst for an expert fantasy football manager. Using ONLY the fact sheet, write 2-4 plain sentences "
    "(max 90 words) that explain the decision or the player: what drives the value, what the risk is, and what the numbers "
    "say relative to alternatives. Never introduce a statistic, player, or claim not in the fact sheet. No praise, no hedging. "
    "Respond as JSON matching the schema."
)


def explain(settings: Settings, facts: dict, allowed_names: list[str], question: str) -> dict:
    """Grounded multi-sentence explanation. Returns {text, status, model, ms, detail}."""
    user = "Fact sheet (JSON):\n" + json.dumps(facts, indent=1) + "\n\nTask: " + question
    obj = structured(settings, EXPLAIN_SYSTEM, user, EXPLAIN_SCHEMA, max_tokens=1500)
    text = obj.get("explanation", "").strip() if isinstance(obj, dict) else ""
    problem = grounding_problem(text, facts, allowed_names, max_words=110) if text else None
    if text and problem:
        _record("rejected", LAST.get("model"), LAST.get("ms"), f"rejected: {problem}")
        text = ""
    return {"text": text or None, **LAST}
