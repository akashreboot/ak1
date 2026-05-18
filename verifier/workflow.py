"""Saga workflow engine — the spine of the verification system.

This is the local stand-in for Temporal. It implements the same
behavioral contracts the deck claims:

  * Durable: every span persists to SQLite; state is recoverable.
  * Idempotent: workflow_id = sha1(agent_id|onboarding_event_id);
    a re-trigger no-ops if the run is already completed.
  * Retried per activity, not per workflow.
  * Replayable: completed activity results are cached on the Context
    so a resumed run skips them.
  * Generator-yielded: every span streams to whoever's listening (the
    Live Demo page consumes the generator; in production Temporal
    workers stream OTel spans to Datadog).

If you wanted Temporal, you'd swap the `activity()` decorator for
`@temporalio.activity.defn` and the `run_verification` body for a
`@workflow.defn` class. The flow shape is identical.
"""
from __future__ import annotations

import hashlib
import random
import time
from typing import Callable, Generator, Optional

from verifier import db
from verifier.trace import Span, TraceContext, now_iso


# ── Workflow-level identity ────────────────────────────────────────────────

def workflow_id_for(agent_id: str, event_id: str) -> str:
    """Stable hash so a duplicate webhook delivery is a no-op."""
    h = hashlib.sha1(f"{agent_id}|{event_id}".encode()).hexdigest()[:16]
    return f"verify-{agent_id}-{h}"


# ── Retry decorator ────────────────────────────────────────────────────────

class RetryableError(Exception):
    pass


class FatalError(Exception):
    pass


class HitlPause(Exception):
    """Raised when a workflow must pause for human review.

    In real Temporal we'd `await signal()`; here we record the HITL row
    and end the workflow run with status='quarantined'. The HITL page
    resolves the row, which writes the final verification.
    """
    def __init__(self, reason: str, scraped: dict):
        super().__init__(reason)
        self.reason = reason
        self.scraped = scraped


def activity(
    ctx: TraceContext,
    name: str,
    owner: str,
    fn: Callable,
    max_attempts: int = 3,
    initial_backoff_s: float = 0.5,
    *args, **kwargs,
) -> Generator[Span, None, object]:
    """Wrap an activity with start/retry/ok/error spans + exponential backoff.

    `yield from` callers can extract the return value:
        result = yield from activity(ctx, "fetch", "API", _fn)
    """
    cache_key = f"activity:{name}"
    if cache_key in ctx.results:
        # Replay path — Temporal does this transparently. Surface a span.
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
                detail=_summarize_result(result),
                duration_ms=duration_ms,
            )
            ctx.results[cache_key] = result
            return result
        except HitlPause:
            # Propagate immediately; do not retry.
            raise
        except FatalError as e:
            yield ctx.span("error", owner, f"✗ {name} failed (fatal)", detail=str(e))
            raise
        except Exception as e:  # noqa: BLE001
            last_err = e
            if attempt < max_attempts:
                backoff = initial_backoff_s * (2 ** (attempt - 1))
                backoff += random.uniform(0, 0.25)  # jitter
                yield ctx.span(
                    "retry", owner, f"⟳ {name} attempt {attempt} failed — backing off",
                    detail=f"{type(e).__name__}: {e}  · sleep {backoff:.2f}s",
                )
                time.sleep(backoff)
            else:
                yield ctx.span("error", owner, f"✗ {name} failed after {max_attempts} attempts", detail=str(e))
                raise

    # Unreachable, but for the type checker:
    raise last_err if last_err else RuntimeError(f"activity {name} exhausted retries")


def _summarize_result(result) -> Optional[str]:
    if result is None:
        return None
    if isinstance(result, dict):
        keys = ", ".join(f"{k}={v!r}" for k, v in list(result.items())[:4] if k != "html")
        return keys[:240]
    return str(result)[:240]


# ── The workflow ───────────────────────────────────────────────────────────

def run_verification(
    agent_id: str,
    event_id: Optional[str] = None,
    headed_browser: bool = True,
) -> Generator[Span, None, str]:
    """Top-level verification saga. Yields Span objects; returns final status string.

    The Streamlit Live Demo page iterates this generator, updating the UI on
    each span. Same generator would emit OTel spans in production.
    """
    from verifier.fixtures import get_agent
    from verifier import activities

    agent = get_agent(agent_id)
    event_id = event_id or f"evt-{int(time.time() * 1000)}"
    run_id = workflow_id_for(agent_id, event_id)

    ctx = TraceContext(run_id=run_id, agent=agent)
    db.insert_workflow_run(run_id=run_id, agent_id=agent_id, payload=agent, started_at=now_iso())

    yield ctx.span("start", "Temporal", "Workflow started",
                   detail=f"run_id={run_id}  agent_id={agent_id}  state={agent['state']}")

    try:
        # 1) Metadata fetch
        ctx.crm = yield from activity(ctx, "Fetch agent metadata", "Agent API",
                                      activities.fetch_metadata)

        # 2) JoinReal verification
        ctx.joinreal = yield from activity(
            ctx, "Verify on JoinReal", "Playwright",
            activities.verify_joinreal, headed_browser=headed_browser,
        )

        # 3) DRE verification (state-specific; CAPTCHA states quarantine via HitlPause)
        ctx.dre = yield from activity(
            ctx, f"Verify on {agent['state']} DRE", "Playwright",
            activities.verify_dre, headed_browser=headed_browser,
        )

        # 4) Compare CRM vs DRE expiration date
        comparison = yield from activity(ctx, "Compare expiration", "Claude (Haiku)",
                                         activities.compare_expirations)

        # 5) Write the ledger
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
                            activities.quarantine_captcha, reason=hp.reason, scraped=hp.scraped)
        yield ctx.span("end", "Temporal", "⏸ Workflow paused — awaiting human review",
                       detail=hp.reason)
        db.set_workflow_status(run_id, "quarantined", completed_at=now_iso())
        return "quarantined_hitl"

    except Exception as e:  # noqa: BLE001
        yield ctx.span("error", "Temporal", "✗ Workflow failed", detail=f"{type(e).__name__}: {e}")
        db.set_workflow_status(run_id, "failed", completed_at=now_iso(), error=str(e))
        return "failed"
