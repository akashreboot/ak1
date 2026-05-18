import streamlit as st
from components.styles import page_setup, hero, card, divider, footer, REAL_CYAN, REAL_INDIGO, REAL_MUTED
from components.diagrams import throughput_fig

page_setup("Deployment Strategy", icon="🚀")

hero(
    eyebrow="06 · Deployment Strategy",
    title_html='Always-on. <span class="gradient-text">Always-running.</span> No matter what.',
    subtitle=(
        "The workflow must execute every time a trigger fires. Here's how we deploy, scale, secure, and "
        "release changes safely — without ever dropping an event."
    ),
)

st.write("")

# Topology
st.markdown("### Deployment topology")

# ── Layered topology diagram (styled HTML grid, not ASCII art) ───────────
_TIER_CARD = (
    "background:{bg}; border:1px solid {border}; border-radius:10px; "
    "padding:10px 14px; text-align:center;"
)
_TIER_LABEL = (
    "color:{c}; font-size:0.68rem; text-transform:uppercase; "
    "letter-spacing:0.14em; font-weight:700; margin-bottom:4px;"
)
_TIER_VALUE = "color:#E2E8F0; font-size:0.92rem; font-weight:600;"
_TIER_SUB = "color:#94A3B8; font-size:0.74rem; margin-top:2px;"


def _svc(label, value, sub=None, tone="cyan"):
    tones = {
        "cyan":   ("rgba(6,182,212,0.10)",   "rgba(6,182,212,0.45)",   "#22D3EE"),
        "violet": ("rgba(139,92,246,0.10)",  "rgba(139,92,246,0.45)",  "#A78BFA"),
        "mint":   ("rgba(16,185,129,0.10)",  "rgba(16,185,129,0.45)",  "#34D399"),
        "amber":  ("rgba(245,158,11,0.10)",  "rgba(245,158,11,0.45)",  "#FBBF24"),
        "muted":  ("rgba(100,116,139,0.10)", "rgba(100,116,139,0.40)", "#94A3B8"),
    }
    bg, border, lc = tones[tone]
    sub_html = f'<div style="{_TIER_SUB}">{sub}</div>' if sub else ""
    return (
        f'<div style="{_TIER_CARD.format(bg=bg, border=border)}">'
        f'<div style="{_TIER_LABEL.format(c=lc)}">{label}</div>'
        f'<div style="{_TIER_VALUE}">{value}</div>{sub_html}</div>'
    )


def _arrow(direction="down"):
    glyph = {"down": "▼", "right": "▶"}[direction]
    return (
        f'<div style="text-align:center; color:#64748B; font-size:0.7rem; '
        f'padding:6px 0;">{glyph}</div>'
    )


def _region_wrap(title, inner, accent="cyan", passive=False):
    accents = {"cyan": "#06B6D4", "muted": "#64748B"}
    c = accents[accent]
    op = "0.55" if passive else "1.0"
    suffix = " · passive" if passive else ""
    return (
        f'<div style="border:1px dashed {c}; border-radius:14px; padding:14px 16px; '
        f'margin:8px 0; opacity:{op};">'
        f'<div style="color:{c}; font-size:0.72rem; text-transform:uppercase; '
        f'letter-spacing:0.16em; font-weight:700; margin-bottom:10px;">'
        f'{title}{suffix}</div>{inner}</div>'
    )


c1, c2 = st.columns([1.5, 1])
with c1:
    # Row 1 — ingress
    row1 = (
        '<div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:10px;">'
        + _svc("Ingress",  "API Gateway",        "POST /webhook/crm",          "cyan")
        + _svc("Bus",      "EventBridge",        "agent.activated",            "cyan")
        + _svc("Outbox",   "DynamoDB",           "poller backstop",            "cyan")
        + "</div>"
    )
    # Row 2 — orchestrator
    row2 = (
        '<div style="display:grid; grid-template-columns:1fr; gap:10px;">'
        + _svc("Orchestrator", "Temporal Cloud", "multi-region · signal-resumable", "violet")
        + "</div>"
    )
    # Row 3 — workers (multi-AZ)
    row3 = (
        '<div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:10px;">'
        + _svc("Compute · AZ-a", "EKS workers", "Playwright + Camoufox", "violet")
        + _svc("Compute · AZ-b", "EKS workers", "Playwright + Camoufox", "violet")
        + _svc("Compute · AZ-c", "EKS workers", "Playwright + Camoufox", "violet")
        + "</div>"
    )
    # Row 4 — external
    row4 = (
        '<div style="display:grid; grid-template-columns:1fr 1fr; gap:10px;">'
        + _svc("T3 runner", "Browserbase API", "residential proxies · CAPTCHA solver", "amber")
        + _svc("LLM",        "Anthropic API",   "Haiku classify · Opus vision fallback", "amber")
        + "</div>"
    )
    # Row 5 — storage
    row5 = (
        '<div style="display:grid; grid-template-columns:1.2fr 1fr 0.9fr; gap:10px;">'
        + _svc("Ledger",   "RDS Postgres", "Multi-AZ", "mint")
        + _svc("Artifacts","S3",           "CRR → us-west-2", "mint")
        + _svc("Cache",    "Redis",        "selector cache · session", "mint")
        + "</div>"
    )

    primary = _region_wrap(
        "AWS · us-east-1  (primary)",
        row1 + _arrow() + row2 + _arrow() + row3 + _arrow() + row4 + _arrow() + row5,
        accent="cyan",
    )

    # Passive standby
    standby_inner = (
        '<div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:10px;">'
        + _svc("Compute", "EKS workers",      "warm",                "muted")
        + _svc("Ledger",  "RDS read replica", "promotable",          "muted")
        + _svc("Cutover", "Route 53",         "DNS failover · ≤ 30s", "muted")
        + "</div>"
    )
    standby = _region_wrap(
        "AWS · us-west-2  (warm standby)", standby_inner,
        accent="muted", passive=True,
    )

    st.markdown(primary + _arrow() + standby, unsafe_allow_html=True)

