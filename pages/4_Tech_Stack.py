import streamlit as st
import pandas as pd
from components.styles import page_setup, hero, card, divider, footer, REAL_CYAN, REAL_INDIGO, REAL_MUTED
from components.diagrams import cost_breakdown_fig

page_setup("Tech Stack & Why", icon="🛠️")

hero(
    eyebrow="04 · Tech Stack & Why",
    title_html='Every choice. <span class="gradient-text">Every alternative.</span> Every reason I picked one.',
    subtitle=(
        "This is the part of the deck I'd most want to debate with you. Each row below is a decision "
        "I'd make on day one, with the alternatives I rejected and the reasons why."
    ),
)

st.write("")

# Decision table tabs
tabs = st.tabs([
    "⚡ Orchestration",
    "🌐 Browser automation",
    "🧠 LLM / vision",
    "📨 Event ingress",
    "🗄️ Data & storage",
    "📊 Observability",
    "🚢 Deployment",
])

with tabs[0]:
    card(
        "Pick: Temporal.io (Cloud)",
        """
        Temporal's <b>durable execution</b> model is the single biggest lever for this problem. Browser automation is
        long-running (tens of seconds to minutes), pod-fragile, and full of partial failures. Temporal lets me write
        the workflow as straight-line Python and get crash-safe execution, auto-retries, and idempotency for free.<br/><br/>
        Critical for us: <b>signals</b> let a human (or Slack button) push a decision back into a paused workflow
        without redesigning the data flow.
        """,
        pills=[("Pick", "mint"), ("Durable execution", "violet")],
    )
    c1, c2, c3 = st.columns(3)
    with c1:
        card("Considered: AWS Step Functions",
             "Native to AWS, integrates with EventBridge cleanly. But JSON state-machine language is verbose, hard to test locally, "
             "and long activities (browser sessions) push you into Lambda-vs-ECS gymnastics. Better when your steps are AWS-service calls.",
             pills=[("Rejected", "amber")])
    with c2:
        card("Considered: Apache Airflow",
             "Excellent at batch DAGs and ETL. Wrong shape for event-driven, sub-minute, stateful per-entity workflows. "
             "Retries are coarse (whole task), no native signals, scheduler isn't designed for this latency.",
             pills=[("Rejected", "amber")])
    with c3:
        card("Considered: Prefect / Dagster",
             "Modern, Pythonic, great DX. Closer to Airflow's batch shape than to per-entity durable workflows. "
             "Prefect 3 is improving here, but Temporal's track record at this exact pattern is unmatched.",
             pills=[("Rejected", "amber")])

with tabs[1]:
    card(
        "Pick: Stagehand on top of Playwright, hosted on Browserbase",
        """
        Stagehand gives me four primitives — <code>act()</code>, <code>extract()</code>, <code>observe()</code>,
        <code>agent()</code> — built on Playwright. The killer feature is <b>auto-caching of successful selectors</b>:
        steady-state runs cost ~zero LLM tokens, but the moment a DOM changes, the AI re-engages, finds a new
        selector, and updates the cache.<br/><br/>
        Browserbase handles the parts I don't want to own: managed Chromium farm, residential proxy rotation,
        CAPTCHA solving, fingerprinting. We pay per session — they handle 50-state IP diversity.
        """,
        pills=[("Pick", "mint"), ("AI primitives", "violet"), ("Self-healing", "cyan")],
    )
    c1, c2, c3 = st.columns(3)
    with c1:
        card("Considered: Browser-Use",
             "Pure agent loop — LLM decides every click. Resilient and impressive, but <b>expensive and slow</b> "
             "per verification. Better as a fallback than as the primary engine for steady-state automation.",
             pills=[("Fallback only", "blue")])
    with c2:
        card("Considered: Playwright alone",
             "What we'd use without AI. Fast, deterministic, free. But every DOM change is a JIRA ticket and a "
             "deploy. With 50 DRE sites, that's a permanent maintenance tax I'd rather pay Stagehand to absorb.",
             pills=[("Underneath Stagehand", "blue")])
    with c3:
        card("Considered: Selenium / Puppeteer",
             "Selenium has the largest community but worst DX in 2026. Puppeteer is Chromium-only. Playwright is "
             "the strict superset for our needs and has the cleanest tracing tooling for debugging.",
             pills=[("Rejected", "amber")])

with tabs[2]:
    card(
        "Pick: Claude Opus 4.7 for vision + extraction, Haiku 4.5 for cheap classification",
        """
        Opus handles the hard cases: screenshot → element coordinates, ambiguous name matching, free-form
        expiration-date parsing. Haiku runs the cheap things: "is this listing the right agent? yes/no",
        "did this page error out? yes/no". <b>Two-tier routing</b> keeps spend predictable.<br/><br/>
        Why Anthropic specifically: Claude's vision is currently the strongest at structured-document
        understanding (which is exactly what a DRE page is) and tool-use is reliable.
        """,
        pills=[("Pick", "mint"), ("Two-tier routing", "violet")],
    )
    c1, c2 = st.columns(2)
    with c1:
        card("Considered: GPT-4o / GPT-5",
             "Capable peer. Slightly behind on long-context document understanding; Anthropic also "
             "has a more conservative refusal profile on personally-identifiable data, which matters here.",
             pills=[("Peer", "blue")])
    with c2:
        card("Considered: Open-source (Llama 3.3, Qwen2-VL)",
             "Tempting for cost. But self-hosting a vision model that's reliable enough to be in the critical "
             "path of a compliance workflow is a separate engineering project. Revisit in 12–18 months.",
             pills=[("Future", "violet")])

