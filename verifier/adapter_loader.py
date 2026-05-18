"""Per-state DRE adapter loader.

Adapters live as versioned YAML in `verifier/adapters/`. The loader:
  - parses YAML
  - applies URL overrides (so the live demo points at local Flask mocks)
  - exposes a normalized adapter object

In production this same loader reads from S3, with the active version
gated by a feature flag stored in Postgres. Bug in CA? Push a new YAML,
flip the flag, no code deploy.
"""
from __future__ import annotations

import os
from pathlib import Path

import yaml

ADAPTERS_DIR = Path(__file__).resolve().parent / "adapters"


def load_adapter(state_code: str) -> dict:
    """Load + normalize an adapter for the given two-letter state code."""
    path = ADAPTERS_DIR / f"{state_code.lower()}.yaml"
    if not path.exists():
        raise FileNotFoundError(
            f"No DRE adapter for state '{state_code}'. "
            f"In production this would fall through to vision-only mode."
        )
    with open(path) as f:
        cfg = yaml.safe_load(f)

    # Apply URL overrides — in the demo we point search_url at the local
    # Flask mock. Env var pattern: REAL_DRE_BASE_CA=http://127.0.0.1:8802
    env_key = f"REAL_DRE_BASE_{state_code.upper()}"
    if env_key in os.environ:
        cfg["search_url"] = os.environ[env_key].rstrip("/") + cfg.get("search_path", "/")
    return cfg


def list_states() -> list[str]:
    return sorted(
        p.stem.upper() for p in ADAPTERS_DIR.glob("*.yaml")
    )
