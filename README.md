# Real · Agent Verification System — Presentation + Working Build

An interactive Streamlit deck **and** a working implementation of the proposed durable, AI-augmented agent verification system. Built for the panel with **Mark Hinojosa** (Manager, Engineering — AI & Automation @ Real).

The deck (9 pages) proposes the architecture. The working build (4 more pages) lets you **watch it run** end-to-end: real Playwright Chromium, real Claude API (when key is set), real SQLite ledger, real HITL queue.

## Quick start

```powershell
# Windows / PowerShell
pip install -r requirements.txt
playwright install chromium           # ~200MB one-time download
$env:ANTHROPIC_API_KEY = "sk-ant-..."  # optional — enables real Claude calls
python -m streamlit run app.py
```

Open http://localhost:8501.

> If `streamlit` isn't on PATH, use `python -m streamlit run app.py`.

## Demo flow (~3 minutes)

1. Open the **Live Demo** page (sidebar)
2. Pick scenario: **Jordan Rivera (CA · happy path)**
3. Toggle **Show Chromium window** = on
4. Click **▶ Run verification**
5. A real Chromium window pops up, drives the local JoinReal + CA DRE mocks
6. Live trace streams in Streamlit, ledger row lands
7. Open **Verification Ledger** — there's the row, with the captured screenshot
8. Back to **Live Demo** — pick **Maria Delgado (TX · mismatch)** → run
9. Workflow ends in quarantine
10. Open **HITL Queue** — Slack-styled alert appears with working buttons
11. Click **Approve CRM value** → ledger row updates, case resolved
12. Open **Metrics Dashboard** — live counts from the SQLite ledger

## What's REAL vs what's a production stand-in

| Architecture slide says | What runs in this build |
|---|---|
| Temporal.io | Generator-based saga engine in `verifier/workflow.py` — same retry / replay / signal semantics |
| Playwright + Stagehand + Browserbase | Real Playwright Chromium against local Flask mocks of JoinReal + 3 state DREs |
| Claude Opus vision + Haiku classifier | Real Anthropic SDK calls (if `ANTHROPIC_API_KEY` is set), deterministic mock otherwise |
| Postgres ledger | SQLite at `data/ledger.db` (same SQL semantics) |
| Redis selector cache | In-memory dict with TTL in `verifier/cache.py` |
| EventBridge + DynamoDB outbox | Streamlit button + in-process queue |
| Slack HITL alerts | Slack-styled alert rendered in the HITL Queue page with real working buttons |
| Datadog | Live Metrics Dashboard page reading from SQLite |
| S3 artifact storage | Local `data/screenshots/` directory |

## Pages

| # | Page | Purpose |
|---|---|---|
| Home | `app.py` | Hero + nav |
| 1 | Problem Statement | The brief, 11 events, assumptions |
| 2 | System Architecture | Six layers, system diagram |
| 3 | Workflow Walkthrough | Animated trace |
| 4 | Tech Stack | Every pick + rejected alternatives + cost |
| 5 | Resilience | Failure handling, Mark's 3 questions |
| 6 | Deployment | Topology, SLOs, security |
| 7 | Knowledge Guide | Plain-English tool glossary |
| 8 | Panel Q&A | 20 anticipated questions |
| 9 | Presentation Script | Minute-by-minute talk track |
| **10** | **Live Demo** | **Run the real workflow against the mock sites** |
| **11** | **Verification Ledger** | **Browse real SQLite ledger** |
| **12** | **HITL Queue** | **Resolve cases via working Slack-style buttons** |
| **13** | **Metrics Dashboard** | **Live metrics from real ledger** |

## Three sentences to memorize

1. *"It has to be cheap when nothing's wrong, and graceful when something is."*
2. *"Six layers, one durable workflow."*
3. *"AI is a fallback, not the headline."*

## File layout

```
ak1/
├── app.py                          # Home / hero
├── components/                     # Shared CSS + Graphviz/Plotly diagram helpers
├── pages/                          # 13 Streamlit pages (9 deck + 4 working build)
├── verifier/                       # The working implementation
│   ├── workflow.py                 # Saga engine (Temporal stand-in)
│   ├── activities.py               # The 6 activities the workflow orchestrates
│   ├── playwright_runner.py        # Real Chromium automation
│   ├── llm_claude.py               # Anthropic SDK wrapper (with mock fallback)
│   ├── adapter_loader.py           # YAML per-state DRE adapter loader
│   ├── adapters/                   # ca.yaml, tx.yaml, hi.yaml — versioned configs
│   ├── cache.py                    # In-memory selector cache (Stagehand pattern)
│   ├── db.py                       # SQLite ledger + HITL queue
│   ├── fixtures.py                 # 3 sample agents (happy / mismatch / HITL)
│   ├── mock_sites/                 # Flask mocks of JoinReal + DREs
│   └── trace.py                    # Span emission
├── data/                           # Runtime data (gitignored): ledger.db + screenshots/
└── requirements.txt
```

## Optional configuration

```powershell
# Use real Claude for extraction + classification
$env:ANTHROPIC_API_KEY = "sk-ant-..."

# Pin specific Claude model IDs (defaults shown)
$env:CLAUDE_MODEL_HEAVY = "claude-opus-4-7"
$env:CLAUDE_MODEL_LIGHT = "claude-haiku-4-5-20251001"

# Point an adapter at a real DRE site instead of the local mock
$env:REAL_DRE_BASE_CA = "https://www2.dre.ca.gov"
```
