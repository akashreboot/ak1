"""Confidence-scored disambiguation for DRE search results.

Public DRE lookups frequently return multiple rows for the same license #
(different license types, same number used across professions in WA, etc.).
This module picks the right row from a list of candidates.

Scoring (max 1.0):
  * license_type_match : 0.40   exact-or-fuzzy match on declared agent license type
  * status_match       : 0.20   row.status == "Active"
  * name_similarity    : 0.30   token-set Jaccard between names
  * geography_signal   : 0.10   row.city ∈ agent.service_areas (or state if no city)

Thresholds:
  score ≥ 0.85 → confident_pick
  0.55–0.85    → ai_tiebreak (call out for LLM)
  < 0.55       → quarantine (HITL)
"""
from __future__ import annotations

import re
from typing import Optional


def _tokenize(name: str) -> set[str]:
    return {t.lower() for t in re.split(r"[\s,]+", name) if len(t) >= 2}


def name_similarity(a: Optional[str], b: Optional[str]) -> float:
    if not a or not b:
        return 0.0
    ta, tb = _tokenize(a), _tokenize(b)
    if not ta or not tb:
        return 0.0
    inter = ta & tb
    union = ta | tb
    return len(inter) / len(union)


def score_candidate(candidate: dict, expected: dict) -> tuple[float, dict]:
    """Score one DRE result row against expected agent metadata."""
    breakdown = {}

    # license_type
    cand_type = (candidate.get("license_type") or "").strip().lower()
    exp_type = (expected.get("license_type") or "").strip().lower()
    if cand_type and exp_type:
        if cand_type == exp_type:
            t_score = 1.0
        else:
            t_tokens = set(re.split(r"\s+", cand_type))
            e_tokens = set(re.split(r"\s+", exp_type))
            t_score = len(t_tokens & e_tokens) / max(1, len(t_tokens | e_tokens))
    else:
        t_score = 0.5  # unknown, neutral
    breakdown["license_type"] = round(t_score, 3)

    # status
    status = (candidate.get("status") or "").lower()
    s_score = 1.0 if "active" in status else (0.0 if "cancel" in status or "expired" in status else 0.4)
    breakdown["status"] = round(s_score, 3)

    # name similarity
    n_score = name_similarity(candidate.get("name"), expected.get("name"))
    breakdown["name"] = round(n_score, 3)

    # geography
    cand_city = (candidate.get("city") or "").lower()
    exp_cities = {(c or "").lower() for c in (expected.get("service_areas") or [])}
    exp_state = (expected.get("state_full_name") or "").lower()
    if cand_city and (cand_city in exp_cities or any(cand_city in c for c in exp_cities)):
        g_score = 1.0
    elif cand_city and exp_state and exp_state[:3] in cand_city:
        g_score = 0.6
    elif candidate.get("state_code") and candidate["state_code"] == expected.get("state_code"):
        g_score = 0.6
    else:
        g_score = 0.4
    breakdown["geography"] = round(g_score, 3)

    total = 0.40 * t_score + 0.20 * s_score + 0.30 * n_score + 0.10 * g_score
    return round(total, 3), breakdown


def disambiguate(candidates: list[dict], expected: dict) -> dict:
    """Pick the best matching row, or signal quarantine.

    Returns:
      {
        decision: "confident_pick" | "ai_tiebreak" | "quarantine",
        pick: <candidate dict> | None,
        confidence: float,
        breakdown: { ... per-field ... },
        all_scored: [ {candidate, score, breakdown}, ... ]
      }
    """
    if not candidates:
        return {"decision": "quarantine", "pick": None, "confidence": 0.0,
                "breakdown": {}, "all_scored": [], "reason": "no_candidates"}

    scored = []
    for c in candidates:
        score, breakdown = score_candidate(c, expected)
        scored.append({"candidate": c, "score": score, "breakdown": breakdown})
    scored.sort(key=lambda x: x["score"], reverse=True)

    top = scored[0]
    second = scored[1] if len(scored) > 1 else None
    confidence = top["score"]

    # If two candidates are very close, force AI tiebreak even if score is high
    margin = (confidence - second["score"]) if second else 1.0

    if confidence >= 0.85 and margin >= 0.10:
        decision = "confident_pick"
    elif confidence >= 0.55:
        decision = "ai_tiebreak"
    else:
        decision = "quarantine"

    return {
        "decision": decision, "pick": top["candidate"], "confidence": confidence,
        "breakdown": top["breakdown"], "all_scored": scored, "margin": round(margin, 3),
    }
