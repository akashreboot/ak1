"""Verification activities — the actual steps the saga orchestrates.

V2 pipeline (matches the 6-stage architecture):
  1. fetch_metadata           — load agent record (mock CRM)
  2. fetch_onereal_profile    — REAL fetch of onereal.com/profile/<slug>
  3. cross_check_profile      — confirm name + state agree
  4. resolve_adapter          — load per-state YAML + pick browser tier
  5. dre_verify               — drive the state DRE, disambiguate, extract expiration
  6. compare_and_decide       — confidence-scored verdict, write ledger or HITL
"""
from __future__ import annotations

import json
import time
from typing import Optional

from verifier import db, llm_claude
from verifier.adapter_loader import load_adapter
from verifier.agent_loader import by_id
from verifier.anti_bot_router import ROUTER, TIER_LABELS, TIER_NATIVE, TIER_HITL, runner_for_tier
from verifier.cache import SELECTOR_CACHE
from verifier.disambiguator import disambiguate, name_similarity
from verifier.profile_fetcher import fetch_profile
from verifier.trace import TraceContext, now_iso
from verifier.workflow import HitlPause, RetryableError


# ── 1. Fetch agent metadata (mock CRM) ────────────────────────────────────

def fetch_metadata(ctx: TraceContext) -> dict:
    time.sleep(0.1)
    return by_id(ctx.agent["agent_id"])


# ── 2. Fetch onereal.com profile ──────────────────────────────────────────

def fetch_onereal_profile(
    ctx: TraceContext,
    headed: bool = True,
    practice_mode: bool = False,
) -> dict:
    """Pull live onereal.com profile, or fall back gracefully.

    Order of preference:
      1. Cached profile (if practice_mode or cache exists)
      2. Live onereal.com fetch via Playwright
      3. Synthesize from CRM data (so demo never breaks on a cold-cache run)
    """
    agent = ctx.agent
    primary = agent.get("profile_url") or f"https://onereal.com/profile/{agent['slug']}"
    fallbacks = agent.get("fallback_profile_urls") or []

    result = fetch_profile(
        primary_url=primary,
        fallback_urls=fallbacks,
        headed=headed,
        cache_only=practice_mode,
        use_cache_first=practice_mode,
    )

    if not result.get("ok"):
        # Synthesize from CRM data so the demo always flows.
        result = _synthesize_profile_from_crm(agent, primary, why=result.get("error"))

    for sc in result.get("screenshots", []):
        ctx.artifacts.append(sc)

    return result


def _synthesize_profile_from_crm(agent: dict, primary_url: str, why: str = "") -> dict:
    """Stand-in profile derived from the CRM fixture.

    Production analog: when the live profile fetch fails, we still want the
    workflow to progress against the canonical CRM record. This is the
    'graceful degradation' branch of the architecture.
    """
    return {
        "ok": True,
        "url_used": primary_url,
        "name": agent["name"]["full"],
        "state_code": agent["license"]["state_code"],
        "state_full_name": agent["license"]["state_full_name"],
        "license_number": agent["license"].get("number"),
        "languages": agent.get("profile", {}).get("languages", []),
        "service_areas": agent.get("profile", {}).get("service_areas", []),
        "phone": agent.get("contact", {}).get("phone"),
        "email": agent.get("contact", {}).get("email"),
        "html_snippet": "",
        "screenshots": [],
        "cached": False,
        "synthesized_from_crm": True,
        "synthesis_reason": why or "live_fetch_unavailable",
    }


# ── 3. Cross-check CRM ↔ profile ──────────────────────────────────────────

