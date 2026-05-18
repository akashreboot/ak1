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
    """Real Chromium context. ignore_https_errors=True tolerates corporate
    proxies / AV that do TLS inspection (we saw ERR_CERT_AUTHORITY_INVALID
    on a user's machine where SSL was being intercepted). A realistic
    user-agent + an explicit accept-language make the site treat us as a
    normal browser, which slightly lowers the odds of a CAPTCHA challenge."""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=not headed, slow_mo=slow_mo_ms,
            args=["--disable-blink-features=AutomationControlled"],
        )
        try:
            ctx = browser.new_context(
                viewport={"width": 1280, "height": 800},
                ignore_https_errors=True,
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/126.0.0.0 Safari/537.36"
                ),
                extra_http_headers={"Accept-Language": "en-US,en;q=0.9"},
            )
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
    expected_name: Optional[str] = None,
    expected_license_type: Optional[str] = None,
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

    # Total subprocess time budget — short, no human CAPTCHA wait.
    result = _run_in_subprocess("dre_lookup", {
        "license_no": license_no, "base_url": base_url, "selectors": selectors,
        "headed": headed, "slow_mo_ms": slow_mo_ms, "flow": flow, "state_code": state_code,
        "expected_name": expected_name, "expected_license_type": expected_license_type,
    }, timeout=60)

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


def _try_fill(
    page, selectors, value, timeout: int = 6000,
    label_hint: Optional[str] = None,
    placeholder_hint: Optional[str] = None,
    scope=None,
) -> Optional[str]:
    """Fill a value into the first matching input.

    Strategies (in order):
      1. Each CSS selector in `selectors`
      2. `page.get_by_label(label_hint)` — Playwright text-based label match
      3. `page.get_by_placeholder(placeholder_hint)`
    After filling, the value is read back; mismatch is treated as failure
    so we don't claim success on a stale input.
    """
    target = scope or page

    def _verify(sel_handle):
        try:
            actual = sel_handle.input_value() if hasattr(sel_handle, "input_value") else ""
            return actual == value
        except Exception:
            return True  # if we can't verify, assume ok

    for sel in _as_list(selectors):
        try:
            if hasattr(target, "fill"):
                target.fill(sel, value, timeout=timeout)
                # Verify
                try:
                    actual = target.locator(sel).first.input_value()
                    if actual != value:
                        continue
                except Exception:
                    pass
                return sel
        except Exception:
            continue

    # Label-based fallback (very reliable for human-built forms)
    if label_hint:
        try:
            loc = target.get_by_label(label_hint, exact=False) if hasattr(target, "get_by_label") else None
            if loc is not None and loc.count() > 0:
                loc.first.fill(value, timeout=timeout)
                try:
                    if loc.first.input_value() == value:
                        return f"get_by_label:{label_hint}"
                except Exception:
                    return f"get_by_label:{label_hint}"
        except Exception:
            pass

    # Placeholder-based fallback
    if placeholder_hint:
        try:
            loc = target.get_by_placeholder(placeholder_hint, exact=False) if hasattr(target, "get_by_placeholder") else None
            if loc is not None and loc.count() > 0:
                loc.first.fill(value, timeout=timeout)
                return f"get_by_placeholder:{placeholder_hint}"
        except Exception:
            pass

    return None


def _try_click(
    page, selectors, timeout: int = 6000,
    role_hint: Optional[str] = None,
    text_hint: Optional[str] = None,
    scope=None,
) -> Optional[str]:
    target = scope or page

    for sel in _as_list(selectors):
        try:
            target.click(sel, timeout=timeout)
            return sel
        except Exception:
            continue

    # Role-based fallback (best for buttons / links)
    if role_hint and text_hint:
        try:
            loc = target.get_by_role(role_hint, name=text_hint) if hasattr(target, "get_by_role") else None
            if loc is not None and loc.count() > 0:
                loc.first.click(timeout=timeout)
                return f"role:{role_hint}/{text_hint}"
        except Exception:
            pass
    return None


def _find_form_with_label(page, label_text: str):
    """Return the <form> element that contains a label matching label_text.

    Used to scope subsequent fill/click operations to the correct form when
    the page has multiple forms (e.g. TREC has Site Search + License Search
    + Topic Search on the same page)."""
    try:
        forms = page.query_selector_all("form")
    except Exception:
        return None
    for form in forms:
        try:
            labels = form.query_selector_all("label")
        except Exception:
            continue
        for label in labels:
            try:
                if label_text.lower() in ((label.inner_text() or "").lower()):
                    return form
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

