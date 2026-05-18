import streamlit as st
from components.styles import page_setup, hero, card, divider, footer, REAL_CYAN, REAL_INDIGO, REAL_MUTED

page_setup("Q&A", icon="🎯")

hero(
    eyebrow="08 · Q&A",
    title_html='20 anticipated questions <span class="gradient-text">and how we answer them</span>, and how I\'d answer.',
    subtitle=(
        "Grouped by likely line of questioning. Each answer is short — the kind I can actually deliver "
        "out loud in 60–90 seconds. The 'one-liner' is the soundbite if I have only 10."
    ),
)

st.write("")

groups = st.tabs([
    "🏗️  Architecture",
    "🛡️  Resilience & failures",
    "🤖  AI & browser automation",
    "📈  Scale, cost & metrics",
    "👥  Team, process, risk",
])

def qa(idx, q, oneliner, detail, pills=None):
    pills_html = ""
    if pills:
        pills_html = "<div style='margin-bottom:10px;'>" + "".join(
            f'<span class="pill pill-{c}">{t}</span>' for t, c in pills
        ) + "</div>"
    st.markdown(
        f"""
        <div class="card">
            {pills_html}
            <div style="color:{REAL_CYAN}; font-weight:700; font-size:0.85rem; letter-spacing:0.12em; text-transform:uppercase;">Q{idx}</div>
            <h3 style="margin:4px 0 8px 0;">{q}</h3>
            <div style="color:#A7F3D0; font-style:italic; margin-bottom:10px;">→ {oneliner}</div>
            <div style="color:#CBD5E1; line-height:1.65;">{detail}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with groups[0]:
    qa(1,
       "Why Temporal? Why not just a cron and a script?",
       "Because the workflow is long, stateful, and partially dependent on a third party — exactly the shape Temporal exists for.",
       """
       A cron + script gives me one big retry boundary: the whole job. Temporal gives me <b>retry per step</b>,
       <b>replay across crashes</b>, and <b>signals</b> for HITL. Without it I'd reinvent half of Temporal in
       three months and reinvent the other half the next quarter.
       """,
       pills=[("Orchestration", "violet")])

    qa(2,
       "Why not just brute-force scrape with Playwright + a queue?",
       "We could ship faster — but every DRE redesign becomes a P1 instead of a config change.",
       """
       That works at 5 states. At 50, we'd spend most of our calendar maintaining selectors. Stagehand
       absorbs the maintenance cost into the system itself: a redesigned page just causes a cache miss,
       not an outage.
       """,
       pills=[("Browser AI", "cyan")])

    qa(3,
       "How does this fit into Real's existing systems?",
       "It listens to the CRM and writes back into the CRM. Everything else is internal to the verification service.",
       """
       The blast radius is small by design. The only external contracts are the CRM webhook contract
       and the verification-result write-back. The browser layer never touches Real's other systems.
       """,
       pills=[("Integration", "blue")])

    qa(4,
       "Build vs buy — is there a SaaS that just does this?",
       "Nothing covers 50-state DRE verification end-to-end. The closest are vertical license-verification vendors that re-sell what they scrape themselves.",
       """
       I'd evaluate vendors as a Phase 0 sanity check, but my expectation is that we'd still need to write
       the orchestration + HITL + CRM integration ourselves — that's the actual hard part. A managed
       scraping service like Bright Data could shave a couple of states off our adapter list.
       """,
       pills=[("Vendor", "amber")])

with groups[1]:
    qa(5,
       "What's the single biggest failure mode you're worried about?",
       "A silent semantic mismatch — the scraper returns a wrong-but-plausible expiration date.",
       """
       Crashes are easy: they retry and alert. The dangerous case is "DRE page loaded the wrong agent's
       row but the name is similar." That's why every verification has <b>multi-field cross-checks</b>
       (name + state + license #) and a <b>confidence score</b> that pushes ambiguous matches to HITL.
       """,
       pills=[("Quality", "red")])

    qa(6,
       "What happens if a DRE site is down for hours?",
       "Activities back off exponentially up to a cap. After the cap, the verification quarantines for the morning.",
       """
       We don't infinite-retry. After ~30 minutes of failed attempts, the workflow logs the state-level
       outage to Datadog and quarantines that agent's verification for human review. Synthetic monitors
       will already have alerted us, so Ops is expecting it.
       """,
       pills=[("Backoff", "violet")])

    qa(7,
       "How do you detect a UI change before it breaks a verification?",
       "Hourly synthetic verifications against every state, using a fixture agent.",
       """
       Datadog Synthetics runs a known-good agent through every state once an hour. Any state's success
       rate dipping below 95% pages the on-call adapter owner. The adapter dashboard shows green/yellow/red
       per state continuously.
       """,
       pills=[("Synthetics", "cyan")])

    qa(8,
       "What's the recovery time if you push a bad adapter?",
       "Under a minute — feature flag flips back, in-flight workflows continue on the new version, no redeploy.",
       """
       Adapters are config. Each version has a flag. A bad rollout: flip the flag, traffic returns to the
       previous adapter, in-flight workflows finish with the version they started on. <b>No code change. No restart.</b>
       """,
       pills=[("Rollback", "mint")])

with groups[2]:
    qa(9,
       "Why Stagehand over Browser-Use?",
       "Stagehand caches what works. Browser-Use re-reasons every run — great for prototyping, expensive in steady state.",
       """
       Browser-Use is genuinely impressive — it'll handle pages we haven't seen. But its agent loop reasons
       at every step, which is slow and pricey at our volume. Stagehand's hybrid (cached selector first,
       AI when needed) is the better fit for a production verification pipeline. I'd still keep Browser-Use
       in my pocket for the worst, never-seen-before adapter.
       """,
       pills=[("AI primitives", "violet")])

    qa(10,
       "Why Claude specifically? Why not GPT-5 or Gemini?",
       "Best vision-on-documents performance in my evals, and our infra is comfortable with Anthropic.",
       """
       The DRE listing page is a structured document. Claude's vision is currently the most reliable at
       structured-document understanding, and Anthropic's tool-use is solid. I'd run live A/B tests
       against GPT-5 quarterly — we should never be locked in. The codebase abstracts the LLM behind
       a single interface for exactly that reason.
       """,
       pills=[("LLM", "cyan")])

    qa(11,
       "How much does the LLM cost per verification?",
       "Steady-state: ~$0.04 per verify. First month after launch: ~$0.18 while the cache warms.",
       """
       Most calls are zero-cost cache hits. The expensive cases are vision fallbacks (a screenshot + Opus
       reasoning, ~$0.10–0.20). At 5k/week steady-state I budget $200/month for LLM. We monitor cost per
       verification as a first-class metric in Datadog.
       """,
       pills=[("Cost", "amber")])

    qa(12,
       "How do you handle CAPTCHA?",
       "Browserbase has CAPTCHA solving included. For sites where solving is unreliable, we fall back to a manual reCAPTCHA-tagged HITL queue.",
       """
       Most state DREs don't have CAPTCHA. The handful that do (e.g. Hawaii) — Browserbase's built-in
       solver covers reCAPTCHA v2/v3 and hCaptcha. For exotic challenges we explicitly mark the adapter
       as HITL-required for the relevant action.
       """,
       pills=[("CAPTCHA", "red")])

with groups[3]:
    qa(13,
       "How does this scale to 10× the agents?",
       "Workers scale horizontally on Temporal queue depth. The bottleneck becomes Browserbase session quota — which is a vendor knob, not an architecture change.",
       """
       At 10× we'd need a multi-region Browserbase agreement and probably regional Temporal task queues
       to keep latency tight. The architecture absorbs 10×; we'd negotiate vendor capacity in parallel.
       """,
       pills=[("Scale", "blue")])

    qa(14,
       "What's the metric you'd want on the homepage of the ops dashboard?",
       "First-pass verification success rate, broken down by state, last 7 days.",
       """
       It's the leading indicator of everything that matters: adapter health, vendor health, vision-model
       quality. If it drops, something is broken before HITL volume tells us. Secondary: cost per verify
       and p95 duration.
       """,
       pills=[("Metrics", "cyan")])

    qa(15,
       "What's the ROI vs the current manual process?",
       "13 FTEs of effort replaced by ~$5.7k/month of cloud cost. Payback in ~2 weeks.",
       """
       At 5k weekly verifications and 6 min per manual verify, that's 500 hrs/week — call it 13 fully-loaded
       FTEs at $7–9k/month each. Even if my cost estimate is double, it's an order-of-magnitude win — and
       Ops time gets redirected to the 1.5% of cases where humans actually add judgment.
       """,
       pills=[("ROI", "mint")])

    qa(16,
       "What would you do if you only had 2 weeks?",
       "Ship a working CA-only pipeline against a Temporal sandbox, with manual approval gating and zero AI.",
       """
       Crawl-walk-run. Week 1: webhook + workflow skeleton + CA adapter in pure Playwright + Postgres
       ledger. Week 2: HITL queue + Slack + dashboard. Layer Stagehand and additional states after.
       That gets us value in production fast and de-risks the architecture.
       """,
       pills=[("MVP", "amber")])

with groups[4]:
    qa(17,
       "Who owns this on call?",
       "Engineering owns the system; an Ops analyst owns the HITL queue. Adapters have a per-state DRI rotation.",
       """
       Two distinct on-call rotations. Engineering pages on workflow / infra failures (durable-execution
       errors, queue stalls). Ops pages on HITL volume spikes. Per-state adapter owners are notified
       when their synthetic monitor goes yellow, not paged.
       """,
       pills=[("On-call", "violet")])

    qa(18,
       "What testing strategy lets you trust deploys?",
       "Three layers: unit tests on adapters, integration tests against recorded HAR fixtures, hourly synthetics in prod.",
       """
       Unit tests are cheap and catch logic regressions. Integration tests against checked-in HAR fixtures
       catch parsing regressions without hitting real DRE sites. Hourly synthetics in prod catch <em>their</em>
       changes. The trifecta means a deploy is rarely the cause of a prod failure.
       """,
       pills=[("Testing", "cyan")])

    qa(19,
       "What's the biggest unknown / risk?",
       "Some DRE sites may quietly rate-limit residential IPs. We'd discover that at scale, not in a pilot.",
       """
       Honest answer: state-level anti-bot behavior is opaque. I'd plan for it (adaptive concurrency,
       state-tagged Browserbase sessions, per-state success-rate alerts) and budget a contingency for
       a small number of adapters going HITL-only as a stopgap.
       """,
       pills=[("Risk", "red")])

    qa(20,
       "If I gave you the green light tomorrow, what's day one?",
       "Lock the CRM event contract with the Eng team, then ship a sandbox Temporal workflow that just logs.",
       """
       Day 1: confirm the webhook payload + retry semantics with whoever owns the CRM. Day 2–3: skeleton
       workflow in a sandbox account that logs every event end-to-end. By end of week 1, the CA happy
       path. By end of week 2, the first verification written to a ledger. Then we scale states.
       """,
       pills=[("Day one", "mint")])

divider()

# Bonus
st.markdown("### Bonus: tricky questions I've prepared for")
b1, b2 = st.columns(2)
with b1:
    card(
        "\"Is this just an AI hype project?\"",
        """
        Fair pushback. AI is a tactic here, not the strategy. The strategy is <b>durable execution</b> and
        <b>adapter versioning</b> — both pre-AI patterns. AI is the cheapest insurance against the only
        thing we can't control: when DRE sites change. If Stagehand vanished tomorrow, we'd swap to plain
        Playwright + a slightly higher HITL rate and we'd still have a working system.
        """,
        pills=[("Honest", "amber")],
    )
with b2:
    card(
        "\"Why should this be a service, not a script in our existing platform?\"",
        """
        Because the failure profile is wildly different from the rest of the platform. This system is
        slow, IO-heavy, vendor-dependent, and needs HITL. Putting it inside a CRUD service would mix two
        very different on-call profiles. A small, focused service is easier to monitor and easier to fund
        as it grows.
        """,
        pills=[("Architecture", "violet")],
    )

divider()

c1, c2 = st.columns([1, 1])
with c1:
    st.page_link("pages/7_Knowledge_Guide.py", label="← Knowledge Guide", width="stretch")
with c2:
    st.page_link("pages/9_Presentation_Script.py", label="Next: Presentation Script →", width="stretch")

footer()
