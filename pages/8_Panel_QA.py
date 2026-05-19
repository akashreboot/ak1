"""Q&A — anticipated questions, brief answers."""
import streamlit as st

from components.styles import page_setup, hero, card, divider, footer

page_setup("Q&A", icon="🎯")

hero(
    eyebrow="08 · Q&A",
    title_html='Anticipated questions, <span class="gradient-text">brief answers.</span>',
    subtitle="The top 10. Longer answers in the working build pages.",
)

st.write("")

QA = [
    ("Why not a single Computer-Use agent for every site?",
     "Cost. ~$0.50/call × 50K calls/month = $300K/year. Deterministic selectors do 95% of the work at ~$0.005/call. AI is a fallback, not the default."),
    ("What happens when a state DRE changes its HTML?",
     "Selectors miss → Claude-vision fallback extracts the value → adapter version bump after canary. Live trace shows which path was used."),
    ("Cloudflare blocks Playwright. Now what?",
     "Auto-router promotes the state's tier (T1 → T2 Camoufox → T3 Browserbase). After 3 wins at the higher tier, it auto-demotes."),
    ("How is this not 50 hand-written scrapers?",
     "Adapter-as-data. Each state's flow is a YAML with selectors + flow type. The same workflow engine drives all 50. New state ≈ new YAML."),
    ("What's the durability story?",
     "Temporal saga. Every activity is replayable; a pod can die mid-run and the workflow resumes from the last successful step on a new pod."),
    ("What's the HITL UX?",
     "Slack-styled alert with Approve / Reject / Reassign buttons. Buttons resolve a durable workflow signal — operator action moves the saga forward."),
    ("How do you handle disambiguation?",
     "Scored: license_type (40%), status=Active (20%), name token similarity (30%), city/geography (10%). ≥ 0.85 + margin ≥ 0.10 = confident pick. Lower = LLM tiebreak. Below 0.55 = HITL."),
    ("What's the cost per verification?",
     "≈ $0.02 at steady state (T1 majority). LLM spend < $0.005/agent. HITL is the biggest variable — 2.5% escalation rate is the design target."),
    ("Single point of failure?",
     "None we can't survive: workers are stateless + multi-AZ; ledger is RDS Multi-AZ with read replica; event bus has DynamoDB outbox; warm standby in second region."),
    ("Can this expand beyond verification?",
     "Yes — the same ledger drives a 'license expiring in 30 days' reminder pipeline (Stage 2). The adapter-as-data pattern generalizes to any browser-driven compliance check."),
]

for q, a in QA:
    st.markdown(
        f"""
        <div class="card" style="margin:8px 0;">
            <div style="color:#22D3EE; font-weight:700; font-size:0.95rem;">{q}</div>
            <div style="color:#CBD5E1; font-size:0.88rem; margin-top:6px; line-height:1.55;">{a}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

divider()

st.markdown("### Three sentences I'll keep coming back to")
c1, c2, c3 = st.columns(3)
with c1:
    card("Cheap when stable",
         "Deterministic selectors are the default. AI only when the DOM moves.",
         pills=[("Cost-aware", "cyan")])
with c2:
    card("Data, not code",
         "Adapter-as-data. New state = new YAML, not a redeploy.",
         pills=[("Operability", "mint")])
with c3:
    card("HITL is a feature",
         "Quarantine path is first-class. Slack with action buttons.",
         pills=[("UX", "amber")])

st.write("")
nav1, nav2 = st.columns(2)
with nav1:
    st.page_link("pages/7_Knowledge_Guide.py", label="← Knowledge", width="stretch")
with nav2:
    st.page_link("pages/9_Presentation_Script.py", label="Next: Talk track →", width="stretch")

footer()
