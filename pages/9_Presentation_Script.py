import streamlit as st
from components.styles import page_setup, hero, card, divider, footer, REAL_CYAN, REAL_INDIGO, REAL_MUTED

page_setup("Presentation Script", icon="🎤")

hero(
    eyebrow="09 · Talk Track",
    title_html='The <span class="gradient-text">10-minute</span> presentation, beat by beat.',
    subtitle=(
        "Below is the minute-by-minute script for the panel. Practice it out loud twice — don't memorize "
        "it word-for-word. The bold lines are the ones to say verbatim; the rest is connective tissue."
    ),
)

st.write("")

# Pre-flight checklist
st.markdown("### Pre-flight checklist")
p1, p2, p3 = st.columns(3)
with p1:
    card(
        "Tech",
        """
        <ul style="margin:0; padding-left:18px;">
            <li>Streamlit running locally + tunnel as backup</li>
            <li>Browser zoom 110%, fullscreen</li>
            <li>Mic/cam test 5 min before</li>
            <li>Charged laptop + charger</li>
            <li>Wifi backup hotspot</li>
        </ul>
        """,
        pills=[("Logistics", "blue")],
    )
with p2:
    card(
        "Mindset",
        """
        <ul style="margin:0; padding-left:18px;">
            <li>You did the research. You know more than they think.</li>
            <li>Slow down. Pauses feel longer to you than to them.</li>
            <li>"I don't know" is a valid answer — pair it with "here's how I'd find out."</li>
            <li>Smile on the first sentence. It carries through audio.</li>
        </ul>
        """,
        pills=[("Mental", "violet")],
    )
with p3:
    card(
        "What to bring up if there's silence",
        """
        <ul style="margin:0; padding-left:18px;">
            <li>The HITL Slack alert mock (page 5)</li>
            <li>The cost-per-verification metric (page 4)</li>
            <li>The 2-week MVP plan (panel Q16)</li>
            <li>Adapter-as-data rollback story (page 6)</li>
        </ul>
        """,
        pills=[("Recovery", "cyan")],
    )

divider()

# Script
st.markdown("### Minute-by-minute talk track")

beats = [
    ("0:00 – 0:45",
     "Open with the why",
     [
         ("VERBATIM", "\"Mark, thanks for the time. Before I jump in — what I built is a working presentation, not a slide deck. We'll click through it together.\""),
         ("BEAT", "Pause for ~2 seconds. Smile."),
         ("VERBATIM", "\"The brief was: verify every newly-activated Real agent against JoinReal and their state's DRE — autonomously, across 50 states, resilient to UI changes. So I designed for two principles: it has to be cheap when nothing's wrong, and graceful when something is.\""),
     ]),
    ("0:45 – 2:00",
     "Anchor on the problem",
     [
         ("ACTION", "Click to Page 1 (Problem Statement)."),
         ("VERBATIM", "\"The hardest part isn't any single step — it's that there are 11 of them, against 50 different DRE websites, and the dangerous failure mode is silent. A scraper that returns the wrong-but-plausible expiration date is worse than one that crashes.\""),
         ("POINT", "Briefly trace the 11 events on the right column."),
         ("CONNECT", "\"So I designed the system to fail loudly and recover cheaply.\""),
     ]),
    ("2:00 – 4:00",
     "The architecture",
     [
         ("ACTION", "Click to Page 2 (System Architecture)."),
         ("VERBATIM", "\"Six layers. One durable workflow.\""),
         ("WALKTHROUGH",
          "Trace left-to-right on the diagram: CRM event → EventBridge + outbox → Temporal workflow → "
          "Stagehand + Playwright on Browserbase → JoinReal + DRE → ledger + observability → HITL."),
         ("KEY POINT",
          "\"The two non-obvious choices: Temporal in the middle, and Stagehand for browser AI. The first makes the workflow "
          "crash-safe. The second makes UI changes a cache miss instead of an outage.\""),
     ]),
    ("4:00 – 5:30",
     "Live workflow walkthrough",
     [
         ("ACTION", "Click to Page 3 (Workflow Walkthrough). Hit the ▶ Run button."),
         ("VERBATIM", "\"This is the happy path for one California agent. Every step is a Temporal activity with its own retry policy. Watch the trace.\""),
         ("BEAT", "Let the animation play (~10s). Don't talk over it."),
         ("WRAP", "\"Total: under 90 seconds. Of those 12 steps, 9 are deterministic Playwright. 3 use Stagehand's AI primitives. The cache means most of those AI calls are zero-token cache hits.\""),
     ]),
    ("5:30 – 6:30",
     "Tech choices — the one you'd debate",
     [
         ("ACTION", "Page 4 (Tech Stack). Click straight to the Browser tab."),
         ("VERBATIM",
          "\"I'll skip the obvious ones and focus on the choice you'd most challenge me on. Stagehand over plain Playwright over Browser-Use.\""),
         ("ARGUMENT",
          "Plain Playwright: cheapest, but every DOM change is a maintenance ticket. Browser-Use: most flexible but expensive at our volume. "
          "Stagehand sits in the middle — Playwright underneath, AI on top, with a cache that learns. That's the right shape for production verification."),
     ]),
    ("6:30 – 8:00",
     "Mark's three questions",
     [
         ("ACTION", "Page 5 (Resilience)."),
         ("VERBATIM", "\"Your three design questions get explicit answers here.\""),
         ("Q1: UI changes",
          "Self-healing cache → AI re-derivation → vision fallback → versioned adapter rollback. Plus hourly synthetic monitors."),
         ("Q2: Failures for review",
          "Slack alert with side-by-side screenshot + 3 inline buttons that fire Temporal signals. The Ops Dashboard is the workbench."),
         ("Q3: Always-running",
          "EventBridge + outbox guarantees we never lose an event. Temporal guarantees we never lose a workflow. EKS in 3 AZs guarantees we never lose a pod. Warm-standby in a second region."),
     ]),
    ("8:00 – 8:45",
     "Deployment + cost",
     [
         ("ACTION", "Page 6 (Deployment)."),
         ("KEY POINT",
          "\"This pipeline replaces ~13 FTEs of manual work for about $5.7k/month of cloud cost. The payback is in the first two weeks of operation.\""),
         ("CONNECT", "\"And critically, an Ops analyst's time gets redirected to the 1.5% of cases where human judgment actually adds value.\""),
     ]),
    ("8:45 – 9:30",
     "Close",
     [
         ("VERBATIM",
          "\"To summarize: durable workflow as the spine. Cheap deterministic browser as the default. AI as the fallback, not the headline. Humans on the cases that need them.\""),
         ("VERBATIM",
          "\"If you greenlit this tomorrow, day one is locking the CRM event contract with your team. By the end of week one, California's happy path runs end-to-end. By the end of week two, the first verification lands in the ledger.\""),
         ("VERBATIM",
          "\"I'd love your questions.\""),
     ]),
    ("9:30 – end",
     "Q&A",
     [
         ("MINDSET", "Don't rush. Each question gets a 60–90s answer. Page 8 has 20 of them prepared."),
         ("LISTEN", "If they ask something off-script, the structure is: restate the question → state your answer in one sentence → support it with one example → ask if you addressed what they meant."),
     ]),
]

