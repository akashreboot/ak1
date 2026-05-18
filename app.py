"""
Real · Agent Verification System — Presentation Deck

Run:
    streamlit run app.py
"""
import streamlit as st

from components.styles import page_setup, hero, stat_card, card, divider, footer, REAL_CYAN, REAL_MUTED

page_setup("Agent Verification System", icon="🏠")

st.sidebar.page_link("app.py", label="Home", icon="🏠")
st.sidebar.page_link("pages/1_Problem_Statement.py", label="Problem Statement", icon="📋")
st.sidebar.page_link("pages/2_System_Architecture.py", label="System Architecture", icon="🏗️")
st.sidebar.page_link("pages/3_Workflow_Walkthrough.py", label="Workflow Walkthrough", icon="🔄")
st.sidebar.page_link("pages/4_Tech_Stack.py", label="Tech Stack & Why", icon="🛠️")
st.sidebar.page_link("pages/5_Resilience.py", label="Resilience & Failures", icon="🛡️")
st.sidebar.page_link("pages/6_Deployment.py", label="Deployment Strategy", icon="🚀")
st.sidebar.page_link("pages/7_Knowledge_Guide.py", label="Knowledge Guide", icon="📚")
st.sidebar.page_link("pages/8_Panel_QA.py", label="Panel Q&A", icon="🎯")
st.sidebar.page_link("pages/9_Presentation_Script.py", label="Presentation Script", icon="🎤")
st.sidebar.markdown("---")
st.sidebar.markdown("**Working build · v2**")
st.sidebar.page_link("pages/10_Live_Demo.py", label="Live Demo", icon="🟢")
st.sidebar.page_link("pages/14_Newly_Joined.py", label="Newly Joined (20)", icon="🆕")
st.sidebar.page_link("pages/11_Verification_Ledger.py", label="Verification Ledger", icon="📒")
st.sidebar.page_link("pages/12_HITL_Queue.py", label="HITL Queue", icon="👤")
st.sidebar.page_link("pages/13_Metrics_Dashboard.py", label="Metrics Dashboard", icon="📊")
st.sidebar.page_link("pages/15_Adapter_Registry.py", label="Adapter Registry", icon="🗂️")

with st.sidebar:
    st.markdown(
        f"""
        <div style="margin-top:24px; padding-top:18px; border-top:1px solid rgba(255,255,255,0.06);">
            <div style="color:{REAL_MUTED}; font-size:0.78rem; text-transform:uppercase; letter-spacing:0.15em;">Audience</div>
            <div style="margin-top:6px; font-weight:600;">Mark Hinojosa</div>
            <div style="color:{REAL_MUTED}; font-size:0.82rem;">Mgr, Engineering — AI & Automation @ Real</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# Hero
hero(
    eyebrow="Automation Business Case · Real",
    title_html='An <span class="gradient-text">autonomous, self-healing</span><br/>Agent Verification System for all <span class="glow-text">50 U.S. states</span>',
    subtitle=(
        "Every week, hundreds of new Real agents activate in the CRM. Each one must be cross-verified against "
        "JoinReal.com and their state's Department of Real Estate. This deck proposes a durable, "
        "AI-augmented browser automation system that does it in &lt; 90 seconds per agent — with graceful "
        "degradation when the web changes underneath us."
    ),
)

st.write("")

# Hero KPIs
c1, c2, c3, c4 = st.columns(4)
with c1: stat_card("&lt; 90s", "Per-agent verification")
with c2: stat_card("99.4%", "Target first-pass success")
with c3: stat_card("50 / 50", "U.S. states covered")
with c4: stat_card("24 / 7", "Always-on event-driven")

divider()

# Why this matters
left, right = st.columns([1.1, 1])

with left:
    st.markdown("### Why this matters for Real")
    card(
        "Compliance is a hard floor, not a nice-to-have",
        "Real publishes agents to JoinReal.com under their licensing state. An expired or mismatched license is a "
        "regulatory risk in every state Real operates in. Today this work is partially manual — the cost scales "
        "linearly with hiring, and the failure mode is invisible until an audit.",
        pills=[("Compliance", "red"), ("Regulatory risk", "amber")],
    )
    card(
        "The volume curve is non-linear",
        "Real onboards across all 50 states. License formats, DRE search flows, and result layouts differ in every "
        "single one. Writing 50 brittle scrapers and maintaining them is not a strategy — it's a tax that grows "
        "with every UI change.",
        pills=[("Scale", "blue"), ("Maintenance debt", "violet")],
    )
    card(
        "AI changes the economics of browser automation",
        "In 2026 we don't have to pick between deterministic scripts and a research project. Stagehand, Browser-Use, "
        "and Claude vision let us write <em>intent-level</em> automations: deterministic selectors when the page is "
        "stable, AI fallback the moment it isn't — with the same workflow code.",
        pills=[("AI-native", "cyan"), ("Self-healing", "mint")],
    )

with right:
    st.markdown("### What you'll see in this deck")
    st.markdown(
        f"""
        <div class="card">
            <ol style="line-height:1.9; color:#CBD5E1; padding-left:18px;">
                <li><b style="color:{REAL_CYAN}">Problem Statement</b> — Real's onboarding flow, mapped end-to-end</li>
                <li><b style="color:{REAL_CYAN}">System Architecture</b> — 6 layers, one durable workflow</li>
                <li><b style="color:{REAL_CYAN}">Workflow Walkthrough</b> — interactive trace of a single verification</li>
                <li><b style="color:{REAL_CYAN}">Tech Stack &amp; Why</b> — every choice + the alternatives I rejected</li>
                <li><b style="color:{REAL_CYAN}">Resilience &amp; Failures</b> — UI change? CAPTCHA? Outage? Here's the plan.</li>
                <li><b style="color:{REAL_CYAN}">Deployment</b> — guaranteed execution per trigger, multi-region</li>
                <li><b style="color:{REAL_CYAN}">Knowledge Guide</b> — what each tool does &amp; when you'd pick it</li>
                <li><b style="color:{REAL_CYAN}">Panel Q&amp;A</b> — 20 questions I'm prepared for</li>
                <li><b style="color:{REAL_CYAN}">Presentation Script</b> — minute-by-minute talk track</li>
            </ol>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        f"""
        <div class="card">
            <h3 style="margin-top:0;">Three things to remember</h3>
            <div style="color:#CBD5E1; line-height:1.7;">
                <div style="margin-bottom:8px;">🧱 <b>Durable workflow</b> — every step is replayable. A pod can die mid-run; the verification still completes.</div>
                <div style="margin-bottom:8px;">🤖 <b>AI as a fallback</b>, not the default — cheap selectors first, smart vision when the world changes.</div>
                <div>👀 <b>Humans see what matters</b> — only ambiguous verifications hit the Ops queue. Everything else is silent success.</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

divider()

st.markdown("### Navigate the deck →")
nav1, nav2, nav3 = st.columns(3)
with nav1:
    st.page_link("pages/1_Problem_Statement.py", label="📋  Start with the problem", width="stretch")
with nav2:
    st.page_link("pages/2_System_Architecture.py", label="🏗️  Jump to architecture", width="stretch")
with nav3:
    st.page_link("pages/9_Presentation_Script.py", label="🎤  Read the talk track", width="stretch")

footer()
