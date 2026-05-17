import streamlit as st
from components.styles import page_setup, hero, card, divider, footer, REAL_CYAN, REAL_INDIGO, REAL_MUTED
from components.diagrams import architecture_graph

page_setup("System Architecture", icon="🏗️")

hero(
    eyebrow="02 · System Architecture",
    title_html='Six layers. <span class="gradient-text">One durable workflow.</span>',
    subtitle=(
        "The architecture separates concerns so each layer can fail and recover independently. "
        "Trigger, orchestration, browser automation, target sites, persistence, and human-in-the-loop "
        "are all swappable parts — but they're tied together by a single Temporal workflow that owns the "
        "verification's lifecycle from event to ledger entry."
    ),
)

st.write("")

# Big diagram
st.markdown("### System diagram")
st.markdown(
    f"<div style='color:{REAL_MUTED}; font-size:0.9rem; margin-bottom:8px;'>"
    f"Left → right. The Temporal workflow in the center owns the entire saga; everything else is a callable activity or sink."
    f"</div>",
    unsafe_allow_html=True,
)
g = architecture_graph()
st.graphviz_chart(g, use_container_width=True)

divider()

# Layer-by-layer
st.markdown("### What each layer does — and why it exists")

l1, l2 = st.columns(2)

with l1:
    card(
        "① Trigger layer",
        """
        <b>Goal:</b> never miss an activation event, even if downstream is down.<br/><br/>
        <b>How:</b> CRM emits an <code>agent.activated</code> event to a webhook. The webhook lands in
        <b>AWS EventBridge</b>, which dual-writes to a DynamoDB <b>outbox table</b>.
        A poller backstops the webhook so we recover from missed deliveries.<br/><br/>
        <b>Why not just a webhook?</b> Webhooks fail silently. The outbox + poller turn an at-most-once
        delivery into at-least-once. Temporal handles the dedupe.
        """,
        pills=[("EventBridge", "cyan"), ("Outbox pattern", "blue")],
    )
    card(
        "② Orchestration layer — the spine",
        """
        <b>Goal:</b> guarantee every event becomes a completed verification, even across pod restarts and
        cross-region failover.<br/><br/>
        <b>How:</b> a single <b>Temporal workflow</b> per agent. Each step (API call, JoinReal nav, DRE nav,
        verify, write) is an <b>activity</b> with its own retry policy. The workflow itself is durable: if a
        worker dies mid-DRE-fetch, Temporal replays history and resumes.<br/><br/>
        <b>Idempotency key:</b> <code>agent_id + onboarding_event_id</code>. Re-delivery doesn't double-write.
        """,
        pills=[("Temporal.io", "violet"), ("Durable execution", "mint")],
    )
    card(
        "③ Browser automation layer — the worker",
        """
        <b>Goal:</b> navigate any U.S. real-estate website and extract a license expiration date, even when
        the page changes.<br/><br/>
        <b>How:</b> <b>Stagehand</b> on top of <b>Playwright</b>, running on <b>Browserbase</b> (managed
        cloud browsers + residential proxies + CAPTCHA solving). Stagehand caches successful selectors
        so the steady-state path costs ~0 LLM tokens. When the DOM shifts, Stagehand's AI primitives
        (<code>act</code>, <code>extract</code>, <code>observe</code>) re-derive the action.<br/><br/>
        <b>Last resort:</b> screenshot → Claude Opus vision → coordinates. Slow, but always works.
        """,
        pills=[("Stagehand", "violet"), ("Playwright", "blue"), ("Browserbase", "cyan")],
    )

with l2:
    card(
        "④ Target adapter registry",
        """
        <b>Goal:</b> isolate per-state quirks so the workflow code stays uniform.<br/><br/>
        <b>How:</b> a versioned YAML registry of <b>DRE adapters</b> — one per state. Each adapter declares
        the URL, the search form fields, the result table layout, and the expiration field locator. If
        California's site changes tomorrow, we ship a new <code>ca-v3.yaml</code> with a feature flag and
        roll it forward. <b>No code change, no redeploy.</b><br/><br/>
        Adapters can mark themselves <em>vision-only</em> for sites that refuse to be templated.
        """,
        pills=[("Adapter pattern", "blue"), ("YAML config", "mint")],
    )
    card(
        "⑤ Data + observability",
        """
        <b>Goal:</b> total auditability. Every verification is reproducible from logs alone.<br/><br/>
        <b>How:</b><br/>
        • <b>PostgreSQL</b> — the verification ledger. One row per attempt, with status, mismatch reason, and S3 pointer.<br/>
        • <b>S3</b> — screenshots at every step, full HAR file, Playwright trace. Used to debug and to prove a
        verification when an auditor asks.<br/>
        • <b>Datadog + Sentry</b> — golden-signal metrics (success rate per state, p95 duration, LLM cost
        per verification) and exception capture.
        """,
        pills=[("PostgreSQL", "blue"), ("S3", "amber"), ("Datadog", "violet")],
    )
    card(
        "⑥ Human-in-the-loop",
        """
        <b>Goal:</b> when AI isn't sure, a human gets a 30-second decision, not a 30-minute investigation.<br/><br/>
        <b>How:</b> every <em>quarantined</em> verification posts to a Slack channel with the screenshot,
        the API data, and a one-click "approve / reject / re-run" inline action that calls back into the
        Temporal workflow via signal. The Ops Dashboard (also a Streamlit app, behind SSO) shows the
        queue and the resolved history.<br/><br/>
        <b>Target HITL rate:</b> &lt; 1.5% of verifications, declining as adapters mature.
        """,
        pills=[("Slack", "mint"), ("Signals", "violet"), ("HITL", "amber")],
    )

divider()

# Data flow
st.markdown("### End-to-end data flow for a single agent")
st.markdown(
    f"""
    <div class="card">
        <pre style="margin:0; color:#CBD5E1; font-size:0.86rem; line-height:1.6; background:transparent; border:none;">
<span style="color:{REAL_CYAN}">[CRM]</span>  agent.activated(agent_id=A1234, state="CA")
   │
   ▼
<span style="color:{REAL_CYAN}">[EventBridge]</span>  → outbox (DynamoDB) → poller backstop
   │
   ▼
<span style="color:{REAL_INDIGO}">[Temporal Workflow: VerifyAgent(A1234)]</span>
   │   activity: fetch_agent_metadata(A1234)
   │      → POST /internal/agents/A1234  → {{ name, state, license_no, expires_at }}
   │
   │   activity: verify_joinreal(name, state)
   │      → Stagehand.act("search for agent name")
   │      → Stagehand.observe(matching listing)
   │      → Stagehand.extract(state field) → assert == CRM.state
   │
   │   activity: verify_dre(state, license_no)
   │      → load adapter("ca-v3.yaml")
   │      → Playwright.fill(license_no) → submit
   │      → Stagehand.extract(expiration_date)
   │      → on miss: vision_fallback(screenshot)
   │
   │   activity: write_verification_ledger(result)
   │      → PostgreSQL + S3 artifact pointers
   │
   ▼
<span style="color:#34D399">[Success]</span>  → CRM patched, Datadog metric, done.
<span style="color:#EF4444">[Mismatch]</span>  → Slack quarantine, await operator signal.
        </pre>
    </div>
    """,
    unsafe_allow_html=True,
)

divider()

c1, c2 = st.columns([1, 1])
with c1:
    st.page_link("pages/1_Problem_Statement.py", label="← Problem Statement", use_container_width=True)
with c2:
    st.page_link("pages/3_Workflow_Walkthrough.py", label="Next: Workflow Walkthrough →", use_container_width=True)

footer()
