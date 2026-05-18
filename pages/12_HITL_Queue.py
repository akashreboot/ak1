"""Human-in-the-loop queue — the Ops workbench.

Every quarantined verification lands here. The operator gets a 30-second
decision via a Slack-styled alert + 3 inline buttons (Approve CRM /
Approve DRE / Reject). Each click resolves the case AND updates the
verification ledger row — the equivalent of a Temporal signal resuming
the paused workflow.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

import streamlit as st

from components.styles import (
    page_setup, hero, card, divider, footer,
    REAL_CYAN, REAL_MUTED, REAL_AMBER, REAL_MINT, REAL_RED, REAL_INDIGO,
)
from verifier import db
from verifier.trace import now_iso

page_setup("HITL Queue", icon="👤")

hero(
    eyebrow="12 · HITL Queue · Ops workbench",
    title_html='The <span class="gradient-text">1.5%</span> of verifications that need a human.',
    subtitle=(
        "In production these alerts arrive in Slack with inline buttons. Here, the alert renders "
        "in-page with the same buttons — clicking one resolves the case via a workflow signal "
        "and updates the ledger row."
    ),
)

st.write("")

pending = db.fetch_hitl(status="pending")
resolved = db.fetch_hitl(status=None)
resolved = [r for r in resolved if r["status"] != "pending"]

c1, c2, c3 = st.columns(3)
c1.metric("Open cases", len(pending))
c2.metric("Resolved (this session)", len(resolved))
c3.metric("p95 decision time", "≤ 30s", help="Target Ops SLO")

divider()

if not pending:
    st.info("👍  No open cases. Trigger a mismatch or CAPTCHA scenario on the Live Demo page to populate the queue.")
else:
    for case in pending:
        case = dict(case)
        crm = json.loads(case["crm_snapshot"])
        scraped = json.loads(case["scraped_data"])
        dre_data = scraped.get("dre") or scraped.get("dre_attempt") or {}
        joinreal = scraped.get("joinreal") or {}

        # Slack-styled alert
        st.markdown(
            f"""
            <div style="border:1px solid #4A154B; border-left:6px solid #ECB22E; border-radius:10px;
                        padding:0; background:#1A1D21; margin-bottom:18px; box-shadow:0 6px 20px rgba(0,0,0,0.35);">
              <div style="background:#222529; padding:8px 16px; border-bottom:1px solid #2C2F33;
                          display:flex; align-items:center; gap:10px;">
                <div style="width:8px; height:8px; background:#ECB22E; border-radius:50%;"></div>
                <span style="color:#D1D2D3; font-weight:600; font-size:0.92rem;">
                  #agent-verify-ops
                </span>
                <span style="color:#9A9C9F; font-size:0.78rem;">· Real Verify Bot · {case['created_at'][:19].replace('T',' ')}</span>
              </div>
              <div style="padding:14px 16px;">
                <div style="color:#D1D2D3; font-size:0.95rem; margin-bottom:8px;">
                  🟡 <b>Verification needs review</b> · agent <code style='background:#222529; padding:2px 6px; border-radius:4px;'>{case['agent_id']}</code>
                </div>
                <div style="color:#9A9C9F; font-size:0.88rem; line-height:1.55;">
                  {case['summary']}
                </div>
                <table style="margin-top:10px; color:#D1D2D3; font-size:0.86rem; width:100%;">
                  <tr><td style="color:#9A9C9F; width:200px;">Agent</td><td>{case['agent_name']}</td></tr>
                  <tr><td style="color:#9A9C9F;">CRM expiration</td><td>{crm.get('expires_at','—')}</td></tr>
                  <tr><td style="color:#9A9C9F;">Scraped expiration</td><td>{dre_data.get('expiration','—')}</td></tr>
                  <tr><td style="color:#9A9C9F;">JoinReal state</td><td>{joinreal.get('state_listed','—')}</td></tr>
                  <tr><td style="color:#9A9C9F;">License #</td><td><code style='background:#222529; padding:2px 6px; border-radius:4px;'>{crm.get('license_no','')}</code></td></tr>
                </table>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Real working buttons — these resolve the case and update the ledger
        b1, b2, b3, b4 = st.columns(4)
        with b1:
            if st.button(f"✅ Approve CRM value", key=f"approve_crm_{case['id']}", use_container_width=True):
                _resolve(case, "approved_crm", "match", f"Operator approved CRM value ({crm.get('expires_at','')})")
                st.rerun()
        with b2:
            if st.button(f"✅ Approve scraped value", key=f"approve_dre_{case['id']}", use_container_width=True):
                _resolve(case, "approved_scraped", "mismatch", f"Operator approved scraped value ({dre_data.get('expiration','')})")
                st.rerun()
        with b3:
            if st.button(f"🚫 Reject (open ticket)", key=f"reject_{case['id']}", use_container_width=True):
                _resolve(case, "rejected", "mismatch", "Rejected — manual investigation ticket opened")
                st.rerun()
        with b4:
            if st.button(f"⟳ Re-run verification", key=f"rerun_{case['id']}", use_container_width=True):
                _resolve(case, "re_run", "pending_review", "Operator requested re-run")
                st.rerun()


def _resolve(case_row, status: str, ledger_result: str, note: str):
    """Resolve a HITL case + update the verification ledger row (the 'signal').

    In Temporal this is `workflow_handle.signal('hitl_resolved', ...)` —
    the paused workflow receives the message and finishes its final step.
    Here we just update both rows in one transaction.
    """
    ts = now_iso()
    db.resolve_hitl(case_row["id"], status=status, resolver="ops@real.local", note=note, resolved_at=ts)
    # Update the matching verification ledger row by run_id
    with db.connect() as con:
        con.execute(
            "UPDATE verifications SET result=?, mismatch_reason=COALESCE(mismatch_reason,?) WHERE run_id=?",
            (ledger_result, note, case_row["run_id"]),
        )
    st.toast(f"Case #{case_row['id']} → {status}", icon="✅")


if resolved:
    divider()
    st.markdown("### Resolution history (this session)")
    for r in resolved[:10]:
        r = dict(r)
        status_color = {
            "approved_crm":     REAL_MINT,
            "approved_scraped": REAL_AMBER,
            "rejected":         REAL_RED,
            "re_run":           REAL_CYAN,
        }.get(r["status"], REAL_MUTED)
        st.markdown(
            f"""
            <div class="card" style="padding:10px 14px;">
                <div style="display:flex; gap:12px; align-items:center;">
                    <span class="pill" style="background:{status_color}22; color:{status_color}; border:1px solid {status_color}55;">{r['status']}</span>
                    <b>{r['agent_name']}</b>
                    <span style="color:{REAL_MUTED}; font-size:0.85rem;">· {r['agent_id']}</span>
                    <span style="color:{REAL_MUTED}; font-size:0.82rem; margin-left:auto;">{(r['resolved_at'] or '')[:19].replace('T',' ')}</span>
                </div>
                <div style="color:#CBD5E1; font-size:0.85rem; margin-top:4px;">{r['resolution_note'] or ''}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

footer()