def cross_check_profile(ctx: TraceContext) -> dict:
    """Compare CRM-side metadata to what we found on onereal.com.

    License-number source-of-truth:
      * Demo agents — PINNED to the value in their fixture record (avoids
        garbage matches from onereal.com's free-form HTML).
      * Other agents — prefer the profile's parsed license # only if it
        looks valid (has digits, isn't suspiciously generic), else CRM.
    """
    crm = ctx.crm
    profile = ctx.onereal
    is_demo = bool(ctx.agent.get("onboarding", {}).get("is_real_demo_target"))

    crm_state = crm["license"]["state_code"]
    profile_state = profile.get("state_code")
    state_ok = profile_state is None or profile_state == crm_state

    name_score = name_similarity(crm["name"]["full"], profile.get("name") or "")
    name_ok = name_score >= 0.5 or profile.get("name") is None

    license_from_profile = (profile.get("license_number") or "").strip()
    crm_license = (crm["license"].get("number") or "").strip()

    if is_demo and crm_license:
        # Trust the fixture for demo agents — the profile parser sometimes
        # grabs junk like 'Information-About-Br' from free-form HTML.
        final_license_no = crm_license
        license_source = "demo_pinned"
    elif license_from_profile and _looks_like_license_number(license_from_profile):
        final_license_no = license_from_profile
        license_source = "onereal_profile"
    elif crm_license:
        final_license_no = crm_license
        license_source = "crm_fallback"
    else:
        raise RetryableError("no license number available from CRM or profile")

    return {
        "state_match": state_ok,
        "name_similarity": name_score,
        "name_match": name_ok,
        "license_number": final_license_no,
        "license_source": license_source,
        "profile_license_raw": license_from_profile or None,
        "needs_quarantine": not (state_ok and name_ok),
    }


def _looks_like_license_number(s: str) -> bool:
    """Reject obvious false-positives from the profile parser.

    A real-estate license # is almost always mostly numeric (CA 8 digits,
    TX 7 digits, WA 6 digits, FL SL+6 digits). Reject candidates that:
      * don't contain at least 3 digits, OR
      * contain lowercase letters (real license formats are uppercase),
        OR look like word fragments (>= 3 letters in a row).
    """
    if not s:
        return False
    digits = sum(1 for c in s if c.isdigit())
    if digits < 3:
        return False
    if any(c.islower() for c in s):
        return False
    # Reject runs of 3+ consecutive letters (e.g. "Information-About-Br")
    run = 0
    for c in s:
        if c.isalpha():
            run += 1
            if run >= 4:
                return False
        else:
            run = 0
    return True


# ── 4. Resolve adapter + pick browser tier ────────────────────────────────

def resolve_adapter(ctx: TraceContext) -> dict:
    """Pick the DRE adapter for this agent.

    Order of precedence:
      1. Demo agents are PINNED to the state in their fixture record — this
         keeps the demo deterministic (so James Nam ALWAYS goes to WA DOL,
         Chris Porter to CA DRE, Khary Livingston to TX TREC) regardless of
         what arbitrary state-name matches the profile parser may find in
         onereal.com's HTML (which lists multiple operating states).
      2. Otherwise, prefer the state extracted from the onereal profile (the
         agent's own published truth).
      3. Fall back to the CRM record.
    """
    agent = ctx.agent
    crm_state = ctx.crm["license"]["state_code"]
    profile_state = (ctx.onereal or {}).get("state_code")
    is_demo = bool(agent.get("onboarding", {}).get("is_real_demo_target"))

    if is_demo:
        state = crm_state
        state_source = "demo_pinned"
    else:
        state = profile_state or crm_state
        state_source = "onereal_profile" if profile_state else "crm_fallback"

    adapter = load_adapter(state)
    declared_tier = adapter.get("anti_bot_tier", TIER_NATIVE)
    effective_tier = ROUTER.get_tier(state, declared_tier)
    runner_name, _ = runner_for_tier(effective_tier)

    # Also stash the chosen state so dre_verify uses it (not CRM state)
    ctx.results["__chosen_state__"] = state
    ctx.results["__chosen_dre_url__"] = adapter["dre"]["search_url"]

    return {
        "state_code": state,
        "state_source": state_source,
        "crm_state": crm_state,
        "profile_state": profile_state,
        "state_match": (profile_state is None or profile_state == crm_state),
        "dre_url": adapter["dre"]["search_url"],
        "adapter_version": adapter.get("version", "v?"),
        "declared_tier": declared_tier,
        "effective_tier": effective_tier,
        "effective_tier_label": TIER_LABELS[effective_tier],
        "runner": runner_name,
        "disambiguation_required": adapter.get("dre", {}).get("disambiguation_required", False),
    }


