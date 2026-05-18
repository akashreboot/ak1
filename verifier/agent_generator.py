"""Generate the 100-agent fixture used by the Newly Joined page.

Deterministic (seeded) so every CI run produces the same dataset.

Layout:
  * 100 agents total
  * 80 "steady state" — verified ≥ 30 days ago
  * 20 "newly joined" — active flag flipped to True within the last 7 days
  * 3 demo agents (from data/demo_agents.json) are inserted into the newly-joined batch
    so the panel can watch the real onereal.com flow run for them
"""
from __future__ import annotations

import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
OUT_PATH = DATA_DIR / "agents.json"
DEMO_PATH = DATA_DIR / "demo_agents.json"


FIRST_NAMES = [
    "Amelia", "Olivia", "Liam", "Noah", "Sofia", "Mateo", "Ava", "Lucas",
    "Mia", "Ethan", "Isabella", "Aiden", "Camila", "Jayden", "Aria", "Carter",
    "Diego", "Yuki", "Priya", "Wei", "Aisha", "Hiro", "Layla", "Riley",
    "Naomi", "Caleb", "Esther", "Oliver", "Maya", "Asher", "Hannah", "Jack",
    "Zoe", "Kai", "Lila", "Ezra", "Lena", "Rohan", "Anika", "Sam", "Maya",
    "Jordan", "Maria", "Tomas", "Elena", "Ravi", "Akira", "Nina", "Soren",
    "Iris",
]
LAST_NAMES = [
    "Rivera", "Garcia", "Smith", "Johnson", "Brown", "Davis", "Wilson",
    "Anderson", "Taylor", "Thomas", "Hernandez", "Moore", "Jackson",
    "Martin", "Lee", "Perez", "White", "Chen", "Patel", "Kim", "Nguyen",
    "Singh", "Khan", "Yamamoto", "Tanaka", "Cohen", "Reyes", "Diaz",
    "Park", "Liu", "Wang", "Lopez", "Ramirez", "Carter", "Mitchell",
    "Roberts", "Phillips", "Campbell", "Parker", "Evans",
]

STATE_DATA = {
    "CA": {
        "full": "California",
        "license_prefix": "021",
        "license_type": "Real Estate Salesperson",
        "cities": ["Los Angeles", "San Diego", "San Francisco", "San Jose", "Sacramento"],
        "areas": [["Los Angeles", "Orange"], ["San Diego"], ["San Francisco", "San Mateo"], ["Santa Clara"], ["Sacramento", "Placer"]],
    },
    "TX": {
        "full": "Texas",
        "license_prefix": "07",
        "license_type": "Sales Agent",
        "cities": ["Houston", "Dallas", "Austin", "San Antonio", "Fort Worth"],
        "areas": [["Harris"], ["Dallas", "Collin"], ["Travis", "Williamson"], ["Bexar"], ["Tarrant"]],
    },
    "WA": {
        "full": "Washington",
        "license_prefix": "14",
        "license_type": "Real Estate Broker",
        "cities": ["Seattle", "Bellevue", "Tacoma", "Spokane", "Everett"],
        "areas": [["King"], ["King"], ["Pierce"], ["Spokane"], ["Snohomish", "King"]],
    },
    "NY": {
        "full": "New York",
        "license_prefix": "10",
        "license_type": "Real Estate Salesperson",
        "cities": ["New York", "Brooklyn", "Queens", "Buffalo", "Albany"],
        "areas": [["Manhattan"], ["Brooklyn"], ["Queens"], ["Erie"], ["Albany"]],
    },
    "FL": {
        "full": "Florida",
        "license_prefix": "SL3",
        "license_type": "Real Estate Sales Associate",
        "cities": ["Miami", "Orlando", "Tampa", "Jacksonville", "Fort Lauderdale"],
        "areas": [["Miami-Dade"], ["Orange"], ["Hillsborough"], ["Duval"], ["Broward"]],
    },
}

# Distribution: heavy on the 3 demo states (CA/TX/WA) so the panel sees realistic mix
STATE_WEIGHTS = {"CA": 28, "TX": 28, "WA": 24, "NY": 12, "FL": 8}


def _slug(first: str, last: str, n: int) -> str:
    base = f"{first}-{last}".lower().replace(" ", "-")
    return base if n == 0 else f"{base}-{n}"


def _phone(rng: random.Random, state: str) -> str:
    area_code = {"CA": "415", "TX": "512", "WA": "206", "NY": "212", "FL": "305"}[state]
    return f"+1 ({area_code}) {rng.randint(200,999)}-{rng.randint(1000,9999)}"


def _license_no(rng: random.Random, state: str) -> str:
    prefix = STATE_DATA[state]["license_prefix"]
    if state == "FL":
        return f"{prefix}{rng.randint(100000, 999999)}"
    return f"{prefix}{rng.randint(100000, 999999)}"


def _expiration(rng: random.Random, joined_at: datetime, valid: bool) -> str:
    """Future date for active; near-past for stale outliers."""
    if valid:
        delta_days = rng.randint(365, 365 * 3)
    else:
        delta_days = -rng.randint(30, 90)
    return (joined_at + timedelta(days=delta_days)).strftime("%Y-%m-%d")


