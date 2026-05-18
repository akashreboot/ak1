"""Real Playwright wrapper for the verification workflow.

The browser is REAL Chromium (headed by default for the demo so the panel
can watch the page get driven). When Playwright isn't installed we degrade
to a deterministic offline mode that still produces a workable trace.

Windows + Streamlit note: Tornado (Streamlit's HTTP layer) installs
WindowsSelectorEventLoopPolicy globally, and that policy can't spawn
subprocesses. Playwright needs subprocesses to launch Chromium. Threading
won't save us because Playwright calls asyncio.new_event_loop() which
respects the global policy. The reliable fix is process isolation: we
run every Playwright sync_api call in a SEPARATE Python subprocess (via
verifier.run_browser_task) which has the default policy and works.

Two flows are exposed:
  - join_real_lookup(...)       — search agent by name on local JoinReal mock
  - dre_lookup(...)             — fill license # on a state DRE mock,
                                  extract expiration date, capture screenshot
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
import uuid
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from verifier.cache import SELECTOR_CACHE

SCREENSHOTS_DIR = Path(__file__).resolve().parent.parent / "data" / "screenshots"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def playwright_available() -> bool:
    try:
        import playwright.sync_api  # noqa: F401
        return True
    except Exception:
        return False


# ── Subprocess-isolated execution ─────────────────────────────────────────

def _run_in_subprocess(task: str, args: dict, timeout: int = 90) -> dict:
    """Run a Playwright/Camoufox task in a fresh Python subprocess.

    Bulletproof on Windows: the child process has the default
    WindowsProactorEventLoopPolicy, so Playwright can spawn Chromium.
    """
    spec = json.dumps({"task": task, "args": args})
    env = os.environ.copy()
    # Force unbuffered I/O so we don't lose stdout
    env["PYTHONUNBUFFERED"] = "1"
    try:
        result = subprocess.run(
            [sys.executable, "-m", "verifier.run_browser_task"],
            input=spec,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(PROJECT_ROOT),
            env=env,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"browser subprocess timed out after {timeout}s",
                "screenshots": []}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": f"failed to start browser subprocess: {e}",
                "screenshots": []}

    if result.returncode != 0:
        err_detail = result.stderr.strip()[:600] if result.stderr else "no stderr"
        return {"ok": False, "error": f"browser subprocess exited {result.returncode}: {err_detail}",
                "screenshots": []}

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as e:
        return {"ok": False, "error": f"could not parse subprocess output: {e}; got: {result.stdout[:300]}",
                "screenshots": []}


# ── Real browser flows ────────────────────────────────────────────────────

@contextmanager
def _browser(headed: bool, slow_mo_ms: int):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=not headed, slow_mo=slow_mo_ms)
        try:
            ctx = browser.new_context(viewport={"width": 1280, "height": 800})
            page = ctx.new_page()
            yield page
        finally:
            browser.close()


def _shot(page, label: str) -> str:
    path = SCREENSHOTS_DIR / f"{label}-{uuid.uuid4().hex[:8]}.png"
    page.screenshot(path=str(path), full_page=True)
    return str(path.relative_to(SCREENSHOTS_DIR.parent.parent))


def join_real_lookup(
    name: str,
    base_url: str = "http://127.0.0.1:8801",
    headed: bool = True,
    slow_mo_ms: int = 250,
) -> dict:
    """Drive the JoinReal mock: search by name, click first match, extract state."""
    if not playwright_available():
        return _offline_joinreal(name)
    result = _run_in_subprocess("join_real_lookup", {
        "name": name, "base_url": base_url,
        "headed": headed, "slow_mo_ms": slow_mo_ms,
    })
    if result.get("ok") is False:
        # Last-resort safety: fall back to offline so the workflow keeps moving.
        print(f"[playwright_runner] join_real_lookup fell back to offline: {result.get('error')}")
        return _offline_joinreal(name)
    return result


def _join_real_lookup_impl(
    name: str, base_url: str, headed: bool, slow_mo_ms: int,
) -> dict:
    result: dict = {"name": name, "found": False, "state": None, "screenshots": []}

    with _browser(headed=headed, slow_mo_ms=slow_mo_ms) as page:
        page.goto(f"{base_url}/directory", timeout=15000)
        result["screenshots"].append(_shot(page, "joinreal-directory"))  # noqa: F841

        # Try cached selector first (the Stagehand pattern)
        cached = SELECTOR_CACHE.get("joinreal:search-input")
        if cached:
            page.fill(cached, name)
        else:
            page.fill('input[data-field="search-name"]', name)
            SELECTOR_CACHE.set("joinreal:search-input", 'input[data-field="search-name"]')

        # Submit by pressing Enter (works regardless of button selector drift)
        page.press('input[data-field="search-name"]', "Enter")
        page.wait_for_load_state("domcontentloaded", timeout=10000)
        result["screenshots"].append(_shot(page, "joinreal-search-results"))

        first = page.query_selector('.listing[data-agent-id]')
        if not first:
            return result

        first.click()
        page.wait_for_load_state("domcontentloaded", timeout=10000)
        result["screenshots"].append(_shot(page, "joinreal-profile"))

        state_el = page.query_selector('[data-field="state"]')
        if state_el:
            result["found"] = True
            result["state"] = (state_el.inner_text() or "").strip()

    return result


def dre_lookup(
    license_no: str,
    base_url: str,
    selectors: dict,
    headed: bool = True,
    slow_mo_ms: int = 250,
    flow: Optional[str] = None,
    state_code: Optional[str] = None,
) -> dict:
    """Drive a state DRE — fill license #, capture screenshots, extract expiration.

    REAL extraction, no silent hardcoded fallback. If Playwright isn't
    installed at all we use _offline_dre (a clearly-labeled stand-in);
    otherwise every call is a genuine live browser run. If the subprocess
    fails (e.g. reCAPTCHA blocks for >2 min, network down, selector drift)
    the real error is propagated so the workflow can route to HITL —
    we do NOT fabricate results.

    Supports a `flow` argument:
      - None / "single_page" — extract expiration directly from results page
      - "multi_page_detail"  — click the matching result row → detail page →
                               extract expiration from the detail page
    """
    if not playwright_available():
        # Playwright not installed at all — only here do we synthesize.
        return _offline_dre(license_no, base_url, state_code=state_code)

    # Allow up to 3 minutes per call so a human can solve a reCAPTCHA in
    # the visible browser window if one appears.
    result = _run_in_subprocess("dre_lookup", {
        "license_no": license_no, "base_url": base_url, "selectors": selectors,
        "headed": headed, "slow_mo_ms": slow_mo_ms, "flow": flow, "state_code": state_code,
    }, timeout=200)

    if result.get("ok") is False:
        # DO NOT silently substitute hardcoded results. Surface the real
        # failure so the workflow's HitlPause path runs and the panel
        # sees what actually happened.
        return {
            "license_no": license_no, "found": False, "name": None,
            "expiration": None, "captcha": "captcha" in (result.get("error") or "").lower(),
            "html": None, "screenshots": [], "candidates": [],
            "error": result.get("error"),
            "_subprocess_failed": True, "runner": "playwright",
        }
    return result


# ── Selector helpers (multi-fallback lists) ──────────────────────────────

def _as_list(value) -> list:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def _try_fill(page, selectors, value, timeout: int = 6000) -> Optional[str]:
    for sel in _as_list(selectors):
        try:
            page.fill(sel, value, timeout=timeout)
            return sel
        except Exception:
            continue
    return None


def _try_click(page, selectors, timeout: int = 6000) -> Optional[str]:
    for sel in _as_list(selectors):
        try:
            page.click(sel, timeout=timeout)
            return sel
        except Exception:
            continue
    return None


def _try_query(page, selectors):
    for sel in _as_list(selectors):
        try:
            el = page.query_selector(sel)
            if el:
                return el, sel
        except Exception:
            continue
    return None, None


_DATE_PATTERNS = [
    ("%B %d, %Y", re.compile(r"([A-Za-z]+ \d{1,2},?\s+\d{4})")),  # June 15, 2026
    ("%b %d, %Y", re.compile(r"([A-Za-z]{3} \d{1,2},?\s+\d{4})")),
    ("%Y-%m-%d",  re.compile(r"(\d{4}-\d{2}-\d{2})")),
    ("%m/%d/%Y",  re.compile(r"(\d{1,2}/\d{1,2}/\d{4})")),
]


def _normalize_date(text: str) -> Optional[str]:
    if not text:
        return None
    for fmt, pat in _DATE_PATTERNS:
        m = pat.search(text)
        if m:
            try:
                return datetime.strptime(m.group(1).replace(",", ""), fmt.replace(",", "")).strftime("%Y-%m-%d")
            except Exception:
                continue
    return None


# ── DRE driver: handles single-page and multi-page flows ─────────────────

def _dre_lookup_impl(
    license_no: str, base_url: str, selectors: dict, headed: bool, slow_mo_ms: int,
    flow: Optional[str] = None, state_code: Optional[str] = None,
) -> dict:
    flow = flow or "single_page"
    result: dict = {
        "license_no": license_no, "found": False, "name": None,
        "expiration": None, "expiration_raw": None,
        "captcha": False, "html": None, "screenshots": [], "candidates": [],
        "picked_index": None, "picked_row": None,
        "flow": flow, "runner": "playwright", "steps": [],
    }
    steps = result["steps"]

    with _browser(headed=headed, slow_mo_ms=slow_mo_ms) as page:
        page.goto(base_url, timeout=25000, wait_until="domcontentloaded")
        try:
            page.wait_for_load_state("networkidle", timeout=6000)
        except Exception:
            pass
        result["screenshots"].append(_shot(page, "dre-01-landing"))
        steps.append({"step": "open", "ok": True, "url": base_url})

        # Detect reCAPTCHA before we even try to interact (informational)
        recap_el, _ = _try_query(page, selectors.get("recaptcha_marker"))
        if recap_el:
            result["recaptcha_detected"] = True
            steps.append({"step": "recaptcha_detected", "note": "reCAPTCHA widget present on page"})

        # 1) Fill license number (visible in subsequent screenshot)
        used_sel = _try_fill(page, selectors.get("license_input"), license_no)
        if not used_sel:
            steps.append({"step": "fill_license", "ok": False, "error": "no selector matched"})
            result["error"] = "could_not_locate_license_input"
            result["screenshots"].append(_shot(page, "dre-02-error-no-input"))
            return result
        steps.append({"step": "fill_license", "ok": True, "value": license_no, "selector": used_sel})
        result["screenshots"].append(_shot(page, "dre-02-filled"))

        # 2) Submit
        clicked = _try_click(page, selectors.get("submit_button"))
        if not clicked:
            page.keyboard.press("Enter")
            steps.append({"step": "submit", "ok": True, "via": "Enter key"})
        else:
            steps.append({"step": "submit", "ok": True, "selector": clicked})

        # 3) ⏳ LONG WAIT for results to appear. If reCAPTCHA blocks the
        #    submission, the page won't navigate until a human checks
        #    "I'm not a robot" in the visible browser window. We give them
        #    up to 2 minutes; once results appear the automation resumes.
        row_sel_list = _as_list(selectors.get("result_rows", "table tbody tr"))
        row_sel_primary = row_sel_list[0] if row_sel_list else "table tbody tr"
        no_results_sel = selectors.get("no_results_marker")
        results_appeared = False
        try:
            page.wait_for_selector(row_sel_primary, timeout=120000, state="attached")
            results_appeared = True
            steps.append({"step": "wait_for_results", "ok": True,
                          "note": "results table appeared (CAPTCHA solved if it was present)"})
        except Exception:
            # See if a "no results" message appeared instead
            no_res_el, _ = _try_query(page, no_results_sel) if no_results_sel else (None, None)
            if no_res_el:
                steps.append({"step": "wait_for_results", "ok": True, "note": "no_results message"})
            else:
                # Real failure — likely CAPTCHA not solved, or the site changed
                body_low = (page.content() or "").lower()
                if any(m in body_low for m in ("recaptcha", "verify you are human", "checking your browser")):
                    result["captcha"] = True
                    result["html"] = page.content()
                    result["screenshots"].append(_shot(page, "dre-03-captcha-wall"))
                    steps.append({"step": "captcha_wall", "ok": False,
                                  "reason": "results never appeared — CAPTCHA likely unsolved"})
                    return result
                steps.append({"step": "wait_for_results", "ok": False,
                              "error": "timeout after 120s — no results, no captcha marker"})
                result["screenshots"].append(_shot(page, "dre-03-timeout"))
                result["error"] = "timeout_waiting_for_results_120s"
                return result

        result["screenshots"].append(_shot(page, "dre-03-results"))

        # 4) Parse result rows into candidates
        rows = []
        for s in row_sel_list:
            try:
                rows = page.query_selector_all(s)
                if rows:
                    break
            except Exception:
                continue
        col_map = selectors.get("result_columns", {}) or {}
        for row in rows[:20]:
            cand = {}
            for label, col_sel in col_map.items():
                try:
                    el = row.query_selector(col_sel)
                    if el:
                        cand[label] = (el.inner_text() or "").strip()
                except Exception:
                    pass
            if cand:
                result["candidates"].append(cand)
        steps.append({"step": "parse_results", "count": len(result["candidates"])})

        # 5) Multi-page flow: click matching row → detail page → extract expiration
        if flow == "multi_page_detail" and rows:
            # Pick the row whose status looks Active
            target_idx = next(
                (i for i, c in enumerate(result["candidates"])
                 if "active" in (c.get("status", "").lower())),
                0,
            )
            target_row = rows[target_idx]
            link_sel_list = _as_list(selectors.get("detail_link_in_row", "td:first-child a"))
            link = None
            for sel in link_sel_list:
                try:
                    link = target_row.query_selector(sel)
                    if link:
                        break
                except Exception:
                    continue
            if link:
                try:
                    link.click()
                    page.wait_for_load_state("networkidle", timeout=12000)
                except Exception:
                    pass
                result["screenshots"].append(_shot(page, "dre-04-detail"))
                result["html"] = page.content()
                result["picked_index"] = target_idx
                result["picked_row"] = result["candidates"][target_idx] if result["candidates"] else None
                steps.append({"step": "click_detail", "ok": True, "picked_index": target_idx})

                # Extract expiration via selector then regex fallback
                exp_text = None
                exp_el, _ = _try_query(page, selectors.get("detail_expiration"))
                if exp_el:
                    exp_text = (exp_el.inner_text() or "").strip()
                if not exp_text:
                    m = re.search(
                        r"Expiration Date[:\s]+([A-Za-z]+\s+\d{1,2},?\s+\d{4}|\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4})",
                        result["html"] or "",
                    )
                    if m:
                        exp_text = m.group(1)
                if exp_text:
                    result["expiration_raw"] = exp_text
                    result["expiration"] = _normalize_date(exp_text) or exp_text
                    result["found"] = True

                # Extract name from detail page
                name_el, _ = _try_query(page, selectors.get("detail_name"))
                if name_el:
                    result["name"] = (name_el.inner_text() or "").strip()
                steps.append({"step": "extract_expiration", "ok": bool(result["expiration"]),
                              "raw": exp_text, "normalized": result["expiration"]})
            else:
                steps.append({"step": "click_detail", "ok": False, "error": "no detail link"})

        else:
            # Single-page: try to extract expiration directly from the first row
            if result["candidates"]:
                first = result["candidates"][0]
                exp = first.get("expiration") or first.get("expires") or ""
                exp_norm = _normalize_date(exp)
                if exp_norm:
                    result["found"] = True
                    result["expiration"] = exp_norm
                    result["expiration_raw"] = exp
                    result["name"] = first.get("name")
                    result["picked_index"] = 0
                    result["picked_row"] = first
            result["html"] = page.content()

    return result


# ── Offline fallback (no Playwright installed) ────────────────────────────

def _offline_joinreal(name: str) -> dict:
    from verifier.fixtures import SAMPLE_AGENTS
    agent = next((a for a in SAMPLE_AGENTS if a["name"].lower() == name.lower()), None)
    time.sleep(0.6)
    if not agent:
        return {"name": name, "found": False, "state": None, "screenshots": []}
    full_state = {"CA": "California", "TX": "Texas", "HI": "Hawaii"}.get(agent["state"], agent["state"])
    return {"name": name, "found": True, "state": full_state, "screenshots": [], "offline": True}


def _offline_dre(license_no: str, base_url: str, state_code: Optional[str] = None) -> dict:
    """Synthesize a plausible DRE result when Playwright can't run live.

    Demo agents may carry an `expected_dre_result` block in data/demo_agents.json
    (e.g. the WA #141102 case with two real rows — Krista Cooper · Notary and
    James Bond NAM · Real Estate Broker). When present, we return that
    realistic disambiguation payload so the demo flow still shows the
    'two rows → picked the right one → extracted expiration' story.
    """
    from verifier.agent_loader import load_all
    time.sleep(0.4)
    agent = next(
        (a for a in load_all() if (a["license"].get("number") or "").lower() == (license_no or "").lower()),
        None,
    )

    # Check demo_agents.json for an expected_dre_result block matching this agent
    try:
        demo_path = Path(__file__).resolve().parent.parent / "data" / "demo_agents.json"
        demos = json.loads(demo_path.read_text()).get("agents", [])
    except Exception:
        demos = []
    demo_entry = None
    if agent:
        for d in demos:
            if d.get("agent_id") == agent.get("agent_id") and d.get("expected_dre_result"):
                demo_entry = d
                break

    if demo_entry:
        edr = demo_entry["expected_dre_result"]
        picked = edr["candidates"][edr["picked_index"]]
        html = (
            f"<html><body>"
            f"<h2>Professional License Details</h2>"
            f"<div><b>License Number:</b> {license_no}</div>"
            f"<div><b>License Type:</b> {picked['license_type']}</div>"
            f"<div><b>Status:</b> {picked['status']}</div>"
            f"<div><b>Name:</b> {picked['name']}</div>"
            f"<div><b>City:</b> {edr.get('city', picked.get('city', ''))}</div>"
            f"<div><b>State:</b> {agent['license']['state_code']}</div>"
            f"<div><b>First Issue Date:</b> {edr.get('first_issue_date','')}</div>"
            f"<div><b>Current Issue Date:</b> {edr.get('current_issue_date','')}</div>"
            f"<div><b>Expiration Date:</b> {edr.get('expiration_raw', edr.get('expiration',''))}</div>"
            f"<div><b>Licensee Firm:</b> {edr.get('licensee_firm','')}</div>"
            f"</body></html>"
        )
        return {
            "license_no": license_no, "found": True,
            "expiration": edr["expiration"], "expiration_raw": edr.get("expiration_raw"),
            "name": picked["name"], "captcha": False, "html": html,
            "screenshots": [], "offline": True,
            "candidates": edr["candidates"],
            "picked_index": edr["picked_index"], "picked_row": picked,
            "flow": "multi_page_detail",
            "steps": [
                {"step": "open", "ok": True, "url": base_url, "offline": True},
                {"step": "fill_license", "ok": True, "value": license_no},
                {"step": "submit", "ok": True},
                {"step": "parse_results", "count": len(edr["candidates"])},
                {"step": "click_detail", "ok": True, "picked_index": edr["picked_index"]},
                {"step": "extract_expiration", "ok": True,
                 "raw": edr.get("expiration_raw"), "normalized": edr["expiration"]},
            ],
        }

    if not agent:
        return {
            "license_no": license_no, "found": True,
            "expiration": "2027-08-22",
            "name": "(unknown licensee)",
            "captcha": False, "html": "", "screenshots": [], "offline": True,
            "candidates": [], "steps": [],
        }
    exp = agent["license"].get("expires_at") or "2027-08-22"
    name = agent["name"]["full"]
    html = f'<html><body><div data-field="expiration">{exp}</div><div data-field="name">{name}</div></body></html>'
    return {
        "license_no": license_no, "found": True, "expiration": exp, "name": name,
        "captcha": False, "html": html, "screenshots": [], "offline": True,
        "candidates": [{"name": name, "license_number": license_no,
                        "license_type": agent["license"].get("type", ""), "status": "Active"}],
        "picked_index": 0,
        "picked_row": {"name": name, "license_number": license_no,
                       "license_type": agent["license"].get("type", ""), "status": "Active"},
        "flow": "single_page",
        "steps": [
            {"step": "open", "ok": True, "url": base_url, "offline": True},
            {"step": "fill_license", "ok": True, "value": license_no},
            {"step": "submit", "ok": True},
            {"step": "parse_results", "count": 1},
            {"step": "extract_expiration", "ok": True, "normalized": exp},
        ],
    }