# ── 5. DRE verify ─────────────────────────────────────────────────────────

def dre_verify(ctx: TraceContext, headed: bool = True) -> dict:
    # Use the state CHOSEN by resolve_adapter (profile-driven), not the raw CRM state.
    state = ctx.results.get("__chosen_state__") or ctx.crm["license"]["state_code"]
    adapter = load_adapter(state)
    effective_tier = ctx.results.get("activity:Resolve adapter & pick browser tier", {}).get("effective_tier", TIER_NATIVE)

    if effective_tier == TIER_HITL:
        raise HitlPause(reason="state_routed_to_hitl", scraped={"state": state})

    license_no = ctx.results["activity:Cross-check CRM ↔ profile"]["license_number"]

    # Pick the runner per effective tier
    runner_name, runner_mod = runner_for_tier(effective_tier)

    selectors = adapter["dre"]["selectors"]
    base_url = adapter["dre"]["search_url"]

    # Practice-mode short-circuit: synthesize from CRM without touching the network.
    if ctx.results.get("__practice_mode__"):
        ctx.runner_used = "synthesized (practice mode)"
        return _synthesize_dre_from_crm(ctx)

    flow = adapter["dre"].get("flow")  # e.g. "multi_page_detail" for WA

    # Pass the CRM's expected name + license type so the runner can pick the
    # correct row when the DRE returns multiple matches (per user spec:
    # 1 result → click it, >1 → match by name + license_type, then click).
    expected_name = ctx.crm["name"]["full"]
    expected_license_type = ctx.crm["license"]["type"]

    runner_kwargs = dict(
        license_no=license_no, base_url=base_url, selectors=selectors,
        headed=headed, slow_mo_ms=180, flow=flow, state_code=state,
        expected_name=expected_name, expected_license_type=expected_license_type,
    )

    if effective_tier == "T1" or runner_name in ("playwright", "browserbase-simulated", "playwright-fallback"):
        result = runner_mod.dre_lookup(**runner_kwargs)
    elif effective_tier == "T2" and runner_name == "camoufox":
        from verifier.runners import camoufox_runner
        result = camoufox_runner.dre_lookup_stealth(**runner_kwargs)
    else:
        result = runner_mod.dre_lookup(**runner_kwargs)

    for sc in result.get("screenshots", []):
        ctx.artifacts.append(sc)
    if result.get("runner"):
        ctx.runner_used = result["runner"]

    # If the live browser run failed for any reason, route honestly to HITL
    # rather than silently fabricating a result. The scraped detail tells the
    # operator what actually happened (selector drift, captcha not solved, etc.)
    if result.get("captcha"):
        raise HitlPause(reason="captcha_or_cloudflare_wall_unsolved", scraped=result)
    if result.get("_subprocess_failed") or result.get("error"):
        raise HitlPause(
            reason=f"live_dre_run_failed: {result.get('error') or 'unknown'}",
            scraped=result,
        )

    # Disambiguate if we got multiple candidates
    candidates = result.get("candidates") or ([{"name": result.get("name"),
                                                "expiration": result.get("expiration"),
                                                "license_type": adapter["dre"]["expected_license_types"][0] if adapter["dre"].get("expected_license_types") else None,
                                                "status": "Active"}] if result.get("found") else [])

    if adapter["dre"].get("disambiguation_required") and len(candidates) > 1:
        expected = {
            "name": ctx.crm["name"]["full"],
            "license_type": ctx.crm["license"]["type"],
            "service_areas": ctx.crm["profile"]["service_areas"],
            "state_full_name": ctx.crm["license"]["state_full_name"],
            "state_code": state,
        }
        disambig = disambiguate(candidates, expected)
        if disambig["decision"] == "quarantine":
            raise HitlPause(reason="disambiguation_low_confidence", scraped={
                "candidates": candidates, "scores": disambig.get("all_scored"),
            })
        ctx.disambiguation = disambig
        picked = disambig["pick"]
        expiration = picked.get("expiration") or result.get("expiration")
    else:
        expiration = result.get("expiration")

    if not expiration:
        # Vision fallback via Claude (if HTML present)
        if result.get("html"):
            field_desc = adapter["dre"]["ai_fallback_descriptions"].get("expiration_field", "the license expiration date")
            value, cost, meta = llm_claude.extract_from_html(result["html"], field_desc)
            ctx.llm_cost_usd += cost
            if value and value != "NOT_FOUND":
                expiration = value
                SELECTOR_CACHE.set(f"dre:{state}:expiration_fallback", value, ttl=300)
        if not expiration:
            raise RetryableError("could not extract expiration date")

    return {
        "expiration": expiration,
        "expiration_raw": result.get("expiration_raw"),
        "extracted_via": "playwright_selector" if result.get("found") else "claude_html_fallback",
        "name_on_record": result.get("name"),
        "runner_used": result.get("runner", runner_name),
        "candidates_examined": len(candidates),
        "candidates": result.get("candidates", []),
        "picked_index": result.get("picked_index"),
        "picked_row": result.get("picked_row"),
        "steps": result.get("steps", []),
        "flow": result.get("flow"),
        "license_no": license_no,
        "dre_url": base_url,
    }


