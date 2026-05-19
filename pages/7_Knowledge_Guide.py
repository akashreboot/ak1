"""Knowledge guide — one-line reference for each piece of the stack."""
import streamlit as st
import pandas as pd

from components.styles import page_setup, hero, card, divider, footer

page_setup("Knowledge Guide", icon="📚")

hero(
    eyebrow="07 · Reference",
    title_html='Glossary <span class="gradient-text">in one line per tool.</span>',
    subtitle="What it is, when we use it, what we'd use instead.",
)

st.write("")

ROWS = [
    ("Playwright",   "Browser automation library (Python + headed Chromium)",                "T1 path — most states"),
    ("Camoufox",     "Firefox fork with C++ stealth (~0% bot-detection rate)",               "T2 path — Cloudflare-light"),
    ("Browserbase",  "Managed browser-as-a-service + residential proxies + CAPTCHA solver",  "T3 path — hard anti-bot"),
    ("Temporal",     "Durable workflow engine — retries, replay, signals as primitives",     "Saga orchestration"),
    ("EventBridge",  "AWS event bus — schema-validated, multi-target",                       "CRM trigger ingress"),
    ("RDS Postgres", "Managed relational DB with point-in-time recovery",                    "Ledger + audit log"),
    ("S3 (CRR)",     "Object store with cross-region replication",                           "Screenshots, HTML snapshots"),
    ("Redis",        "In-memory cache with TTL",                                             "Selector cache, session state"),
    ("Claude Opus",  "Strongest Claude model — vision + complex extraction",                 "AI selector recovery fallback"),
    ("Claude Haiku", "Fastest Claude model — classifier, low latency",                       "Match/mismatch decision"),
    ("Slack webhook","Posts a message + interactive action buttons",                         "HITL alert channel"),
    ("Datadog",      "Observability platform — spans, metrics, logs, dashboards",             "Production telemetry"),
]

df = pd.DataFrame(ROWS, columns=["Term", "What it is", "When we use it"])
st.dataframe(df, width="stretch", hide_index=True, height=460)

divider()

st.markdown("### Three terms worth memorizing")
c1, c2, c3 = st.columns(3)
with c1:
    card("Saga",
         "A workflow made of retryable activities. Each activity is its own unit; the workflow itself is durable.",
         pills=[("Pattern", "violet")])
with c2:
    card("Disambiguation",
         "Picking the right row when a DRE returns multiple matches. Weighted scoring by type + status + name + city.",
         pills=[("Algorithm", "cyan")])
with c3:
    card("HITL",
         "Human-in-the-loop. Quarantine path for cases that need a person. First-class, not an exception.",
         pills=[("Pattern", "amber")])

st.write("")
nav1, nav2 = st.columns(2)
with nav1:
    st.page_link("pages/6_Deployment.py", label="← Deployment", width="stretch")
with nav2:
    st.page_link("pages/8_Panel_QA.py", label="Next: Q&A →", width="stretch")

footer()
