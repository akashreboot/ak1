import streamlit as st
from components.styles import page_setup, hero, card, divider, footer, REAL_CYAN, REAL_INDIGO, REAL_MUTED, REAL_RED, REAL_AMBER, REAL_MINT
from components.diagrams import resilience_pyramid_fig, state_coverage_map_fig

page_setup("Resilience & Failures", icon="🛡️")

hero(
    eyebrow="05 · Resilience & Failure Handling",
    title_html='What happens when the <span class="gradient-text">internet changes underneath us?</span>',
    subtitle=(
        "Mark's three design questions get answered here: how we mitigate UI changes, how we surface failures "
        "for human review, and how we make sure the workflow always runs (deployment is on the next page)."
    ),
)

st.write("")

# Pyramid
top, side = st.columns([1.5, 1])
with top:
    st.markdown("### Defense-in-depth — six fallback layers")
    st.plotly_chart(resilience_pyramid_fig(), width="stretch", config={"displayModeBar": False})
    st.markdown(
        f"""
        <div style="color:{REAL_MUTED}; font-size:0.9rem; margin-top:-10px;">
            Read top-to-bottom: each layer kicks in only when the layer below it fails. The system <em>tries to be cheap</em>
            and degrades to <em>smarter and more expensive</em> only as needed.
        </div>
        """,
        unsafe_allow_html=True,
    )

with side:
    card(
        "Design principle",
        """
        Most automation systems treat a UI change as an <em>outage</em>. We treat it as a <b>routine event</b>.
        Cached selector misses? AI re-derives. AI extraction unsure? Vision fallback. Vision unsure?
        Human reviewer with full context in Slack. Every failure has a defined next layer.
        """,
        pills=[("Graceful degradation", "violet")],
    )
    card(
        "Failure budget",
        """
        Internal SLO: <b>≥ 99% first-pass success</b> at the workflow level, <b>≤ 1.5% HITL</b>, <b>0%</b>
        silently-failed verifications. We page on the budget burn rate, not on individual incidents.
        """,
        pills=[("SLO", "cyan")],
    )

divider()

st.markdown("### Mark's three questions — answered")

q1, q2, q3 = st.tabs([
    "1 · How do we mitigate failures from UI changes on JoinReal / DRE?",
    "2 · How do we surface failures for human review?",
    "3 · How do we guarantee the workflow always runs?",
])

with q1:
    c1, c2 = st.columns(2)
    with c1:
        card(
            "Layer A — Stagehand selector cache + AI re-derivation",
            """
            Stagehand caches the working selector for each <code>act/extract</code>. On the next run we try the
            cached selector first (fast, free). If it misses, the AI primitive re-derives the action using the
            page's accessibility tree and updates the cache. <b>One UI change = one cache miss</b>, not 50.
            """,
            pills=[("Self-healing", "cyan")],
        )
        card(
            "Layer B — Vision fallback (Claude Opus)",
            """
            When DOM-based extraction is unsure (e.g. confidence &lt; 0.85, or the adapter declares
            vision-only), we screenshot the page and ask Claude to locate the field. Slow (~22s p50),
            but works even when the page is canvas-rendered or behind a JS framework that rewrites the DOM.
            """,
            pills=[("Vision", "violet")],
        )
    with c2:
        card(
            "Layer C — Adapter versioning + canary",
            """
            Every state has a versioned adapter (<code>ca-v3.yaml</code>). When we deploy a new version,
            it canaries on 5% of traffic for that state. If the success rate dips, we auto-rollback. New
            adapters are ship-able <b>without a code release</b> — they're config in S3 + Postgres.
            """,
            pills=[("Versioning", "blue")],
        )
        card(
            "Layer D — Hourly synthetic monitors",
            """
            Datadog Synthetics runs a fixture-agent verification against every state adapter <b>every hour</b>.
            We see UI changes before real verifications start failing. Adapter health is on a public ops
            dashboard — green/yellow/red per state.
            """,
            pills=[("Synthetic", "mint")],
        )

    st.markdown("##### Per-state adapter maturity (today's snapshot)")
    st.plotly_chart(state_coverage_map_fig(), width="stretch", config={"displayModeBar": False})

