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
c1, c2 = st.columns([1.3, 1])
with c1:
    st.markdown(
        f"""
        <div class="card">
            <pre style="background:transparent; border:none; color:#CBD5E1; font-size:0.86rem; line-height:1.5;">
┌──────────────────── AWS · us-east-1  (primary) ────────────────────┐
│                                                                    │
│  ┌─ API Gateway ─┐    ┌─ EventBridge ─┐    ┌─ DynamoDB outbox ─┐   │
│  │  /webhook/crm │ ──▶│ event bus     │ ──▶│ + poller backstop │   │
│  └───────────────┘    └───────────────┘    └───────────────────┘   │
│                                │                                   │
│                                ▼                                   │
│                       Temporal Cloud (multi-region)                │
│                                │                                   │
│        ┌───────────────────────┼────────────────────────┐          │
│        ▼                       ▼                        ▼          │
│  ┌──────────────┐      ┌──────────────┐         ┌──────────────┐   │
│  │ EKS · AZ-a   │      │ EKS · AZ-b   │         │ EKS · AZ-c   │   │
│  │  workers     │      │  workers     │         │  workers     │   │
│  └──────────────┘      └──────────────┘         └──────────────┘   │
│        │                                                           │
│        ▼  (Browserbase API)                                        │
│  Managed browser cloud · residential proxies · CAPTCHA solver      │
│        │                                                           │
│        ▼                                                           │
│  RDS Postgres (Multi-AZ) · S3 (CRR to us-west-2) · Redis           │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
                                │
                  (passive)     ▼
        ┌──── AWS · us-west-2 (warm standby) ────┐
        │   EKS workers · RDS read replica · ... │
        └────────────────────────────────────────┘
            </pre>
        </div>
        """,
        unsafe_allow_html=True,
    )
with c2:
    card("Why this shape",
         "Stateless workers, durable workflow state in Temporal, durable event state in EventBridge + DynamoDB. "
         "We can lose every pod and not lose work. The warm standby in us-west-2 gives us a one-button DNS cutover "
         "if the primary region degrades.",
         pills=[("Multi-AZ", "blue"), ("Warm DR", "violet")])
    card("CI/CD",
         "<b>GitHub Actions</b> → build → integration tests against a sandbox JoinReal mirror + recorded DRE "
         "fixtures → push image → <b>ArgoCD</b> rolls out to EKS with automated rollback on health-check failure. "
         "Adapter changes are config-only and ship through a separate, faster pipeline.",
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
