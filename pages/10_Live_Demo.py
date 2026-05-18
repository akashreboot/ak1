"""Live Demo — the working verification system.

The panel sees:
  1. A choice of three scenarios (happy / mismatch / HITL).
  2. The mock target sites that are live in-process (links to open them in another tab).
  3. A Run button that drives the real workflow, real Playwright, real (or simulated)
     Claude API, and a real SQLite ledger.
  4. A live trace stream as spans emit.
  5. The resulting ledger row and any HITL case.
"""
from __future__ import annotations

import html as _html
import os
import time

import streamlit as st

from components.styles import (
    page_setup, hero, card, divider, footer,
    REAL_CYAN, REAL_INDIGO, REAL_MUTED, REAL_MINT, REAL_AMBER, REAL_RED, REAL_VIOLET, REAL_BLUE,
)
from verifier import db
from verifier.fixtures import SAMPLE_AGENTS
from verifier.mock_sites.manager import start_all, status as mock_status
from verifier.playwright_runner import playwright_available

page_setup("Live Demo", icon="🟢")

# Boot the mock JoinReal + DRE servers (idempotent).
ports = start_all()

hero(
    eyebrow="10 · Live Demo · working build",
    title_html='Watch the verification system <span class="gradient-text">actually run</span>.',
    subtitle=(
        "This is the same workflow code described on pages 2–6, running in-process against local mock "
        "JoinReal + DRE sites. The browser is real Chromium. The ledger is real SQLite. The Claude API "
        "calls are real if you've set ANTHROPIC_API_KEY; otherwise a deterministic mock keeps the demo flowing."
    ),
)

# ── System status ─────────────────────────────────────────────────────────
st.write("")
status_cols = st.columns(5)

