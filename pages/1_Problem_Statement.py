import streamlit as st
from components.styles import page_setup, hero, card, divider, footer, REAL_CYAN, REAL_MUTED, REAL_INDIGO

page_setup("Problem Statement", icon="📋")

hero(
    eyebrow="01 · The Problem",
    title_html='<span class="gradient-text">Many agents.</span> 50 states. Zero room for a missed license.',
    subtitle=(
        "Real onboards new agents continuously, across all 50 U.S. states. Every activation triggers a chain of "
        "verifications that today is partially manual and entirely brittle. Here's the exact business case I'm solving."
    ),
)

st.write("")

# Re-stated problem
left, right = st.columns([1.05, 1])
with left:
    st.markdown("### The business case, as stated")
    st.markdown(
        f"""
        <div class="card">
            <div style="margin-bottom:10px;">
                <span class="pill pill-cyan">Source</span>
                <span class="pill pill-blue">Real · Automation Business Case</span>
            </div>
            <ul style="line-height:1.8; color:#CBD5E1;">
                <li>Real processes <b>many new agent onboardings weekly</b> across all 50 U.S. states.</li>
                <li>When onboarding is complete, agents become active in the <b>CRM</b> and are added to the <b>JoinReal.com directory</b> under their licensing state — and need to be verified.</li>
                <li>Additionally, each agent's <b>license expiration date</b> must be retrieved from their state's <b>Department of Real Estate</b> website to ensure it matches the CRM.</li>
                <li>The solution must <b>operate autonomously</b> with minimal human intervention and be <b>resilient to UI changes</b> and <b>missing data</b>.</li>
            </ul>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("### Three things that make this hard")
    card(
        "1 · No API for the truth source",
        "JoinReal and most state DREs are <b>HTML-only</b>. No webhook, no JSON, no SLA. The system has to drive a real browser, "
        "and the browser has to look like a human.",
        pills=[("HTML scraping", "violet")],
    )
    card(
        "2 · 50 different DRE flows",
        "California's eLicensing form is not Arizona's. Search params, result tables, expiration field labels — every state is "
        "its own micro-project. And every state's website changes on its own schedule.",
        pills=[("Heterogeneity", "amber")],
    )
    card(
        "3 · Verification is mostly silent — until it isn't",
        "99% of agents are legitimate. The system needs to be <b>cheap and fast in the happy path</b>, and <b>loud and precise</b> "
        "when something is off (mismatched state, expired license, wrong name).",
        pills=[("Signal vs noise", "mint")],
    )

with right:
    st.markdown("### The 11 events I have to handle")
    events = [
        ("Trigger", "Agent pays onboarding fee → becomes active in CRM"),
        ("Extract", "Call Agent API → JSON (name, state, license #, expiration)"),
        ("Navigate", "Open JoinReal.com agent directory"),
        ("Action", "Type agent name into 'Find Agent by Name'"),
        ("Action", "Click matching listing in search results"),
        ("Verify", "Confirm state on JoinReal matches CRM"),
        ("Navigate", "Open the state DRE license search (CA assumed)"),
        ("Action", "Submit agent's license number"),
        ("Action", "Open the correct DRE listing"),
        ("Extract", "Pull license expiration date from listing"),
        ("Verify", "Match expiration to CRM metadata → record result"),
    ]
    for i, (kind, label) in enumerate(events, start=1):
        kind_color = {
            "Trigger": "cyan", "Extract": "blue", "Navigate": "violet",
            "Action": "mint", "Verify": "amber",
        }[kind]
        st.markdown(
            f"""
            <div class="step-row">
                <div class="step-num">{i}</div>
                <div>
                    <span class="pill pill-{kind_color}">{kind}</span>
                    <div style="margin-top:4px; color:#E6EAF2;">{label}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

divider()

# Assumptions
st.markdown("### Assumptions, limitations, and what I'd want clarified before building")

a1, a2, a3 = st.columns(3)
with a1:
    card(
        "Assumptions I'm making",
        """
        <ul style="margin:0; padding-left:18px;">
            <li>CRM can emit a webhook or be polled (Salesforce / Chime).</li>
            <li>Agent API returns license # and expiration in a stable schema.</li>
            <li>JoinReal listings are publicly searchable without auth.</li>
            <li>DRE sites are accessible from US IP ranges with reasonable rate limits.</li>
            <li>Volume is hundreds–low thousands per week, not millions per hour.</li>
        </ul>
        """,
        pills=[("Assumptions", "blue")],
    )
with a2:
    card(
        "Known limitations",
        """
        <ul style="margin:0; padding-left:18px;">
            <li>A handful of DREs (e.g. <em>Hawaii, Mississippi</em>) gate license search behind CAPTCHAs.</li>
            <li>Some states delay license updates by 24–72h after renewal — false negatives possible.</li>
            <li>Name matching is fuzzy (DBA, middle initials). Need a confidence threshold.</li>
            <li>JoinReal pagination has soft limits — name collisions in large states need disambiguation.</li>
        </ul>
        """,
        pills=[("Limitations", "amber")],
    )
with a3:
    card(
        "Questions I'd ask Mark on day 1",
        """
        <ol style="margin:0; padding-left:18px;">
            <li>Does the CRM support outbound webhooks today, or do we need an outbox poller?</li>
            <li>What's the existing definition of "verified" — boolean, or a state machine?</li>
            <li>Where should verification results land — back into the CRM, into a separate ledger, both?</li>
            <li>SLA expectations: minutes after onboarding, end-of-day, weekly batch?</li>
            <li>Who owns the on-call rotation for HITL exceptions today?</li>
        </ol>
        """,
        pills=[("Open questions", "cyan")],
    )

divider()

st.markdown(
    f"""
    <div class="quote-block">
        In short: this is a <b>silent compliance loop</b>. The win isn't speed for its own sake — it's
        catching the 0.6% of agents whose CRM state and license reality don't match,
        <span style="color:{REAL_CYAN};">before</span> a regulator does.
    </div>
    """,
    unsafe_allow_html=True,
)

st.write("")
c1, c2 = st.columns([1, 1])
with c1:
    st.page_link("app.py", label="← Home", use_container_width=True)
with c2:
    st.page_link("pages/2_System_Architecture.py", label="Next: System Architecture →", use_container_width=True)

footer()