with q2:
    c1, c2 = st.columns([1.2, 1])
    with c1:
        card(
            "Where failures go",
            """
            Every quarantined verification posts to the <code>#agent-verify-ops</code> Slack channel with:
            <ul>
                <li>The CRM agent payload (name, state, license #)</li>
                <li>A side-by-side screenshot — CRM data on left, scraped value on right</li>
                <li>The exact mismatch (state, expiration, no listing found)</li>
                <li>Three inline buttons: <span class="kbd">Approve</span> <span class="kbd">Reject + open ticket</span> <span class="kbd">Re-run</span></li>
            </ul>
            Each button sends a Temporal <b>signal</b> back to the paused workflow. There is no separate ticketing system to keep in sync.
            """,
            pills=[("Slack", "mint"), ("Signals", "violet")],
        )
        card(
            "Ops Dashboard (Streamlit, behind SSO)",
            """
            A queue view for the team, with: filters by state / failure type, full Playwright trace
            on click, "bulk re-run this state" once an adapter is fixed, and metrics over time.
            <br/><br/>
            The dashboard <b>is what Ops actually uses</b> — Slack is the alert, the dashboard is the
            workbench.
            """,
            pills=[("HITL", "amber")],
        )
    with c2:
        st.markdown(
            f"""
            <div class="card" style="border-left:3px solid {REAL_AMBER};">
                <h3 style="margin-top:0; color:{REAL_AMBER};">Example Slack alert</h3>
                <pre style="background:transparent; border:none; color:#CBD5E1; font-size:0.82rem; line-height:1.5;">
🟡  Verification needs review · agent A-CA-3304

State (CRM):     California
State (JoinReal): California  ✓
License #:       02145778
Expiration (CRM): 2027-03-14
Expiration (DRE): 2027-03-04  ✗

📎 trace: real-verify/A-CA-3304/2026-05-17.zip

[ Approve CRM ] [ Approve DRE ] [ Reject ] [ Re-run ]
                </pre>
            </div>
            """,
            unsafe_allow_html=True,
        )
        card(
            "Why this design works",
            """
            The operator gets a <b>30-second decision</b>, not a 30-minute investigation. The trace bundle
            answers "did the scraper do the right thing?" instantly. The buttons make their decision
            structured, auditable data — not a Slack reply we have to parse.
            """,
            pills=[("Speed", "cyan")],
        )

with q3:
    c1, c2 = st.columns(2)
    with c1:
        card(
            "At the event boundary — at-least-once delivery",
            """
            Webhook → EventBridge → DynamoDB outbox. A poller scans the outbox every 60s for events the
            webhook missed. <b>We don't trust a single delivery path.</b>
            """,
            pills=[("Outbox pattern", "blue")],
        )
        card(
            "At the workflow boundary — durable execution",
            """
            Temporal owns the saga. Workers can be killed at any point; on restart, Temporal replays the
            workflow history and resumes from the last completed activity. <b>Zero lost work, ever.</b>
            """,
            pills=[("Temporal", "violet")],
        )
        card(
            "Activity-level retries",
            """
            Each activity has its own retry policy. Browser activities: 3 attempts, exponential
            backoff with jitter, fresh Browserbase session each retry. Network activities: 5 attempts,
            shorter intervals. <b>Retries are typed</b> — only retryable errors trigger them.
            """,
            pills=[("Retries", "mint")],
        )
    with c2:
        card(
            "Multi-AZ workers, multi-region failover",
            """
            EKS workers run across 3 AZs. Temporal Cloud is multi-region by default. If <code>us-east-1</code>
            degrades, we fail over to <code>us-west-2</code> — workers reconnect, in-flight workflows resume.
            """,
            pills=[("Multi-AZ", "blue")],
        )
        card(
            "Backpressure + adaptive concurrency",
            """
            Browserbase has session limits. KEDA scales workers based on Temporal task-queue depth, with
            <b>state-aware concurrency caps</b> (e.g. only 10 concurrent CA DRE sessions to avoid
            rate-limiting from the state).
            """,
            pills=[("KEDA", "cyan")],
        )
        card(
            "Disaster recovery",
            """
            Postgres has continuous backups + PITR. S3 is cross-region replicated for compliance artifacts.
            RTO 1h, RPO 5 min. Quarterly DR drills replay an EventBridge archive into a sandbox cluster.
            """,
            pills=[("DR", "amber")],
        )

divider()

c1, c2 = st.columns([1, 1])
with c1:
    st.page_link("pages/4_Tech_Stack.py", label="← Tech Stack", width="stretch")
with c2:
    st.page_link("pages/6_Deployment.py", label="Next: Deployment Strategy →", width="stretch")

footer()
