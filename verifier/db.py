"""SQLite-backed durable state for the verification system.

Mirrors the data model of the proposed Postgres ledger so the demo behaves
the same way the production system would: every workflow run is recorded,
every span is replayable, every HITL case is auditable.
"""
from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "ledger.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

_lock = threading.Lock()


SCHEMA = """
CREATE TABLE IF NOT EXISTS workflow_runs (
    run_id          TEXT PRIMARY KEY,
    agent_id        TEXT NOT NULL,
    workflow_status TEXT NOT NULL,        -- running | completed | failed | quarantined
    started_at      TEXT NOT NULL,
    completed_at    TEXT,
    payload_json    TEXT NOT NULL,
    error_message   TEXT
);

CREATE TABLE IF NOT EXISTS trace_events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id      TEXT NOT NULL,
    seq         INTEGER NOT NULL,
    ts          TEXT NOT NULL,
    kind        TEXT NOT NULL,           -- start | activity | retry | ok | warn | error | end
    owner       TEXT NOT NULL,           -- Temporal | API | Playwright | Stagehand | Verify | Postgres
    title       TEXT NOT NULL,
    detail      TEXT,
    duration_ms INTEGER,
    FOREIGN KEY (run_id) REFERENCES workflow_runs(run_id)
);
CREATE INDEX IF NOT EXISTS idx_trace_run_seq ON trace_events(run_id, seq);

CREATE TABLE IF NOT EXISTS verifications (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id              TEXT NOT NULL,
    agent_id            TEXT NOT NULL,
    agent_name          TEXT NOT NULL,
    licensing_state     TEXT NOT NULL,
    license_number      TEXT NOT NULL,
    crm_expires_at      TEXT NOT NULL,
    joinreal_state      TEXT,
    dre_expires_at      TEXT,
    result              TEXT NOT NULL,    -- match | mismatch | error | pending_review
    mismatch_reason     TEXT,
    confidence          REAL,
    artifact_path       TEXT,
    created_at          TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_verify_agent ON verifications(agent_id);
CREATE INDEX IF NOT EXISTS idx_verify_result ON verifications(result);

CREATE TABLE IF NOT EXISTS hitl_queue (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id          TEXT NOT NULL UNIQUE,
    agent_id        TEXT NOT NULL,
    agent_name      TEXT NOT NULL,
    summary         TEXT NOT NULL,
    crm_snapshot    TEXT NOT NULL,    -- JSON
    scraped_data    TEXT NOT NULL,    -- JSON
    status          TEXT NOT NULL,    -- pending | approved_crm | approved_scraped | rejected | re_run
    resolver        TEXT,
    resolution_note TEXT,
    created_at      TEXT NOT NULL,
    resolved_at     TEXT
);
CREATE INDEX IF NOT EXISTS idx_hitl_status ON hitl_queue(status);
"""


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    """Thread-safe SQLite connection with foreign keys + row factory."""
    with _lock:
        con = sqlite3.connect(DB_PATH, isolation_level=None, timeout=10.0)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys = ON;")
        con.execute("PRAGMA journal_mode = WAL;")
        try:
            yield con
        finally:
            con.close()


def init_db() -> None:
    with connect() as con:
        con.executescript(SCHEMA)


def insert_workflow_run(run_id: str, agent_id: str, payload: dict, started_at: str) -> None:
    with connect() as con:
        con.execute(
            """INSERT INTO workflow_runs(run_id, agent_id, workflow_status, started_at, payload_json)
               VALUES (?, ?, 'running', ?, ?)""",
            (run_id, agent_id, started_at, json.dumps(payload)),
        )


def set_workflow_status(run_id: str, status: str, completed_at: str | None = None, error: str | None = None) -> None:
    with connect() as con:
        con.execute(
            """UPDATE workflow_runs SET workflow_status=?, completed_at=COALESCE(?, completed_at), error_message=?
               WHERE run_id=?""",
            (status, completed_at, error, run_id),
        )


