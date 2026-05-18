"""Sample agents for the live demo.

Three deliberately-shaped cases:
  1. Happy path — everything matches, fast verify.
  2. Mismatch — DRE expiration differs from CRM (the classic compliance miss).
  3. Quirky state — Hawaii, where the DRE site requires HITL (CAPTCHA on real site).
"""
from __future__ import annotations

SAMPLE_AGENTS = [
    {
        "agent_id": "A-CA-3304",
        "name": "Jordan A. Rivera",
        "state": "CA",
        "license_no": "02145778",
        "expires_at": "2027-03-14",
        "onboarded_at": "2026-05-17T13:42:08Z",
        "scenario": "happy_path",
        "description": "California agent · everything matches · happy path",
    },
    {
        "agent_id": "A-TX-8814",
        "name": "Maria Q. Delgado",
        "state": "TX",
        "license_no": "0712334",
        "expires_at": "2026-11-22",
        "onboarded_at": "2026-05-17T14:08:31Z",
        "scenario": "mismatch",
        "description": "Texas agent · CRM and DRE disagree on expiration (compliance flag)",
    },
    {
        "agent_id": "A-HI-0042",
        "name": "Wei Chen",
        "state": "HI",
        "license_no": "RB-22041",
        "expires_at": "2028-01-09",
        "onboarded_at": "2026-05-17T14:21:55Z",
        "scenario": "captcha_hitl",
        "description": "Hawaii agent · DRE blocked by CAPTCHA · routed to HITL",
    },
]


def get_agent(agent_id: str) -> dict:
    for a in SAMPLE_AGENTS:
        if a["agent_id"] == agent_id:
            return dict(a)
    raise KeyError(agent_id)
