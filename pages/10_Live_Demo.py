"""Live Demo — runs the V2 verification workflow against REAL onereal.com profiles
and REAL state DRE sites.

3 demo scenarios:
  1. WA · James Nam        — Salesforce Lightning DRE · T2 Camoufox (with fallback)
  2. CA · Chris Porter     — Classic ASP DRE · T1 Playwright
  3. TX · Khary Livingston — TREC license search · T1 Playwright + disambiguation

Safety net for demo day:
  * Practice Mode toggle  — force cached profile + skip live DRE network calls
  * Per-step timeouts     — workflow can't hang the UI
  * Cache-on-success      — first live run caches the profile so subsequent
                            runs survive a network blip
"""
from __future__ import annotations

import html as _html
import os
import time
from pathlib import Path

import streamlit as st

from components.styles import (
    page_setup, hero, card, divider, footer,
    REAL_CYAN, REAL_INDIGO, REAL_MUTED, REAL_MINT, REAL_AMBER, REAL_RED,
    REAL_VIOLET, REAL_BLUE,
)
from verifier import db
from verifier.agent_loader import demo_targets, newly_joined
from verifier.anti_bot_router import (
    ROUTER, TIER_LABELS, camoufox_available, browserbase_available,
)
from verifier.playwright_runner import playwright_available

page_setup("Live Demo · v2", icon="🟢")

hero(
    eyebrow="10 · Live Demo · v2 pipeline",
    title_html='Watch the verification system <span class="gradient-text">actually run</span> against the real internet.',
    subtitle=(
        "Three real onereal.com profiles, three real state license-lookup sites. "
        "The workflow constructs the profile URL from the agent's slug, extracts the license number "
        "from the live profile, picks the right browser tier (T1 Playwright or T2 Camoufox) per "
        "state, disambiguates DRE results when needed, and writes a real SQLite ledger row."
    ),
)

st.write("")

# ── System status row ────────────────────────────────────────────────────
status_cols = st.columns(6)

with status_cols[0]:
    pw_ok = playwright_available()
    st.markdown(
        f"""
        <div class="card" style="text-align:center;">
            <div style="color:{REAL_MUTED}; font-size:0.72rem; text-transform:uppercase; letter-spacing:0.12em;">T1 · Playwright</div>
            <div style="font-size:1.05rem; font-weight:700; color:{REAL_MINT if pw_ok else REAL_AMBER}; margin-top:4px;">
                {'● Ready' if pw_ok else '○ Not installed'}
            </div>
        </div>
        """, unsafe_allow_html=True,
    )

with status_cols[1]:
    cf_ok = camoufox_available()
    st.markdown(
        f"""
        <div class="card" style="text-align:center;">
            <div style="color:{REAL_MUTED}; font-size:0.72rem; text-transform:uppercase; letter-spacing:0.12em;">T2 · Camoufox</div>
            <div style="font-size:1.05rem; font-weight:700; color:{REAL_MINT if cf_ok else REAL_AMBER}; margin-top:4px;">
                {'● Ready' if cf_ok else '○ Fallback to T1'}
            </div>
        </div>
        """, unsafe_allow_html=True,
    )

with status_cols[2]:
    bb_ok = browserbase_available()
    st.markdown(
        f"""
        <div class="card" style="text-align:center;">
            <div style="color:{REAL_MUTED}; font-size:0.72rem; text-transform:uppercase; letter-spacing:0.12em;">T3 · Browserbase</div>
            <div style="font-size:1.05rem; font-weight:700; color:{REAL_AMBER}; margin-top:4px;">
                {'● Live' if bb_ok else '○ Simulated'}
            </div>
        </div>
        """, unsafe_allow_html=True,
    )

with status_cols[3]:
    has_key = bool(os.getenv("ANTHROPIC_API_KEY"))
    st.markdown(
        f"""
        <div class="card" style="text-align:center;">
            <div style="color:{REAL_MUTED}; font-size:0.72rem; text-transform:uppercase; letter-spacing:0.12em;">LLM</div>
            <div style="font-size:1.05rem; font-weight:700; color:{REAL_MINT if has_key else REAL_AMBER}; margin-top:4px;">
                {'● Claude live' if has_key else '○ Mocked'}
            </div>
        </div>
        """, unsafe_allow_html=True,
    )

