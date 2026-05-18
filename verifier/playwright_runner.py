"""Real Playwright wrapper for the verification workflow.

The browser is REAL Chromium (headed by default for the demo so the panel
can watch the page get driven). When Playwright isn't installed we degrade
to a deterministic offline mode that still produces a workable trace.

Windows + Python 3.9 note: Streamlit installs a SelectorEventLoop on its
script thread; Playwright needs to spawn Chromium via asyncio subprocess,
which requires ProactorEventLoop on Windows. We isolate Playwright in a
dedicated worker thread that owns its own ProactorEventLoop.

Two flows are exposed:
  - join_real_lookup(...)       — search agent by name on local JoinReal mock
  - dre_lookup(...)             — fill license # on a state DRE mock,
                                  extract expiration date, capture screenshot
"""
from __future__ import annotations

import asyncio
import sys
import threading
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Optional

from verifier.cache import SELECTOR_CACHE

SCREENSHOTS_DIR = Path(__file__).resolve().parent.parent / "data" / "screenshots"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)


def playwright_available() -> bool:
    try:
        import playwright.sync_api  # noqa: F401
        return True
    except Exception:
        return False


# ── Isolated execution: Windows-safe event loop for Playwright ────────────

def _run_playwright_isolated(fn: Callable, *args, **kwargs) -> Any:
    """Run a Playwright sync_api call in a dedicated thread with its own loop.

    Why: Streamlit's script thread on Windows has a SelectorEventLoop that
    can't spawn subprocesses. Playwright spawns Chromium via asyncio.
    Solution: dedicated thread, fresh ProactorEventLoop on Windows.
    """
    result: dict = {"value": None, "error": None}

    def worker() -> None:
        try:
            if sys.platform == "win32":
                # ProactorEventLoop is required for subprocess_exec on Windows.
                loop = asyncio.ProactorEventLoop()  # type: ignore[attr-defined]
            else:
                loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result["value"] = fn(*args, **kwargs)
            finally:
                try:
                    loop.close()
                except Exception:
                    pass
        except Exception as e:  # noqa: BLE001
            result["error"] = e

    t = threading.Thread(target=worker, name="playwright-worker", daemon=False)
    t.start()
    t.join()

    if result["error"] is not None:
        raise result["error"]
    return result["value"]


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
    try:
        return _run_playwright_isolated(
            _join_real_lookup_impl, name, base_url, headed, slow_mo_ms,
        )
    except Exception as e:  # noqa: BLE001
        # Last-resort safety: fall back to offline so the workflow keeps moving.
        print(f"[playwright_runner] join_real_lookup fell back to offline: {e}")
        return _offline_joinreal(name)


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
) -> dict:
    """Drive a state DRE mock — fill license #, extract expiration."""
    if not playwright_available():
        return _offline_dre(license_no, base_url)
    try:
        return _run_playwright_isolated(
            _dre_lookup_impl, license_no, base_url, selectors, headed, slow_mo_ms,
        )
    except Exception as e:  # noqa: BLE001
        print(f"[playwright_runner] dre_lookup fell back to offline: {e}")
        return _offline_dre(license_no, base_url)


def _dre_lookup_impl(
    license_no: str, base_url: str, selectors: dict, headed: bool, slow_mo_ms: int,
) -> dict:
    result: dict = {
        "license_no": license_no, "found": False, "name": None,
        "expiration": None, "captcha": False, "html": None, "screenshots": [],
    }

    with _browser(headed=headed, slow_mo_ms=slow_mo_ms) as page:
        page.goto(base_url, timeout=15000)
        result["screenshots"].append(_shot(page, "dre-landing"))

        # Detect CAPTCHA wall (Hawaii path)
        if page.query_selector('[data-captcha-wall]'):
            result["captcha"] = True
            result["html"] = page.content()
            return result

        page.fill(selectors["license_input"], license_no)
        try:
            page.click(selectors["submit_button"], timeout=3000)
        except Exception:
            # Form submission via Enter as a fallback
            page.press(selectors["license_input"], "Enter")
        page.wait_for_load_state("domcontentloaded", timeout=10000)
        result["screenshots"].append(_shot(page, "dre-results"))

        if page.query_selector(selectors.get("no_results_marker", "[data-no-results]")):
            result["html"] = page.content()
            return result

        exp_el = page.query_selector(selectors["expiration_field"])
        name_el = page.query_selector(selectors.get("agent_name_field", '[data-field="name"]'))
        if exp_el:
            result["found"] = True
            result["expiration"] = (exp_el.inner_text() or "").strip()
        if name_el:
            result["name"] = (name_el.inner_text() or "").strip()
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


def _offline_dre(license_no: str, base_url: str) -> dict:
    from verifier.fixtures import SAMPLE_AGENTS
    time.sleep(0.8)
    agent = next((a for a in SAMPLE_AGENTS if a["license_no"] == license_no), None)
    if not agent:
        return {"license_no": license_no, "found": False, "expiration": None, "captcha": False,
                "html": None, "screenshots": [], "offline": True}
    if agent["state"] == "HI":
        return {"license_no": license_no, "found": False, "expiration": None, "captcha": True,
                "html": "<html data-captcha-wall></html>", "screenshots": [], "offline": True}
    exp = agent["expires_at"] if agent["state"] != "TX" else "2027-11-22"
    html = f'<html><body><div data-field="expiration">{exp}</div><div data-field="name">{agent["name"]}</div></body></html>'
    return {"license_no": license_no, "found": True, "expiration": exp, "name": agent["name"],
            "captcha": False, "html": html, "screenshots": [], "offline": True}
