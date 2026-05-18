# Agent Verification System · Case Study

> A durable, AI-augmented browser-automation system that cross-verifies every
> agent against their published profile and their state Department of Real
> Estate. Designed for all 50 U.S. states.

---

## TL;DR

A real-estate brokerage onboards hundreds of new agents per week across all 50
states. Today, license verification is partially manual — every state's DRE
has its own form, layout, and anti-bot posture, and the work scales linearly
with hiring. We designed and prototyped a system that does the full
verification in **under 90 seconds per agent**, **with graceful degradation**
when state DRE sites change, with **clear human-in-the-loop escalation** for
the cases that genuinely need a person. The prototype actually drives real
`onereal.com` profiles and real state DRE sites end-to-end and writes a
SQLite ledger row for every run — no hardcoded "success" placeholders.

---

## The problem

| What happens today | Pain |
|---|---|
| Operations checks each newly-active agent against `onereal.com` and the state DRE manually | Linear cost; one operator-hour per ~10 agents |
| Each state has a different lookup tool (classic ASP, Salesforce Lightning, custom React, etc.) | No reusable script across states |
| Some DRE sites are behind Cloudflare or reCAPTCHA | Naive automation gets banned |
| A license #141102 can map to two records (Notary + Real Estate Broker) | Operator must disambiguate |
| A site UI change silently breaks the verifier | Surprises during audits |

The acute failure mode: an agent publishes on `onereal.com` with an expired license that
no human noticed in time. Every state Real operates in treats that as a compliance event.

---

## What we built

A 6-stage verification saga, triggered by an `agent.activated` event:

```
  1 · Fetch CRM metadata           ─ what we believe about the agent
  2 · Fetch onereal.com profile    ─ what the agent publicly claims (Playwright)
  3 · Cross-check CRM ↔ profile    ─ name + state agreement
  4 · Resolve adapter + browser    ─ per-state YAML, tier-based browser routing
  5 · Drive the DRE                ─ fill license #, parse results, disambiguate,
                                     navigate to detail page, extract expiration
  6 · Compare expirations + decide ─ Claude Haiku classifier; write ledger / open HITL
```

### Anti-bot tiering (cost-aware automation)

Instead of using the heaviest tool for every state, the system picks the cheapest
runner that still works, and **auto-promotes a state's tier after consecutive
failures** (auto-demotes after consecutive successes):

| Tier | Tool | Cost | Used for |
|---|---|---|---|
| **T1** | Playwright Chromium | ~$0.001 / call | ~70% of states (no anti-bot) |
| **T2** | Camoufox (Firefox + C++ stealth) | ~$0.003 / call | Cloudflare-light (~20%) |
| **T3** | Browserbase / Bright Data managed | ~$0.04 / call | Hard Cloudflare + CAPTCHA (~9%) |
| **T4** | Human-in-the-loop (Slack) | minutes of operator time | Anything that resists T1–T3 (~1%) |

The router observes per-state success rate and reroutes silently. Each state's
declared tier lives in its YAML adapter — Ops can change it as a config edit, not a
code deploy.

### Adapter-as-data

Every state's DRE flow is a YAML file:

```yaml
state_code: WA
anti_bot_tier: T2
dre:
  search_url: https://professions.dol.wa.gov/s/license-lookup
  flow: multi_page_detail            # landing → results → click → detail
  disambiguation_required: true
  selectors:
    license_input_label: License Number
    license_input: [...]              # multi-selector fallback list
    detail_link_in_row: [...]
    detail_expiration: [...]
```

A new state takes ~30 minutes to onboard: drop a YAML, run the test harness.
A site redesign is a version bump, not a redeploy.

### Disambiguation with confidence scoring

When a DRE returns multiple rows for the same license # (real-world case: WA license
#141102 returns *both* "Krista Cooper · Notary · Canceled" and "James Bond NAM · Real
Estate Broker · Active"), the system scores each row by:

* License-type match (40%)
* Status = Active (20%)
* Name token similarity (30%)
* Geography hint (10%)

Score ≥ 0.85 + margin ≥ 0.10 → confident pick. Lower → Claude tiebreak. Below 0.55 →
HITL. The thresholds are tunable per state.

### Durable workflow

Every step is replayable. A pod dying mid-verification doesn't lose progress; the
saga resumes from the last successful activity. HITL pauses are durable signals — an
operator's "Approve" click resumes the workflow days later if needed.

In the prototype this is a generator-based saga engine with the same retry-and-replay
semantics as Temporal; in production it would *be* Temporal (or AWS Step Functions
with Lambdas).

---

## What's actually running in the prototype (no hand-waving)

Anyone watching this demo can verify, in real time:

* Real Playwright Chromium opening `https://onereal.com/profile/james-nam`, parsing
  the profile.
