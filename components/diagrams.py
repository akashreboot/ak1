"""Reusable diagram + visualization helpers (Plotly, Graphviz)."""
import graphviz
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

from components.styles import (
    REAL_BLUE, REAL_INDIGO, REAL_VIOLET, REAL_CYAN, REAL_MINT, REAL_AMBER, REAL_RED,
)


def architecture_graph() -> graphviz.Digraph:
    g = graphviz.Digraph("arch", format="svg")
    g.attr(
        rankdir="LR",
        bgcolor="transparent",
        fontname="Inter",
        nodesep="0.35",
        ranksep="0.7",
        pad="0.2",
    )
    g.attr(
        "node",
        shape="box",
        style="rounded,filled",
        fontname="Inter",
        fontsize="11",
        color="#3B82F6",
        fillcolor="#141B2D",
        fontcolor="#E6EAF2",
        penwidth="1.4",
    )
    g.attr("edge", color="#475569", fontname="Inter", fontsize="9", fontcolor="#94A3B8")

    # --- Trigger layer ---
    with g.subgraph(name="cluster_trigger") as c:
        c.attr(label="① TRIGGER", style="dashed,rounded", color="#22D3EE", fontcolor="#22D3EE", fontsize="10")
        c.node("crm", "Real CRM\n(agent activated)", fillcolor="#0EA5E9", color="#0EA5E9", fontcolor="white")
        c.node("webhook", "Webhook /\nOutbox Poller", fillcolor="#1E3A8A")
        c.node("bus", "AWS EventBridge\n(event bus)", fillcolor="#1E3A8A")

    # --- Orchestration ---
    with g.subgraph(name="cluster_orch") as c:
        c.attr(label="② ORCHESTRATION", style="dashed,rounded", color="#6366F1", fontcolor="#6366F1", fontsize="10")
        c.node("temporal", "Temporal.io\nWorkflow (durable)", fillcolor="#4F46E5", color="#6366F1", fontcolor="white")
        c.node("api", "Agent API\n(metadata fetch)", fillcolor="#1E293B")

    # --- Browser layer ---
    with g.subgraph(name="cluster_browser") as c:
        c.attr(label="③ BROWSER AUTOMATION", style="dashed,rounded", color="#8B5CF6", fontcolor="#8B5CF6", fontsize="10")
        c.node("stagehand", "Stagehand\n(act / extract / observe)", fillcolor="#7C3AED", color="#8B5CF6", fontcolor="white")
        c.node("playwright", "Playwright\n(deterministic core)", fillcolor="#1E293B")
        c.node("browserbase", "Browserbase\n(managed browsers + proxies)", fillcolor="#1E293B")
        c.node("vision", "Vision Fallback\n(Claude Opus)", fillcolor="#1E293B")

    # --- Targets ---
    with g.subgraph(name="cluster_targets") as c:
        c.attr(label="④ TARGETS", style="dashed,rounded", color="#34D399", fontcolor="#34D399", fontsize="10")
        c.node("joinreal", "JoinReal.com\nDirectory", fillcolor="#065F46", color="#34D399", fontcolor="white")
        c.node("dre", "DRE Adapter Registry\n(50-state, versioned)", fillcolor="#065F46", color="#34D399", fontcolor="white")

    # --- Persistence / Observability ---
    with g.subgraph(name="cluster_data") as c:
        c.attr(label="⑤ DATA + OBSERVABILITY", style="dashed,rounded", color="#F59E0B", fontcolor="#F59E0B", fontsize="10")
        c.node("pg", "PostgreSQL\n(verification ledger)", fillcolor="#1E293B")
        c.node("s3", "S3\n(screenshots, HAR, traces)", fillcolor="#1E293B")
        c.node("dd", "Datadog + Sentry\n(metrics, traces, alerts)", fillcolor="#1E293B")

    # --- Human-in-the-loop ---
    with g.subgraph(name="cluster_hitl") as c:
        c.attr(label="⑥ HUMAN-IN-THE-LOOP", style="dashed,rounded", color="#EF4444", fontcolor="#EF4444", fontsize="10")
        c.node("slack", "Slack alerts\n(quarantine queue)", fillcolor="#7F1D1D", color="#EF4444", fontcolor="white")
        c.node("dash", "Ops Dashboard\n(1-click resolve)", fillcolor="#7F1D1D", color="#EF4444", fontcolor="white")

    # Edges
    g.edge("crm", "webhook", label="event")
    g.edge("webhook", "bus")
    g.edge("bus", "temporal", label="start workflow")
    g.edge("temporal", "api", label="fetch metadata")
    g.edge("temporal", "stagehand", label="navigate + extract")
    g.edge("stagehand", "playwright", label="cached selectors")
    g.edge("stagehand", "vision", label="DOM fail →", style="dashed")
    g.edge("playwright", "browserbase")
    g.edge("vision", "browserbase")
    g.edge("browserbase", "joinreal")
    g.edge("browserbase", "dre")
    g.edge("temporal", "pg", label="ledger")
    g.edge("stagehand", "s3", label="artifacts")
    g.edge("temporal", "dd", label="telemetry")
    g.edge("dd", "slack", label="on failure", style="dashed", color="#EF4444")
    g.edge("pg", "dash")

    return g