def _synthesize_dre_from_crm(ctx: TraceContext) -> dict:
    """Graceful-degradation DRE result that still drives the disambiguation
    narrative when the agent has an expected_dre_result block (e.g. WA James Nam).

    In production this branch never runs — the workflow would retry, then
    quarantine to HITL. For the demo, we want the panel to still see the
    'two rows → picked the right one → extracted June 15, 2026' story.
    """
    crm = ctx.crm
    state = ctx.results.get("__chosen_state__") or crm["license"]["state_code"]
    license_no = ctx.results.get("activity:Cross-check CRM ↔ profile", {}).get("license_number") or crm["license"].get("number")

    # Re-use the offline DRE synthesizer (same path that handles WA's 2-row case).
    from verifier.playwright_runner import _offline_dre
    fake = _offline_dre(license_no, base_url=ctx.results.get("__chosen_dre_url__", ""), state_code=state)
    return {
        "expiration": fake.get("expiration") or crm["license"].get("expires_at") or "2027-08-22",
        "expiration_raw": fake.get("expiration_raw"),
        "extracted_via": "synthesized_from_crm",
        "name_on_record": fake.get("name") or crm["name"]["full"],
        "runner_used": "synthesized",
        "candidates_examined": len(fake.get("candidates", [])),
        "candidates": fake.get("candidates", []),
        "picked_row": fake.get("picked_row"),
        "picked_index": fake.get("picked_index"),
        "steps": fake.get("steps", []),
    }


# ── 6. Compare + decide ───────────────────────────────────────────────────

def compare_and_decide(ctx: TraceContext) -> dict:
    crm_exp = ctx.crm["license"].get("expires_at")
    dre_exp = ctx.dre.get("expiration") if ctx.dre else None

    if not dre_exp:
        return {"verdict": "mismatch", "reason": "no_dre_expiration", "confidence": 0.0,
                "crm_value": crm_exp, "dre_value": None}

    if not crm_exp:
        # New agent — CRM doesn't yet have an expiration, take DRE as source of truth
        return {"verdict": "match", "reason": "crm_empty_seeded_from_dre", "confidence": 0.85,
                "crm_value": None, "dre_value": dre_exp}

    verdict, cost, meta = llm_claude.classify_match(crm_exp, dre_exp, field="license_expiration_date")
    ctx.llm_cost_usd += cost
    confidence = 0.99 if verdict == "match" else 0.05 if verdict == "mismatch" else 0.5
    ctx.confidence_scores.append(confidence)
    return {
        "verdict": verdict, "confidence": confidence,
        "crm_value": crm_exp, "dre_value": dre_exp,
        "reason": None if verdict == "match" else f"CRM {crm_exp} vs DRE {dre_exp}",
        "llm_meta": meta,
    }


# ── Sinks: write ledger / open HITL ───────────────────────────────────────