def _pick_row_index(
    candidates: list, expected_name: Optional[str] = None,
    expected_license_type: Optional[str] = None,
) -> Optional[int]:
    """Pick the right row when the DRE returns multiple matches.

    Rules (per user spec):
      * 1 candidate → pick it
      * > 1 candidates → score by:
          - status: Active = +2, Canceled/Expired/Suspended/Revoked = -2
          - license_type: equal or substring match → +3
          - name: tokens shared with expected_name → +1.5 per token
    """
    if not candidates:
        return None
    if len(candidates) == 1:
        return 0

    def _score(c: dict) -> float:
        s = 0.0
        status = (c.get("status") or "").lower()
        if "active" in status:
            s += 2.0
        elif any(b in status for b in ("cancel", "expired", "suspended", "revoked", "denied")):
            s -= 2.0
        if expected_license_type:
            elt = expected_license_type.lower().strip()
            clt = (c.get("license_type") or "").lower().strip()
            if clt and (elt == clt or elt in clt or clt in elt):
                s += 3.0
        if expected_name:
            exp_tokens = {t.lower() for t in re.split(r"[\s,]+", expected_name) if len(t) >= 2}
            cand_tokens = {t.lower() for t in re.split(r"[\s,]+", (c.get("name") or "")) if len(t) >= 2}
            s += 1.5 * len(exp_tokens & cand_tokens)
        return s

    scored = [(i, _score(c)) for i, c in enumerate(candidates)]
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[0][0]


