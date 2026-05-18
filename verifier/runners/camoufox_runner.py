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
    _run_playwright_isolated,
    _shot,
    SCREENSHOTS_DIR,
    playwright_available,
)


def camoufox_available() -> bool:
    try:
        import camoufox  # noqa: F401
        return True
    except Exception:
        return False


# ── DRE lookup using Camoufox ─────────────────────────────────────────────

def dre_lookup_stealth(
    license_no: str,
    base_url: str,
    selectors: dict,
    headed: bool = True,
    slow_mo_ms: int = 250,
) -> dict:
    """Drive a DRE site through Camoufox (Firefox + stealth patches)."""
    if not camoufox_available():
        # Fall back to plain Playwright. Caller's trace should note this.
        if not playwright_available():
            from verifier.playwright_runner import _offline_dre
            return _offline_dre(license_no, base_url)
        from verifier.playwright_runner import _dre_lookup_impl
        return _run_playwright_isolated(
            _dre_lookup_impl, license_no, base_url, selectors, headed, slow_mo_ms,
        )

    try:
        return _run_playwright_isolated(
            _dre_lookup_camoufox_impl, license_no, base_url, selectors, headed, slow_mo_ms,
        )
    except Exception as e:  # noqa: BLE001
        print(f"[camoufox_runner] dre_lookup_stealth fell back: {e}")
        from verifier.playwright_runner import _offline_dre
        return _offline_dre(license_no, base_url)


def _dre_lookup_camoufox_impl(
    license_no: str, base_url: str, selectors: dict, headed: bool, slow_mo_ms: int,
) -> dict:
    from camoufox.sync_api import Camoufox  # type: ignore

    result: dict = {
        "license_no": license_no, "found": False, "name": None,
        "expiration": None, "captcha": False, "html": None, "screenshots": [],
        "candidates": [], "runner": "camoufox",
    }

    with Camoufox(headless=not headed, geoip=True) as browser:
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
