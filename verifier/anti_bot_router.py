"""Anti-bot tier router.

Each state adapter declares its current tier. The router:
  * picks the correct runner (Playwright / Camoufox / Browserbase / HITL)
  * tracks per-state success rate
  * auto-promotes a state's tier after N consecutive failures

Tiers (in order of cheapness):
  T1 · Native      — plain Playwright
  T2 · Stealth     — Camoufox (Firefox + C++ stealth patches)
  T3 · Managed     — Browserbase API (simulated in demo — narrated only)
  T4 · HITL        — surface CAPTCHA/Cloudflare wall to a human operator
"""
from __future__ import annotations

import os
import threading
from collections import defaultdict, deque
from dataclasses import dataclass


TIER_NATIVE = "T1"
TIER_STEALTH = "T2"
TIER_MANAGED = "T3"
TIER_HITL = "T4"

TIER_LABELS = {
    TIER_NATIVE:  "T1 · Playwright",
    TIER_STEALTH: "T2 · Camoufox (stealth Firefox)",
    TIER_MANAGED: "T3 · Browserbase (managed, simulated)",
    TIER_HITL:    "T4 · Human-in-the-loop",
}

# Promotion threshold: 3 consecutive failures in current tier → bump up
PROMOTE_AFTER_FAILURES = 3
HISTORY_SIZE = 10


@dataclass
class TierState:
    state_code: str
    declared_tier: str
    effective_tier: str
    recent_outcomes: deque  # of True/False


class AntiBotRouter:
    def __init__(self):
        self._state: dict[str, TierState] = {}
        self._lock = threading.Lock()

    def _get_or_init(self, state_code: str, declared_tier: str) -> TierState:
        if state_code not in self._state:
            self._state[state_code] = TierState(
                state_code=state_code,
                declared_tier=declared_tier,
                effective_tier=declared_tier,
                recent_outcomes=deque(maxlen=HISTORY_SIZE),
            )
        return self._state[state_code]

    def get_tier(self, state_code: str, declared_tier: str) -> str:
        with self._lock:
            s = self._get_or_init(state_code, declared_tier)
            return s.effective_tier

    def record_result(self, state_code: str, declared_tier: str, success: bool) -> str:
        """Record an outcome; auto-promote tier on consecutive failures.

        Returns the (possibly new) effective tier.
        """
        with self._lock:
            s = self._get_or_init(state_code, declared_tier)
            s.recent_outcomes.append(success)
            if not success:
                last_n = list(s.recent_outcomes)[-PROMOTE_AFTER_FAILURES:]
                if len(last_n) == PROMOTE_AFTER_FAILURES and not any(last_n):
                    s.effective_tier = _next_tier(s.effective_tier)
            else:
                # Auto-demote back to declared on a clean streak
                last_n = list(s.recent_outcomes)[-3:]
                if len(last_n) == 3 and all(last_n) and s.effective_tier != s.declared_tier:
                    s.effective_tier = s.declared_tier
            return s.effective_tier

    def snapshot(self) -> dict[str, dict]:
        with self._lock:
            out = {}
            for k, v in self._state.items():
                last = list(v.recent_outcomes)
                out[k] = {
                    "declared": v.declared_tier,
                    "effective": v.effective_tier,
                    "recent": last,
                    "success_rate": (sum(1 for x in last if x) / len(last)) if last else None,
                }
            return out


def _next_tier(t: str) -> str:
    return {TIER_NATIVE: TIER_STEALTH, TIER_STEALTH: TIER_MANAGED, TIER_MANAGED: TIER_HITL}.get(t, TIER_HITL)


# Process-wide singleton
ROUTER = AntiBotRouter()


# ── Runner dispatch ───────────────────────────────────────────────────────

def camoufox_available() -> bool:
    try:
        import camoufox  # noqa: F401
        return True
    except Exception:
        return False


def browserbase_available() -> bool:
    return bool(os.getenv("BROWSERBASE_API_KEY"))


def runner_for_tier(tier: str):
    """Return the appropriate runner module for the given tier.

    For T2 we return Camoufox if installed; otherwise we transparently fall
    back to plain Playwright (and the trace will note this so the panel
    sees what happened).

    For T3 (Browserbase) we always fall back to plain Playwright in the
    demo since Browserbase is a paid managed service — but the trace
    narrates "T3 · Browserbase (simulated)".

    T4 returns None — caller should skip browser and go straight to HITL.
    """
    if tier == TIER_NATIVE:
        from verifier import playwright_runner
        return ("playwright", playwright_runner)
    if tier == TIER_STEALTH:
        if camoufox_available():
            from verifier.runners import camoufox_runner
            return ("camoufox", camoufox_runner)
        from verifier import playwright_runner
        return ("playwright-fallback", playwright_runner)
    if tier == TIER_MANAGED:
        # In demo we always simulate. In production this would be a Browserbase client.
        from verifier import playwright_runner
        return ("browserbase-simulated", playwright_runner)
    if tier == TIER_HITL:
        return ("hitl", None)
    raise ValueError(f"unknown tier: {tier}")
