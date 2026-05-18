"""Verification Ledger — live view of the SQLite ledger.

Every verification (match, mismatch, pending review, error) writes a row here.
This is the page Compliance/Ops would use during an audit.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from components.styles import (
    page_setup, hero, divider, footer,
    REAL_CYAN, REAL_MINT, REAL_AMBER, REAL_RED, REAL_MUTED,
)
from verifier import db

page_setup("Verification Ledger", icon="📒")

hero(
    eyebrow="11 · Verification Ledger",
    title_html='The <span class="gradient-text">audit trail</span>. One row per verification attempt.',
    subtitle=(
        "Same schema we'd run on Postgres in production. Every row links to a workflow run, "
        "the screenshots Playwright captured, and the LLM-derived confidence."
    ),
)

st.write("")

m = db.metrics_summary()
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Total verifications", m["total_verifications"])
c2.metric("Matched", m["match"], delta_color="off")
c3.metric("Pending review", m["pending_review"], delta_color="off")
c4.metric("Mismatches", m["mismatch"], delta_color="off")
c5.metric("Open HITL cases", m["hitl_open"], delta_color="off")

divider()

result_filter = st.selectbox(
    "Filter by result",
    options=["(all)", "match", "pending_review", "mismatch", "error"],
    index=0,
)
rows = db.fetch_verifications(
    limit=200,
    result_filter=None if result_filter == "(all)" else result_filter,
)

if not rows:
    st.info("No verifications yet — head to the Live Demo page and click Run.")
    footer()
    st.stop()

df = pd.DataFrame([dict(r) for r in rows])
display_cols = [
    "id", "created_at", "agent_id", "agent_name", "licensing_state",
    "license_number", "result", "crm_expires_at", "dre_expires_at",
    "joinreal_state", "mismatch_reason", "confidence",
]
df_view = df[[c for c in display_cols if c in df.columns]]


def _color_result(v):
    return {
        "match":          f"background-color: rgba(52,211,153,0.18); color: #6EE7B7;",
        "pending_review": f"background-color: rgba(245,158,11,0.18); color: #FCD34D;",
        "mismatch":       f"background-color: rgba(239,68,68,0.18); color: #FCA5A5;",
        "error":          f"background-color: rgba(239,68,68,0.18); color: #FCA5A5;",
    }.get(v, "")


styled = df_view.style.map(_color_result, subset=["result"])
st.dataframe(styled, width="stretch", height=420, hide_index=True)

divider()

# Drill-down on a single row
st.markdown("### Drill-down")
selected_id = st.selectbox("Inspect verification", options=df["id"].tolist())
row = df[df["id"] == selected_id].iloc[0].to_dict()

cols = st.columns([1.1, 1])
with cols[0]:
    st.markdown(f"##### Row #{row['id']} · {row['agent_name']}  ({row['agent_id']})")
    st.json({k: v for k, v in row.items() if v not in (None, "")})

def _parse_artifacts(val):
    """Backward-compat: artifact_path may be a single path string OR a JSON array."""
    if not val:
        return []
    if isinstance(val, list):
        return val
    s = str(val).strip()
    if s.startswith("["):
        try:
            return json.loads(s)
        except json.JSONDecodeError:
            return [s]
    return [s]


with cols[1]:
    artifacts = _parse_artifacts(row.get("artifact_path"))
    if artifacts:
        st.markdown(f"##### Captured artifacts · {len(artifacts)} screenshot(s)")
        project_root = Path(__file__).resolve().parent.parent
        for p in artifacts:
            apath = project_root / p
            if apath.exists():
                label = Path(p).stem.replace("-", " ").title()
                st.image(str(apath), caption=label, width="stretch")
            else:
                st.caption(f"⚠ missing: `{p}`")
    else:
        st.info("No artifacts captured for this row (likely an offline-mode run).")

    # Show the matching trace
    traces = db.fetch_traces(row["run_id"])
    if traces:
        with st.expander(f"Workflow trace ({len(traces)} spans)", expanded=False):
            for t in traces:
                t = dict(t)
                st.markdown(
                    f"<div style='display:flex; gap:8px; padding:4px 0; "
                    f"border-bottom:1px solid rgba(255,255,255,0.05);'>"
                    f"<span style='color:{REAL_MUTED}; font-family:JetBrains Mono; font-size:0.78rem; width:50px;'>#{t['seq']:02d}</span>"
                    f"<span class='pill pill-cyan' style='font-size:0.7rem;'>{t['owner']}</span>"
                    f"<span style='flex:1;'>{t['title']}</span>"
                    f"<span style='color:{REAL_MUTED}; font-family:JetBrains Mono; font-size:0.78rem;'>{t['duration_ms'] or ''}{'ms' if t['duration_ms'] else ''}</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

divider()

with st.expander("🗃  Raw SQLite file — open in DB Browser, DBeaver, or VS Code"):
    st.code(str((Path(__file__).resolve().parent.parent / "data" / "ledger.db")), language="bash")

footer()
