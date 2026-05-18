"""Claude API wrapper for the verification system.

Two-tier routing, exactly as proposed in the deck:
  - Heavy: Claude Opus 4.7 for vision + ambiguous extraction
  - Light: Claude Haiku 4.5 for cheap classification (~1/20 the cost)

If ANTHROPIC_API_KEY is set in the environment, calls are real.
Otherwise we fall back to a deterministic mock so the demo still works.
"""
from __future__ import annotations

import base64
import os
import re
import time
from pathlib import Path
from typing import Optional

# Approximate per-1M-token pricing (USD) for cost telemetry.
PRICES = {
    "opus":  {"input":  15.00, "output":  75.00},
    "haiku": {"input":   0.80, "output":   4.00},
}

MODEL_HEAVY = os.getenv("CLAUDE_MODEL_HEAVY", "claude-opus-4-7")
MODEL_LIGHT = os.getenv("CLAUDE_MODEL_LIGHT", "claude-haiku-4-5-20251001")


def _have_key() -> bool:
    return bool(os.getenv("ANTHROPIC_API_KEY"))


def _client():
    from anthropic import Anthropic  # noqa: PLC0415  (lazy import)
    return Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])


def _cost(model_tier: str, usage) -> float:
    p = PRICES.get(model_tier)
    if not p:
        return 0.0
    return (usage.input_tokens * p["input"] + usage.output_tokens * p["output"]) / 1_000_000


def extract_from_html(html: str, field_description: str, max_chars: int = 6000) -> tuple[str, float, dict]:
    """Use Claude to extract a single field from HTML. Returns (value, cost_usd, meta).

    Mocked behavior (when no API key): regex/keyword search of the field
    description against the HTML, falling back to '' if not found.
    """
    snippet = html[:max_chars]
    if not _have_key():
        return _mock_extract(snippet, field_description), 0.0, {"mode": "mock"}

    client = _client()
    msg = client.messages.create(
        model=MODEL_HEAVY,
        max_tokens=200,
        messages=[{
            "role": "user",
            "content": (
                "You are an extraction agent for a license-verification system. "
                f"From the HTML below, extract ONLY the value for: '{field_description}'. "
                "Respond with the value and nothing else. If not present, respond with 'NOT_FOUND'.\n\n"
                f"HTML:\n{snippet}"
            ),
        }],
    )
    value = msg.content[0].text.strip()
    cost = _cost("opus", msg.usage)
    return value, cost, {
        "mode": "live",
        "model": MODEL_HEAVY,
        "input_tokens": msg.usage.input_tokens,
        "output_tokens": msg.usage.output_tokens,
    }


def classify_match(crm_value: str, scraped_value: str, field: str) -> tuple[str, float, dict]:
    """Two-tier: cheap Haiku confirms or flags a match. Returns ('match'|'mismatch'|'uncertain', cost, meta)."""
    if not _have_key():
        return _mock_classify(crm_value, scraped_value), 0.0, {"mode": "mock"}

    client = _client()
    msg = client.messages.create(
        model=MODEL_LIGHT,
        max_tokens=50,
        messages=[{
            "role": "user",
            "content": (
                f"Field: {field}\n"
                f"CRM value:     {crm_value!r}\n"
                f"Scraped value: {scraped_value!r}\n\n"
                "Are these the same? Respond with exactly one word: MATCH, MISMATCH, or UNCERTAIN."
            ),
        }],
    )
    raw = msg.content[0].text.strip().upper()
    if "MATCH" in raw and "MISMATCH" not in raw:
        verdict = "match"
    elif "MISMATCH" in raw:
        verdict = "mismatch"
    else:
        verdict = "uncertain"
    return verdict, _cost("haiku", msg.usage), {"mode": "live", "model": MODEL_LIGHT, "raw": raw}


def vision_extract(image_path: Path, field_description: str) -> tuple[str, float, dict]:
    """Last-resort vision fallback: screenshot -> Opus vision -> extracted value."""
    if not _have_key():
        return _mock_extract_from_filename(image_path, field_description), 0.0, {"mode": "mock"}

    client = _client()
    img_b64 = base64.standard_b64encode(image_path.read_bytes()).decode("ascii")
    msg = client.messages.create(
        model=MODEL_HEAVY,
        max_tokens=200,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": img_b64}},
                {"type": "text", "text": f"Extract ONLY the value for '{field_description}' from this screenshot. Respond with the value alone, or 'NOT_FOUND'."},
            ],
        }],
    )
    return msg.content[0].text.strip(), _cost("opus", msg.usage), {
        "mode": "live", "model": MODEL_HEAVY, "vision": True,
        "input_tokens": msg.usage.input_tokens, "output_tokens": msg.usage.output_tokens,
    }


# ── Mock fallbacks (no API key) ────────────────────────────────────────────

def _mock_extract(html: str, field_description: str) -> str:
    """Very simple HTML extraction: look for the field name + a sibling/cell value."""
    fd = field_description.lower()
    # Try data attributes first
    if "expir" in fd:
        m = re.search(r'data-field=["\']expiration["\'][^>]*>([^<]+)', html, re.I)
        if m:
            return m.group(1).strip()
        m = re.search(r"Expir(?:ation|es)\s+Date[^<]*</[^>]+>\s*<[^>]+>([^<]+)", html, re.I)
        if m:
            return m.group(1).strip()
    if "name" in fd:
        m = re.search(r'data-field=["\']name["\'][^>]*>([^<]+)', html, re.I)
        if m:
            return m.group(1).strip()
    if "state" in fd:
        m = re.search(r'data-field=["\']state["\'][^>]*>([^<]+)', html, re.I)
        if m:
            return m.group(1).strip()
    return "NOT_FOUND"


def _mock_classify(a: str, b: str) -> str:
    if a is None or b is None:
        return "uncertain"
    return "match" if a.strip().lower() == b.strip().lower() else "mismatch"


def _mock_extract_from_filename(image_path: Path, field_description: str) -> str:
    return "NOT_FOUND"