with status_cols[4]:
    metrics = db.metrics_summary()
    st.markdown(
        f"""
        <div class="card" style="text-align:center;">
            <div style="color:{REAL_MUTED}; font-size:0.72rem; text-transform:uppercase; letter-spacing:0.12em;">Ledger</div>
            <div style="font-size:1.4rem; font-weight:800; color:{REAL_CYAN}; margin-top:2px;">{metrics["total_verifications"]}</div>
        </div>
        """, unsafe_allow_html=True,
    )

with status_cols[5]:
    nj_count = len(newly_joined())
    st.markdown(
        f"""
        <div class="card" style="text-align:center;">
            <div style="color:{REAL_MUTED}; font-size:0.72rem; text-transform:uppercase; letter-spacing:0.12em;">Newly joined</div>
            <div style="font-size:1.4rem; font-weight:800; color:{REAL_AMBER}; margin-top:2px;">{nj_count}</div>
        </div>
        """, unsafe_allow_html=True,
    )

divider()

# ── Demo targets ─────────────────────────────────────────────────────────
st.markdown("### 1 · Pick a demo scenario")

targets = demo_targets()
if not targets:
    st.error("No demo targets configured. Edit `data/demo_agents.json` and re-run.")
    st.stop()

scen_cols = st.columns(len(targets))
selected_idx = st.session_state.get("demo_selected", 0)
labels = []

for i, agent in enumerate(targets):
    state = agent["license"]["state_code"]
    tier = ROUTER.get_tier(state, {"WA": "T2"}.get(state, "T1"))
    tier_color = {"T1": "mint", "T2": "violet", "T3": "amber", "T4": "red"}[tier]
    with scen_cols[i]:
        st.markdown(
            f"""
            <div class="card" style="min-height:180px;">
                <div style="margin-bottom:8px;">
                    <span class="pill pill-{tier_color}">{TIER_LABELS[tier]}</span>
                </div>
                <div style="font-weight:700; font-size:1.1rem;">{agent['name']['full']}</div>
                <div style="color:{REAL_MUTED}; font-size:0.85rem; margin-top:2px;">
                    {agent["license"]["state_full_name"]} · {agent.get('scenario','').replace('_',' ')}
                </div>
                <div style="margin-top:10px;">
                    <a href="{agent['profile_url']}" target="_blank" style="color:{REAL_CYAN}; font-size:0.82rem; font-family:JetBrains Mono;">{agent['profile_url']}</a>
                </div>
                <div style="margin-top:6px;">
                    <span style="color:{REAL_MUTED}; font-size:0.78rem;">DRE: </span>
                    <span style="color:#CBD5E1; font-size:0.82rem;">{agent['license']['state_full_name']}</span>
                </div>
            </div>
            """, unsafe_allow_html=True,
        )
    labels.append(f"{agent['name']['full']} ({state})")

selected_idx = st.radio(
    "Scenario", options=list(range(len(targets))),
    format_func=lambda i: labels[i],
    horizontal=True, label_visibility="collapsed",
    index=selected_idx,
)
selected_agent = targets[selected_idx]

# ── Controls ─────────────────────────────────────────────────────────────
st.markdown("### 2 · Run the verification")
c1, c2, c3, c4 = st.columns([1, 1, 1, 1])
with c1:
    headed = st.toggle("Show browser", value=True, help="Headed Chromium / Firefox window appears.")
with c2:
    practice = st.toggle("Practice mode (cached)", value=False,
                         help="Use cached profile data instead of live network. Demo-safe.")
with c3:
    reset = st.toggle("Reset ledger first", value=False)
with c4:
    run_clicked = st.button("▶  Run verification", width="stretch")

# ── Trace placeholder ────────────────────────────────────────────────────
st.markdown("### 3 · Live trace")

