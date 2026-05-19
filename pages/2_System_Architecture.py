"""System architecture — overview + interactive flowcharts."""
import streamlit as st
import pandas as pd

from components.styles import page_setup, hero, card, divider, footer
from components.mermaid import mermaid

page_setup("System Architecture", icon="🏗️")

hero(
    eyebrow="02 · Architecture",
    title_html='One engine, <span class="gradient-text">fifty configs.</span>',
    subtitle=(
        "Every state's DRE flow is a YAML. The same workflow code drives them all. "
        "AI is called only when deterministic selectors miss."
    ),
)

st.write("")

# ── KPI tiles ────────────────────────────────────────────────────────────
c1, c2, c3 = st.columns(3)
with c1:
    card("Code", "1 workflow engine", pills=[("Same for all 50 states", "cyan")])
with c2:
    card("Config", "50 state YAMLs", pills=[("~80 lines each", "violet")])
with c3:
    card("AI calls / run", "2 hot · 2 cold", pills=[("Fallback only", "mint")])

divider()

# ── Overview text ────────────────────────────────────────────────────────
st.markdown("### What this system actually does")
st.markdown(
    """
    A CRM event triggers the workflow. We fetch the agent's public profile, parse out their
    state and license number, load that state's YAML, and drive the corresponding DRE site.
    We compare the published expiration date against the CRM's record. Match → ledger.
    Mismatch → human review.

    **Adapter-as-data, not adapter-as-code.** New state = new YAML, not a redeploy.
    AI is the fallback path — it fires only when CSS selectors fail or when two
    candidates score within 0.1 of each other on disambiguation.
    """
)

divider()

# ── The 6-stage pipeline (existing visual) ───────────────────────────────
st.markdown("### Six durable stages")

STAGES = [
    ("1", "CRM trigger",     "agent.activated → fetch metadata",               "cyan"),
    ("2", "Profile fetch",   "Playwright opens onereal.com/profile/<slug>",    "cyan"),
    ("3", "Cross-check",     "name + state agree between CRM ↔ profile",       "blue"),
    ("4", "Resolve adapter", "load <state>.yaml; pick browser tier T1–T4",     "violet"),
    ("5", "Drive DRE",       "fill license # → disambiguate → extract expiry", "violet"),
    ("6", "Decide",          "Claude classifies; write ledger or open HITL",   "mint"),
]
TONES = {
    "cyan":   ("rgba(6,182,212,0.10)",  "rgba(6,182,212,0.45)",  "#22D3EE"),
    "blue":   ("rgba(96,165,250,0.10)", "rgba(96,165,250,0.45)", "#60A5FA"),
    "violet": ("rgba(139,92,246,0.10)", "rgba(139,92,246,0.45)", "#A78BFA"),
    "mint":   ("rgba(16,185,129,0.10)", "rgba(16,185,129,0.45)", "#34D399"),
}
html = '<div style="display:grid; grid-template-columns:repeat(6,1fr); gap:8px; margin:6px 0 18px;">'
for n, name, desc, tone in STAGES:
    bg, border, c = TONES[tone]
    html += (
        f'<div style="background:{bg}; border:1px solid {border}; border-radius:10px; '
        f'padding:14px 10px; min-height:140px;">'
        f'<div style="color:{c}; font-weight:700; font-size:1.1rem;">{n}</div>'
        f'<div style="color:#E2E8F0; font-weight:600; font-size:0.92rem; margin-top:4px;">{name}</div>'
        f'<div style="color:#94A3B8; font-size:0.78rem; line-height:1.4; margin-top:6px;">{desc}</div>'
        f'</div>'
    )
html += "</div>"
st.markdown(html, unsafe_allow_html=True)

divider()

# ── Flowchart 1: the full verification cycle ─────────────────────────────
st.markdown("### The verification cycle, end to end")
st.markdown(
    "<span style='color:#94A3B8;'>Yellow nodes are AI calls. Red nodes are HITL paths.</span>",
    unsafe_allow_html=True,
)