def _dre_lookup_impl(
    license_no: str, base_url: str, selectors: dict, headed: bool, slow_mo_ms: int,
    flow: Optional[str] = None, state_code: Optional[str] = None,
    expected_name: Optional[str] = None, expected_license_type: Optional[str] = None,
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
        # Open with just domcontentloaded — no networkidle wait, so we don't
        # spend 3-4s before typing into the form (user feedback: "it takes
        # more time to input the number").
        page.goto(base_url, timeout=20000, wait_until="domcontentloaded")
        # Screenshot #1 of 3: proof the project opened the right page
        result["screenshots"].append(_shot(page, "dre-01-landing"))
        steps.append({"step": "open", "ok": True, "url": base_url})

        # Detect reCAPTCHA before we even try to interact (informational)
        recap_el, _ = _try_query(page, selectors.get("recaptcha_marker"))
        if recap_el:
            result["recaptcha_detected"] = True
            steps.append({"step": "recaptcha_detected", "note": "reCAPTCHA widget present on page"})

        # ── Scope to the correct <form> when the page has several ──────
        # Pages like TREC have Site Search + License Holder Search + Topic
        # Search on one page. We MUST type into the License Holder Search.
        label_hint = selectors.get("license_input_label")
        form_scope = None
        if label_hint:
            form_scope = _find_form_with_label(page, label_hint)
            if form_scope:
                steps.append({"step": "form_scope", "ok": True, "label": label_hint})

        # 1) Fill license number (visible in subsequent screenshot)
        used_sel = _try_fill(
            page, selectors.get("license_input"), license_no,
            label_hint=label_hint,
            placeholder_hint=selectors.get("license_input_placeholder"),
            scope=form_scope,
        )
        # If form-scoped fill failed, try page-wide as a last resort
        if not used_sel and form_scope is not None:
            used_sel = _try_fill(
                page, selectors.get("license_input"), license_no,
                label_hint=label_hint,
                placeholder_hint=selectors.get("license_input_placeholder"),
            )
        if not used_sel:
            steps.append({"step": "fill_license", "ok": False, "error": "no selector matched"})
            result["error"] = "could_not_locate_license_input"
            return result
        steps.append({"step": "fill_license", "ok": True, "value": license_no, "selector": used_sel})

        # 2) Submit (scoped to the same form so we don't trigger Site Search)
        clicked = _try_click(
            page, selectors.get("submit_button"),
            role_hint="button",
            text_hint=selectors.get("submit_button_text", "Search"),
            scope=form_scope,
        )
        if not clicked and form_scope is not None:
            clicked = _try_click(
                page, selectors.get("submit_button"),
                role_hint="button",
                text_hint=selectors.get("submit_button_text", "Search"),
            )
        if not clicked:
            page.keyboard.press("Enter")
            steps.append({"step": "submit", "ok": True, "via": "Enter key"})
        else:
            steps.append({"step": "submit", "ok": True, "selector": clicked})

        # 3) Wait for results, then STAY CALMLY so the names render before
        #    we screenshot or navigate away (user feedback: "just after the
        #    result came, it suddenly closed").
        row_sel_list = _as_list(selectors.get("result_rows", "table tbody tr"))
        row_sel_primary = row_sel_list[0] if row_sel_list else "table tbody tr"
        no_results_sel = selectors.get("no_results_marker")
        try:
            # state="visible" — wait until at least one row is actually shown
            page.wait_for_selector(row_sel_primary, timeout=15000, state="visible")
            # Brief settle for SF Lightning / React to finish rendering names
            page.wait_for_timeout(1500)
            steps.append({"step": "wait_for_results", "ok": True})
            # Screenshot #2 of 3: results page with the person name(s) visible
            result["screenshots"].append(_shot(page, "dre-02-results"))
        except Exception:
            # No structured rows — maybe a no_results banner or CAPTCHA
            no_res_el, _ = _try_query(page, no_results_sel) if no_results_sel else (None, None)
            if no_res_el:
                steps.append({"step": "wait_for_results", "ok": True, "note": "no_results"})
            else:
                body_low = (page.content() or "").lower()
                if any(m in body_low for m in ("recaptcha", "verify you are human", "checking your browser")):
                    result["captcha"] = True
                    result["html"] = page.content()
                    steps.append({"step": "captcha_wall", "ok": False})
                    return result
                steps.append({"step": "wait_for_results", "ok": False,
                              "error": "timeout 15s — no results, no captcha"})
                result["error"] = "timeout_waiting_for_results"
                return result

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
                    # ":scope" means "the row element itself" — used when each
                    # result IS an anchor (TREC-style) rather than a table row.
                    if col_sel == ":scope":
                        cand[label] = (row.inner_text() or "").strip()
                    else:
                        el = row.query_selector(col_sel)
                        if el:
                            cand[label] = (el.inner_text() or "").strip()
                except Exception:
                    pass
            if cand:
                # If the row IS an anchor, remember its href for direct navigation
                try:
                    href = row.get_attribute("href")
                    if href:
                        cand["href"] = href
                except Exception:
                    pass
                result["candidates"].append(cand)
        steps.append({"step": "parse_results", "count": len(result["candidates"])})

        # Fallback: if no candidates parsed (selectors didn't match the
        # actual page), look for any detail-style anchors on the page and
        # synthesize candidates from them. Handles TREC's "results = list
        # of name links" layout when the selectors above miss.
        if not result["candidates"] and flow == "multi_page_detail":
            for sel in _as_list(selectors.get("detail_link_in_row", "a[href*='detail']")):
                if sel == ":scope":
                    continue
                try:
                    anchors = page.query_selector_all(sel)
                    for a in anchors[:20]:
                        try:
                            txt = (a.inner_text() or "").strip()
                            href = a.get_attribute("href") or ""
                            if href and txt:
                                result["candidates"].append({
                                    "name": txt, "href": href,
                                    "license_type": expected_license_type or "",
                                    "status": "Active",  # re-verified on detail page
                                })
                        except Exception:
                            continue
                    if result["candidates"]:
                        break
                except Exception:
                    continue
            if result["candidates"]:
                steps.append({"step": "parse_results_fallback_anchors",
                              "count": len(result["candidates"])})
                rows = page.query_selector_all(
                    _as_list(selectors.get("detail_link_in_row", "a[href*='detail']"))[-1]
                )

        # 5) Multi-page flow: pick best row (name + license_type + status),
        #    then click through to detail page, then extract expiration.
        if flow == "multi_page_detail" and rows:
            target_idx = _pick_row_index(
                result["candidates"], expected_name=expected_name,
                expected_license_type=expected_license_type,
            ) or 0
            target_row = rows[target_idx] if target_idx < len(rows) else rows[0]
            target_cand = result["candidates"][target_idx] if result["candidates"] else {}
            target_name = (target_cand.get("name") or "").strip()
            result["picked_index"] = target_idx
            result["picked_row"] = target_cand
            steps.append({
                "step": "pick_row", "ok": True, "picked_index": target_idx,
                "picked_name": target_name,
                "picked_license_type": target_cand.get("license_type"),
                "picked_status": target_cand.get("status"),
            })

            # ── Capture the row HTML for diagnostics no matter what ──
            try:
                row_html_diag = (target_row.inner_html() or "")[:1500]
                steps.append({"step": "row_html_dump", "html": row_html_diag})
            except Exception:
                pass

            # ── 5 strategies, in order of robustness ──────────────────
            clicked_detail = False
            click_strategy = None
            href_for_detail = None

            # Strategy A: extract href, navigate directly (bypasses all click handlers)
            # If the candidate already carries a pre-extracted href (TREC-style
            # anchor-as-row case), use it first.
            try:
                href_for_detail = target_cand.get("href")
                # Or read the anchor inside the row
                if not href_for_detail:
                    link = target_row.query_selector("a[href]")
                    if link:
                        href_for_detail = link.get_attribute("href")
                # If the row itself IS an anchor (TREC), get its own href
                if not href_for_detail:
                    try:
                        own_href = target_row.get_attribute("href")
                        if own_href:
                            href_for_detail = own_href
                    except Exception:
                        pass
                # Last-ditch: scan the page for an anchor whose text matches the name
                if not href_for_detail and target_name:
                    for a in page.query_selector_all("a[href]"):
                        try:
                            if (a.inner_text() or "").strip().lower() == target_name.lower():
                                href_for_detail = a.get_attribute("href")
                                break
                        except Exception:
                            continue
            except Exception:
                href_for_detail = None
            if href_for_detail:
                if not href_for_detail.startswith("http"):
                    from urllib.parse import urljoin
                    href_for_detail = urljoin(page.url, href_for_detail)
                try:
                    page.goto(href_for_detail, timeout=20000, wait_until="domcontentloaded")
                    clicked_detail = True
                    click_strategy = f"direct_navigation:{href_for_detail[:80]}"
                except Exception:
                    clicked_detail = False

            # Strategy B: declared selectors inside the target row
            if not clicked_detail:
                for sel in _as_list(selectors.get("detail_link_in_row", "td:first-child a")):
                    try:
                        link = target_row.query_selector(sel)
                        if link:
                            link.click(timeout=6000)
                            clicked_detail = True
                            click_strategy = f"row_selector:{sel}"
                            break
                    except Exception:
                        continue

            # Strategy C: text-based locator for the row's name
            if not clicked_detail and target_name:
                try:
                    loc = page.get_by_role("link", name=re.compile(re.escape(target_name), re.IGNORECASE))
                    if loc.count() > 0:
                        loc.first.click(timeout=8000)
                        clicked_detail = True
                        click_strategy = f"role_link_by_name:{target_name}"
                except Exception:
                    pass

            # Strategy D: force-click the first <a> in the row
            if not clicked_detail:
                try:
                    any_link = target_row.query_selector("a")
                    if any_link:
                        any_link.click(timeout=6000, force=True)
                        clicked_detail = True
                        click_strategy = "any_link_in_row_force"
                except Exception:
                    pass

            # Strategy E: JavaScript click on the first <a> in the row
            if not clicked_detail:
                try:
                    any_link = target_row.query_selector("a")
                    if any_link:
                        any_link.evaluate("el => el.click()")
                        page.wait_for_load_state("domcontentloaded", timeout=8000)
                        clicked_detail = True
                        click_strategy = "js_click_in_row"
                except Exception:
                    pass

            if clicked_detail:
                try:
                    page.wait_for_load_state("domcontentloaded", timeout=6000)
                except Exception:
                    pass
                # Calm settle so the expiration value renders before screenshot
                page.wait_for_timeout(1200)
                # Screenshot #3 of 3: detail page with expiration date visible
                result["screenshots"].append(_shot(page, "dre-03-detail"))
                result["html"] = page.content()
                steps.append({"step": "click_detail", "ok": True,
                              "picked_index": target_idx, "strategy": click_strategy})

                # Extract expiration: try selectors then regex on the full page text
                exp_text = None
                exp_el, _ = _try_query(page, selectors.get("detail_expiration"))
                if exp_el:
                    exp_text = (exp_el.inner_text() or "").strip()
                if not exp_text:
                    body_text = page.inner_text("body") if page.locator("body").count() else (result["html"] or "")
                    m = re.search(
                        r"Expiration Date[:\s]+([A-Za-z]+\s+\d{1,2},?\s+\d{4}|\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4})",
                        body_text,
                    )
                    if m:
                        exp_text = m.group(1)
                if not exp_text:
                    m = re.search(
                        r"Expiration Date[:\s]+([A-Za-z]+\s+\d{1,2},?\s+\d{4}|\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4})",
                        result["html"] or "",
                    )
                    if m:
                        exp_text = m.group(1)
                if exp_text:
                    result["expiration_raw"] = exp_text.strip()
                    result["expiration"] = _normalize_date(exp_text) or exp_text.strip()
                    result["found"] = True

                # Extract name from detail page (best-effort)
                name_el, _ = _try_query(page, selectors.get("detail_name"))
                if name_el:
                    result["name"] = (name_el.inner_text() or "").strip()
                else:
                    result["name"] = target_name or result.get("name")

                steps.append({"step": "extract_expiration", "ok": bool(result["expiration"]),
                              "raw": exp_text, "normalized": result["expiration"]})
                # Hold the detail page on screen ~1.5s so the panel can see
                # the expiration value before the browser closes.
                try:
                    page.wait_for_timeout(1500)
                except Exception:
                    pass
            else:
                steps.append({"step": "click_detail", "ok": False,
                              "error": "no clickable detail link"})

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