trace_placeholder = st.empty()
status_placeholder = st.empty()
artifact_placeholder = st.empty()


OWNER_COLORS = {
    "Temporal":              REAL_VIOLET,
    "CRM API":               REAL_BLUE,
    "Playwright (onereal)":  REAL_CYAN,
    "DRE":                   REAL_CYAN,
    "Adapter":               REAL_BLUE,
    "Anti-bot router":       REAL_VIOLET,
    "Verify":                REAL_AMBER,
    "Claude (Haiku)":        "#F472B6",
    "Claude":                "#F472B6",
    "Postgres":              REAL_MINT,
    "Slack":                 REAL_AMBER,
}


def render_event(ev) -> str:
    color = {
        "start":    REAL_VIOLET, "activity": REAL_BLUE, "ok":    REAL_MINT,
        "retry":    REAL_AMBER,  "error":    REAL_RED,  "end":   REAL_VIOLET,
        "warn":     REAL_AMBER,  "hitl":     REAL_AMBER,"replay":REAL_MUTED,
    }.get(ev.kind, REAL_INDIGO)
    icon = {
        "start": "🚀", "activity": "▶", "ok": "✓", "retry": "⟳", "error": "✗",
        "end": "🏁", "warn": "⚠", "hitl": "👤", "replay": "⟲",
    }.get(ev.kind, "•")
    owner_color = OWNER_COLORS.get(ev.owner, REAL_INDIGO)
    dur = f"<span style='color:{REAL_MUTED}; font-family:JetBrains Mono; font-size:0.78rem;'>· {ev.duration_ms}ms</span>" if ev.duration_ms else ""
    detail = (
        f"<div style='color:{REAL_MUTED}; font-size:0.82rem; font-family:JetBrains Mono; margin-top:4px;'>{_html.escape(str(ev.detail))}</div>"
        if ev.detail else ""
    )
    return (
        f"<div style='display:flex; gap:14px; padding:8px 12px; margin:4px 0; "
        f"background:rgba(20,27,45,0.55); border-left:3px solid {color}; border-radius:8px;'>"
        f"  <div style='color:{REAL_MUTED}; font-family:JetBrains Mono; font-size:0.78rem; flex:0 0 60px;'>#{ev.seq:02d}</div>"
        f"  <div style='flex:0 0 160px;'><span class='pill' style='background:{owner_color}22; color:{owner_color}; border:1px solid {owner_color}55;'>{ev.owner}</span></div>"
        f"  <div style='flex:1;'><b>{icon} {_html.escape(ev.title)}</b> {dur}{detail}</div>"
        f"</div>"
    )


