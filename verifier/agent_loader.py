"""Load + filter agents from the JSON fixture.

In production this is `SELECT * FROM agents WHERE active_since > NOW() - interval '7d'`.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "agents.json"


def load_all() -> list[dict]:
    if not DATA_PATH.exists():
        # Lazy generation if missing
        from verifier.agent_generator import write_fixture
        write_fixture()
    return json.loads(DATA_PATH.read_text())["agents"]


def newly_joined(within_days: int = 7) -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=within_days)
    out = []
    for a in load_all():
        if not a["onboarding"].get("newly_joined"):
            continue
        ts = a["onboarding"]["active_since"]
        if datetime.fromisoformat(ts) >= cutoff:
            out.append(a)
    return out


def by_id(agent_id: str) -> dict:
    for a in load_all():
        if a["agent_id"] == agent_id:
            return a
    raise KeyError(agent_id)


def demo_targets() -> list[dict]:
    """The 3 real-onereal-URL demo agents (have is_real_demo_target flag)."""
    return [a for a in load_all() if a["onboarding"].get("is_real_demo_target")]
