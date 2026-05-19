"""Workflow walkthrough — one verification, end to end."""
import time
import streamlit as st

from components.styles import (
    page_setup, hero, card, divider, footer,
    REAL_CYAN, REAL_MUTED, REAL_MINT,
)

page_setup("Workflow Walkthrough", icon="🔄")

hero(
    eyebrow="03 · Walkthrough",
    title_html='One verification, <span class="gradient-text">CRM event → ledger row.</span>',
    subtitle="The same 6 stages run for every state. Click Run to animate.",
)

st.write("")

# ── Sample event payload ────────────────────────────────────────────────
sample_agent = {
    "agent_id":    "A-TX-839005",
    "name":        "Aahil Virani",
    "state":       "TX",
    "license_no":  "839005",
    "expires_at":  "2027-06-29",
    "active_since":"2026-05-18T13:42:08Z",
}

with st.expander("📦  Incoming event payload (from CRM)", expanded=False):
    st.json(sample_agent)

# ── 6-stage trace, matches the actual workflow code ─────────────────────
STEPS = [
    ("Receive event",                    "EventBridge → outbox → workflow start",       "Temporal",            0.5),
    ("Fetch agent metadata",             "GET /internal/agents/A-TX-839005",            "CRM API",             0.4),
    ("Fetch onereal profile",            "Playwright opens /profile/aahil-virani",      "Playwright",          1.6),
    ("Cross-check CRM ↔ profile",        "name + state agree · license # = 839005",     "Verify",              0.3),
    ("Resolve adapter + browser tier",   "tx.yaml @ v2 · tier T1 (Playwright)",         "Adapter",             0.3),
    ("Drive TX TREC",                    "URL-param search → detail page",              "DRE / Playwright",    2.4),
    ("Extract expiration",               "Expiration Date: 06/29/2027 → 2027-06-29",    "DRE",                 0.3),
    ("Compare expirations",              "CRM 2027-06-29 == DRE 2027-06-29 ✓",          "Claude (Haiku)",      0.4),
    ("Write ledger",                     "row #ver_88241 · screenshots in S3",          "Postgres + S3",       0.3),
]

OWNER_COLORS = {
    "Temporal":          "#A78BFA",
    "CRM API":           "#60A5FA",
    "Playwright":        "#22D3EE",
    "Verify":            "#FBBF24",
    "Adapter":           "#A78BFA",
    "DRE / Playwright":  "#22D3EE",
    "DRE":               "#22D3EE",
    "Claude (Haiku)":    "#F472B6",
    "Postgres + S3":     "#34D399",
}


def _row(t_label: str, owner: str, name: str, detail: str, accent: str) -> str:
    oc = OWNER_COLORS.get(owner, REAL_CYAN)
    return (
        f"<div style='display:flex; gap:12px; padding:8px 12px; margin:4px 0; "
        f"background:rgba(20,27,45,0.55); border-left:3px solid {accent}; border-radius:8px;'>"
        f"<div style='font-family:JetBrains Mono; color:{REAL_MUTED}; flex:0 0 56px;'>{t_label}</div>"
        f"<div style='flex:0 0 140px;'><span class='pill' "
        f"style='background:{oc}22; color:{oc}; border:1px solid {oc}55;'>{owner}</span></div>"
        f"<div style='flex:1;'><b style='color:#E2E8F0;'>{name}</b>"
        f"<div style='color:{REAL_MUTED}; font-size:0.83rem; font-family:JetBrains Mono; margin-top:2px;'>{detail}</div>"
        f"</div></div>"
    )


run = st.button("▶  Run verification", width="stretch")
trace_slot = st.empty()  # ← FIX: empty() replaces in-place; container() appends

if run:
    progress = st.progress(0)
    accumulated = ""
    elapsed = 0.0
    for i, (name, detail, owner, dur) in enumerate(STEPS, 1):
        time.sleep(dur * 0.4)
        elapsed += dur
        accumulated += _row(f"+{elapsed:.1f}s", owner, f"🟢 {name}", detail, REAL_MINT)
        trace_slot.markdown(accumulated, unsafe_allow_html=True)
        progress.progress(i / len(STEPS))
    st.success(f"✓ Verification complete in {elapsed:.1f}s · MATCH · ledger row #ver_88241")
else:
    # Static preview
    preview = ""
    for name, detail, owner, _ in STEPS:
        preview += _row("—", owner, name, detail, "rgba(99,102,241,0.4)")
    trace_slot.markdown(preview, unsafe_allow_html=True)

divider()

# ── Why this is a workflow, not a script ────────────────────────────────
c1, c2 = st.columns(2)
with c1:
    card(
        "Why this is a workflow, not a script",
        "Each step is a Temporal activity with its own retry policy, timeout, and idempotency "
        "contract. If step 7 fails, steps 1–6 don't rerun.",
        pills=[("Durable", "violet"), ("Replayable", "mint")],
    )
with c2:
    card(
        "Per-step SLOs",
        "p95 budget: 90 seconds end-to-end. Profile fetch ≤ 3s · DRE drive ≤ 5s · ledger write ≤ 100ms. "
        "Spans are emitted per activity to Datadog.",
        pills=[("p95 < 90s", "cyan")],
    )

st.write("")
nav1, nav2 = st.columns(2)
with nav1:
    st.page_link("pages/2_System_Architecture.py", label="← Architecture", width="stretch")
with nav2:
    st.page_link("pages/4_Tech_Stack.py", label="Next: Stack →", width="stretch")

footer()
