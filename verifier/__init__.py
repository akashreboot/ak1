"""Real Agent Verification System — runtime package."""
from verifier.db import init_db

# Ensure schema exists the first time anything imports this package.
init_db()