mermaid("""
flowchart TB
  classDef ai fill:#7c2d12,stroke:#f59e0b,color:#fef3c7,stroke-width:2px;
  classDef det fill:#0e7490,stroke:#06b6d4,color:#cffafe;
  classDef store fill:#065f46,stroke:#10b981,color:#d1fae5;
  classDef hitl fill:#991b1b,stroke:#ef4444,color:#fee2e2;
  classDef config fill:#5b21b6,stroke:#8b5cf6,color:#ede9fe;

  subgraph TRIG[" 1 · Trigger "]
    direction LR
    A([CRM event: agent.activated]):::det --> B[Fetch agent metadata]:::det
  end

  subgraph PROF[" 2 · Profile + cross-check "]
    direction LR
    C[Fetch onereal.com profile<br/>Playwright]:::det --> D{Profile parsed?}:::det
    D -- yes --> E[Cross-check<br/>name + state]:::det
    D -- no --> X1[Quarantine to HITL]:::hitl
  end

  subgraph DRE[" 3 · Drive DRE "]
    direction LR
    F[(Load &lt;state&gt;.yaml<br/>from adapter registry)]:::config --> G[Pick browser tier<br/>T1 → T2 → T3 → T4]:::det
    G --> H[Drive state DRE<br/>fill license # + search]:::det
    H --> I{Selectors hit?}:::det
    I -- yes --> J[Extract expiration]:::det
    I -- no --> K[Claude Opus<br/>extract from HTML]:::ai
    K --> J
  end

  subgraph DIS[" 4 · Disambiguate "]
    direction LR
    L{Multiple rows?}:::det
    L -- 1 row --> M[Use that row]:::det
    L -- many --> N[Score: type+status+name+city]:::det
    N --> O{Confident?}:::det
    O -- yes --> M
    O -- close margin --> P[Claude Haiku tiebreak]:::ai
    P --> M
  end

  subgraph DEC[" 5 · Decide + persist "]
    direction LR
    Q[Claude Haiku<br/>compare expiration dates]:::ai --> R{Verdict}:::det
    R -- match --> S[(Write ledger row)]:::store
    R -- mismatch --> X2[Quarantine to HITL]:::hitl
    R -- ambiguous --> X2
  end

  TRIG --> PROF
  E --> DRE
  J --> DIS
  M --> Q
  X1 --> U[Slack alert<br/>action buttons resume workflow]:::hitl
  X2 --> U
  S --> T2([Done])
""", height=1100)

divider()

# ── Flowchart 2: the 50-state routing model ──────────────────────────────
st.markdown("### The 50-state routing model")
st.markdown(
    "One profile parser, one engine, **fifty state YAMLs**. The agent's state decides "
    "which YAML is loaded — the engine code never branches per state."
)

mermaid("""
flowchart LR
  classDef state fill:#5b21b6,stroke:#8b5cf6,color:#ede9fe;
  classDef engine fill:#0e7490,stroke:#06b6d4,color:#cffafe;
  classDef dre fill:#7c2d12,stroke:#f59e0b,color:#fef3c7;

  P([onereal.com profile]):::engine -->|state=WA| R1[wa.yaml]:::state
  P -->|state=CA| R2[ca.yaml]:::state
  P -->|state=TX| R3[tx.yaml]:::state
  P -->|...| R4[+ 47 others]:::state

  R1 --> E[[Generic runner<br/>Playwright · Camoufox · Browserbase]]:::engine
  R2 --> E
  R3 --> E
  R4 --> E

  E --> D1[professions.dol.wa.gov]:::dre
  E --> D2[dre.ca.gov]:::dre
  E --> D3[trec.texas.gov]:::dre
  E --> D4[... 47 state DREs]:::dre
""", height=560)

divider()

