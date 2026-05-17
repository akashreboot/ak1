# Real · Agent Verification System — Presentation Deck

An interactive Streamlit deck proposing a durable, AI-augmented browser-automation system for verifying newly-onboarded Real agents against JoinReal.com and the 50 state Departments of Real Estate.

Built for the panel with **Mark Hinojosa** (Manager, Engineering — AI & Automation @ Real).

## Run locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Open http://localhost:8501.

## Deck structure

| Page                       | What it covers                                                                  |
| -------------------------- | ------------------------------------------------------------------------------- |
| `app.py` — Home            | Hero, why-this-matters, navigation                                              |
| `1_Problem_Statement`      | Problem re-statement, 11 events, assumptions / limitations / open questions     |
| `2_System_Architecture`   | Six-layer architecture, system diagram, end-to-end data flow                    |
| `3_Workflow_Walkthrough`  | Live animated trace of one verification + funnel / SLOs                         |
| `4_Tech_Stack`            | Every choice + alternatives I rejected, with cost breakdown                     |
| `5_Resilience`            | Defense-in-depth pyramid, Mark's 3 questions answered, state adapter map        |
| `6_Deployment`            | Topology, scaling, release strategy, security/compliance, SLOs                  |
| `7_Knowledge_Guide`       | Plain-English explainer of every tool + alternatives + glossary                 |
| `8_Panel_QA`              | 20 anticipated questions grouped by theme, with soundbite + detail answers     |
| `9_Presentation_Script`   | Minute-by-minute talk track + rehearsal tips                                    |

## Why this design (the elevator pitch)

- **Durable workflow as the spine** (Temporal.io) — crash-safe, idempotent, signal-driven
- **Cheap-by-default browser layer** (Playwright + Stagehand selector cache) with AI re-derivation on cache miss
- **Vision fallback** (Claude Opus 4.7) when DOM extraction is unsure
- **Adapter-as-data** for 50 DRE flows — versioned YAML, no code redeploys to fix a state
- **HITL via workflow signals** — Slack alert + inline buttons, no separate ticketing system

## Three sentences to memorize

1. *"It has to be cheap when nothing's wrong, and graceful when something is."*
2. *"Six layers, one durable workflow."*
3. *"AI is a fallback, not the headline."*

## Files

```
.
├── app.py                       # Home / hero
├── components/
│   ├── styles.py                # Shared CSS, hero, card, stat_card, page_setup
│   └── diagrams.py              # Graphviz architecture + Plotly figures
├── pages/                       # 9 deck pages (auto-discovered by Streamlit)
├── .streamlit/config.toml       # Dark theme, brand colors
├── requirements.txt
└── README.md
```
