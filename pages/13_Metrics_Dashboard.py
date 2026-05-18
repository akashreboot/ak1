"""Metrics Dashboard — Datadog stand-in.

Real numbers from the real ledger. In production these same queries hit
Postgres and the panel renders in Datadog; locally it's just SQLite.
"""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from components.styles import (
    page_setup, hero, divider, footer,
    REAL_CYAN, REAL_MINT, REAL_AMBER, REAL_RED, REAL_VIOLET, REAL_INDIGO, REAL_BLUE, REAL_MUTED,
)
from verifier import db
from verifier.cache import SELECTOR_CACHE

page_setup("Metrics Dashboard", icon="📊")

hero(
    eyebrow="13 · Metrics Dashboard",
    title_html='<span class="gradient-text">Live metrics</span> from the real ledger.',
    subtitle=(
        "Same queries we'd run in Datadog. Updates as you trigger more verifications "
        "on the Live Demo page."
    ),
)

st.write("")

m = db.metrics_summary()

k1, k2, k3, k4, k5 = st.columns(5)
total = max(m["total_verifications"], 1)
match_rate = (m["match"] / total) * 100
k1.metric("Total verifications", m["total_verifications"])
k2.metric("First-pass match rate", f"{match_rate:.1f}%", help="Target ≥ 99%")
k3.metric("Pending review", m["pending_review"])
k4.metric("Workflow runs", m["runs_completed"] + m["runs_running"])
k5.metric("Open HITL", m["hitl_open"])

divider()

rows = db.fetch_verifications(limit=500)
if not rows:
    st.info("No verifications recorded yet. Run a few on the Live Demo page.")
    footer()
    st.stop()

df = pd.DataFrame([dict(r) for r in rows])
df["created_at"] = pd.to_datetime(df["created_at"])
df = df.sort_values("created_at")

# Outcome breakdown
c1, c2 = st.columns(2)
with c1:
    st.markdown("##### Outcome breakdown")
    counts = df["result"].value_counts().reset_index()
    counts.columns = ["result", "count"]
    color_map = {"match": REAL_MINT, "pending_review": REAL_AMBER, "mismatch": REAL_RED, "error": REAL_RED}
    fig = px.bar(
        counts, x="result", y="count", color="result",
        color_discrete_map=color_map, text="count",
    )
    fig.update_layout(
        height=320, showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter", color="#E6EAF2"),
        margin=dict(l=10, r=10, t=10, b=10),
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="rgba(255,255,255,0.06)")
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

with c2:
    st.markdown("##### Per-state success rate")
    by_state = df.groupby("licensing_state").agg(
        total=("result", "count"),
        match=("result", lambda s: (s == "match").sum()),
    ).reset_index()
    by_state["success_rate"] = (by_state["match"] / by_state["total"] * 100).round(1)
    fig = px.bar(
        by_state, x="licensing_state", y="success_rate", text="success_rate",
        color="success_rate",
        color_continuous_scale=[REAL_RED, REAL_AMBER, REAL_MINT], range_color=[0, 100],
    )
    fig.update_traces(texttemplate="%{text}%", textposition="outside")
    fig.update_layout(
        height=320, coloraxis_showscale=False,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter", color="#E6EAF2"),
        margin=dict(l=10, r=10, t=10, b=10),
        yaxis=dict(range=[0, 110], gridcolor="rgba(255,255,255,0.06)"),
    )
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

divider()

# Timeline
st.markdown("##### Verifications over time")
df["bucket"] = df["created_at"].dt.floor("min")
timeline = df.groupby(["bucket", "result"]).size().reset_index(name="count")
fig = px.area(
    timeline, x="bucket", y="count", color="result",
    color_discrete_map={"match": REAL_MINT, "pending_review": REAL_AMBER, "mismatch": REAL_RED, "error": REAL_RED},
)
fig.update_layout(
    height=320, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter", color="#E6EAF2"),
    margin=dict(l=10, r=10, t=10, b=10),
    xaxis=dict(gridcolor="rgba(255,255,255,0.06)"),
    yaxis=dict(gridcolor="rgba(255,255,255,0.06)"),
)
st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

divider()

# Cache stats + workflow run summary
c1, c2 = st.columns(2)
with c1:
    s = SELECTOR_CACHE.stats()
    st.markdown("##### Selector cache (Stagehand stand-in)")
    cc1, cc2, cc3 = st.columns(3)
    cc1.metric("Hits", s["hits"])
    cc2.metric("Misses", s["misses"])
    cc3.metric("Hit rate", f"{s['hit_rate']*100:.0f}%")
    st.caption(f"Live entries: {s['size']}. In production this is Redis with TTL eviction.")

with c2:
    st.markdown("##### Workflow runs")
    with db.connect() as con:
        runs = list(con.execute("SELECT workflow_status, COUNT(*) AS c FROM workflow_runs GROUP BY workflow_status"))
    if runs:
        rdf = pd.DataFrame([dict(r) for r in runs])
        fig = px.pie(rdf, values="c", names="workflow_status", hole=0.6,
                     color="workflow_status",
                     color_discrete_map={"completed": REAL_MINT, "running": REAL_CYAN, "quarantined": REAL_AMBER, "failed": REAL_RED})
        fig.update_layout(
            height=240, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Inter", color="#E6EAF2"),
            margin=dict(l=10, r=10, t=10, b=10),
            showlegend=True,
        )
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

footer()
