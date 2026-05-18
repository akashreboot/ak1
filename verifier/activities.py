"""Activities — the individual steps the workflow orchestrates.

Each activity:
  * receives the TraceContext (so it can record artifact paths, LLM cost, etc.)
  * raises RetryableError / FatalError / HitlPause as appropriate
  * returns a serializable result that the workflow stores for replay
"""
from __future__ import annotations

import time
from datetime import datetime, timezone

from verifier import db
from verifier import llm_claude
from verifier.adapter_loader import load_adapter
from verifier.cache import SELECTOR_CACHE
from verifier.fixtures import get_agent
from verifier.playwright_runner import dre_lookup, join_real_lookup, playwright_available
from verifier.trace import TraceContext, now_iso
from verifier.workflow import HitlPause, RetryableError


STATE_FULL_NAME = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CA": "California",
    "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware", "FL": "Florida", "GA": "Georgia",
    "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois", "IN": "Indiana", "IA": "Iowa",
    "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi",
    "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada", "NH": "New Hampshire",
    "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York", "NC": "North Carolina",
    "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania",
    "RI": "Rhode Island", "SC": "South Carolina", "SD": "South Dakota", "TN": "Tennessee",
    "TX": "Texas", "UT": "Utah", "VT": "Vermont", "VA": "Virginia", "WA": "Washington",
    "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming",
}


# ── 1. Metadata fetch (mocked CRM API) ────────────────────────────────────

def fetch_metadata(ctx: TraceContext) -> dict:
    """In production this hits the internal Agent API. Here we read fixtures."""
    time.sleep(0.15)
    return get_agent(ctx.agent["agent_id"])


# ── 2. JoinReal verification ──────────────────────────────────────────────

def verify_joinreal(ctx: TraceContext, headed_browser: bool = True) -> dict:
    """Find the agent on JoinReal, confirm the listed state matches the CRM."""
    agent = ctx.agent
    result = join_real_lookup(name=agent["name"], headed=headed_browser, slow_mo_ms=180)

    if not result.get("found"):
        raise RetryableError(f"agent '{agent['name']}' not found in JoinReal directory")

    for sc in result.get("screenshots", []):
        ctx.artifacts.append(sc)

    expected = STATE_FULL_NAME.get(agent["state"], agent["state"])
    listed = result.get("state", "")
    if expected.lower() not in (listed or "").lower():
        raise RetryableError(
            f"JoinReal lists state '{listed}', CRM has '{expected}'"
        )

    return {"state_listed": listed, "state_match": True, "offline": result.get("offline", False)}


# ── 3. DRE verification (state-specific) ──────────────────────────────────

def verify_dre(ctx: TraceContext, headed_browser: bool = True) -> dict:
    agent = ctx.agent
    adapter = load_adapter(agent["state"])

    if adapter.get("maturity") == "vision_only":
        # Hawaii-style: go straight to vision/HITL path
        # (In a real implementation we'd still try the page and let CAPTCHA detection kick in.)
        pass

    # Attempt deterministic Playwright extraction first
    result = dre_lookup(
        license_no=agent["license_no"],
        base_url=adapter["search_url"],
        selectors=adapter["selectors"],
        headed=headed_browser,
        slow_mo_ms=180,
    )
    for sc in result.get("screenshots", []):
        ctx.artifacts.append(sc)

    if result.get("captcha"):
        raise HitlPause(reason="captcha_wall", scraped={
            "license_no": agent["license_no"], "state": agent["state"], "captcha": True,
        })

    if not result.get("found"):
        # AI fallback: re-derive the field from HTML via Claude
        if result.get("html"):
            field_desc = adapter["ai_fallback_descriptions"]["expiration_field"]
            value, cost, meta = llm_claude.extract_from_html(result["html"], field_desc)
            ctx.llm_cost_usd += cost
            if value and value != "NOT_FOUND":
                # Cache the successful AI-derived path
                SELECTOR_CACHE.set(f"dre:{agent['state']}:expiration", value, ttl=300)
                return {
                    "expiration": value, "extracted_via": "claude_html_fallback",
                    "name": result.get("name"), "llm_meta": meta,
                }
        raise RetryableError("no listing found for license; AI fallback also failed")

    return {
        "expiration": result["expiration"], "extracted_via": "playwright_selector",
        "name": result.get("name"),
        "offline": result.get("offline", False),
    }


# ── 4. Compare expirations (two-tier LLM classification) ───────────────────

