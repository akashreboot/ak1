import time
import streamlit as st
from components.styles import page_setup, hero, card, divider, footer, REAL_CYAN, REAL_INDIGO, REAL_MUTED, REAL_MINT, REAL_AMBER, REAL_RED
from components.diagrams import workflow_sequence_graph, failure_funnel_fig

page_setup("Workflow Walkthrough", icon="🔄")

hero(
    eyebrow="03 · Workflow Walkthrough",
    title_html='Watch a single verification go from <span class="gradient-text">CRM event</span> to <span class="glow-text">ledger entry</span>.',
    subtitle=(
        "This is the happy path for one California agent. Press Run to step through it live — every step is the "
        "same activity that runs in production, with its own retry policy, timeout, and artifact."
    ),
)

st.write("")

# Live demo
demo_col, side_col = st.columns([1.6, 1])

with demo_col:
    st.markdown("### Live trace: VerifyAgent workflow")

    sample_agent = {
        "agent_id": "A-CA-3304",
        "name": "Jordan A. Rivera",
        "state": "CA",
        "license_no": "02145778",
        "expires_at": "2027-03-14",
        "onboarded_at": "2026-05-17T13:42:08Z",
    }

    with st.expander("📦  Incoming event payload (from CRM)", expanded=True):
        st.json(sample_agent)

    steps = [
        ("Receive event",            "EventBridge → outbox → Temporal start",                   "Temporal",   0.6, "ok"),
        ("Fetch agent metadata",     "GET /internal/agents/A-CA-3304 (200, 84ms)",              "Agent API",  0.4, "ok"),
        ("Open JoinReal directory",  "Browserbase session bw-7a2c · TTFB 312ms",                "Playwright", 0.7, "ok"),
        ("Search agent name",        "Stagehand.act('search 'Jordan A. Rivera'')",              "Stagehand",  0.9, "ok"),
        ("Click matching listing",   "Top result · name+state match · confidence 0.97",         "Stagehand",  0.6, "ok"),
        ("Verify state on JoinReal", "Listing state = 'California' ✓ matches CRM",              "Verify",     0.3, "ok"),
        ("Open CA DRE eLicensing",   "https://www2.dre.ca.gov/PublicASP/pplinfo.asp",           "Playwright", 0.8, "ok"),
        ("Submit license number",    "fill #lic_id='02145778' → submit",                        "Playwright", 0.9, "ok"),
        ("Open agent listing",       "1 result · clicked detail page",                          "Playwright", 0.5, "ok"),
        ("Extract expiration",       "Stagehand.extract('License Exp Date') → 2027-03-14",      "Stagehand",  0.8, "ok"),
        ("Compare to CRM",           "DRE 2027-03-14 == CRM 2027-03-14 ✓",                      "Verify",     0.3, "ok"),
        ("Write ledger entry",       "row #ver_88241 · s3://real-verify/...trace.zip",          "Postgres+S3", 0.4, "ok"),
    ]

    run = st.button("▶  Run verification", use_container_width=True)
    log_box = st.container()

    if run:
        progress = st.progress(0)
        log = ""
        total_time = 0.0
        for i, (name, detail, owner, dur, status) in enumerate(steps, 1):
            time.sleep(dur * 0.35)  # animate
            total_time += dur
            badge = "🟢" if status == "ok" else "🟡"
            log += (
                f"<div style='display:flex; gap:12px; padding:8px 12px; margin:4px 0; "
                f"background:rgba(20,27,45,0.55); border-left:3px solid {REAL_MINT}; border-radius:8px;'>"
                f"<div style='font-family:JetBrains Mono; color:{REAL_MUTED}; flex:0 0 60px;'>+{total_time:.1f}s</div>"
                f"<div style='flex:0 0 110px;'><span class='pill pill-cyan'>{owner}</span></div>"
                f"<div style='flex:1;'><b>{badge} {name}</b><br/>"
                f"<span style='color:{REAL_MUTED}; font-size:0.85rem; font-family:JetBrains Mono;'>{detail}</span></div>"
                f"</div>"
            )
            log_box.markdown(log, unsafe_allow_html=True)
            progress.progress(i / len(steps))
        st.success(f"✓ Verification complete in {total_time:.1f}s · result: MATCH · ledger row #ver_88241")
    else:
        # static preview
        log = ""
        for name, detail, owner, dur, status in steps:
            log += (
                f"<div style='display:flex; gap:12px; padding:8px 12px; margin:4px 0; "
                f"background:rgba(20,27,45,0.55); border-left:3px solid rgba(99,102,241,0.4); border-radius:8px;'>"
                f"<div style='font-family:JetBrains Mono; color:{REAL_MUTED}; flex:0 0 60px;'>—</div>"
                f"<div style='flex:0 0 110px;'><span class='pill pill-cyan'>{owner}</span></div>"
                f"<div style='flex:1;'><b>{name}</b><br/>"
                f"<span style='color:{REAL_MUTED}; font-size:0.85rem; font-family:JetBrains Mono;'>{detail}</span></div>"
                f"</div>"
            )
        log_box.markdown(log, unsafe_allow_html=True)

with side_col:
    st.markdown("### Step graph")
    st.graphviz_chart(workflow_sequence_graph(), use_container_width=True)

    card(
        "Why this is a workflow, not a script",
        """
        Each numbered step is a <b>Temporal activity</b>. Activities have:
        <ul style="margin:6px 0; padding-left:18px;">
            <li>Their own retry policy (exponential, jittered)</li>
            <li>Their own timeout (no zombie browser sessions)</li>
            <li>Their own idempotency contract</li>
        </ul>
        If step 8 fails, step 1–7 don't re-run. Temporal stores their results.
        """,
        pills=[("Durable", "violet"), ("Replayable", "mint")],
    )

divider()

st.markdown("### What it looks like in aggregate")
fcol, kcol = st.columns([1.5, 1])
with fcol:
    st.markdown("##### Funnel — last 10,000 events (synthetic)")
    st.plotly_chart(failure_funnel_fig(), use_container_width=True, config={"displayModeBar": False})

with kcol:
    st.markdown("##### Per-step SLOs")
    st.markdown(
        f"""
        <div class="card">
            <table style="width:100%; color:#CBD5E1; font-size:0.9rem;">
                <tr style="color:{REAL_CYAN}; text-align:left;"><th>Step</th><th>p50</th><th>p95</th></tr>
                <tr><td>Fetch metadata</td><td>120ms</td><td>380ms</td></tr>
                <tr><td>JoinReal verify</td><td>9.4s</td><td>22s</td></tr>
                <tr><td>DRE verify (CA)</td><td>14.1s</td><td>38s</td></tr>
                <tr><td>Vision fallback</td><td>22s</td><td>1m 40s</td></tr>
                <tr><td>Ledger write</td><td>40ms</td><td>110ms</td></tr>
            </table>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        f"""
        <div class="card">
            <h3 style="margin:0 0 8px 0;">Failure budget</h3>
            <div style="color:#CBD5E1;">
                We allow <b>0.6% of verifications</b> to require human review on a 30-day rolling window.
                Above that, the system stops auto-publishing and pages the on-call.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

divider()

c1, c2 = st.columns([1, 1])
with c1:
    st.page_link("pages/2_System_Architecture.py", label="← System Architecture", use_container_width=True)
with c2:
    st.page_link("pages/4_Tech_Stack.py", label="Next: Tech Stack & Why →", use_container_width=True)

footer()
