"""Saga workflow engine — V2 pipeline.

The spine of the verification system. Implements Temporal-equivalent semantics:
durable spans, per-activity retries with exponential backoff + jitter, replay
via cached results, signal-resumable HITL.

V2 pipeline (6 stages):
  1. Fetch agent metadata
  2. Fetch onereal.com profile (REAL network call)
  3. Cross-check CRM ↔ profile
  4. Resolve adapter & pick browser tier
  5. DRE verify (Playwright or Camoufox depending on tier)
  6. Compare expirations + decide
"""
from __future__ import annotations

import hashlib
import random
import time
from typing import Callable, Generator, Optional

from verifier import db
from verifier.trace import Span, TraceContext, now_iso


# ── Workflow identity ──────────────────────────────────────────────────────

def workflow_id_for(agent_id: str, event_id: str) -> str:
    h = hashlib.sha1(f"{agent_id}|{event_id}".encode()).hexdigest()[:16]
    return f"verify-{agent_id}-{h}"


# ── Exceptions ─────────────────────────────────────────────────────────────

class RetryableError(Exception):
    pass


class FatalError(Exception):
    pass


class HitlPause(Exception):
    def __init__(self, reason: str, scraped: dict):
        super().__init__(reason)
        self.reason = reason
        self.scraped = scraped


# ── Activity wrapper ───────────────────────────────────────────────────────

def activity(
    ctx: TraceContext,
    name: str,
    owner: str,
    fn: Callable,
    max_attempts: int = 3,
    initial_backoff_s: float = 0.5,
    *args, **kwargs,
) -> Generator[Span, None, object]:
    """Wrap an activity with start/retry/ok/error spans + exponential backoff."""
    cache_key = f"activity:{name}"
    if cache_key in ctx.results:
        yield ctx.span("replay", owner, f"⟳ replay (cached) {name}")
        return ctx.results[cache_key]

    last_err: Optional[Exception] = None
    for attempt in range(1, max_attempts + 1):
        yield ctx.span(
            "activity", owner,
            f"▶ {name}" + (f" (retry {attempt}/{max_attempts})" if attempt > 1 else ""),
        )
        started = time.time()
        try:
            result = fn(ctx, *args, **kwargs)
            duration_ms = int((time.time() - started) * 1000)
            yield ctx.span(
                "ok", owner, f"✓ {name}",
                detail=_summarize_result(result), duration_ms=duration_ms,
            )
            ctx.results[cache_key] = result
            return result
        except HitlPause:
            raise
        except FatalError as e:
            yield ctx.span("error", owner, f"✗ {name} (fatal)", detail=str(e))
            raise
        except Exception as e:  # noqa: BLE001
            last_err = e
            if attempt < max_attempts:
                backoff = initial_backoff_s * (2 ** (attempt - 1)) + random.uniform(0, 0.25)
                yield ctx.span(
                    "retry", owner, f"⟳ {name} attempt {attempt} failed — backing off",
                    detail=f"{type(e).__name__}: {e}  · sleep {backoff:.2f}s",
                )
                time.sleep(backoff)
            else:
                yield ctx.span("error", owner, f"✗ {name} failed after {max_attempts} attempts", detail=str(e))
                raise

    raise last_err if last_err else RuntimeError(f"activity {name} exhausted retries")


def _summarize_result(result) -> Optional[str]:
    if result is None:
        return None
    if isinstance(result, dict):
        keys = ", ".join(
            f"{k}={v!r}" for k, v in list(result.items())[:5]
            if k not in ("html", "html_snippet", "all_scored")
        )
        return keys[:280]
    return str(result)[:280]


# ── The workflow ───────────────────────────────────────────────────────────

