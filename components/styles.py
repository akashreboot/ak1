"""Shared styling and reusable UI components for the Real Agent Verification System deck."""
from __future__ import annotations

import streamlit as st


REAL_NAVY = "#0B0F1A"
REAL_NAVY_2 = "#141B2D"
REAL_BLUE = "#3B82F6"
REAL_INDIGO = "#6366F1"
REAL_VIOLET = "#8B5CF6"
REAL_CYAN = "#22D3EE"
REAL_MINT = "#34D399"
REAL_AMBER = "#F59E0B"
REAL_RED = "#EF4444"
REAL_TEXT = "#E6EAF2"
REAL_MUTED = "#94A3B8"


GLOBAL_CSS = f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600&display=swap');

    html, body, [class*="css"], .stApp {{
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
        color: {REAL_TEXT};
    }}

    .stApp {{
        background:
            radial-gradient(1200px 600px at 10% -10%, rgba(99,102,241,0.18), transparent 60%),
            radial-gradient(900px 500px at 90% 0%, rgba(34,211,238,0.12), transparent 60%),
            radial-gradient(700px 700px at 50% 110%, rgba(139,92,246,0.10), transparent 60%),
            linear-gradient(180deg, {REAL_NAVY} 0%, #070A12 100%);
    }}

    code, pre, .stCodeBlock {{
        font-family: 'JetBrains Mono', monospace !important;
    }}

    h1, h2, h3, h4 {{
        font-family: 'Inter', sans-serif !important;
        font-weight: 800 !important;
        letter-spacing: -0.02em;
    }}

    h1 {{ font-size: 2.6rem !important; line-height: 1.1 !important; }}
    h2 {{ font-size: 1.9rem !important; line-height: 1.2 !important; }}
    h3 {{ font-size: 1.35rem !important; line-height: 1.25 !important; }}

    .gradient-text {{
        background: linear-gradient(90deg, {REAL_BLUE}, {REAL_INDIGO}, {REAL_VIOLET});
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }}

    .glow-text {{
        background: linear-gradient(90deg, {REAL_CYAN}, {REAL_INDIGO});
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }}

    .hero-eyebrow {{
        display: inline-block;
        padding: 6px 14px;
        border: 1px solid rgba(99,102,241,0.4);
        background: rgba(99,102,241,0.08);
        border-radius: 999px;
        font-size: 0.78rem;
        font-weight: 600;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: {REAL_CYAN};
        margin-bottom: 18px;
    }}

    .card {{
        background: linear-gradient(180deg, rgba(20,27,45,0.85) 0%, rgba(11,15,26,0.85) 100%);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 16px;
        padding: 22px 24px;
        margin-bottom: 14px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.25);
        transition: transform .25s ease, border-color .25s ease, box-shadow .25s ease;
    }}
    .card:hover {{
        transform: translateY(-2px);
        border-color: rgba(99,102,241,0.45);
        box-shadow: 0 18px 40px rgba(99,102,241,0.15);
    }}

    .stat-card {{
        background: linear-gradient(135deg, rgba(99,102,241,0.18), rgba(34,211,238,0.08));
        border: 1px solid rgba(99,102,241,0.35);
        border-radius: 18px;
        padding: 20px;
        text-align: center;
    }}
    .stat-number {{
        font-size: 2.4rem;
        font-weight: 800;
        background: linear-gradient(90deg, {REAL_CYAN}, {REAL_INDIGO});
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }}
    .stat-label {{
        font-size: 0.85rem;
        color: {REAL_MUTED};
        text-transform: uppercase;
        letter-spacing: 0.1em;
        margin-top: 4px;
    }}

    .pill {{
        display: inline-block;
        padding: 4px 10px;
        border-radius: 999px;
        font-size: 0.75rem;
        font-weight: 600;
        margin-right: 6px;
        margin-bottom: 6px;
    }}
    .pill-blue   {{ background: rgba(59,130,246,0.15);  color: #93C5FD; border: 1px solid rgba(59,130,246,0.35); }}
    .pill-violet {{ background: rgba(139,92,246,0.15);  color: #C4B5FD; border: 1px solid rgba(139,92,246,0.35); }}
    .pill-cyan   {{ background: rgba(34,211,238,0.15);  color: #67E8F9; border: 1px solid rgba(34,211,238,0.35); }}
    .pill-mint   {{ background: rgba(52,211,153,0.15);  color: #6EE7B7; border: 1px solid rgba(52,211,153,0.35); }}
    .pill-amber  {{ background: rgba(245,158,11,0.15);  color: #FCD34D; border: 1px solid rgba(245,158,11,0.35); }}
    .pill-red    {{ background: rgba(239,68,68,0.15);   color: #FCA5A5; border: 1px solid rgba(239,68,68,0.35); }}

    .step-row {{
        display: flex;
        align-items: flex-start;
        gap: 16px;
        padding: 14px 18px;
        margin: 8px 0;
        background: rgba(20,27,45,0.65);
        border: 1px solid rgba(255,255,255,0.05);
        border-left: 3px solid {REAL_INDIGO};
        border-radius: 12px;
    }}
    .step-num {{
        flex: 0 0 36px;
        height: 36px;
        width: 36px;
        border-radius: 50%;
        background: linear-gradient(135deg, {REAL_BLUE}, {REAL_INDIGO});
        color: white;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 700;
        font-size: 0.95rem;
    }}

    .quote-block {{
        border-left: 4px solid {REAL_CYAN};
        padding: 14px 18px;
        background: rgba(34,211,238,0.06);
        border-radius: 8px;
        font-style: italic;
        color: #CBD5E1;
    }}

    .footer-note {{
        text-align: center;
        color: {REAL_MUTED};
        font-size: 0.85rem;
        padding: 30px 0 10px 0;
        border-top: 1px solid rgba(255,255,255,0.06);
        margin-top: 40px;
    }}

    /* Streamlit native overrides */
    section[data-testid="stSidebar"] {{
        background: linear-gradient(180deg, #0A0E1A 0%, #050811 100%);
        border-right: 1px solid rgba(255,255,255,0.06);
    }}
    section[data-testid="stSidebar"] .stMarkdown h2 {{
        color: {REAL_CYAN} !important;
        font-size: 0.9rem !important;
        letter-spacing: 0.15em;
        text-transform: uppercase;
    }}

    [data-testid="stMetric"] {{
        background: rgba(20,27,45,0.65);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 14px;
        padding: 14px 18px;
    }}
    [data-testid="stMetricValue"] {{
        font-size: 1.8rem !important;
        font-weight: 800 !important;
        color: {REAL_CYAN} !important;
    }}

    div.stButton > button {{
        background: linear-gradient(90deg, {REAL_BLUE}, {REAL_INDIGO}) !important;
        color: white !important;
        border: none !important;
        font-weight: 600 !important;
        padding: 10px 22px !important;
        border-radius: 10px !important;
        transition: transform .2s ease, box-shadow .2s ease;
    }}
    div.stButton > button:hover {{
        transform: translateY(-1px);
        box-shadow: 0 10px 24px rgba(99,102,241,0.35) !important;
    }}

    .stTabs [data-baseweb="tab-list"] {{
        gap: 6px;
    }}
    .stTabs [data-baseweb="tab"] {{
        background: rgba(20,27,45,0.7);
        border-radius: 10px;
        padding: 8px 16px;
        border: 1px solid rgba(255,255,255,0.05);
    }}
    .stTabs [aria-selected="true"] {{
        background: linear-gradient(90deg, {REAL_BLUE}, {REAL_INDIGO}) !important;
        color: white !important;
    }}

    .divider {{
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.15), transparent);
        margin: 28px 0;
    }}

    .kbd {{
        display: inline-block;
        padding: 2px 8px;
        background: rgba(255,255,255,0.06);
        border: 1px solid rgba(255,255,255,0.12);
        border-radius: 6px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.78rem;
        color: {REAL_CYAN};
    }}
</style>
"""


def inject_global_css():
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)


def hero(eyebrow: str, title_html: str, subtitle: str):
    st.markdown(
        f"""
        <div style="padding: 12px 0 8px 0;">
            <span class="hero-eyebrow">{eyebrow}</span>
            <h1 style="margin:0;">{title_html}</h1>
            <p style="font-size:1.05rem; color:{REAL_MUTED}; max-width: 820px; margin-top: 12px;">{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def stat_card(number: str, label: str):
    st.markdown(
        f"""
        <div class="stat-card">
            <div class="stat-number">{number}</div>
            <div class="stat-label">{label}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def card(title: str, body_html: str, pills: list[tuple[str, str]] | None = None):
    pills_html = ""
    if pills:
        pills_html = "<div style='margin-bottom:10px;'>" + "".join(
            f'<span class="pill pill-{c}">{t}</span>' for t, c in pills
        ) + "</div>"
    st.markdown(
        f"""
        <div class="card">
            {pills_html}
            <h3 style="margin:0 0 8px 0;">{title}</h3>
            <div style="color:#CBD5E1; line-height:1.6;">{body_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def divider():
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)


def footer():
    st.markdown(
        f"""
        <div class="footer-note">
            Built for Real · Engineering, AI &amp; Automation · Agent Verification System Case Study
        </div>
        """,
        unsafe_allow_html=True,
    )


def page_setup(page_title: str, icon: str = "⚡"):
    st.set_page_config(
        page_title=f"Real · {page_title}",
        page_icon=icon,
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inject_global_css()
    with st.sidebar:
        st.markdown(
            f"""
            <div style="padding: 8px 0 18px 0;">
                <div style="font-size:1.6rem; font-weight:900; letter-spacing:-0.04em;">
                    <span class="gradient-text">real</span><span style="color:{REAL_CYAN}">.</span>verify
                </div>
                <div style="color:{REAL_MUTED}; font-size:0.8rem; margin-top:2px;">
                    Agent Verification System
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("## Deck")
