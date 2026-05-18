"""Fetch + parse a onereal.com agent profile.

The URL pattern is not stable on onereal.com — observed in the wild:
  https://onereal.com/profile/<slug>
  https://onereal.com/<slug>
  https://onereal.com/<slug>/about

So the fetcher walks a list of candidate URLs and returns the first 200.
Parsed fields:
  * full name
  * licensing state (from "Washington - 141102" style strings)
  * license number (the trailing digits)
  * service areas, languages, contact (best-effort)

Caches parsed JSON + raw HTML to data/cache/profiles/ so a re-run survives
network failures during the demo.

Real Playwright fetch is used (so JS-rendered content works on onereal's
SPA). The runner is isolated via the same ProactorEventLoop worker we
use elsewhere (Windows-safe).
"""
from __future__ import annotations

import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from verifier.playwright_runner import (
    _run_in_subprocess,
    _browser,
    _shot,
    playwright_available,
)

CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "cache" / "profiles"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


# ── Public API ────────────────────────────────────────────────────────────

def fetch_profile(
    primary_url: str,
    fallback_urls: Optional[list[str]] = None,
    headed: bool = True,
    slow_mo_ms: int = 200,
    use_cache_first: bool = False,
    cache_only: bool = False,
) -> dict:
    """Fetch + parse an onereal profile.

    Returns:
      {
        ok: bool,
        url_used: str | None,
        name: str | None,
        state_code: str | None,
        state_full_name: str | None,
        license_number: str | None,
        languages: [str],
        service_areas: [str],
        cached: bool,
        html_snippet: str (first 4kb),
        screenshots: [path]
      }
    """
    fallback_urls = fallback_urls or []
    candidates = [primary_url, *fallback_urls]
    cache_key = _cache_key_for(primary_url)
    cache_path = CACHE_DIR / f"{cache_key}.json"

    # Practice/offline mode
    if cache_only or (use_cache_first and cache_path.exists()):
        if cache_path.exists():
            data = json.loads(cache_path.read_text())
            data["cached"] = True
            return data
        if cache_only:
            return _err(primary_url, "no_cache_available")

    # Live fetch
    if not playwright_available():
        if cache_path.exists():
            data = json.loads(cache_path.read_text())
            data["cached"] = True
            return data
        return _err(primary_url, "playwright_not_installed")

    result = _run_in_subprocess("fetch_profile", {
        "candidates": candidates, "headed": headed, "slow_mo_ms": slow_mo_ms,
    }, timeout=60)
    if result.get("ok") is False:
        # Fall back to cache if live fetch failed
        if cache_path.exists():
            data = json.loads(cache_path.read_text())
            data["cached"] = True
            data["live_fetch_error"] = result.get("error")
            return data
        return _err(primary_url, f"fetch_failed: {result.get('error')}")

    # Persist cache on success
    if result.get("ok"):
        cache_path.write_text(json.dumps(result, indent=2))
    return result


# ── Internal: real Playwright fetch ───────────────────────────────────────

def _fetch_profile_impl(candidates: list[str], headed: bool, slow_mo_ms: int) -> dict:
    last_error = None
    with _browser(headed=headed, slow_mo_ms=slow_mo_ms) as page:
        for url in candidates:
            try:
                response = page.goto(url, timeout=20000, wait_until="domcontentloaded")
                if response is None:
                    continue
                status = response.status
                if status == 200:
                    # Let any client-side rendering settle
                    try:
                        page.wait_for_load_state("networkidle", timeout=5000)
                    except Exception:
                        pass
                    html = page.content()
                    title = page.title()
                    sc = _shot(page, f"profile-{_slug_from_url(url)}")
                    parsed = _parse_profile(html, url, title)
                    parsed["screenshots"] = [sc]
                    parsed["url_used"] = url
                    parsed["ok"] = True
                    parsed["cached"] = False
                    parsed["fetched_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
                    return parsed
                if status in (301, 302, 303, 307, 308):
                    continue
                last_error = f"HTTP {status}"
            except Exception as e:  # noqa: BLE001
                last_error = str(e)
                continue
    return _err(candidates[0] if candidates else None, last_error or "all_urls_failed")


# ── Parsing ───────────────────────────────────────────────────────────────

# Match patterns like "Washington - 141102", "California – SL3123456", etc.
LICENSE_PAT = re.compile(
    r"(Alabama|Alaska|Arizona|Arkansas|California|Colorado|Connecticut|Delaware|"
    r"Florida|Georgia|Hawaii|Idaho|Illinois|Indiana|Iowa|Kansas|Kentucky|Louisiana|"
    r"Maine|Maryland|Massachusetts|Michigan|Minnesota|Mississippi|Missouri|Montana|"
    r"Nebraska|Nevada|New\s+Hampshire|New\s+Jersey|New\s+Mexico|New\s+York|"
    r"North\s+Carolina|North\s+Dakota|Ohio|Oklahoma|Oregon|Pennsylvania|"
    r"Rhode\s+Island|South\s+Carolina|South\s+Dakota|Tennessee|Texas|Utah|Vermont|"
    r"Virginia|Washington|West\s+Virginia|Wisconsin|Wyoming)\s*[-–:]\s*"
    r"([A-Z0-9\-]{4,20})",
    re.IGNORECASE,
)

STATE_TO_CODE = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR",
    "california": "CA", "colorado": "CO", "connecticut": "CT", "delaware": "DE",
    "florida": "FL", "georgia": "GA", "hawaii": "HI", "idaho": "ID",
    "illinois": "IL", "indiana": "IN", "iowa": "IA", "kansas": "KS",
    "kentucky": "KY", "louisiana": "LA", "maine": "ME", "maryland": "MD",
    "massachusetts": "MA", "michigan": "MI", "minnesota": "MN", "mississippi": "MS",
    "missouri": "MO", "montana": "MT", "nebraska": "NE", "nevada": "NV",
    "new hampshire": "NH", "new jersey": "NJ", "new mexico": "NM", "new york": "NY",
    "north carolina": "NC", "north dakota": "ND", "ohio": "OH", "oklahoma": "OK",
    "oregon": "OR", "pennsylvania": "PA", "rhode island": "RI",
    "south carolina": "SC", "south dakota": "SD", "tennessee": "TN", "texas": "TX",
    "utah": "UT", "vermont": "VT", "virginia": "VA", "washington": "WA",
    "west virginia": "WV", "wisconsin": "WI", "wyoming": "WY",
}


