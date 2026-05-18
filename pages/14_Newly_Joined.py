"""Newly Joined — the 20-agent trigger feed.

In production, EventBridge would deliver each `agent.activated` event one at a
time. Here we let the panel see the queue and "Run all" or run one at a time.
"""
from __future__ import annotations

import time
from pathlib import Path

import pandas as pd
import streamlit as st

from components.styles import (
    page_setup, hero, card, divider, footer,
    REAL_CYAN, REAL_MINT, REAL_AMBER, REAL_MUTED, REAL_INDIGO,
)
from verifier.agent_loader import newly_joined

page_setup("Newly Joined", icon="🆕")

hero(
    eyebrow="14 · Newly Joined · trigger feed",
    title_html='20 newly-activated agents <span class="gradient-text">awaiting verification</span>.',
    subtitle=(
        "These agents flipped active=True in the last 7 days. The verification workflow processes them "
        "asynchronously — match silently, mismatch quarantines to HITL. "
        "The 3 real-onereal-URL agents are marked with a 🎯 — those are the ones to verify live."
    ),
)

st.write("")

agents = newly_joined()
if not agents:
    st.info("No newly joined agents in the last 7 days. Regenerate the fixture: `python -m verifier.agent_generator`")
    footer()
    st.stop()

# Summary metrics
c1, c2, c3, c4 = st.columns(4)
c1.metric("Pending verification", len(agents))
c2.metric("Real-URL demo targets", sum(1 for a in agents if a["onboarding"].get("is_real_demo_target")))
c3.metric("States represented", len({a["license"]["state_code"] for a in agents}))
c4.metric("Avg license expiration ", "—", help="Will populate after verifications")

divider()

# Bulk-run option
st.markdown("### Bulk actions")
b1, b2, b3 = st.columns([1, 1, 2])
with b1:
    only_demo = st.toggle("Only real-URL agents", value=True,
                          help="Filter to the 3 demo agents with real onereal.com URLs")
with b2:
    headed = st.toggle("Show browser", value=True)

display = [a for a in agents if (not only_demo or a["onboarding"].get("is_real_demo_target"))]

run_all = st.button(f"▶  Run verification for all {len(display)} agents", width="content")

# Table
divider()
st.markdown("### The queue")
rows = []
for a in display:
    is_demo = a["onboarding"].get("is_real_demo_target")
    rows.append({
        "🎯": "🎯" if is_demo else "",
        "Agent ID": a["agent_id"],
        "Name": a["name"]["full"],
        "State": a["license"]["state_code"],
        "License #": a["license"]["number"] or "(from profile)",
        "License Type": a["license"]["type"],
        "Slug → URL": a["profile_url"],
        "Active since": a["onboarding"]["active_since"][:19].replace("T", " "),
        "Status": a["verification"]["status"],
    })
df = pd.DataFrame(rows)


def _color_status(v):
    return {
        "pending":        "background-color: rgba(245,158,11,0.15); color: #FCD34D;",
        "match":          "background-color: rgba(52,211,153,0.15); color: #6EE7B7;",
        "mismatch":       "background-color: rgba(239,68,68,0.15); color: #FCA5A5;",
        "hitl":           "background-color: rgba(239,68,68,0.15); color: #FCA5A5;",
    }.get(v, "")


st.dataframe(
    df.style.map(_color_status, subset=["Status"]),
    width="stretch",
    hide_index=True,
    height=420,
)

# Bulk-run execution
if run_all:
    from verifier.workflow import run_verification

    progress = st.progress(0)
    status_box = st.empty()
    log_box = st.empty()
    log_html = ""

    for i, agent in enumerate(display, 1):
        status_box.info(f"Running {i}/{len(display)} · {agent['name']['full']} ({agent['license']['state_code']})...")
        log_html += (
            f"<div style='padding:6px 12px; background:rgba(20,27,45,0.6); border-left:3px solid {REAL_CYAN}; "
            f"border-radius:6px; margin:3px 0;'>"
            f"<b>▶ {agent['name']['full']}</b> — running workflow..."
            f"</div>"
        )
        log_box.markdown(log_html, unsafe_allow_html=True)

        final = "unknown"
        try:
            spans = list(run_verification(agent_id=agent["agent_id"], headed_browser=headed))
            for sp in spans:
                if sp.kind == "end":
                    final = sp.title
        except Exception as e:  # noqa: BLE001
            final = f"crashed: {type(e).__name__}"

        color = REAL_MINT if "MATCH" in final else REAL_AMBER if "paused" in final else REAL_INDIGO
        log_html += (
            f"<div style='padding:6px 12px; background:rgba(20,27,45,0.6); border-left:3px solid {color}; "
            f"border-radius:6px; margin:3px 0;'>"
            f"<b>{agent['name']['full']}</b> — {final}"
            f"</div>"
        )
        log_box.markdown(log_html, unsafe_allow_html=True)
        progress.progress(i / len(display))

    status_box.success(f"✓ Processed {len(display)} agents. Check the Ledger and HITL Queue pages.")

st.write("")
nav1, nav2, nav3, nav4 = st.columns(4)
with nav1:
    st.page_link("pages/10_Live_Demo.py", label="🟢  Live Demo (single)", width="stretch")
with nav2:
    st.page_link("pages/11_Verification_Ledger.py", label="📒  Ledger", width="stretch")
with nav3:
    st.page_link("pages/12_HITL_Queue.py", label="👤  HITL Queue", width="stretch")
with nav4:
    st.page_link("pages/15_Adapter_Registry.py", label="🗂️  Adapter Registry", width="stretch")

footer()
