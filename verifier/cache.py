"""TTL-bounded selector cache.

Stand-in for the Redis cache in production. Stagehand caches working
selectors so the steady-state path costs ~zero LLM tokens; when a cached
selector misses, the AI re-derives + updates the cache.

Same semantics, in-memory: key -> (value, expires_at).
"""
from __future__ import annotations

import threading
import time
from typing import Any, Optional


class SelectorCache:
    def __init__(self, default_ttl_seconds: int = 3600):
        self._store: dict[str, tuple[Any, float]] = {}
        self._lock = threading.Lock()
        self.default_ttl = default_ttl_seconds
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                self.misses += 1
                return None
            value, expires_at = entry
            if time.time() > expires_at:
                del self._store[key]
                self.misses += 1
                return None
            self.hits += 1
            return value

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        with self._lock:
            expires_at = time.time() + (ttl if ttl is not None else self.default_ttl)
            self._store[key] = (value, expires_at)

    def invalidate(self, key: str) -> None:
        with self._lock:
            self._store.pop(key, None)

    def stats(self) -> dict:
        with self._lock:
            total = self.hits + self.misses
            hit_rate = (self.hits / total) if total else 0.0
            return {
                "size": len(self._store),
                "hits": self.hits,
                "misses": self.misses,
                "hit_rate": hit_rate,
            }


# Process-wide singleton
SELECTOR_CACHE = SelectorCache()