def compare_expirations(ctx: TraceContext) -> dict:
    crm_exp = ctx.crm["expires_at"]
    dre_exp = ctx.dre.get("expiration")
    if not dre_exp:
        return {"verdict": "mismatch", "reason": "no_dre_value", "confidence": 0.0}

    # Light-tier classifier (Haiku) confirms equality. In real use we'd use
    # this for ambiguous string cases like "March 14, 2027" vs "2027-03-14".
    verdict, cost, meta = llm_claude.classify_match(crm_exp, dre_exp, field="license_expiration_date")
    ctx.llm_cost_usd += cost
    confidence = 0.99 if verdict == "match" else 0.05 if verdict == "mismatch" else 0.5
    ctx.confidence_scores.append(confidence)
    return {
        "verdict": verdict, "confidence": confidence,
        "crm_value": crm_exp, "dre_value": dre_exp, "llm_meta": meta,
        "reason": None if verdict == "match" else f"expiration mismatch: CRM {crm_exp} vs DRE {dre_exp}",
    }


# ── 5a. Match — write the happy-path ledger row ────────────────────────────

def write_match(ctx: TraceContext) -> dict:
    artifact = ctx.artifacts[-1] if ctx.artifacts else None
    vid = db.insert_verification(
        run_id=ctx.run_id,
        agent_id=ctx.agent["agent_id"],
        agent_name=ctx.agent["name"],
        licensing_state=ctx.agent["state"],
        license_number=ctx.agent["license_no"],
        crm_expires_at=ctx.crm["expires_at"],
        joinreal_state=ctx.joinreal.get("state_listed"),
        dre_expires_at=ctx.dre.get("expiration"),
        result="match",
        mismatch_reason=None,
        confidence=ctx.confidence_scores[-1] if ctx.confidence_scores else None,
        artifact_path=artifact,
        created_at=now_iso(),
    )
    return {"verification_id": vid, "artifact": artifact}


# ── 5b. Mismatch — write a pending ledger row + open a HITL case ───────────

def quarantine_mismatch(ctx: TraceContext, reason: str) -> dict:
    artifact = ctx.artifacts[-1] if ctx.artifacts else None
    vid = db.insert_verification(
        run_id=ctx.run_id,
        agent_id=ctx.agent["agent_id"],
        agent_name=ctx.agent["name"],
        licensing_state=ctx.agent["state"],
        license_number=ctx.agent["license_no"],
        crm_expires_at=ctx.crm["expires_at"],
        joinreal_state=ctx.joinreal.get("state_listed"),
        dre_expires_at=ctx.dre.get("expiration"),
        result="pending_review",
        mismatch_reason=reason,
        confidence=ctx.confidence_scores[-1] if ctx.confidence_scores else None,
        artifact_path=artifact,
        created_at=now_iso(),
    )
    hid = db.insert_hitl(
        run_id=ctx.run_id,
        agent_id=ctx.agent["agent_id"],
        agent_name=ctx.agent["name"],
        summary=f"Expiration mismatch · CRM {ctx.crm['expires_at']} · DRE {ctx.dre.get('expiration')}",
        crm=ctx.crm,
        scraped={"joinreal": ctx.joinreal, "dre": ctx.dre},
        created_at=now_iso(),
    )
    return {"verification_id": vid, "hitl_id": hid, "reason": reason}


# ── 5c. CAPTCHA / vision-only — straight to HITL ───────────────────────────

def quarantine_captcha(ctx: TraceContext, reason: str, scraped: dict) -> dict:
    artifact = ctx.artifacts[-1] if ctx.artifacts else None
    vid = db.insert_verification(
        run_id=ctx.run_id,
        agent_id=ctx.agent["agent_id"],
        agent_name=ctx.agent["name"],
        licensing_state=ctx.agent["state"],
        license_number=ctx.agent["license_no"],
        crm_expires_at=ctx.crm["expires_at"],
        joinreal_state=ctx.joinreal.get("state_listed") if ctx.joinreal else None,
        dre_expires_at=None,
        result="pending_review",
        mismatch_reason=reason,
        confidence=0.0,
        artifact_path=artifact,
        created_at=now_iso(),
    )
    hid = db.insert_hitl(
        run_id=ctx.run_id,
        agent_id=ctx.agent["agent_id"],
        agent_name=ctx.agent["name"],
        summary=f"CAPTCHA wall on {ctx.agent['state']} DRE · vision/manual review required",
        crm=ctx.crm,
        scraped={"joinreal": ctx.joinreal, "dre_attempt": scraped},
        created_at=now_iso(),
    )
    return {"verification_id": vid, "hitl_id": hid, "reason": reason}
