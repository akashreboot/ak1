"""System architecture — minimalist 6-stage flow."""
import streamlit as st
import pandas as pd

from components.styles import page_setup, hero, card, divider, footer

page_setup("System Architecture", icon="🏗️")

hero(
    eyebrow="02 · Architecture",
    title_html='Six durable stages, <span class="gradient-text">one workflow.</span>',
    subtitle=(
        "Triggered by the CRM. Every verification runs the same saga: "
        "fetch profile → cross-check → resolve adapter → drive DRE → compare → decide."
    ),
)

st.write("")

# ── The 6-stage flow as a horizontal pipeline ────────────────────────────
STAGES = [
    ("1", "CRM trigger",     "agent.activated → fetch metadata",              "cyan"),
    ("2", "Profile fetch",   "Playwright opens onereal.com/profile/<slug>",   "cyan"),
    ("3", "Cross-check",     "name + state agree between CRM ↔ profile",      "blue"),
    ("4", "Resolve adapter", "load <state>.yaml; pick browser tier T1–T4",    "violet"),
    ("5", "Drive DRE",       "fill license # → disambiguate → extract expiry","violet"),
    ("6", "Decide",          "Claude classifies; write ledger or open HITL",  "mint"),
]

TONES = {
    "cyan":   ("rgba(6,182,212,0.10)",  "rgba(6,182,212,0.45)",  "#22D3EE"),
    "blue":   ("rgba(96,165,250,0.10)", "rgba(96,165,250,0.45)", "#60A5FA"),
    "violet": ("rgba(139,92,246,0.10)", "rgba(139,92,246,0.45)", "#A78BFA"),
    "mint":   ("rgba(16,185,129,0.10)", "rgba(16,185,129,0.45)", "#34D399"),
}

html = '<div style="display:grid; grid-template-columns:repeat(6,1fr); gap:8px; margin:6px 0 18px;">'
for n, name, desc, tone in STAGES:
    bg, border, c = TONES[tone]
    html += (
        f'<div style="background:{bg}; border:1px solid {border}; border-radius:10px; '
        f'padding:14px 10px; min-height:140px;">'
        f'<div style="color:{c}; font-weight:700; font-size:1.1rem;">{n}</div>'
        f'<div style="color:#E2E8F0; font-weight:600; font-size:0.92rem; margin-top:4px;">{name}</div>'
        f'<div style="color:#94A3B8; font-size:0.78rem; line-height:1.4; margin-top:6px;">{desc}</div>'
        f'</div>'
    )
html += "</div>"
st.markdown(html, unsafe_allow_html=True)

divider()

st.markdown("### Four pillars")
c1, c2 = st.columns(2)
with c1:
    card("🧱  Durable workflow",
         "Every activity is replayable. Worker crashes don't lose progress.",
         pills=[("Temporal-equivalent", "violet")])
    card("🗂️  Adapter-as-data",
         "Each state's DRE flow is a versioned YAML. New state = drop a file.",
         pills=[("Config, not code", "cyan")])
with c2:
    card("📡  Anti-bot tiering",
         "T1 Playwright → T2 Camoufox → T3 Browserbase → T4 HITL. Auto-promote on failures.",
         pills=[("Self-healing", "mint")])
    card("🤖  AI as fallback",
         "Cheap selectors first. Claude vision only when DOM drifts. Same code path.",
         pills=[("Cheap → smart", "amber")])

divider()

st.markdown("### Routing decisions per agent")
ROUTES = [
    ("Profile state",    "extracted from onereal.com HTML",      "WA · CA · TX · …"),
    ("Adapter",          "<state>.yaml loaded from registry",    "wa.yaml / ca.yaml / tx.yaml"),
    ("Browser tier",     "router queries per-state success rate","T1 / T2 / T3 / T4"),
    ("Search strategy",  "form-fill OR URL-param navigation",    "per adapter flag"),
    ("Disambiguation",   "score by type + status + name + city", "1 row pick / many score"),
]
df = pd.DataFrame(ROUTES, columns=["Decision", "Source", "Possible values"])
st.dataframe(df, width="stretch", hide_index=True)

st.write("")
nav1, nav2 = st.columns(2)
with nav1:
    st.page_link("pages/1_Problem_Statement.py", label="← Problem", width="stretch")
with nav2:
    st.page_link("pages/3_Workflow_Walkthrough.py", label="Next: Walkthrough →", width="stretch")

footer()