with status_cols[0]:
    st.markdown(
        f"""
        <div class="card" style="text-align:center;">
            <div style="color:{REAL_MUTED}; font-size:0.75rem; text-transform:uppercase; letter-spacing:0.12em;">Browser</div>
            <div style="font-size:1.1rem; font-weight:700; color:{REAL_MINT if playwright_available() else REAL_AMBER}; margin-top:6px;">
                {"● Playwright" if playwright_available() else "○ Offline mode"}
            </div>
            <div style="color:{REAL_MUTED}; font-size:0.78rem;">
                {"Real Chromium" if playwright_available() else "pip install playwright"}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with status_cols[1]:
    has_key = bool(os.getenv("ANTHROPIC_API_KEY"))
    st.markdown(
        f"""
        <div class="card" style="text-align:center;">
            <div style="color:{REAL_MUTED}; font-size:0.75rem; text-transform:uppercase; letter-spacing:0.12em;">LLM</div>
            <div style="font-size:1.1rem; font-weight:700; color:{REAL_MINT if has_key else REAL_AMBER}; margin-top:6px;">
                {"● Claude (live)" if has_key else "○ Mocked"}
            </div>
            <div style="color:{REAL_MUTED}; font-size:0.78rem;">
                {"ANTHROPIC_API_KEY set" if has_key else "Set key to go live"}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with status_cols[2]:
    s = mock_status()
    live_mocks = sum(1 for v in s.values() if v["running"])
    st.markdown(
        f"""
        <div class="card" style="text-align:center;">
            <div style="color:{REAL_MUTED}; font-size:0.75rem; text-transform:uppercase; letter-spacing:0.12em;">Mock targets</div>
            <div style="font-size:1.1rem; font-weight:700; color:{REAL_MINT}; margin-top:6px;">● {live_mocks}/4 live</div>
            <div style="color:{REAL_MUTED}; font-size:0.78rem;">JoinReal · CA · TX · HI</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with status_cols[3]:
    metrics = db.metrics_summary()
    st.markdown(
        f"""
        <div class="card" style="text-align:center;">
            <div style="color:{REAL_MUTED}; font-size:0.75rem; text-transform:uppercase; letter-spacing:0.12em;">Ledger</div>
            <div style="font-size:1.4rem; font-weight:800; color:{REAL_CYAN}; margin-top:4px;">{metrics["total_verifications"]}</div>
            <div style="color:{REAL_MUTED}; font-size:0.78rem;">verifications recorded</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with status_cols[4]:
    st.markdown(
        f"""
        <div class="card" style="text-align:center;">
            <div style="color:{REAL_MUTED}; font-size:0.75rem; text-transform:uppercase; letter-spacing:0.12em;">HITL queue</div>
            <div style="font-size:1.4rem; font-weight:800; color:{REAL_AMBER if metrics["hitl_open"] else REAL_MINT}; margin-top:4px;">{metrics["hitl_open"]}</div>
            <div style="color:{REAL_MUTED}; font-size:0.78rem;">open cases</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ── Mock site links ───────────────────────────────────────────────────────
with st.expander("📡  Mock target sites — open them in another tab to inspect", expanded=False):
    site_cols = st.columns(4)
    sites = [
        ("JoinReal directory",  "http://127.0.0.1:8801/directory"),
        ("CA DRE eLicensing",   "http://127.0.0.1:8802/PublicASP/pplinfo.asp"),
        ("TX TREC search",      "http://127.0.0.1:8803/Public/LicenseeNameSearch.aspx"),
        ("HI DRE (CAPTCHA)",    "http://127.0.0.1:8804/license_search"),
    ]
    for i, (label, url) in enumerate(sites):
        with site_cols[i]:
            st.markdown(
                f"""
                <div class="card" style="padding:14px 16px;">
                    <div style="font-weight:600;">{label}</div>
                    <a href="{url}" target="_blank" style="color:{REAL_CYAN}; font-family:JetBrains Mono; font-size:0.82rem;">{url}</a>
                </div>
                """,
                unsafe_allow_html=True,
            )

divider()

# ── Scenario picker ───────────────────────────────────────────────────────
st.markdown("### 1 · Pick a scenario")

scenario_cols = st.columns(len(SAMPLE_AGENTS))
agent_labels = []
for i, a in enumerate(SAMPLE_AGENTS):
    scenario_color = {
        "happy_path":   ("mint",   "✅ Happy path"),
        "mismatch":     ("amber",  "⚠ Mismatch → HITL"),
        "captcha_hitl": ("red",    "🔒 CAPTCHA → HITL"),
    }[a["scenario"]]
    with scenario_cols[i]:
        st.markdown(
            f"""
            <div class="card" style="min-height:160px;">
                <div style="margin-bottom:8px;">
                    <span class="pill pill-{scenario_color[0]}">{scenario_color[1]}</span>
                </div>
                <div style="font-weight:700; font-size:1.05rem;">{a["name"]}</div>
                <div style="color:{REAL_MUTED}; font-size:0.88rem; margin-top:2px;">
                    {a["state"]} · {a["license_no"]} · exp {a["expires_at"]}
                </div>
                <div style="color:#CBD5E1; margin-top:8px; font-size:0.85rem;">{a["description"]}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    agent_labels.append(f"{a['name']} — {a['state']} · {scenario_color[1]}")

selected = st.radio(
    "Scenario",
    options=list(range(len(SAMPLE_AGENTS))),
    format_func=lambda i: agent_labels[i],
    horizontal=True,
    label_visibility="collapsed",
)
selected_agent = SAMPLE_AGENTS[selected]

# ── Run controls ──────────────────────────────────────────────────────────
st.markdown("### 2 · Run the verification")
ctrl1, ctrl2, ctrl3 = st.columns([1, 1, 1])
with ctrl1:
    headed = st.toggle("Show Chromium window", value=True,
                       help="When on, a real Chromium window pops up. Turn off for screenshare-only mode.")
with ctrl2:
    reset = st.toggle("Reset ledger before run", value=False,
                      help="Wipes prior verifications + HITL queue so the demo starts clean.")
with ctrl3:
    run_clicked = st.button("▶  Run verification", use_container_width=True)

# ── Workflow execution ────────────────────────────────────────────────────
st.markdown("### 3 · Live trace")

trace_placeholder = st.empty()
status_placeholder = st.empty()
artifact_placeholder = st.empty()

OWNER_COLORS = {
    "Temporal":       REAL_VIOLET,
    "Agent API":      REAL_BLUE,
    "Playwright":     REAL_CYAN,
    "Stagehand":      REAL_VIOLET,
    "Claude (Haiku)": "#F472B6",
    "Claude":         "#F472B6",
    "Postgres":       REAL_MINT,
    "Slack":          REAL_AMBER,
    "Adapter":        REAL_BLUE,
    "Verify":         REAL_AMBER,
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
        f"  <div style='color:{REAL_MUTED}; font-family:JetBrains Mono; font-size:0.78rem; flex:0 0 64px;'>#{ev.seq:02d}</div>"
        f"  <div style='flex:0 0 130px;'><span class='pill' style='background:{owner_color}22; color:{owner_color}; border:1px solid {owner_color}55;'>{ev.owner}</span></div>"
        f"  <div style='flex:1;'><b>{icon} {_html.escape(ev.title)}</b> {dur}{detail}</div>"
        f"</div>"
    )


if run_clicked:
    if reset:
        db.reset_demo()
        st.toast("Ledger reset.", icon="🧹")

    if headed and not playwright_available():
        st.warning(
            "Playwright isn't installed. Run `pip install playwright && playwright install chromium` "
            "to see a real Chromium window. The demo will continue in offline mode (no visible browser, "
            "but ledger/HITL flows still run end-to-end)."
        )

    # Import here so the page loads even if the workflow module errors
    from verifier.workflow import run_verification

    events_html_acc = ""
    final_status = None
    try:
        for ev in run_verification(
            agent_id=selected_agent["agent_id"],
            headed_browser=headed and playwright_available(),
        ):
            events_html_acc += render_event(ev)
            trace_placeholder.markdown(events_html_acc, unsafe_allow_html=True)
            # Small delay so the panel can read the stream
            time.sleep(0.05)
        # The generator's StopIteration carries the return value, which Python
        # surfaces if we re-run the iterator. We instead just check the DB:
        run = None
    except Exception as e:  # noqa: BLE001
        events_html_acc += render_event(type("X", (), {
            "kind": "error", "owner": "Temporal", "title": f"Workflow crashed: {type(e).__name__}",
            "detail": str(e), "duration_ms": None, "seq": 99,
        })())
        trace_placeholder.markdown(events_html_acc, unsafe_allow_html=True)

    # Final summary
    latest = db.fetch_verifications(limit=1)
    if latest:
        v = dict(latest[0])
        if v["result"] == "match":
            status_placeholder.success(
                f"✅ MATCH · ledger row #{v['id']} · "
                f"CRM {v['crm_expires_at']} = DRE {v['dre_expires_at']}"
            )
        elif v["result"] == "pending_review":
            status_placeholder.warning(
                f"⏸ Quarantined · ledger row #{v['id']} · reason: {v['mismatch_reason']} · "
                f"see HITL Queue page to resolve"
            )
        else:
            status_placeholder.error(f"✗ {v['result']} · row #{v['id']}")

        # Show artifact screenshot if real Playwright ran and produced one
        if v.get("artifact_path"):
            from pathlib import Path
            apath = Path(__file__).resolve().parent.parent / v["artifact_path"]
            if apath.exists():
                with artifact_placeholder.container():
                    st.markdown("##### Latest artifact (Playwright screenshot)")
                    st.image(str(apath), use_container_width=True)

divider()

st.markdown("### What just happened (architecture cross-reference)")
mapping_cols = st.columns(2)
with mapping_cols[0]:
    card(
        "What's REAL in this demo",
        """
        <ul style="margin:0; padding-left:18px; line-height:1.7;">
            <li><b>Playwright Chromium</b> drove a real browser against the mock sites</li>
            <li><b>Saga workflow</b> emitted spans, retried on failure, persisted to SQLite</li>
            <li><b>Selector cache</b> stored working selectors in-memory (Stagehand pattern)</li>
            <li><b>Adapter YAML</b> was loaded at runtime (no code change to swap states)</li>
            <li><b>SQLite ledger</b> received a real row (open the Ledger page)</li>
            <li><b>HITL queue</b> opens real cases on mismatch (open the HITL Queue page)</li>
            <li><b>Claude API</b> was used for extraction/classification (if key set)</li>
        </ul>
        """,
        pills=[("Real", "mint")],
    )
with mapping_cols[1]:
    card(
        "What's standing in for production services",
        """
        <ul style="margin:0; padding-left:18px; line-height:1.7;">
            <li><b>Temporal Cloud</b> → in-process saga engine, same semantics</li>
            <li><b>Browserbase</b> → local Chromium (needed at scale, not for one verify)</li>
            <li><b>Postgres RDS</b> → SQLite (same SQL)</li>
            <li><b>S3</b> → <code>data/screenshots/</code></li>
            <li><b>EventBridge + DynamoDB outbox</b> → Streamlit button</li>
            <li><b>Slack webhook</b> → Slack-styled alert on HITL Queue page</li>
            <li><b>Datadog</b> → Metrics Dashboard page (queries the same SQLite)</li>
        </ul>
        """,
        pills=[("Production stand-ins", "violet")],
    )

st.write("")
nav1, nav2, nav3 = st.columns(3)
with nav1:
    st.page_link("pages/11_Verification_Ledger.py", label="📒  Verification Ledger", use_container_width=True)
with nav2:
    st.page_link("pages/12_HITL_Queue.py", label="👤  HITL Queue", use_container_width=True)
with nav3:
    st.page_link("pages/13_Metrics_Dashboard.py", label="📊  Metrics Dashboard", use_container_width=True)

footer()