def _parse_profile(html: str, url: str, title: Optional[str] = None) -> dict:
    # License + state extraction
    state_full = None
    state_code = None
    license_number = None
    m = LICENSE_PAT.search(html)
    if m:
        state_full = re.sub(r"\s+", " ", m.group(1)).strip().title()
        license_number = m.group(2).strip()
        state_code = STATE_TO_CODE.get(state_full.lower())

    # Name — prefer "Hi, I'm <NAME>" heading, else page title, else slug
    name = None
    n = re.search(r"Hi,\s*I'?m\s+([A-Z][A-Za-z\.\-'\s]+?)(?:</|<|My Service|License)", html)
    if n:
        name = n.group(1).strip()
    elif title:
        # title often looks like "<Name> | Real" or just "<Name>"
        name = re.sub(r"\s*[\|·\-–]\s*Real.*$", "", title).strip()

    # Languages
    languages: list[str] = []
    lang_match = re.search(r"Languages?\s*:\s*([A-Za-z, ]+?)(?:<|\n|\.|$)", html, re.IGNORECASE)
    if lang_match:
        languages = [l.strip() for l in lang_match.group(1).split(",") if l.strip()]

    # Service areas (best effort — look near "service area" text)
    areas: list[str] = []
    area_section = re.search(
        r"Service\s*Areas?(.*?)(?:Get\s+In\s+Touch|License\s*#|<footer)",
        html, re.IGNORECASE | re.DOTALL,
    )
    if area_section:
        for tag in re.findall(r">([A-Z][A-Za-z\-\s]+?)<", area_section.group(1)):
            tag = tag.strip()
            if 2 <= len(tag) <= 30 and tag not in ("My Service Areas", "Service Areas"):
                areas.append(tag)
    areas = list(dict.fromkeys(areas))[:6]  # dedupe, cap

    # Contact
    phone = None
    pm = re.search(r"\+?1?\s*\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{4}", html)
    if pm:
        phone = pm.group(0).strip()
    email = None
    em = re.search(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", html)
    if em:
        email = em.group(0)

    return {
        "ok": True,
        "url_used": url,
        "name": name,
        "state_code": state_code,
        "state_full_name": state_full,
        "license_number": license_number,
        "languages": languages,
        "service_areas": areas,
        "phone": phone,
        "email": email,
        "html_snippet": html[:4000],
    }


def _slug_from_url(url: str) -> str:
    parts = url.rstrip("/").split("/")
    # drop trailing /about etc
    for tok in reversed(parts):
        if tok and not tok.startswith("http") and tok not in ("about",):
            return re.sub(r"[^a-zA-Z0-9\-]", "_", tok)[:40]
    return "profile"


def _cache_key_for(url: str) -> str:
    return _slug_from_url(url)


def _err(url: Optional[str], why: str) -> dict:
    return {
        "ok": False, "url_used": url, "error": why,
        "name": None, "state_code": None, "state_full_name": None,
        "license_number": None, "languages": [], "service_areas": [],
        "phone": None, "email": None, "html_snippet": "",
        "screenshots": [], "cached": False,
    }