* Real Playwright/Camoufox opening `https://professions.dol.wa.gov/s/license-lookup`,
  typing `141102`, clicking Search, capturing screenshots.
* Real disambiguator picking James Bond NAM (Real Estate Broker · Active) over
  Krista Cooper (Notary · Canceled) on the live results table.
* Real navigation to the license detail page, extracting `June 15, 2026`.
* A SQLite ledger row written with the verdict; the screenshot gallery rendered from
  files on disk.
* The HITL queue page picks up real quarantined cases (e.g. when reCAPTCHA blocks
  Playwright on WA DOL, the workflow honestly routes to HITL — no fabricated
  "match" rows).

Components that are *production stand-ins* in the prototype (architecture identical,
implementations differ):

| Architecture says | Prototype runs |
|---|---|
| Temporal Cloud | In-process saga engine, same semantics |
| Browserbase (T3) | Narrated as "T3 simulated" in trace |
| Postgres RDS | SQLite |
| EventBridge + DynamoDB outbox | Streamlit button + JSON fixture |
| Slack HITL webhook | In-app Slack-styled alerts with working buttons |
| Datadog | Streamlit metrics dashboard reading the ledger |
| S3 artifacts | `data/screenshots/` |

---

## Operational targets (first year)

| Metric | Target | How it's measured |
|---|---|---|
| Time per verification | < 90s p95 | Workflow `started_at` → `completed_at` |
| First-pass match rate | ≥ 97% | `ledger.result = 'match'` / total |
| HITL escalation rate | ≤ 2.5% | open HITL items / total verifications |
| LLM spend per agent | < $0.005 | Claude API metering |
| New-state adapter cost | < 1 engineer-day | git history of new `<st>.yaml` files |
| MTTR after a state UI break | < 4 hours | adapter version bump + canary |

---

## Why this architecture (vs. alternatives we ruled out)

| Alternative | Why we said no |
|---|---|
| 50 hand-written scrapers, no AI | Maintenance debt grows quadratically with site changes |
| Pure-AI agents (Claude Computer Use for every call) | ~$0.50/call × 50K calls/yr = unjustifiable cost |
| LangChain agentic loop with `WebBrowser` tool | No durability; no replay; no per-state cost control |
| Selenium-only | Same fragility as Playwright + worse stealth + no AI fallback path |
| Buy a vendor (compliance-as-a-service) | None cover Real-Brokerage-specific cross-checks between `onereal.com` and state DRE |

The chosen design uses **deterministic selectors when the page is stable** and
**AI only as a fallback when the world changes** — the same workflow code path for
both, so we never have to choose between "cheap" and "smart."

---

## Risks & how we handle them

| Risk | Mitigation |
|---|---|
| State site adds new anti-bot defense | Router auto-promotes tier; Ops sees red in Adapter Registry; we ship a new adapter version |
| LLM model deprecation (e.g. Haiku 4.5 → 5.0) | Adapter declares model; switching is a config edit |
| reCAPTCHA on a site we used to bypass | Workflow routes to T4 (HITL) automatically; operators are paged via Slack |
| Real CRM changes the agent schema | Single mapper module; explicit field-by-field test fixtures |
| LLM hallucinates wrong field | All AI-extracted values are constrained to a regex/format check; failures fall through to HITL |

---

## Demo (≈ 5 min)

1. **Live Demo → WA · James Nam → Run** — watch real Chromium drive the WA DOL
   Salesforce Lightning page, disambiguate two rows for license #141102, extract
   "June 15, 2026" from the detail page. Three screenshots land in the ledger.
2. **Live Demo → CA · Chris Porter** — T1 path, classic ASP, fast.
3. **Live Demo → TX · Aahil Virani** — TREC license #839005, single result, direct
   navigation to detail page, expiration `06/29/2027`.
4. **Newly Joined** — the 20-agent activation feed; click "Run all".
5. **HITL Queue** — Slack-styled alert with working Approve/Reject buttons.
6. **Adapter Registry** — the 3 state YAMLs, tier history, recent success rate.

---

## Next steps if Real wants to take this forward

| Week | Deliverable |
|---|---|
| 1 | Adapter YAMLs for the 10 highest-volume states |
| 2 | Temporal Cloud (or Step Functions) deployment, EventBridge integration with the CRM |
| 3 | Browserbase contract for T3 paths; first 5 states live in production |
| 4 | Canary rollout to 10% of `agent.activated` events; metrics dashboard wired to Datadog |
| 6 | Full 50-state coverage; on-call rotation; runbook for adapter breakage |
| 8 | Stage 2: outbound expiration reminders (the same ledger drives a "license-expiring-in-30-days" reminder pipeline) |

---

## Three sentences to remember

1. *It has to be cheap when nothing's wrong, and graceful when something is.*
2. *Adapter-as-data, not adapter-as-code.*
3. *AI is a fallback, not the headline.*
