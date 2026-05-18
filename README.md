# Agent Verification System

An interactive Streamlit deck plus a working implementation. The deck (9 pages) describes the architecture; the working build (6 pages) lets you watch it run end-to-end against real `onereal.com` profiles and real state DRE sites.

## Quick start (Windows / PowerShell)

```powershell
pip install -r requirements.txt
python -m playwright install chromium       # ~200MB one-time
python -m camoufox fetch                    # ~200MB one-time (optional — T2 stealth)
$env:ANTHROPIC_API_KEY = "sk-ant-..."       # enables real Claude calls
python -m streamlit run app.py
```

Open http://localhost:8501.

> No Anthropic key? The system runs with a deterministic LLM mock.
> No Camoufox? The T2 path transparently falls back to plain Playwright (narrated in the trace).

## Demo day flow (~5 min)

1. **Live Demo** → pick **WA · James Nam** → ▶ Run. A real Chromium window opens, drives the live profile + WA DOL Salesforce Lightning lookup. License #141102 returns two rows (Krista Cooper · Notary + James Bond NAM · Real Estate Broker); the disambiguator picks the right one. Ledger row lands.
2. Pick **CA · Chris Porter** → ▶ Run. T1 path. Fast happy match.
3. Pick **TX · Khary Livingston** → ▶ Run. T1 + disambiguation required.
4. **Newly Joined** → see all 20 newly-active agents in the queue → "Run all" for a batch sweep.
5. **Verification Ledger** → real SQLite rows, each with the captured screenshot.
6. **HITL Queue** → if any quarantined, Slack-styled alerts with working Approve/Reject buttons.
7. **Metrics Dashboard** → live numbers from the real ledger.
8. **Adapter Registry** → all 3 state YAMLs, their declared tier, the router's effective tier, recent success/failure history.

## Demo-day safety nets

| Safety net | Purpose |
|---|---|
| **Practice mode toggle** (top of Live Demo) | Zero network. Synthesizes profile + DRE from CRM data. Demo never fails. |
| **Cached profile snapshots** | First successful live fetch caches the parsed profile to `data/cache/profiles/`. Subsequent runs survive a network blip. |
| **Per-step timeouts + retries** | Every Playwright nav has a 15s timeout. Activities retry 3x with exponential backoff. |
| **Graceful synthesis** | If profile or DRE fetch ultimately fails, the workflow falls back to CRM data and writes a synthesized result — clearly labeled in the trace. |

## V2 architecture (what changed from V1)

V1 used local Flask mocks for JoinReal + DRE. V2 hits **real `onereal.com` profile pages** and **real state DRE sites**. The new pipeline:

```
1 · CRM event (active flag flip)
2 · Profile resolve   — fetch onereal.com/profile/<slug> via Playwright
3 · Cross-check       — name + state agreement, name-similarity scoring
4 · Adapter resolve   — load per-state YAML, anti-bot router picks T1/T2/T3/T4
5 · DRE verify        — Playwright (T1) or Camoufox (T2) drives the state site;
                        disambiguation by license_type + status + name + city
6 · Decide            — Claude Haiku compares CRM vs DRE expiration → ledger
```

### Anti-bot router (4 tiers)

| Tier | Tool | Used for | This demo |
|---|---|---|---|
| **T1** | Playwright | Sites without anti-bot (~70% of states) | **Real** |
| **T2** | Camoufox (Firefox + C++ stealth, 0% headless detection) | Cloudflare-light sites (~20%) | **Real if installed, falls back to T1 otherwise** |
| **T3** | Browserbase / Bright Data managed browsers | Hard Cloudflare + CAPTCHA (~9%) | Simulated (narrated in trace) |
| **T4** | HITL with operator-solved challenge | Sites that resist everything (~1%) | Routes to HITL Queue page |

Router auto-promotes a state's tier after 3 consecutive failures, auto-demotes after 3 successes. Visible on **Adapter Registry** page.

### What's REAL vs production stand-ins

| Architecture says | This build runs |
|---|---|
| Temporal.io | Generator-based saga engine — same retry / replay / signal semantics |
| Playwright + Stagehand + Browserbase | Real Playwright + Camoufox; Browserbase narrated |
| Claude Opus vision + Haiku classifier | Real Anthropic SDK calls (or deterministic mock) |
| Postgres ledger | SQLite at `data/ledger.db` |
| Redis selector cache | In-memory dict with TTL |
| EventBridge + DynamoDB outbox | Streamlit button + `agents.json` |
| Slack HITL alerts | In-page Slack-styled alerts with real working buttons |
| Datadog | Metrics Dashboard reading from SQLite |
| S3 artifacts | `data/screenshots/` |

## Pages

| # | Page | Purpose |
|---|---|---|
| Home | `app.py` | Hero + nav |
| 1–9 | Deck | Architecture, tradeoffs, deployment, panel Q&A, talk track |
| **10** | **Live Demo** | **Pick 1 of 3 real-URL scenarios, run end-to-end** |
| **11** | **Verification Ledger** | **Browse real SQLite ledger with screenshots** |
| **12** | **HITL Queue** | **Slack-styled alerts + real working buttons** |
| **13** | **Metrics Dashboard** | **Live charts from real ledger** |
| **14** | **Newly Joined** | **20-agent trigger feed; batch run** |
| **15** | **Adapter Registry** | **All state YAMLs + auto-router health** |

## File layout

```
ak1/
├── app.py                          # Home / hero
├── components/                     # Shared CSS + diagram helpers
├── pages/                          # 15 Streamlit pages (9 deck + 6 working build)
├── verifier/
│   ├── workflow.py                 # Saga engine
│   ├── activities.py               # 6-stage pipeline
│   ├── agent_loader.py             # Load + filter agents from JSON
│   ├── agent_generator.py          # Generate 100-agent fixture
│   ├── profile_fetcher.py          # Real onereal.com profile parser
│   ├── adapter_loader.py           # Per-state YAML loader
│   ├── disambiguator.py            # Multi-field confidence scoring
│   ├── anti_bot_router.py          # T1-T4 tier routing + auto-promote
│   ├── playwright_runner.py        # Real Chromium (T1)
│   ├── runners/camoufox_runner.py  # Real Firefox + stealth (T2)
│   ├── llm_claude.py               # Anthropic SDK wrapper
│   ├── db.py                       # SQLite ledger + HITL queue
│   ├── trace.py                    # Span emission
│   ├── cache.py                    # Selector cache
│   └── adapters/{ca,tx,wa}.yaml    # Per-state DRE configs
├── data/
│   ├── demo_agents.json            # 3 real-URL demo targets (editable)
│   ├── agents.json                 # 100 generated agents (regenerable)
│   ├── ledger.db                   # Runtime SQLite (gitignored)
│   ├── screenshots/                # Runtime artifacts (gitignored)
│   └── cache/profiles/             # Cached onereal profiles (gitignored)
└── requirements.txt
```

## Three sentences to memorize for the panel

1. *"It has to be cheap when nothing's wrong, and graceful when something is."*
2. *"Adapter-as-data, not adapter-as-code."*
3. *"AI is a fallback, not the headline."*

## Optional configuration

```powershell
$env:ANTHROPIC_API_KEY    = "sk-ant-..."              # real Claude
$env:CLAUDE_MODEL_HEAVY   = "claude-opus-4-7"
$env:CLAUDE_MODEL_LIGHT   = "claude-haiku-4-5-20251001"
$env:REAL_DRE_BASE_CA     = "https://www2.dre.ca.gov" # override per state if needed
```