def generate(seed: int = 7, total: int = 100, newly_joined: int = 20) -> list[dict]:
    rng = random.Random(seed)
    now = datetime.now(timezone.utc)
    used_slugs: dict[str, int] = {}
    agents: list[dict] = []

    state_pool: list[str] = []
    for state, weight in STATE_WEIGHTS.items():
        state_pool.extend([state] * weight)

    for i in range(total):
        is_new = i < newly_joined
        state = state_pool[i % len(state_pool)]
        state_info = STATE_DATA[state]
        first = rng.choice(FIRST_NAMES)
        last = rng.choice(LAST_NAMES)
        full = f"{first} {last}"
        base = f"{first}-{last}".lower()
        used_slugs[base] = used_slugs.get(base, 0) + 1
        slug = _slug(first, last, used_slugs[base] - 1)

        if is_new:
            joined_at = now - timedelta(days=rng.randint(0, 6), hours=rng.randint(0, 23))
            active_since = joined_at + timedelta(minutes=rng.randint(5, 90))
            verification_status = "pending"
        else:
            joined_at = now - timedelta(days=rng.randint(30, 800))
            active_since = joined_at + timedelta(minutes=rng.randint(5, 240))
            verification_status = rng.choices(
                ["match", "match", "match", "match", "match", "match", "match",
                 "mismatch", "hitl"], k=1
            )[0]

        area_idx = rng.randint(0, len(state_info["areas"]) - 1)

        agents.append({
            "agent_id": f"A-{state}-{1000 + i:04d}",
            "external_ids": {"crm_id": f"crm_{rng.randint(100000, 999999)}"},
            "name": {"full": full, "first": first, "last": last},
            "slug": slug,
            "profile_url": f"https://onereal.com/profile/{slug}",
            "onboarding": {
                "joined_at": joined_at.isoformat(timespec="seconds"),
                "active": True,
                "active_since": active_since.isoformat(timespec="seconds"),
                "onboarding_event_id": f"evt-{joined_at.strftime('%Y%m%d')}-A-{state}-{i:04d}",
                "newly_joined": is_new,
            },
            "license": {
                "number": _license_no(rng, state),
                "state_code": state,
                "state_full_name": state_info["full"],
                "type": state_info["license_type"],
                "expires_at": _expiration(rng, joined_at, valid=True),
            },
            "profile": {
                "service_areas": state_info["areas"][area_idx],
                "languages": rng.choice([
                    ["English"], ["English", "Spanish"], ["English", "Mandarin"],
                    ["English", "Korean"], ["English", "Vietnamese"],
                ]),
                "city": state_info["cities"][area_idx],
            },
            "contact": {
                "phone": _phone(rng, state),
                "email": f"{slug.replace('-', '.')}@example.com",
                "website": None,
            },
            "verification": {
                "status": verification_status,
                "last_verified_at": (
                    (joined_at + timedelta(days=rng.randint(1, 30))).isoformat(timespec="seconds")
                    if not is_new else None
                ),
                "last_run_id": None,
            },
        })

    # Splice in the 3 real demo agents at the head of the newly-joined block.
    if DEMO_PATH.exists():
        demo_cfg = json.loads(DEMO_PATH.read_text())
        for j, demo in enumerate(demo_cfg["agents"]):
            state = demo["expected"]["state_code"]
            state_info = STATE_DATA.get(state, STATE_DATA["CA"])
            joined_at = now - timedelta(days=rng.randint(0, 2), hours=rng.randint(0, 23))
            real_agent = {
                "agent_id": demo["agent_id"],
                "external_ids": {"crm_id": f"crm_demo_{j+1}", "demo_id": demo["demo_id"]},
                "name": demo["name"],
                "slug": demo["slug"],
                "profile_url": demo["profile_url"],
                "fallback_profile_urls": demo.get("fallback_profile_urls", []),
                "onboarding": {
                    "joined_at": joined_at.isoformat(timespec="seconds"),
                    "active": True,
                    "active_since": (joined_at + timedelta(minutes=30)).isoformat(timespec="seconds"),
                    "onboarding_event_id": f"evt-demo-{demo['demo_id']}",
                    "newly_joined": True,
                    "is_real_demo_target": True,
                },
                "license": {
                    "number": demo["expected"].get("license_number_hint"),
                    "state_code": state,
                    "state_full_name": demo["expected"]["state_full_name"],
                    "type": demo["expected"]["license_type"],
                    "expires_at": None,
                },
                "profile": {
                    "service_areas": state_info["areas"][0],
                    "languages": ["English"],
                    "city": state_info["cities"][0],
                },
                "contact": {"phone": None, "email": None, "website": None},
                "verification": {"status": "pending", "last_verified_at": None, "last_run_id": None},
                "demo_label": demo["demo_label"],
                "scenario": demo["scenario"],
            }
            # Replace one of the synthetic newly-joined slots with the real agent
            agents[j] = real_agent

    return agents


def write_fixture() -> Path:
    agents = generate()
    OUT_PATH.write_text(json.dumps({"agents": agents}, indent=2))
    return OUT_PATH


if __name__ == "__main__":
    p = write_fixture()
    print(f"Wrote {p} ({len(json.loads(p.read_text())['agents'])} agents)")