def insert_trace(
    run_id: str,
    seq: int,
    ts: str,
    kind: str,
    owner: str,
    title: str,
    detail: str | None = None,
    duration_ms: int | None = None,
) -> None:
    with connect() as con:
        con.execute(
            """INSERT INTO trace_events(run_id, seq, ts, kind, owner, title, detail, duration_ms)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (run_id, seq, ts, kind, owner, title, detail, duration_ms),
        )


def fetch_traces(run_id: str) -> list[sqlite3.Row]:
    with connect() as con:
        return list(con.execute(
            "SELECT * FROM trace_events WHERE run_id=? ORDER BY seq ASC", (run_id,)
        ))


def insert_verification(**fields) -> int:
    cols = ", ".join(fields.keys())
    placeholders = ", ".join("?" * len(fields))
    with connect() as con:
        cur = con.execute(
            f"INSERT INTO verifications({cols}) VALUES ({placeholders})",
            tuple(fields.values()),
        )
        return cur.lastrowid


def fetch_verifications(limit: int = 100, result_filter: str | None = None) -> list[sqlite3.Row]:
    with connect() as con:
        if result_filter:
            return list(con.execute(
                "SELECT * FROM verifications WHERE result=? ORDER BY id DESC LIMIT ?",
                (result_filter, limit),
            ))
        return list(con.execute(
            "SELECT * FROM verifications ORDER BY id DESC LIMIT ?", (limit,)
        ))


def insert_hitl(run_id: str, agent_id: str, agent_name: str, summary: str,
                crm: dict, scraped: dict, created_at: str) -> int:
    with connect() as con:
        cur = con.execute(
            """INSERT INTO hitl_queue(run_id, agent_id, agent_name, summary, crm_snapshot, scraped_data, status, created_at)
               VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)""",
            (run_id, agent_id, agent_name, summary, json.dumps(crm), json.dumps(scraped), created_at),
        )
        return cur.lastrowid


def fetch_hitl(status: str | None = "pending") -> list[sqlite3.Row]:
    with connect() as con:
        if status is None:
            return list(con.execute("SELECT * FROM hitl_queue ORDER BY id DESC"))
        return list(con.execute(
            "SELECT * FROM hitl_queue WHERE status=? ORDER BY id DESC", (status,)
        ))


def resolve_hitl(hitl_id: int, status: str, resolver: str, note: str, resolved_at: str) -> None:
    with connect() as con:
        con.execute(
            """UPDATE hitl_queue SET status=?, resolver=?, resolution_note=?, resolved_at=?
               WHERE id=?""",
            (status, resolver, note, resolved_at, hitl_id),
        )


def metrics_summary() -> dict:
    """Aggregate metrics for the Ledger page."""
    with connect() as con:
        total = con.execute("SELECT COUNT(*) AS c FROM verifications").fetchone()["c"]
        match = con.execute("SELECT COUNT(*) AS c FROM verifications WHERE result='match'").fetchone()["c"]
        mismatch = con.execute("SELECT COUNT(*) AS c FROM verifications WHERE result='mismatch'").fetchone()["c"]
        pending = con.execute("SELECT COUNT(*) AS c FROM verifications WHERE result='pending_review'").fetchone()["c"]
        hitl_open = con.execute("SELECT COUNT(*) AS c FROM hitl_queue WHERE status='pending'").fetchone()["c"]
        runs_running = con.execute("SELECT COUNT(*) AS c FROM workflow_runs WHERE workflow_status='running'").fetchone()["c"]
        runs_done = con.execute("SELECT COUNT(*) AS c FROM workflow_runs WHERE workflow_status='completed'").fetchone()["c"]
    return {
        "total_verifications": total,
        "match": match,
        "mismatch": mismatch,
        "pending_review": pending,
        "hitl_open": hitl_open,
        "runs_running": runs_running,
        "runs_completed": runs_done,
    }


def reset_demo() -> None:
    """Wipe everything for a clean demo run."""
    with connect() as con:
        con.executescript("""
            DELETE FROM trace_events;
            DELETE FROM verifications;
            DELETE FROM hitl_queue;
            DELETE FROM workflow_runs;
        """)