with tabs[3]:
    card(
        "Pick: CRM webhook → AWS EventBridge → DynamoDB outbox → Temporal start",
        """
        EventBridge gives us schema validation, archive, and replay — invaluable when we want to re-run
        verifications retroactively (e.g. after fixing a CA adapter bug). The DynamoDB outbox protects
        against webhook delivery failures: a poller scans for events that landed in the CRM but never made
        it into EventBridge.<br/><br/>
        Temporal's workflow ID is set to <code>verify::{agent_id}::{event_id}</code> — duplicate deliveries
        are no-ops.
        """,
        pills=[("Pick", "mint"), ("Outbox pattern", "cyan")],
    )
    c1, c2 = st.columns(2)
    with c1:
        card("Considered: Kafka",
             "Overkill at hundreds-of-events/week. Worth revisiting at 100k+ agents and "
             "cross-team event sharing.",
             pills=[("Premature", "amber")])
    with c2:
        card("Considered: Polling only",
             "Simpler, but adds latency (verify could be hours behind activation) and makes the system "
             "noisier in logs. Hybrid is the win.",
             pills=[("Hybrid", "blue")])

with tabs[4]:
    card(
        "Pick: PostgreSQL (RDS) + S3 + Redis",
        """
        <b>PostgreSQL</b> for the verification ledger — it's relational data with strong consistency needs,
        and we'll query it for ops dashboards and compliance reports.<br/>
        <b>S3</b> for screenshots, HAR files, Playwright traces. Lifecycle policy moves &gt;90-day artifacts
        to Glacier.<br/>
        <b>Redis</b> for the Stagehand selector cache (hot read path) and ephemeral session state.
        """,
        pills=[("Pick", "mint")],
    )
    c1, c2 = st.columns(2)
    with c1:
        card("Considered: DynamoDB for ledger",
             "Fast and serverless. But ad-hoc analytical queries from Ops would force us into Athena or a "
             "secondary OLAP. Postgres wins on flexibility at this scale.",
             pills=[("Rejected", "amber")])
    with c2:
        card("Considered: ClickHouse / BigQuery",
             "If verification volumes 100x, we'd add ClickHouse for telemetry analytics. Not yet.",
             pills=[("Future", "violet")])

with tabs[5]:
    card(
        "Pick: Datadog + Sentry + structured logs + Streamlit Ops Dashboard",
        """
        <b>Datadog</b> for metrics (success rate per state, p95 duration, LLM $ per verify), traces
        (OpenTelemetry from Temporal + Playwright), and synthetic monitors that exercise the adapters
        every hour against a fixture agent.<br/>
        <b>Sentry</b> for exception capture with full Playwright trace context.<br/>
        <b>Ops Dashboard</b> (a sister Streamlit app behind SSO) for the HITL queue.
        """,
        pills=[("Pick", "mint"), ("OTel", "blue")],
    )

with tabs[6]:
    card(
        "Pick: Kubernetes on EKS, multi-AZ, with HPA + KEDA",
        """
        Temporal workers, Playwright workers, and the HTTP webhook receiver all run as separate
        deployments. <b>KEDA</b> autoscales the Playwright workers off the Temporal task queue depth
        (not CPU) — this is the right signal for browser workloads.<br/>
        Multi-AZ inside one region for first launch; multi-region active-passive once we cross 10k weekly verifications.
        """,
        pills=[("Pick", "mint"), ("KEDA", "violet"), ("Multi-AZ", "blue")],
    )

divider()

# Cost
st.markdown("### Estimated steady-state cost (~5,000 verifications/week)")
ccol1, ccol2 = st.columns([1.4, 1])
with ccol1:
    st.plotly_chart(cost_breakdown_fig(), width="stretch", config={"displayModeBar": False})
with ccol2:
    st.markdown(
        f"""
        <div class="card">
            <h3 style="margin-top:0;">~$5.7k / month</h3>
            <div style="color:#CBD5E1; line-height:1.7;">
                Roughly <b>$1.10 per verification</b> all-in at 5k/week. The dominant cost is Browserbase
                sessions. As Stagehand's selector cache warms up, LLM spend declines sharply — first
                month is ~3× steady-state.
                <br/><br/>
                Comparison: a manual ops analyst at 6 min/agent caps out at ~80 verifications/day. At 5k/week,
                that's ~13 FTEs of effort — call it <b>$80k–110k/month fully loaded</b>.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

divider()

c1, c2 = st.columns([1, 1])
with c1:
    st.page_link("pages/3_Workflow_Walkthrough.py", label="← Workflow Walkthrough", width="stretch")
with c2:
    st.page_link("pages/5_Resilience.py", label="Next: Resilience & Failures →", width="stretch")

footer()
