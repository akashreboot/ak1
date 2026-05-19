"""Tech stack — minimalist."""
import streamlit as st
import pandas as pd

from components.styles import page_setup, hero, card, divider, footer

page_setup("Tech Stack", icon="🛠️")

hero(
    eyebrow="04 · Stack",
    title_html='Every choice <span class="gradient-text">earns its row.</span>',
    subtitle="Managed where possible. Self-hosted only where managed doesn't fit.",
)

st.write("")

ROWS = [
    ("Workflow",       "Temporal Cloud",      "Durable saga + retries + signals as a managed service",     "Step Functions"),
    ("Browser (T1)",   "Playwright (Python)", "Mature, scriptable, headed/headless toggle",                "Selenium"),
    ("Browser (T2)",   "Camoufox",            "Firefox + C++ stealth patches (~0% bot-detection rate)",    "Playwright + stealth plugin"),
    ("Browser (T3)",   "Browserbase",         "Managed browsers + residential proxies + CAPTCHA solving",  "Bright Data"),
    ("LLM",            "Anthropic Claude",    "Opus for vision selector recovery, Haiku for classify",     "GPT-5"),
    ("Compute",        "AWS Fargate (EKS)",   "Stateless workers, multi-AZ, auto-scales on queue depth",   "Lambda (15-min cap kills it)"),
    ("Trigger bus",    "EventBridge",         "Schema-validated events from Salesforce CDC",               "SNS / Kafka"),
    ("Ledger",         "Postgres (RDS)",      "Auditable rows; indexed on agent_id + run_id",              "DynamoDB"),
    ("Artifacts",      "S3 + CRR",            "Cross-region replicated screenshots + HTML snapshots",      "EBS volumes"),
    ("Selector cache", "Redis (ElastiCache)", "TTL'd selector hits; hot-path skips DOM scan",              "DynamoDB DAX"),
    ("HITL",           "Slack webhook",       "Action buttons resolve durable workflow signals",           "Internal UI"),
    ("Observability",  "Datadog",             "Spans per activity; golden signals + per-state dashboards", "Grafana + Tempo"),
]

df = pd.DataFrame(ROWS, columns=["Concern", "Choice", "Why", "Rejected alternative"])
st.dataframe(df, width="stretch", hide_index=True, height=460)

divider()

st.markdown("### Three principles")
c1, c2, c3 = st.columns(3)
with c1:
    card("Managed > self-hosted",
         "Pay for boring infra. Spend engineer-hours on the verifier, not the queue.",
         pills=[("Cost of ownership", "cyan")])
with c2:
    card("Determinism first",
         "Cheap selectors win when the page is stable. AI is the fallback, not the default.",
         pills=[("Cost-aware", "mint")])
with c3:
    card("Replaceable layers",
         "Every choice can be swapped without rewriting the workflow.",
         pills=[("Optionality", "violet")])

st.write("")
nav1, nav2 = st.columns(2)
with nav1:
    st.page_link("pages/3_Workflow_Walkthrough.py", label="← Walkthrough", width="stretch")
with nav2:
    st.page_link("pages/5_Resilience.py", label="Next: Resilience →", width="stretch")

footer()
