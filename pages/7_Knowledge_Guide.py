import streamlit as st
from components.styles import page_setup, hero, card, divider, footer, REAL_CYAN, REAL_INDIGO, REAL_MUTED

page_setup("Knowledge Guide", icon="📚")

hero(
    eyebrow="07 · Knowledge Guide",
    title_html='<span class="gradient-text">Every tool</span>, in plain English. Plus the <span class="glow-text">alternatives</span> I considered.',
    subtitle=(
        "Think of this as the appendix an engineer would actually want — what each piece of the stack does, why we use "
        "it, when you'd swap it out, and where to read more."
    ),
)

st.write("")

categories = st.tabs([
    "🧱 Foundations",
    "🤖 Browser & AI",
    "📦 Infra & ops",
    "📐 Patterns I'm using",
    "📖 Glossary",
])

# ── Foundations ─────────────────────────────────────────
with categories[0]:
    card("Temporal.io",
         """
         <b>What:</b> a durable execution platform. You write workflows as ordinary Python, and Temporal
         guarantees they finish — even across process crashes, deploys, and region failovers.<br/>
         <b>Why here:</b> our workflow spans tens of seconds with external HTTP + browser calls. We need
         retries, idempotency, signals, and replay. Temporal gives all of that for free.<br/>
         <b>When you'd swap:</b> if you're 100% AWS-native and your steps are short Lambda calls, Step Functions
         is fine. For Pythonic, long-running, event-driven sagas — Temporal wins.<br/>
         <b>Read:</b> <a href="https://docs.temporal.io">docs.temporal.io</a> · alternatives:
         <a href="https://aws.amazon.com/step-functions/">Step Functions</a>,
         <a href="https://docs.prefect.io">Prefect</a>,
         <a href="https://airflow.apache.org">Airflow</a>.
         """,
         pills=[("Orchestration", "violet")])

    card("AWS EventBridge",
         """
         <b>What:</b> a serverless event bus. You publish events; rules deliver to targets (Lambda, SQS,
         HTTP, Temporal).<br/>
         <b>Why here:</b> schema validation, archive + replay, fan-out, decoupling. If CRM, finance, and
         marketing all want to react to <code>agent.activated</code>, they each add a rule.<br/>
         <b>Alternatives:</b> Kafka (overkill at our volume), SNS/SQS (works but less expressive),
         direct webhook into Temporal (works, but loses replay).
         """,
         pills=[("Eventing", "cyan")])

    card("Postgres / RDS",
         """
         <b>What:</b> the verification ledger. One row per attempt, FK to agent, JSON column with the trace
         summary, S3 pointer for the heavy artifacts.<br/>
         <b>Why here:</b> we'll query it from Ops, Compliance, and audits. Strong consistency + relational
         joins beat a NoSQL store at this scale.<br/>
         <b>Alternative:</b> DynamoDB if we expected 10× volume and only point lookups.
         """,
         pills=[("OLTP", "blue")])

# ── Browser & AI ─────────────────────────────────────────
with categories[1]:
    card("Playwright",
         """
         <b>What:</b> the modern browser automation library from Microsoft. Multi-browser, fast, with
         <b>traces, video, HAR</b> built in. The 2026 default.<br/>
         <b>Why here:</b> deterministic clicks/extracts on stable pages = the cheapest, fastest, most reliable
         path. Stagehand uses it under the hood.<br/>
         <b>Alternatives:</b> Selenium (legacy), Puppeteer (Chromium only), Cypress (test-focused, not great for scraping).
         """,
         pills=[("Browser core", "blue")])

    card("Stagehand (Browserbase)",
         """
         <b>What:</b> a Playwright-compatible SDK that adds four AI primitives:
         <code>act("click the submit button")</code>, <code>extract("the expiration date")</code>,
         <code>observe()</code> for state, and <code>agent()</code> for full autonomy.<br/>
         <b>Why here:</b> Stagehand's <b>auto-caching of successful selectors</b> is the magic. Steady-state
         runs use the cache (zero LLM cost). When the page changes, the AI re-derives — and the system
         self-heals without us touching code.<br/>
         <b>Alternatives:</b> <a href="https://github.com/browser-use/browser-use">Browser-Use</a>
         (every action reasoned each run — more flexible, more expensive), <a href="https://www.skyvern.com">Skyvern</a>,
         hand-rolled GPT-orchestrated Playwright.
         """,
         pills=[("AI primitives", "violet"), ("Self-healing", "cyan")])

    card("Browserbase",
         """
         <b>What:</b> a hosted Chromium farm. Pay per session; they handle proxies, fingerprints, CAPTCHAs,
         scaling.<br/>
         <b>Why here:</b> running 50-state browsers from a single data center triggers DRE rate limits. Browserbase
         rotates residential IPs by state automatically. We don't want to be a proxy management company.<br/>
         <b>Alternatives:</b> Bright Data + self-hosted Playwright (more control, more ops), <a href="https://www.scrapingbee.com">ScrapingBee</a>,
         <a href="https://oxylabs.io">Oxylabs</a>.
         """,
         pills=[("Browser cloud", "cyan")])

    card("Claude (Opus 4.7 / Haiku 4.5)",
         """
         <b>What:</b> Anthropic's frontier language + vision model. Opus is the reasoning model; Haiku is
         the cheap classifier.<br/>
         <b>Why here:</b> Opus handles ambiguous extraction and vision fallback; Haiku handles per-step
         confidence checks at 1/20th the cost. Two-tier routing keeps spend predictable.<br/>
         <b>Alternatives:</b> GPT-5 (peer), Gemini 2.5 Pro (peer), Llama 3.3 70B + Qwen2-VL (self-hosted, lower cost,
         higher ops burden).
         """,
         pills=[("LLM", "violet")])

