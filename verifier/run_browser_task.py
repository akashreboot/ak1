"""CLI worker for browser automation tasks.

Runs Playwright / Camoufox in a SEPARATE Python subprocess so its asyncio
event-loop policy isn't polluted by Streamlit/Tornado. On Windows this
matters: Tornado installs WindowsSelectorEventLoopPolicy globally, and a
SelectorEventLoop can't spawn subprocesses — which Playwright needs to
launch Chromium. Running in a fresh subprocess gives us the default
WindowsProactorEventLoopPolicy and everything works.

Protocol: JSON via stdin → JSON via stdout. Errors → stderr + exit 1.

Invocation:
    echo '{"task": "fetch_profile", "args": {...}}' | python -m verifier.run_browser_task
"""
from __future__ import annotations

import json
import sys
import traceback


def main() -> None:
    spec = json.loads(sys.stdin.read())
    task = spec["task"]
    args = spec.get("args", {})

    if task == "fetch_profile":
        from verifier.profile_fetcher import _fetch_profile_impl
        result = _fetch_profile_impl(**args)
    elif task == "dre_lookup":
        from verifier.playwright_runner import _dre_lookup_impl
        result = _dre_lookup_impl(**args)
    elif task == "join_real_lookup":
        from verifier.playwright_runner import _join_real_lookup_impl
        result = _join_real_lookup_impl(**args)
    elif task == "dre_lookup_camoufox":
        from verifier.runners.camoufox_runner import _dre_lookup_camoufox_impl
        result = _dre_lookup_camoufox_impl(**args)
    else:
        raise ValueError(f"unknown task: {task}")

    sys.stdout.write(json.dumps(result, default=str))
    sys.stdout.flush()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # noqa: BLE001
        sys.stderr.write(json.dumps({
            "ok": False,
            "error": f"{type(e).__name__}: {e}",
            "traceback": traceback.format_exc(),
        }))
        sys.exit(1)
