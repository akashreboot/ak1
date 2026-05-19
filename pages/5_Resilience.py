"""Resilience — minimalist failure modes."""
import streamlit as st
import pandas as pd

from components.styles import page_setup, hero, card, divider, footer

page_setup("Resilience", icon="🛡️")

hero(
    eyebrow="05 · Resilience",
    title_html='Every failure mode <span class="gradient-text">has a named response.</span>',
    subtitle="If we can't predict it, we surface it. If we can, we route around it.",
)

st.write("")

st.markdown("### Failure modes & response")
ROWS = [
    ("Selector drift (button renamed)",
     "Claude-vision re-extracts via the AI fallback path",
     "Adapter version bump after canary verifies"),
    ("Cloudflare challenge appears",
     "Router auto-promotes T1 → T2 → T3",
     "After 3 consecutive failures at current tier"),
    ("CAPTCHA wall (unsolvable)",
     "Workflow routes to T4 (HITL queue)",
     "Operator paged via Slack"),
    ("State DRE site down",
     "Retry with exponential backoff (max 1 hour)",
     "Reconciliation queue picks up on recovery"),
    ("Worker pod crashes mid-run",
     "Temporal resumes from last successful activity",
     "Zero work lost; no manual intervention"),
    ("Two rows match the same license #",
     "Disambiguator scores type + status + name + city",
     "Below threshold → HITL with both candidates"),
    ("CRM expiration ≠ DRE expiration",
     "Workflow quarantines to HITL with both values",
     "Compliance picks the authoritative source"),
    ("LLM model deprecation",
     "Adapter declares model; rotate via config edit",
     "No code change required"),
]
df = pd.DataFrame(ROWS, columns=["Failure mode", "Automatic response", "Human path"])
st.dataframe(df, width="stretch", hide_index=True, height=370)

divider()

st.markdown("### SLO commitments")
c1, c2, c3, c4 = st.columns(4)
with c1: st.metric("p95 latency",         "< 90 s")
with c2: st.metric("First-pass match",    "≥ 97%")
with c3: st.metric("HITL escalation",     "≤ 2.5%")
with c4: st.metric("MTTR after UI break", "< 4 h")

divider()

st.markdown("### Three principles")
c1, c2, c3 = st.columns(3)
with c1:
    card("🧱  Saga, not script",
         "Each activity is a retryable unit. The workflow can pause, resume, replay.",
         pills=[("Durability", "violet")])
with c2:
    card("📡  Auto-promote on failure",
         "Tier the runner per state. Bump up on streaks of failure; down on streaks of success.",
         pills=[("Self-healing", "mint")])
with c3:
    card("👤  HITL is first-class",
         "Quarantine is a feature. Slack-styled alerts with working buttons close the loop.",
         pills=[("Visible", "amber")])

st.write("")
nav1, nav2 = st.columns(2)
with nav1:
    st.page_link("pages/4_Tech_Stack.py", label="← Stack", width="stretch")
with nav2:
    st.page_link("pages/6_Deployment.py", label="Next: Deployment →", width="stretch")

footer()