if run_clicked:
    if reset:
        db.reset_demo()
        st.toast("Ledger reset.", icon="🧹")
    if not practice and playwright_available():
        st.info(
            "🌐  **Live mode.** A real browser window will open and drive the actual DRE site. "
            "Two screenshots are captured: the landing page (proof the project opened it) and "
            "the license detail page (proof of data extraction). If reCAPTCHA appears the workflow "
            "fails fast and routes to HITL — no human wait."
        )
    if not playwright_available() and not practice:
        st.warning(
            "Playwright isn't installed. The workflow will fall back to the cached profile and "
            "deterministic results. Install Playwright (`pip install playwright && python -m "
            "playwright install chromium`) to see real browser automation.",
        )

    from verifier.workflow import run_verification

    events_html_acc = ""
    try:
        for ev in run_verification(
            agent_id=selected_agent["agent_id"],
            headed_browser=headed,
            practice_mode=practice,
        ):
            events_html_acc += render_event(ev)
            trace_placeholder.markdown(events_html_acc, unsafe_allow_html=True)
            time.sleep(0.04)
    except Exception as e:  # noqa: BLE001
        events_html_acc += (
            f"<div style='padding:8px 12px; background:rgba(239,68,68,0.15); border-left:3px solid {REAL_RED}; border-radius:8px;'>"
            f"<b>✗ Workflow crashed:</b> {_html.escape(str(e))}</div>"
        )
        trace_placeholder.markdown(events_html_acc, unsafe_allow_html=True)

    # Final summary
    latest = db.fetch_verifications(limit=1)
    if latest:
        v = dict(latest[0])
        if v["result"] == "match":
            status_placeholder.success(f"✅ MATCH · ledger row #{v['id']} · CRM {v['crm_expires_at']} = DRE {v['dre_expires_at']}")
        elif v["result"] == "pending_review":
            status_placeholder.warning(
                f"⏸ Quarantined · ledger row #{v['id']} · reason: {v['mismatch_reason']} · "
                f"see HITL Queue page to resolve"
            )
        else:
            status_placeholder.error(f"✗ {v['result']} · row #{v['id']}")

        # Parse all artifacts (profile screenshot + DRE screenshots)
        raw = v.get("artifact_path") or ""
        artifacts = []
        if raw:
            s = str(raw).strip()
            if s.startswith("["):
                try:
                    import json as _json
                    artifacts = _json.loads(s)
                except Exception:
                    artifacts = [s]
            else:
                artifacts = [s]
        project_root = Path(__file__).resolve().parent.parent
        if artifacts:
            with artifact_placeholder.container():
                st.markdown(f"##### Artifacts captured · {len(artifacts)} screenshot(s)")
                cols = st.columns(min(len(artifacts), 3))
                for i, p in enumerate(artifacts):
                    apath = project_root / p
                    if apath.exists():
                        label = Path(p).stem.replace("-", " ").replace("_", " ").title()
                        cols[i % 3].image(str(apath), caption=label, width="stretch")

divider()

# ── Architecture cross-reference ────────────────────────────────────────
st.markdown("### What this demo proves about the architecture")
a, b = st.columns(2)
with a:
    card(
        "What's REAL right now",
        """
        <ul style="margin:0; padding-left:18px; line-height:1.75;">
            <li>Real <b>Playwright Chromium</b> against real <b>onereal.com</b> profile</li>
            <li>Real Playwright/<b>Camoufox</b> against real state DRE sites</li>
            <li>Real <b>Claude API</b> (Opus extraction, Haiku comparison) if key is set</li>
            <li>Real <b>SQLite ledger</b> (open <code>data/ledger.db</code> in any tool)</li>
            <li>Real <b>YAML adapters</b> for CA, TX, WA (versioned, swappable)</li>
            <li>Real <b>disambiguation</b> (multi-field confidence + AI tiebreak)</li>
            <li>Real <b>anti-bot router</b> with auto-promotion on repeated failure</li>
            <li>Real <b>HITL queue</b> with workflow signals</li>
        </ul>
        """,
        pills=[("Real", "mint")],
    )
with b:
    card(
        "Production stand-ins (architecture identical)",
        """
        <ul style="margin:0; padding-left:18px; line-height:1.75;">
            <li><b>Temporal Cloud</b> → in-process saga engine</li>
            <li><b>Browserbase (T3)</b> → simulated (narrated in trace as 'T3 simulated')</li>
            <li><b>Postgres RDS</b> → SQLite (same SQL)</li>
            <li><b>S3 artifacts</b> → <code>data/screenshots/</code></li>
            <li><b>EventBridge + outbox</b> → Streamlit button + agents.json</li>
            <li><b>Slack webhook</b> → in-app Slack-styled alert with real buttons</li>
            <li><b>Datadog</b> → Metrics Dashboard reading SQLite</li>
        </ul>
        """,
        pills=[("Production stand-ins", "violet")],
    )

st.write("")
nav1, nav2, nav3, nav4 = st.columns(4)
with nav1:
    st.page_link("pages/14_Newly_Joined.py", label="🆕  Newly Joined", width="stretch")
with nav2:
    st.page_link("pages/11_Verification_Ledger.py", label="📒  Ledger", width="stretch")
with nav3:
    st.page_link("pages/12_HITL_Queue.py", label="👤  HITL Queue", width="stretch")
with nav4:
    st.page_link("pages/15_Adapter_Registry.py", label="🗂️  Adapter Registry", width="stretch")

footer()