color_map = {
    "VERBATIM": "cyan",
    "BEAT": "violet",
    "ACTION": "amber",
    "POINT": "blue",
    "CONNECT": "mint",
    "WALKTHROUGH": "blue",
    "KEY POINT": "amber",
    "WRAP": "mint",
    "ARGUMENT": "violet",
    "MINDSET": "violet",
    "LISTEN": "cyan",
    "Q1: UI changes": "blue",
    "Q2: Failures for review": "blue",
    "Q3: Always-running": "blue",
}

for time, title, lines in beats:
    st.markdown(
        f"""
        <div class="card" style="border-left:3px solid {REAL_CYAN};">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                <h3 style="margin:0;">{title}</h3>
                <span class="pill pill-violet" style="font-family: 'JetBrains Mono', monospace;">{time}</span>
            </div>
        """,
        unsafe_allow_html=True,
    )
    for kind, text in lines:
        color = color_map.get(kind, "blue")
        st.markdown(
            f"""
            <div style="display:flex; gap:14px; padding:10px 0; align-items:flex-start;">
                <div style="flex:0 0 170px;"><span class="pill pill-{color}">{kind}</span></div>
                <div style="flex:1; color:#CBD5E1; line-height:1.65;">{text}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)

divider()

# Closing & rehearsal tips
st.markdown("### How to rehearse this tomorrow")
r1, r2 = st.columns(2)
with r1:
    card(
        "Two full run-throughs, out loud, with a timer",
        """
        First run: with the deck. Just clicking through, narrating, no notes. <b>Time it.</b> Aim for 9:30,
        worry if you're under 7 or over 11.<br/><br/>
        Second run: deck closed, eyes shut. If you can deliver the spine of the architecture in 90 seconds
        without the screen, you own it. The deck is your scaffolding, not your script.
        """,
        pills=[("Rehearse", "amber")],
    )
with r2:
    card(
        "Three sentences to know cold",
        """
        <ol style="margin:0; padding-left:18px;">
            <li><b>"It has to be cheap when nothing's wrong, and graceful when something is."</b></li>
            <li><b>"Six layers, one durable workflow."</b></li>
            <li><b>"AI is a fallback, not the headline."</b></li>
        </ol>
        These are your reset points. If you get lost, return to one of them.
        """,
        pills=[("Soundbites", "cyan")],
    )

divider()

# Closing message for the user
st.markdown(
    f"""
    <div class="quote-block" style="border-left-color:{REAL_INDIGO};">
        You've got this. The architecture is sound, the tradeoffs are defended, the failure modes are
        named, the script is paced. Tomorrow is execution — and execution is the part you control.
    </div>
    """,
    unsafe_allow_html=True,
)

st.write("")
c1, c2 = st.columns([1, 1])
with c1:
    st.page_link("pages/8_Panel_QA.py", label="← Panel Q&A", use_container_width=True)
with c2:
    st.page_link("app.py", label="Back to Home →", use_container_width=True)

footer()
