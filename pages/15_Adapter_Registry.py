"""Adapter Registry — view all per-state DRE adapters and their current tier health.

In production this is the page Ops uses to see "is California green right now,
or is the auto-router promoting it to T2 because pplinfo.asp changed selectors?"
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st
import yaml

from components.styles import (
    page_setup, hero, card, divider, footer,
    REAL_CYAN, REAL_MUTED, REAL_MINT, REAL_AMBER, REAL_RED, REAL_VIOLET, REAL_BLUE,
)
from verifier.adapter_loader import ADAPTERS_DIR, list_states, load_adapter
from verifier.anti_bot_router import ROUTER, TIER_LABELS

page_setup("Adapter Registry", icon="🗂️")

hero(
    eyebrow="15 · Adapter Registry",
    title_html='Per-state DRE configs <span class="gradient-text">as data, not code</span>.',
    subtitle=(
        "Every state's verification flow lives as a versioned YAML file. New state? Drop a YAML. "
        "Site redesigned? Ship a new version under a feature flag. Auto-router promotes a state's "
        "tier when its current tier starts failing — green/yellow/red shows current health."
    ),
)

st.write("")

states = list_states()
if not states:
    st.warning("No adapters found.")
    footer()
    st.stop()

rows = []
for st_code in states:
    try:
        a = load_adapter(st_code)
    except Exception as e:  # noqa: BLE001
        rows.append({"state": st_code, "error": str(e)})
        continue
    tier = ROUTER.get_tier(st_code, a.get("anti_bot_tier", "T1"))
    snap = ROUTER.snapshot().get(st_code, {})
    rows.append({
        "State": st_code,
        "Full name": a.get("state_full_name", st_code),
        "Adapter version": a.get("version"),
        "Declared tier": a.get("anti_bot_tier", "T1"),
        "Effective tier": tier,
        "Disambiguation": "✓" if a.get("dre", {}).get("disambiguation_required") else "—",
        "Recent success rate": (f"{int(snap['success_rate']*100)}%" if snap.get("success_rate") is not None else "—"),
        "DRE URL": a.get("dre", {}).get("search_url", "—"),
    })

df = pd.DataFrame(rows)


def _color_tier(v):
    return {
        "T1": "background-color: rgba(52,211,153,0.15); color: #6EE7B7;",
        "T2": "background-color: rgba(139,92,246,0.15); color: #C4B5FD;",
        "T3": "background-color: rgba(245,158,11,0.15); color: #FCD34D;",
        "T4": "background-color: rgba(239,68,68,0.15); color: #FCA5A5;",
    }.get(v, "")


st.dataframe(
    df.style.map(_color_tier, subset=["Declared tier", "Effective tier"]),
    use_container_width=True, hide_index=True, height=300,
)

divider()

st.markdown("### Adapter detail")
chosen = st.selectbox("Inspect adapter", options=states, format_func=lambda s: f"{s} · {load_adapter(s).get('state_full_name')}")
adapter = load_adapter(chosen)

c1, c2 = st.columns([1, 1])
with c1:
    st.markdown(f"##### `{chosen.lower()}.yaml` @ {adapter.get('version')}")
    yaml_path = ADAPTERS_DIR / f"{chosen.lower()}.yaml"
    st.code(yaml_path.read_text(), language="yaml")
with c2:
    snap = ROUTER.snapshot().get(chosen, {})
    card(
        "Runtime state",
        f"""
        <ul style="margin:0; padding-left:18px; line-height:1.7;">
            <li><b>Declared tier:</b> {adapter.get('anti_bot_tier','T1')} — <span style="color:{REAL_MUTED};">{TIER_LABELS.get(adapter.get('anti_bot_tier','T1'),'')}</span></li>
            <li><b>Effective tier:</b> {snap.get('effective', adapter.get('anti_bot_tier','T1'))}</li>
            <li><b>Recent outcomes:</b> {''.join('🟢' if r else '🔴' for r in snap.get('recent', [])) or '<span style="color:#94A3B8;">no runs yet</span>'}</li>
            <li><b>DRE URL:</b> <a href="{adapter.get('dre',{}).get('search_url','')}" target="_blank" style="color:{REAL_CYAN}; font-family:JetBrains Mono;">{adapter.get('dre',{}).get('search_url','')}</a></li>
            <li><b>Search method:</b> {adapter.get('dre',{}).get('search_method')}</li>
            <li><b>Disambiguation required:</b> {adapter.get('dre',{}).get('disambiguation_required')}</li>
            <li><b>Expected license types:</b> {', '.join(adapter.get('dre',{}).get('expected_license_types',[]))}</li>
        </ul>
        """,
        pills=[(adapter.get("anti_bot_tier", "T1"), {"T1": "mint", "T2": "violet", "T3": "amber", "T4": "red"}.get(adapter.get("anti_bot_tier","T1"), "blue"))],
    )

divider()

st.markdown("### What the auto-router does")
card(
    "Tier promotion / demotion logic",
    """
    <ul style="margin:0; padding-left:18px; line-height:1.7;">
        <li>Each state starts at its declared tier (T1 by default).</li>
        <li>After <b>3 consecutive failures</b>, the router promotes that state to the next tier (T1 → T2 → T3 → T4).</li>
        <li>After <b>3 consecutive successes</b> at a promoted tier, the router demotes back to the declared tier (gives the cheap path another chance after the site stabilizes).</li>
        <li>The Live Demo trace shows which tier was used for each verification, so the panel can see the routing live.</li>
    </ul>
    """,
    pills=[("Self-healing", "cyan")],
)

footer()
