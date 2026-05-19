"""Problem statement — minimalist version."""
import streamlit as st

from components.styles import (
    page_setup, hero, card, divider, footer,
    REAL_RED,
)

page_setup("Problem Statement", icon="📋")

hero(
    eyebrow="01 · Problem",
    title_html='Manual license verification <span class="gradient-text">does not scale.</span>',
    subtitle=(
        "A brokerage onboards hundreds of agents per week across 50 states. "
        "Every license must be cross-verified against the public profile and the state DRE."
    ),
)

st.write("")

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("Agents activated / week", "~400")
with c2:
    st.metric("States to support", "50")
with c3:
    st.metric("DRE sites with anti-bot", "~30%")
with c4:
    st.metric("Operator-hours today", "linear")

divider()

st.markdown("### The manual flow today")
a, b = st.columns(2)
with a:
    card("1 · CRM marks agent active",
         "Salesforce CDC fires <code>agent.activated</code> — that's the trigger.",
         pills=[("Trigger", "cyan")])
    card("2 · Operator opens onereal.com",
         "Searches the agent; reads the published license number and state.",
         pills=[("Public profile", "blue")])
with b:
    card("3 · Operator opens the state DRE",
         "Different site per state. Types license #. Solves CAPTCHA. Disambiguates.",
         pills=[("Anti-bot", "amber"), ("Disambiguation", "violet")])
    card("4 · Compares expiration dates",
         "If CRM ≠ DRE → flag. Most of the time it matches and the work was busywork.",
         pills=[("Compliance", "red")])

divider()

st.markdown("### Why 50 hand-written scrapers won't work")
cols = st.columns(3)
with cols[0]:
    card("Site heterogeneity",
         "Classic ASP, Salesforce Lightning, Drupal+React, Next.js. No reusable script.",
         pills=[("50 ≠ 1", "blue")])
with cols[1]:
    card("Anti-bot defenses",
         "Cloudflare, reCAPTCHA, IP fingerprinting. Naive automation gets banned.",
         pills=[("Adversarial", "red")])
with cols[2]:
    card("Silent breakage",
         "A UI change can break a scraper invisibly. Audit time is too late.",
         pills=[("Hidden risk", "amber")])

divider()

st.markdown("### Acute failure mode")
st.markdown(
    f"""
    <div class="card" style="border-left:3px solid {REAL_RED};">
        An agent publishes publicly with an <b>expired license</b> that no human caught in time.
        Every state treats that as a <b>compliance event</b>.
    </div>
    """,
    unsafe_allow_html=True,
)

st.write("")
nav1, nav2 = st.columns(2)
with nav1:
    st.page_link("app.py", label="← Home", width="stretch")
with nav2:
    st.page_link("pages/2_System_Architecture.py", label="Next: Architecture →", width="stretch")

footer()
