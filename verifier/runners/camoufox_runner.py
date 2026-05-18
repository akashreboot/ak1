"""Camoufox runner — T2 stealth tier.

Camoufox is a Firefox fork with C++-level fingerprint patches (0% headless
detection rate as of 2026). Same Playwright sync API, different launcher.

Falls back to plain Playwright if Camoufox isn't installed — the trace
will narrate the fallback so the panel sees what happened.
"""
from __future__ import annotations

import uuid
from pathlib import Path
from typing import Optional

from verifier.playwright_runner import (
    _run_in_subprocess,
    _shot,
    SCREENSHOTS_DIR,
    playwright_available,
)


def camoufox_available() -> bool:
    """Returns True only when BOTH the Python module AND the Firefox binary
    are present. Without the binary, Camoufox launches fail with
    'executable doesn't exist'. Detecting that here lets the router fall
    straight to plain Playwright (which is REAL and visible) rather than
    losing time on a subprocess that's guaranteed to crash."""
    try:
        import camoufox  # noqa: F401
    except Exception:
        return False
    # Check that the Firefox binary has been fetched (`python -m camoufox fetch`)
    try:
        import os
        import sys
        from pathlib import Path
        if sys.platform == "win32":
            cache = Path(os.environ.get("LOCALAPPDATA", "")) / "camoufox" / "camoufox" / "Cache"
            exe = cache / "camoufox.exe"
        elif sys.platform == "darwin":
            exe = Path.home() / "Library" / "Caches" / "camoufox" / "camoufox"
        else:
            exe = Path.home() / ".cache" / "camoufox" / "camoufox"
        return exe.exists()
    except Exception:
        # If we can't check, assume not available — better to use the
        # known-good plain-Playwright path than to crash on launch.
        return False


# ── DRE lookup using Camoufox ─────────────────────────────────────────────

def dre_lookup_stealth(
    license_no: str,
    base_url: str,
    selectors: dict,
    headed: bool = True,
    slow_mo_ms: int = 250,
    flow=None,
    state_code=None,
) -> dict:
    """Drive a DRE site through Camoufox (Firefox + stealth patches).

    Fallback chain (no silent hardcoded substitution):
      1. Camoufox (T2 stealth) — if Python module installed AND binary fetched
      2. Plain Playwright Chromium (T1) — real visible browser, may hit CAPTCHA
      3. _offline_dre — ONLY when Playwright itself isn't installed at all
      4. Subprocess failure → propagate error so caller routes to HITL
    """
    pw_args = {
        "license_no": license_no, "base_url": base_url, "selectors": selectors,
        "headed": headed, "slow_mo_ms": slow_mo_ms, "flow": flow, "state_code": state_code,
    }

    # ── Step 1: try Camoufox if available ────────────────────────────
    if camoufox_available():
        result = _run_in_subprocess(
            "dre_lookup_camoufox", pw_args, timeout=200,
        )
        if result.get("ok") is not False:
            result["runner"] = result.get("runner") or "camoufox"
            return result
        # Camoufox subprocess failed (e.g. binary not fetched, OS incompatibility).
        # Don't fake a result — fall through to plain Playwright (still a REAL browser).
        print(f"[camoufox] launch failed; falling back to plain Playwright. error: {result.get('error', '')[:160]}")

    # ── Step 2: plain Playwright (real Chromium, no stealth) ─────────
    if playwright_available():
        result = _run_in_subprocess("dre_lookup", pw_args, timeout=200)
        if result.get("ok") is not False:
            result["runner"] = "playwright-fallback-from-camoufox"
            return result
        # Real subprocess failure — propagate honestly, do NOT fake.
        return {
            "license_no": license_no, "found": False, "name": None,
            "expiration": None, "captcha": "captcha" in (result.get("error") or "").lower(),
            "html": None, "screenshots": [], "candidates": [],
            "error": result.get("error"),
            "_subprocess_failed": True, "runner": "playwright-fallback-from-camoufox",
        }

    # ── Step 3: Playwright not installed at all — synthesize ──────────
    from verifier.playwright_runner import _offline_dre
    return _offline_dre(license_no, base_url, state_code=state_code)


def _dre_lookup_camoufox_impl(
    license_no: str, base_url: str, selectors: dict, headed: bool, slow_mo_ms: int,
    flow=None, state_code=None,
) -> dict:
    from camoufox.sync_api import Camoufox  # type: ignore

    result: dict = {
        "license_no": license_no, "found": False, "name": None,
        "expiration": None, "captcha": False, "html": None, "screenshots": [],
        "candidates": [], "runner": "camoufox",
    }

    # NOTE: geoip=True requires the `camoufox[geoip]` extra; we don't depend on
    # it. Plain Camoufox still gives us the full Firefox stealth fingerprint.
    with Camoufox(headless=not headed) as browser:
        page = browser.new_page()
        page.goto(base_url, timeout=25000, wait_until="domcontentloaded")
        sc = _shot(page, "dre-camoufox-landing")
        result["screenshots"].append(sc)

        # Salesforce / SPA support: wait for likely interactive shell
        try:
            page.wait_for_load_state("networkidle", timeout=8000)
        except Exception:
            pass

        # Detect Cloudflare or CAPTCHA wall first
        body_text = (page.content() or "")[:8000].lower()
        if "checking your browser" in body_text or "cloudflare" in body_text and "challenge" in body_text:
            result["captcha"] = True
            result["html"] = page.content()
            return result

        # Fill license number (use cached or declared selector + AI fallback hint)
        license_selector = selectors.get("license_input")
        if license_selector:
            try:
                page.fill(license_selector, license_no, timeout=8000)
            except Exception:
                # Try a generic input fallback
                page.fill("input[type='text']", license_no)
        try:
            submit_selector = selectors.get("submit_button", "button[type='submit']")
            page.click(submit_selector, timeout=5000)
        except Exception:
            page.keyboard.press("Enter")

        try:
            page.wait_for_load_state("networkidle", timeout=10000)
        except Exception:
            pass
        sc = _shot(page, "dre-camoufox-results")
        result["screenshots"].append(sc)

        result["html"] = page.content()
        # Light table scrape — production code uses the adapter to define columns.
        rows = page.query_selector_all("table tr, [role='row']")
        for row in rows[:25]:
            cells = row.query_selector_all("td, [role='cell']")
            if len(cells) >= 3:
                cell_texts = [(c.inner_text() or "").strip() for c in cells]
                result["candidates"].append({"cells": cell_texts})

    return result
