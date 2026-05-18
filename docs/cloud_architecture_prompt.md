# Cloud Architecture Design Prompt — Agent Verification System

> Paste this prompt into any senior-architect-grade tool (Claude, GPT-5, an AWS
> Solutions Architect, etc.) to get a production cloud architecture for the system
> prototyped in this project. The prompt is self-contained — it doesn't
> assume the reader has seen the prototype.

---

## Prompt — copy from here

You are a senior staff engineer designing the production cloud architecture for a
real-estate brokerage's agent-license verification system. Produce a complete
architecture: services, data stores, queues, integrations, deployment topology, IaC
sketch, observability stack, security posture, cost model, and a rollout plan.
Be specific to AWS (the company's primary cloud); call out where a managed
equivalent on GCP/Azure would be a one-to-one substitute.

### Business context

The company (Real Brokerage Technologies) is a multi-state U.S. real-estate brokerage
that publishes thousands of agents on its public site `onereal.com`. Every newly
activated agent must be verified against:

1. The agent's own `onereal.com/profile/<slug>` page (what the agent publicly claims)
2. The state's Department of Real Estate / equivalent licensing authority
   (e.g. `professions.dol.wa.gov`, `dre.ca.gov`, `trec.texas.gov`) — the
   authoritative record

The two records must agree on: licensee name, state, license number, license type,
status (Active), and expiration date. Mismatches are a compliance risk in every
state the brokerage operates in.

### Functional requirements

* Triggered by an `agent.activated` event from the CRM (Salesforce-derived).
* For each event, run a 6-stage verification saga:
  1. Fetch CRM metadata for the agent.
  2. Fetch the `onereal.com` profile via headless browser; parse name, state, license #.
  3. Cross-check CRM and profile fields agree.
  4. Load a per-state adapter (YAML config) and pick a browser tier.
  5. Drive the state DRE: fill the license #, parse search results, disambiguate
     when multiple rows match the license, navigate to the detail page, extract
     the expiration date. Capture 3 screenshots: landing page, results page,
     detail page.
  6. Compare CRM expiration vs DRE expiration via an LLM classifier (Claude Haiku);
     write the verdict to a ledger; quarantine mismatches to a human-in-the-loop
     queue surfaced in Slack.
* Browser-tier router with 4 levels:
  * T1 — Playwright Chromium (default, cheapest)
  * T2 — Camoufox or equivalent (Firefox + stealth fingerprint patches)
  * T3 — Managed-browser API (Browserbase / Bright Data) for hard Cloudflare + CAPTCHA
  * T4 — Human-in-the-loop operator
  The router auto-promotes a state's tier after 3 consecutive failures and
  auto-demotes after 3 consecutive successes.
* Adapter-as-data: each state's DRE flow is a versioned YAML config (selectors,
  flow type, anti-bot tier, expected license types, disambiguation rules).
  New state ≈ new YAML, not a code deploy.
* Durable workflow semantics: every activity is replayable; pod death does not
  lose progress; HITL pauses are durable signals.
* AI used as fallback only — Claude Opus vision for selector recovery when CSS
  selectors miss; Claude Haiku for classify_match decisions.
* Screenshots and HTML snapshots are persisted as evidence for every verification.

### Non-functional requirements

* Scale target: 1,000 agent activations per day initially, 50,000 per month at
  steady state, designed to absorb 10× spikes (e.g. acquisition events).
* Latency: < 90s p95 per verification.
* Availability: 99.9% for the trigger pipeline; HITL queue tolerates higher latency.
* Cost target: < $0.005 LLM spend per verification, < $0.06 total infra
  per verification at steady state.
