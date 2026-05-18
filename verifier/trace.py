"""Span/event emission for the verification workflow.

Every step of the workflow emits a structured span:
  - persisted to the trace_events table (durable history, replayable)
  - yielded from the workflow generator (live streaming into the UI)

Same pattern Temporal uses internally — we just implement it in 60 lines.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Optional

from verifier import db


@dataclass
class Span:
    run_id: str
    seq: int
    ts: str
    kind: str      # start | activity | retry | ok | warn | error | end | hitl | replay
    owner: str     # Temporal | API | Playwright | Stagehand | Claude | Verify | Postgres | Adapter
    title: str
    detail: Optional[str] = None
    duration_ms: Optional[int] = None
    metadata: dict = field(default_factory=dict)


class TraceContext:
    """Per-workflow-run state container.

    Holds the CRM payload, scraped data, accumulated artifacts, and produces
    Span objects that are persisted to SQLite + yielded to whatever consumer
    (Streamlit UI, log shipper, OTel exporter) is iterating the workflow.
    """

    def __init__(self, run_id: str, agent: dict):
        self.run_id = run_id
        self.agent = agent
        self.seq = 0
        # Activity results, keyed by activity name. Used for "replay" so a
        # resumed workflow doesn't redo completed steps (Temporal semantics).
        self.results: dict[str, Any] = {}
        # Carriers for cross-step data
        self.crm: dict = {}
        self.joinreal: dict = {}
        self.dre: dict = {}
        self.artifacts: list[str] = []
        self.confidence_scores: list[float] = []
        self.llm_cost_usd: float = 0.0

    def span(
        self,
        kind: str,
        owner: str,
        title: str,
        detail: Optional[str] = None,
        duration_ms: Optional[int] = None,
        metadata: Optional[dict] = None,
    ) -> Span:
        self.seq += 1
        sp = Span(
            run_id=self.run_id,
            seq=self.seq,
            ts=datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            kind=kind,
            owner=owner,
            title=title,
            detail=detail,
            duration_ms=duration_ms,
            metadata=metadata or {},
        )
        # Persist
        db.insert_trace(
            run_id=sp.run_id,
            seq=sp.seq,
            ts=sp.ts,
            kind=sp.kind,
            owner=sp.owner,
            title=sp.title,
            detail=sp.detail,
            duration_ms=sp.duration_ms,
        )
        return sp


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")