with c2:
    card("Why this shape",
         "Stateless workers, durable workflow state in Temporal, durable event state in "
         "EventBridge + DynamoDB outbox. We can lose every pod and not lose work. The warm "
         "standby in us-west-2 gives us a one-button DNS cutover if the primary region degrades.",
         pills=[("Multi-AZ", "blue"), ("Warm DR", "violet")])
    card("CI/CD",
         "<b>GitHub Actions</b> → build → integration tests against a sandbox JoinReal mirror "
         "+ recorded DRE fixtures → push image → <b>ArgoCD</b> rolls out to EKS with automated "
         "rollback on health-check failure. Adapter changes are config-only and ship through "
         "a separate, faster pipeline.",
         pills=[("GitOps", "cyan"), ("Canary", "mint")])

divider()

# Scaling
st.markdown("### Scaling model")

s1, s2, s3 = st.columns(3)
with s1:
    card(
        "Horizontal: KEDA on queue depth",
        """
        Playwright workers scale on the Temporal task-queue depth, not CPU. We hold p95 queue age under
        5s for the 'verify' task queue. State-specific queues (CA, TX, FL...) have <b>their own concurrency caps</b>
        to avoid hammering a single DRE site.
        """,
        pills=[("KEDA", "violet")],
    )
with s2:
    card(
        "Vertical: per-pod browser pool",
        """
        Each worker pod runs N Playwright contexts (configurable, default 4). Browser sessions are leased
        from Browserbase, so the pod itself stays light. Pod memory caps prevent runaway sessions.
        """,
        pills=[("Pool", "blue")],
    )
with s3:
    card(
        "Adaptive — rate-limit detection",
        """
        If a state's DRE returns 429 / shows a CAPTCHA wall, we reduce that state's concurrency cap for
        15 minutes and route new tasks to a slower lane. The dashboard shows the throttle.
        """,
        pills=[("Adaptive", "mint")],
    )

# Throughput
st.markdown("### Throughput trajectory after rollout (illustrative)")
st.plotly_chart(throughput_fig(), width="stretch", config={"displayModeBar": False})

divider()

# Release strategy
st.markdown("### Releasing changes safely")
r1, r2 = st.columns(2)
with r1:
    card(
        "Code releases (workflow + workers)",
        """
        <ul style="margin:0; padding-left:18px; line-height:1.7;">
            <li><b>Temporal versioning</b> for workflow code — in-flight runs stay on their starting version.</li>
            <li><b>Blue/green deploy</b> for workers; traffic shifts gradually.</li>
            <li>Automated rollback if the success-rate metric drops &gt; 2 σ for 5 minutes.</li>
        </ul>
        """,
        pills=[("Blue/green", "cyan"), ("Rollback", "amber")],
    )
with r2:
    card(
        "Adapter releases (per state)",
        """
        <ul style="margin:0; padding-left:18px; line-height:1.7;">
            <li>Edit YAML → PR → review → merge.</li>
            <li>New version is published to S3, registered in Postgres with a <b>feature flag</b>.</li>
            <li><b>5% canary</b> for that state's traffic; auto-promote on green metrics, auto-rollback otherwise.</li>
            <li>No code release. No restart. State adapters are <b>data</b>.</li>
        </ul>
        """,
        pills=[("Feature flag", "violet"), ("Canary", "mint")],
    )

divider()

# Security & compliance
st.markdown("### Security &amp; compliance")
sec1, sec2, sec3 = st.columns(3)
with sec1:
    card("Secrets",
         "All credentials in <b>AWS Secrets Manager</b>, rotated via Lambda. Workers receive short-lived "
         "IAM tokens. No secrets in env vars, no secrets in container images.",
         pills=[("IAM", "blue")])
with sec2:
    card("PII handling",
         "Agent names / license numbers are encrypted at rest (KMS) and in transit (TLS 1.3). "
         "S3 screenshots are masked for SSN-like patterns before storage. Access is SSO-gated and audit-logged.",
         pills=[("KMS", "violet"), ("Audit", "amber")])
with sec3:
    card("Compliance posture",
         "We retain verification artifacts for the maximum state-required window (7 years in CA). "
         "Lifecycle policies move &gt;90-day data to Glacier. SOC2-ready audit log on every read/write.",
         pills=[("SOC2", "cyan")])

divider()

# Cost & SLA
st.markdown("### SLOs")
slo1, slo2, slo3, slo4 = st.columns(4)
slo1.metric("Event → workflow start", "&lt; 5s", "p95")
slo2.metric("Verification end-to-end", "&lt; 90s", "p95")
slo3.metric("First-pass success", "≥ 99%", "30d rolling")
slo4.metric("HITL rate", "≤ 1.5%", "30d rolling")

st.markdown(
    f"""
    <div style="color:{REAL_MUTED}; font-size:0.88rem; margin-top:8px;">
        SLOs are tracked in Datadog, with error-budget burn-rate alerts at 2% / 5% / 10% consumption.
        On-call is paged on budget consumption, not on raw incident count.
    </div>
    """,
    unsafe_allow_html=True,
)

divider()

c1, c2 = st.columns([1, 1])
with c1:
    st.page_link("pages/5_Resilience.py", label="← Resilience", width="stretch")
with c2:
    st.page_link("pages/7_Knowledge_Guide.py", label="Next: Knowledge Guide →", width="stretch")

footer()