def run_verification(
    agent_id: str,
    event_id: Optional[str] = None,
    headed_browser: bool = True,
    practice_mode: bool = False,
) -> Generator[Span, None, str]:
    """Top-level verification saga. Yields Span objects; returns final status string."""
    from verifier.agent_loader import by_id
    from verifier import activities

    agent = by_id(agent_id)
    event_id = event_id or f"evt-{int(time.time() * 1000)}"
    run_id = workflow_id_for(agent_id, event_id)

    ctx = TraceContext(run_id=run_id, agent=agent)
    ctx.onereal = {}
    ctx.dre = {}
    ctx.disambiguation = None
    ctx.runner_used = None
    # Propagate practice_mode into the activity context so DRE can short-circuit.
    ctx.results["__practice_mode__"] = practice_mode
    db.insert_workflow_run(run_id=run_id, agent_id=agent_id, payload=agent, started_at=now_iso())

    yield ctx.span(
        "start", "Temporal", "Workflow started",
        detail=f"run_id={run_id}  agent={agent['name']['full']}  state={agent['license']['state_code']}",
    )

    try:
        # 1) CRM metadata
        ctx.crm = yield from activity(ctx, "Fetch agent metadata", "CRM API",
                                      activities.fetch_metadata)

        # 2) onereal.com profile (REAL network call)
        ctx.onereal = yield from activity(
            ctx, "Fetch onereal.com profile", "Playwright (onereal)",
            activities.fetch_onereal_profile,
            headed=headed_browser, practice_mode=practice_mode,
        )

        # 3) Cross-check
        cross = yield from activity(ctx, "Cross-check CRM ↔ profile", "Verify",
                                    activities.cross_check_profile)

        # 4) Adapter resolution + tier pick
        adapter_info = yield from activity(
            ctx, "Resolve adapter & pick browser tier", "Adapter",
            activities.resolve_adapter,
        )

        # Narrate which state was chosen for the DRE lookup (profile-driven)
        state_msg = (
            f"📍 DRE chosen from {adapter_info['state_source']}: "
            f"{adapter_info['state_code']} · {adapter_info['dre_url']}"
        )
        if not adapter_info["state_match"] and adapter_info["profile_state"]:
            state_msg += f"  ⚠ CRM has {adapter_info['crm_state']}, profile has {adapter_info['profile_state']}"
        yield ctx.span("activity", "Adapter", state_msg)

        # Narrate tier choice
        yield ctx.span(
            "activity", "Anti-bot router",
            f"📡 Routing to {adapter_info['effective_tier_label']}",
            detail=f"runner={adapter_info['runner']}  adapter={adapter_info['state_code']}@{adapter_info['adapter_version']}  disambig={adapter_info['disambiguation_required']}",
        )

        # 5) DRE verify — the activity title includes the actual license # so
        #    the panel can see the value being fed into the DRE form.
        chosen_state = ctx.results.get("__chosen_state__") or agent["license"]["state_code"]
        license_no_display = cross.get("license_number") or agent["license"].get("number") or "?"
        ctx.dre = yield from activity(
            ctx, f"Drive {chosen_state} DRE with license #{license_no_display}", "DRE",
            activities.dre_verify, headed=headed_browser,
        )

        # Emit one span for each browser-driving step the runner performed.
        # This makes the live DRE flow visible in the trace exactly like the
        # profile fetch — open → fill → submit → wait → parse → click → extract.
        STEP_LABELS = {
            "open":              ("🌐", "Opened live DRE page"),
            "url_search":        ("🔗", "Search via URL params (no form fill needed)"),
            "form_scope":        ("🎯", "Scoped to license-search form"),
            "recaptcha_detected":("⚠",  "reCAPTCHA widget detected on page"),
            "fill_license":      ("⌨",  "Typed license number into form"),
            "submit":            ("🖱",  "Clicked Search"),
            "wait_for_results":  ("⏳",  "Waited for results"),
            "captcha_wall":      ("🛑", "Blocked by CAPTCHA — routed to HITL"),
            "parse_results":     ("📑", "Parsed candidate rows"),
            "parse_results_fallback_anchors": ("📑", "Parsed result anchors (fallback)"),
            "pick_row":          ("🎯", "Picked best-matching row"),
            "row_html_dump":     ("·",  "(diagnostic) row HTML dumped"),
            "click_detail":      ("👉", "Navigated to license detail page"),
            "extract_expiration":("📅", "Extracted expiration date"),
        }
        for st in (ctx.dre.get("steps") or []):
            icon, label = STEP_LABELS.get(st.get("step", ""), ("·", st.get("step", "step")))
            ok = st.get("ok", True)
            detail_parts = []
            for k, v in st.items():
                if k in ("step", "ok"):
                    continue
                detail_parts.append(f"{k}={v}")
            yield ctx.span(
                "ok" if ok else "warn", "DRE/browser",
                f"{icon} {label}",
                detail=" · ".join(detail_parts)[:240] or None,
            )

        # Narrate the multi-page flow so the panel sees the disambiguation story
        cand_list = ctx.dre.get("candidates") or []
        if cand_list:
            yield ctx.span(
                "ok", "DRE",
                f"📋 DRE returned {len(cand_list)} candidate row(s) for #{license_no_display}",
                detail=" · ".join(
                    f"[{i}] {c.get('name','?')} · {c.get('license_type','?')} · {c.get('status','?')}"
                    for i, c in enumerate(cand_list)
                ),
            )
            picked = ctx.dre.get("picked_row")
            picked_idx = ctx.dre.get("picked_index")
            if picked:
                yield ctx.span(
                    "ok", "Disambiguator",
                    f"🎯 Picked row [{picked_idx}]: {picked.get('name','?')}",
                    detail=f"license_type='{picked.get('license_type','?')}'  status='{picked.get('status','?')}'  city='{picked.get('city','?')}'",
                )
        if ctx.dre.get("expiration"):
            raw = ctx.dre.get("expiration_raw") or ctx.dre.get("expiration")
            yield ctx.span(
                "ok", "DRE",
                f"📅 Extracted Expiration Date: {raw}",
                detail=f"normalized = {ctx.dre['expiration']}",
            )

        # 6) Decide
        comparison = yield from activity(ctx, "Compare expiration (Claude)", "Claude (Haiku)",
                                         activities.compare_and_decide)

        if comparison["verdict"] == "match":
            yield from activity(ctx, "Write ledger (match)", "Postgres",
                                activities.write_match)
            yield ctx.span("end", "Temporal", "✅ Verification complete — MATCH",
                           detail=f"LLM spend: ${ctx.llm_cost_usd:.4f}")
            db.set_workflow_status(run_id, "completed", completed_at=now_iso())
            return "completed_match"
        else:
            yield from activity(ctx, "Quarantine to HITL (mismatch)", "Slack",
                                activities.quarantine_mismatch,
                                reason=comparison.get("reason", "expiration_mismatch"))
            yield ctx.span("end", "Temporal", "⏸ Workflow paused — awaiting human review",
                           detail="Operator decision will resume the workflow via signal.")
            db.set_workflow_status(run_id, "quarantined", completed_at=now_iso())
            return "quarantined_mismatch"

    except HitlPause as hp:
        yield from activity(ctx, f"Quarantine to HITL ({hp.reason})", "Slack",
                            activities.quarantine_captcha,
                            reason=hp.reason, scraped=hp.scraped)
        yield ctx.span("end", "Temporal", "⏸ Workflow paused — awaiting human review",
                       detail=hp.reason)
        db.set_workflow_status(run_id, "quarantined", completed_at=now_iso())
        return "quarantined_hitl"

    except Exception as e:  # noqa: BLE001
        yield ctx.span("error", "Temporal", "✗ Workflow failed", detail=f"{type(e).__name__}: {e}")
        db.set_workflow_status(run_id, "failed", completed_at=now_iso(), error=str(e))
        return "failed"