def workflow_sequence_graph() -> graphviz.Digraph:
    g = graphviz.Digraph("seq", format="svg")
    g.attr(rankdir="TB", bgcolor="transparent", nodesep="0.25", ranksep="0.35")
    g.attr(
        "node",
        shape="box",
        style="rounded,filled",
        fontname="Inter",
        fontsize="11",
        fillcolor="#141B2D",
        color="#6366F1",
        fontcolor="#E6EAF2",
    )
    g.attr("edge", color="#475569", fontname="Inter", fontsize="9")

    steps = [
        ("s1", "1. CRM emits agent.activated event"),
        ("s2", "2. Temporal workflow starts (idempotent on agent_id)"),
        ("s3", "3. Fetch agent metadata via Agent API"),
        ("s4", "4. Open JoinReal.com directory (Browserbase session)"),
        ("s5", "5. Search by agent name, click matching listing"),
        ("s6", "6. Verify state matches CRM metadata"),
        ("s7", "7. Open California DRE license search"),
        ("s8", "8. Submit license number, open listing"),
        ("s9", "9. Extract license expiration date"),
        ("s10", "10. Compare to CRM → write verification record"),
        ("s11", "11. Emit success or quarantine for HITL"),
    ]
    for sid, label in steps:
        g.node(sid, label)
    for (a, _), (b, _) in zip(steps, steps[1:]):
        g.edge(a, b)
    return g


def resilience_pyramid_fig() -> go.Figure:
    """Defense-in-depth pyramid for failure handling."""
    layers = [
        ("Human review (Slack + Ops Dashboard)", REAL_RED),
        ("Vision-model fallback (Claude Opus)", REAL_AMBER),
        ("AI primitives (Stagehand act/extract/observe)", REAL_VIOLET),
        ("Cached selectors w/ self-healing", REAL_INDIGO),
        ("Deterministic Playwright + state adapters", REAL_BLUE),
        ("Workflow retries + idempotency (Temporal)", REAL_CYAN),
    ]
    n = len(layers)
    fig = go.Figure()
    for i, (label, color) in enumerate(layers):
        width = 0.4 + 0.6 * (i / (n - 1))
        fig.add_trace(
            go.Bar(
                x=[width],
                y=[label],
                orientation="h",
                marker=dict(color=color, line=dict(color="rgba(255,255,255,0.1)", width=1)),
                text=[label],
                textposition="inside",
                insidetextanchor="middle",
                textfont=dict(color="white", size=13, family="Inter"),
                hovertemplate=f"<b>{label}</b><extra></extra>",
                showlegend=False,
            )
        )
    fig.update_layout(
        barmode="stack",
        height=420,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=20, b=10),
        xaxis=dict(visible=False, range=[0, 1.1]),
        yaxis=dict(visible=False),
        showlegend=False,
    )
    return fig


