"""Talk track — minute-by-minute outline."""
import streamlit as st

from components.styles import page_setup, hero, card, divider, footer

page_setup("Talk Track", icon="🎤")

hero(
    eyebrow="09 · Talk track",
    title_html='Minute-by-minute. <span class="gradient-text">Bullets only.</span>',
    subtitle="Live explanation will fill in the detail.",
)

st.write("")

SCHEDULE = [
    ("0:00", "Problem",          "Manual verification doesn't scale. 50 states, ~400 agents/week, mixed anti-bot."),
    ("2:00", "Architecture",     "Six durable stages. CRM → profile → cross-check → adapter → DRE → decide."),
    ("4:00", "Walkthrough",      "Pick one demo agent. Show the live browser drive. Point to the trace."),
    ("8:00", "Tiering + adapters","Anti-bot router auto-promotes. Adapter-as-data, not adapter-as-code."),
    ("10:00","Resilience",       "Failure modes table. Pod crash story. HITL flow."),
    ("12:00","Cost + deployment","Per-call $$ numbers. Multi-AZ + warm-standby topology."),
    ("14:00","Rollout",          "8-week plan, gated by canary. First 10 states by volume."),
    ("15:00","Q&A",              "Top 10 expected questions are in the Q&A page."),
]

for t, label, line in SCHEDULE:
    st.markdown(
        f"""
        <div class="card" style="margin:8px 0; display:flex; gap:18px; align-items:center;">
            <div style="color:#22D3EE; font-family:JetBrains Mono; font-weight:700; min-width:60px;">{t}</div>
            <div>
                <div style="color:#E2E8F0; font-weight:700; font-size:0.95rem;">{label}</div>
                <div style="color:#94A3B8; font-size:0.85rem; margin-top:2px;">{line}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

divider()

st.markdown("### Three things to land")
c1, c2, c3 = st.columns(3)
with c1:
    card("It runs",
         "The working build drives real onereal.com and real state DRE sites. Not a slide deck.",
         pills=[("Live", "mint")])
with c2:
    card("It's honest",
         "Real screenshots, real disambiguation, real HITL routing on failures. No fake matches.",
         pills=[("Transparent", "cyan")])
with c3:
    card("It scales",
         "50 states via 50 YAML files. New state ≈ a half-day, not a redeploy.",
         pills=[("Operable", "violet")])

st.write("")
nav1, nav2 = st.columns(2)
with nav1:
    st.page_link("pages/8_Panel_QA.py", label="← Q&A", width="stretch")
with nav2:
    st.page_link("pages/10_Live_Demo.py", label="Run the live demo →", width="stretch")

footer()
