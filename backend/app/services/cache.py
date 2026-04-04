"""In-memory TTL cache for frequently-accessed, rarely-changing data.

Uses a simple dict + timestamp approach — no external dependencies.
Thread-safe via a lock; cache sizes are bounded to prevent memory leaks.
"""

from __future__ import annotations

import threading
import time
from typing import Any

_lock = threading.Lock()
_cache: dict[str, tuple[float, Any]] = {}  # key → (expires_at, value)

DEFAULT_TTL = 60.0  # seconds
MAX_ENTRIES = 256


def get(key: str) -> Any | None:
    """Return cached value if present and not expired, else None."""
    with _lock:
        entry = _cache.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if time.monotonic() > expires_at:
            del _cache[key]
            return None
        return value


def put(key: str, value: Any, ttl: float = DEFAULT_TTL) -> None:
    """Store a value with a TTL in seconds."""
    with _lock:
        # Evict expired entries if cache is full
        if len(_cache) >= MAX_ENTRIES:
            now = time.monotonic()
            expired = [k for k, (exp, _) in _cache.items() if now > exp]
            for k in expired:
                del _cache[k]
            # If still full, evict oldest entry
            if len(_cache) >= MAX_ENTRIES:
                oldest_key = min(_cache, key=lambda k: _cache[k][0])
                del _cache[oldest_key]
        _cache[key] = (time.monotonic() + ttl, value)


def invalidate(key: str) -> None:
    """Remove a specific key from the cache."""
    with _lock:
        _cache.pop(key, None)


def invalidate_prefix(prefix: str) -> None:
    """Remove all keys starting with the given prefix."""
    with _lock:
        keys = [k for k in _cache if k.startswith(prefix)]
        for k in keys:
            del _cache[k]


def clear() -> None:
    """Clear the entire cache."""
    with _lock:
        _cache.clear()