def cost_breakdown_fig() -> go.Figure:
    df = pd.DataFrame({
        "Component": ["Browserbase", "Temporal Cloud", "Claude API (LLM)", "AWS infra (EKS, S3, RDS)", "Proxies + CAPTCHA", "Datadog + Sentry"],
        "Monthly Cost ($)": [1800, 600, 950, 1200, 450, 700],
    })
    fig = px.bar(
        df, x="Monthly Cost ($)", y="Component", orientation="h",
        color="Monthly Cost ($)", color_continuous_scale=[REAL_CYAN, REAL_INDIGO, REAL_VIOLET],
        text="Monthly Cost ($)",
    )
    fig.update_traces(texttemplate="$%{text:,}", textposition="outside")
    fig.update_layout(
        height=380,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter", color="#E6EAF2"),
        coloraxis_showscale=False,
        margin=dict(l=10, r=40, t=20, b=10),
    )
    fig.update_xaxes(showgrid=True, gridcolor="rgba(255,255,255,0.06)")
    fig.update_yaxes(showgrid=False)
    return fig


def throughput_fig() -> go.Figure:
    weeks = list(range(1, 13))
    manual = [42, 41, 40, 43, 44, 41, 45, 42, 43, 44, 45, 42]
    automated = [42, 200, 380, 520, 700, 850, 980, 1100, 1280, 1450, 1620, 1800]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=weeks, y=manual, name="Manual ops capacity",
        mode="lines+markers", line=dict(color=REAL_AMBER, width=3),
        marker=dict(size=8),
    ))
    fig.add_trace(go.Scatter(
        x=weeks, y=automated, name="Automated verifications/week",
        mode="lines+markers", line=dict(color=REAL_CYAN, width=3),
        marker=dict(size=8),
        fill="tozeroy", fillcolor="rgba(34,211,238,0.10)",
    ))
    fig.update_layout(
        height=380,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter", color="#E6EAF2"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        margin=dict(l=10, r=10, t=40, b=10),
        xaxis=dict(title="Week after rollout", gridcolor="rgba(255,255,255,0.06)"),
        yaxis=dict(title="Verifications", gridcolor="rgba(255,255,255,0.06)"),
    )
    return fig


def failure_funnel_fig() -> go.Figure:
    fig = go.Figure(go.Funnel(
        y=[
            "CRM events received",
            "Workflow started",
            "Metadata fetched",
            "JoinReal verified",
            "DRE page loaded",
            "License extracted",
            "Final match recorded",
        ],
        x=[10000, 9985, 9970, 9890, 9790, 9710, 9680],
        textinfo="value+percent initial",
        marker=dict(color=[REAL_CYAN, REAL_BLUE, REAL_INDIGO, REAL_VIOLET, "#A78BFA", REAL_AMBER, REAL_MINT]),
        connector=dict(line=dict(color="rgba(255,255,255,0.1)", width=1)),
    ))
    fig.update_layout(
        height=420,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter", color="#E6EAF2", size=12),
        margin=dict(l=10, r=10, t=20, b=10),
    )
    return fig


def state_coverage_map_fig() -> go.Figure:
    # Stylized US states adapter maturity heatmap
    states = [
        "AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN","IA","KS","KY",
        "LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ","NM","NY","NC","ND",
        "OH","OK","OR","PA","RI","SC","SD","TN","TX","UT","VT","VA","WA","WV","WI","WY"
    ]
    # Maturity: 3 = native adapter, 2 = AI primitives, 1 = vision fallback only
    import random
    random.seed(7)
    # Bias high-volume states to higher maturity
    high = {"CA","TX","FL","NY","NC","AZ","GA","CO","WA","NJ","IL","PA","OH","MA","VA"}
    z = [3 if s in high else random.choice([2, 2, 3, 2, 1]) for s in states]
    df = pd.DataFrame({"state": states, "maturity": z})
    fig = px.choropleth(
        df,
        locations="state",
        locationmode="USA-states",
        color="maturity",
        scope="usa",
        color_continuous_scale=[[0, REAL_AMBER], [0.5, REAL_INDIGO], [1, REAL_CYAN]],
        range_color=[1, 3],
    )
    fig.update_layout(
        height=420,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        geo=dict(bgcolor="rgba(0,0,0,0)", lakecolor="rgba(0,0,0,0)"),
        font=dict(family="Inter", color="#E6EAF2"),
        coloraxis_colorbar=dict(
            title="Adapter<br>maturity",
            tickvals=[1, 2, 3],
            ticktext=["Vision only", "AI primitives", "Native adapter"],
        ),
        margin=dict(l=0, r=0, t=10, b=0),
    )
    return fig