# ── Flowchart 3: tier escalation ─────────────────────────────────────────
st.markdown("### Tier escalation, per state")
st.markdown(
    "Each state's success rate is tracked. **3 consecutive failures → bump up.** "
    "**3 consecutive successes at a higher tier → bump back down.**"
)

mermaid("""
flowchart LR
  classDef t1 fill:#065f46,stroke:#10b981,color:#d1fae5;
  classDef t2 fill:#5b21b6,stroke:#8b5cf6,color:#ede9fe;
  classDef t3 fill:#7c2d12,stroke:#f59e0b,color:#fef3c7;
  classDef t4 fill:#991b1b,stroke:#ef4444,color:#fee2e2;

  T1[T1 · Playwright<br/>~$0.003 / run]:::t1 -- 3 fails --> T2
  T2[T2 · Camoufox<br/>~$0.006 / run]:::t2 -- 3 fails --> T3
  T3[T3 · Browserbase<br/>~$0.04 / run]:::t3 -- can't bypass --> T4
  T4[T4 · HITL operator<br/>~$5 / run]:::t4

  T2 -- 3 wins --> T1
  T3 -- 3 wins --> T2
""", height=420)

divider()

# ── What lives in a state YAML ───────────────────────────────────────────
st.markdown("### What lives in a state YAML")
st.markdown(
    "One file per state. Selectors are fallback lists. Tier is a single key. "
    "Disambiguation rule is declared, not coded."
)
st.code("""state_code: WA
version: v2
anti_bot_tier: T2
dre:
  search_url: https://professions.dol.wa.gov/s/license-lookup
  flow: multi_page_detail
  disambiguation_required: true
  selectors:
    license_input_label: License Number
    license_input:
      - input#License_Number
      - lightning-input[data-label*='License'] input
    detail_link_in_row:
      - td:first-child a
    detail_expiration:
      - text=/Expiration Date:?\\s*([A-Za-z]+ \\d{1,2},? \\d{4})/i""", language="yaml")

divider()

# ── Routing decisions table ──────────────────────────────────────────────
st.markdown("### Routing decisions per agent")
ROUTES = [
    ("Profile state",   "extracted from onereal.com HTML",       "WA · CA · TX · …"),
    ("Adapter",         "<state>.yaml loaded from registry",     "wa.yaml / ca.yaml / tx.yaml"),
    ("Browser tier",    "router queries per-state success rate", "T1 / T2 / T3 / T4"),
    ("Search strategy", "form-fill OR URL-param navigation",     "per adapter flag"),
    ("Disambiguation",  "score by type + status + name + city",  "1 row pick / many score"),
]
df = pd.DataFrame(ROUTES, columns=["Decision", "Source", "Possible values"])
st.dataframe(df, width="stretch", hide_index=True)

divider()

# ── Four pillars ─────────────────────────────────────────────────────────
st.markdown("### Four pillars")
c1, c2 = st.columns(2)
with c1:
    card("🧱  Durable workflow",
         "Every activity is replayable. Worker crashes don't lose progress.",
         pills=[("Temporal-equivalent", "violet")])
    card("🗂️  Adapter-as-data",
         "Each state's DRE flow is a versioned YAML. New state = drop a file.",
         pills=[("Config, not code", "cyan")])
with c2:
    card("📡  Anti-bot tiering",
         "T1 Playwright → T2 Camoufox → T3 Browserbase → T4 HITL. Auto-promote on failures.",
         pills=[("Self-healing", "mint")])
    card("🤖  AI as fallback",
         "Cheap selectors first. Claude vision only when DOM drifts. Same code path.",
         pills=[("Cheap → smart", "amber")])

st.write("")
nav1, nav2 = st.columns(2)
with nav1:
    st.page_link("pages/1_Problem_Statement.py", label="← Problem", width="stretch")
with nav2:
    st.page_link("pages/3_Workflow_Walkthrough.py", label="Next: Walkthrough →", width="stretch")

footer()