* Compliance: SOC 2; PII (license #, phone, email) encrypted at rest and in transit;
  audit log immutable for 7 years.
* Multi-region: active-passive, RPO ≤ 5 min, RTO ≤ 30 min.
* The system must withstand state DRE sites being down for 24 hours without losing
  work — backpressure to the trigger pipeline, retries with exponential backoff,
  reconciliation when the site recovers.

### Integration surfaces

* Inbound: EventBridge bus subscribed to a Salesforce CDC stream (`agent.activated`
  events).
* Outbound:
  * Slack incoming-webhook for HITL alerts with action buttons.
  * Salesforce write-back: verification status, last_verified_at, ledger URL.
  * Datadog (or AWS observability stack) for metrics, traces, logs.
  * S3 for screenshot artifacts; presigned URLs in the HITL UI.
* External APIs:
  * Anthropic Claude API for AI fallback + classification.
  * Browserbase API (or equivalent) for T3 managed browsers.
  * Per-state DRE sites — no API, browser-driven only.

### Tech constraints + preferences

* Primary cloud: AWS. Prefer managed services over self-hosted (RDS, EventBridge,
  Step Functions, Lambda, Fargate, S3, Secrets Manager).
* Browser automation: Playwright (Python), Camoufox for T2.
* Workflow orchestration: prefer Temporal Cloud or AWS Step Functions; explain
  the tradeoff.
* Language: Python 3.11+ for the worker code.
* IaC: Terraform (mandatory) — produce the module structure even if you don't
  produce full HCL.
* CI/CD: GitHub Actions; gated deploys; canary rollouts via feature flags
  (GrowthBook or equivalent).
* Secrets in AWS Secrets Manager; no plaintext config.

### What to deliver

Produce the following artifacts (each as a section in your response):

1. **Logical architecture diagram** — components and their connections, in Mermaid
   or ASCII. Include the trigger bus, the workflow orchestrator, the workers,
   the browser-tier routers, the LLM call sites, the ledger store, the artifact
   store, the HITL channel.

2. **Data model** — the ledger table (every column, with rationale), the
   per-state adapter schema, the HITL item schema, and the audit log layout.
   Indicate which fields are indexed and why.

3. **Workflow definition** — the 6 activities, their idempotency keys, retry
   policies (max attempts, backoff, jitter), and HITL signal handling. Be
   explicit about which steps can be replayed safely and which cannot.

4. **Browser-tier router design** — how the router state is persisted, how
   promotion/demotion decisions are made consistent across worker instances,
   and how the router's metrics feed the Adapter Registry UI.

5. **Deployment topology** — VPC layout, subnets, the Fargate task definitions
   for the workers (with CPU/memory sizing), the RDS instance class, the S3
   bucket policy, multi-region failover sketch.

6. **Observability** — golden signals (latency, traffic, errors, saturation)
   with concrete metric names; trace span attributes that must be on every
   workflow run; the 3 dashboards Ops needs day-1 (Live Demo / Ledger Health /
   Adapter Tier Status); the alert rules and their escalation paths.

7. **Security posture** — IAM scoping (worker role, ops role, HITL role,
   audit-reader role), least-privilege examples, network egress controls
   (only DRE allowlist + Anthropic + Browserbase + Slack), KMS key strategy,
   data retention.

8. **Cost model** — back-of-envelope unit economics for 50,000 verifications
   per month. Identify the top three cost drivers and where they'd grow as
   volume scales 10×.

9. **Rollout plan** — 8-week phased rollout. Week-by-week deliverables,
   canary percentages, go/no-go gates, rollback procedure.

10. **Open questions and risks** — the 5 most important decisions that need
    a real human's input before this design is committed; the 3 biggest
    technical risks and their mitigation.

### Quality bar

* Be specific. "Use Lambda" is not an answer; "Use Lambda with 1024MB memory,
  15-min timeout, behind a private API Gateway with VPC endpoints, idempotent
  via a DynamoDB-backed deduplication key" is.
* Prefer managed services unless there's a concrete reason to self-host.
* Call out anything you're guessing about — don't invent requirements.
* Identify the parts of the architecture that are *load-bearing*
  (system collapses without them) vs *nice-to-have* (could be cut to ship sooner).
* Trace every architectural choice back to a functional or non-functional
  requirement above. If something doesn't trace back, it doesn't belong.

When you're done, produce a 5-sentence executive summary at the top that a
non-technical executive could read in 30 seconds.

---

## End of prompt — paste up to this line

---

## How to use this prompt

1. **Pick your model**: Claude Sonnet 4.6 or Opus 4.7 work well; GPT-5 also fine.
   For best results, give the model "extended thinking" / "step-by-step reasoning"
   if available.
2. **Iterate**: after the first pass, ask "rewrite section 6 (Observability) as
   if we're running 500K verifications/month — what changes?" The model handles
   delta-rewrites well.
3. **Diagram render**: paste any Mermaid output into <https://mermaid.live> for
   a clean PNG. Drop screenshots into the case study deck.
4. **Sanity-check**: the architecture must answer all 10 deliverable sections and
   pass the quality bar above. If section 8 (cost model) doesn't have actual
   dollar numbers, push back.