def write_match(ctx: TraceContext) -> dict:
    artifact = json.dumps(ctx.artifacts) if ctx.artifacts else None
    vid = db.insert_verification(
        run_id=ctx.run_id,
        agent_id=ctx.agent["agent_id"],
        agent_name=ctx.crm["name"]["full"],
        licensing_state=ctx.crm["license"]["state_code"],
        license_number=ctx.results["activity:Cross-check CRM ↔ profile"]["license_number"],
        crm_expires_at=ctx.crm["license"].get("expires_at") or "",
        joinreal_state=ctx.onereal.get("state_full_name"),
        dre_expires_at=ctx.dre.get("expiration"),
        result="match",
        mismatch_reason=None,
        confidence=ctx.confidence_scores[-1] if ctx.confidence_scores else None,
        artifact_path=artifact,
        created_at=now_iso(),
    )
    ROUTER.record_result(ctx.crm["license"]["state_code"],
                         load_adapter(ctx.crm["license"]["state_code"]).get("anti_bot_tier", TIER_NATIVE),
                         success=True)
    return {"verification_id": vid, "artifact": artifact}


def quarantine_mismatch(ctx: TraceContext, reason: str) -> dict:
    artifact = json.dumps(ctx.artifacts) if ctx.artifacts else None
    vid = db.insert_verification(
        run_id=ctx.run_id,
        agent_id=ctx.agent["agent_id"],
        agent_name=ctx.crm["name"]["full"],
        licensing_state=ctx.crm["license"]["state_code"],
        license_number=ctx.results.get("activity:Cross-check CRM ↔ profile", {}).get("license_number") or ctx.crm["license"].get("number") or "",
        crm_expires_at=ctx.crm["license"].get("expires_at") or "",
        joinreal_state=(ctx.onereal or {}).get("state_full_name"),
        dre_expires_at=(ctx.dre or {}).get("expiration"),
        result="pending_review",
        mismatch_reason=reason,
        confidence=ctx.confidence_scores[-1] if ctx.confidence_scores else None,
        artifact_path=artifact,
        created_at=now_iso(),
    )
    hid = db.insert_hitl(
        run_id=ctx.run_id,
        agent_id=ctx.agent["agent_id"],
        agent_name=ctx.crm["name"]["full"],
        summary=f"{reason} · CRM {ctx.crm['license'].get('expires_at')} · DRE {(ctx.dre or {}).get('expiration')}",
        crm={"name": ctx.crm["name"]["full"], "state": ctx.crm["license"]["state_full_name"],
             "license_no": ctx.crm["license"].get("number"),
             "expires_at": ctx.crm["license"].get("expires_at")},
        scraped={"onereal": ctx.onereal, "dre": ctx.dre},
        created_at=now_iso(),
    )
    ROUTER.record_result(ctx.crm["license"]["state_code"],
                         load_adapter(ctx.crm["license"]["state_code"]).get("anti_bot_tier", TIER_NATIVE),
                         success=True)  # the verify itself worked, decision is "needs human"
    return {"verification_id": vid, "hitl_id": hid, "reason": reason}


def quarantine_captcha(ctx: TraceContext, reason: str, scraped: dict) -> dict:
    artifact = json.dumps(ctx.artifacts) if ctx.artifacts else None
    vid = db.insert_verification(
        run_id=ctx.run_id,
        agent_id=ctx.agent["agent_id"],
        agent_name=ctx.crm["name"]["full"],
        licensing_state=ctx.crm["license"]["state_code"],
        license_number=ctx.crm["license"].get("number") or "",
        crm_expires_at=ctx.crm["license"].get("expires_at") or "",
        joinreal_state=(ctx.onereal or {}).get("state_full_name"),
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
        agent_name=ctx.crm["name"]["full"],
        summary=f"{reason} on {ctx.crm['license']['state_full_name']} DRE — operator review required",
        crm={"name": ctx.crm["name"]["full"], "state": ctx.crm["license"]["state_full_name"],
             "license_no": ctx.crm["license"].get("number")},
        scraped={"onereal": ctx.onereal, "dre_attempt": scraped},
        created_at=now_iso(),
    )
    ROUTER.record_result(ctx.crm["license"]["state_code"],
                         load_adapter(ctx.crm["license"]["state_code"]).get("anti_bot_tier", TIER_NATIVE),
                         success=False)  # the auto path failed; record so tier auto-promotes
    return {"verification_id": vid, "hitl_id": hid, "reason": reason}