# ── Infra & ops ─────────────────────────────────────────
with categories[2]:
    card("EKS + KEDA",
         """
         <b>What:</b> Kubernetes managed by AWS, scaled by KEDA which reads custom metrics (e.g. Temporal
         queue depth) rather than just CPU.<br/>
         <b>Why here:</b> browser workers are bursty and not CPU-bound. Scaling on queue depth gives us
         responsive autoscaling without over-provisioning. KEDA also handles "scale to zero" for off-hours.<br/>
         <b>Alternative:</b> ECS Fargate (simpler, slightly less flexible scaling), self-managed K8s (more
         ops work for no gain at this scale).
         """,
         pills=[("Compute", "blue")])

    card("Datadog + Sentry + OpenTelemetry",
         """
         <b>What:</b> Datadog handles metrics, traces, logs, synthetics. Sentry catches exceptions with full
         context. OpenTelemetry is the wire format that ties Temporal, Playwright, and our HTTP layer together.<br/>
         <b>Why here:</b> we need a single pane of glass that goes from "Slack alert" → "Temporal workflow" →
         "Playwright trace" → "screenshot" in 3 clicks.<br/>
         <b>Alternatives:</b> Grafana Cloud (cheaper, more setup), New Relic, Honeycomb (excellent for traces).
         """,
         pills=[("Observability", "amber")])

    card("Streamlit (this deck + the Ops Dashboard)",
         """
         <b>What:</b> a Python framework that turns scripts into web apps. Built by Snowflake.<br/>
         <b>Why here:</b> the Ops Dashboard's audience is internal — engineers + ops analysts. Streamlit
         lets us ship the dashboard with the same Python that runs the workflow logic. <b>Plus, this
         very deck is built in it.</b><br/>
         <b>Alternatives:</b> Retool (faster ops UI, less code), internal React app (more polish, more time),
         <a href="https://nicegui.io">NiceGUI</a>, <a href="https://www.gradio.app">Gradio</a>.
         """,
         pills=[("UI", "mint")])

# ── Patterns ─────────────────────────────────────────
with categories[3]:
    card("Outbox pattern",
         """
         When a service emits an event, write the event to a local table <em>in the same transaction</em>
         as the state change. A poller forwards from that table to the event bus. <b>Guarantees at-least-once
         delivery even if the bus is down.</b>
         """,
         pills=[("Reliability", "violet")])
    card("Saga + compensation",
         """
         A multi-step workflow where each step has a defined rollback. We don't strictly compensate
         (verifications are read-only on external systems), but our workflow structure mirrors saga so
         partial failures are clean.
         """,
         pills=[("Workflow", "blue")])
    card("Adapter registry",
         """
         Per-state DRE configs live as versioned data, not code. New adapter? New YAML. Bad rollout?
         Feature flag rolls it back. <b>Eliminates 'redeploy to fix the Florida scraper' problem.</b>
         """,
         pills=[("Adapter", "cyan")])
    card("Two-tier LLM routing",
         """
         Cheap model handles 90% of decisions (classification, confidence). Expensive model handles the
         10% that need reasoning. <b>10× cost reduction without quality loss</b>.
         """,
         pills=[("Cost", "amber")])
    card("HITL via workflow signals",
         """
         Instead of a separate ticketing system, the Slack button sends a Temporal signal. The paused
         workflow wakes up with the human decision and continues. <b>One source of truth for state.</b>
         """,
         pills=[("HITL", "mint")])

# ── Glossary ─────────────────────────────────────────
with categories[4]:
    st.markdown("##### Quick reference")
    glossary = [
        ("Activity", "A single step in a Temporal workflow. Has its own retries, timeouts, idempotency."),
        ("Signal", "A typed message you can send into a running workflow. Used here for HITL decisions."),
        ("Adapter", "Per-state config that tells the workflow how to navigate that DRE."),
        ("Quarantine", "A verification that couldn't auto-resolve. Sent to Slack + Ops Dashboard."),
        ("HITL", "Human-in-the-loop. The 1.5% of cases that need a human."),
        ("Outbox", "DB table that buffers events before they hit the bus, so we never lose one."),
        ("KEDA", "Kubernetes Event-Driven Autoscaling. Scales pods off custom metrics like queue depth."),
        ("HAR", "HTTP Archive — a recording of every network request a browser made. Gold for debugging."),
        ("Trace", "An end-to-end record of one workflow's execution, including child spans."),
        ("Idempotency key", "A unique value that lets the system safely retry without double-effects."),
        ("Canary", "Sending a small % of traffic to a new version to test it in production."),
        ("Error budget", "How much failure we tolerate before we stop shipping. Drives on-call paging."),
    ]
    cols = st.columns(2)
    for i, (term, defn) in enumerate(glossary):
        with cols[i % 2]:
            st.markdown(
                f"""
                <div class="card" style="padding:14px 18px;">
                    <span style="color:{REAL_CYAN}; font-weight:700;">{term}</span>
                    <div style="color:#CBD5E1; margin-top:4px; font-size:0.92rem;">{defn}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

divider()

c1, c2 = st.columns([1, 1])
with c1:
    st.page_link("pages/6_Deployment.py", label="← Deployment", width="stretch")
with c2:
    st.page_link("pages/8_Panel_QA.py", label="Next: Q&A →", width="stretch")

footer()
