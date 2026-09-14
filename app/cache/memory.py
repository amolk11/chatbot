"""In-memory cache adapter for deterministic offline testing and development."""

import time
from dataclasses import dataclass

from app.cache.interfaces import ICache


@dataclass
class _CacheEntry:
    value: str
    expires_at: float | None = None

    def is_expired(self, current_time: float) -> bool:
        if self.expires_at is None:
            return False
        return current_time > self.expires_at


class InMemoryCache(ICache):
    """In-memory dictionary cache implementing ICache with TTL expiration."""

    def __init__(self) -> None:
        self._store: dict[str, _CacheEntry] = {}

    async def get(self, key: str) -> str | None:
        """Retrieve value if present and unexpired."""
        entry = self._store.get(key)
        if entry is None:
            return None

        now = time.monotonic()
        if entry.is_expired(now):
            del self._store[key]
            return None

        return entry.value

    async def set(self, key: str, value: str, ttl: int | None = None) -> None:
        """Store value with optional TTL in seconds."""
        now = time.monotonic()
        expires_at = (now + ttl) if (ttl is not None and ttl > 0) else None
        self._store[key] = _CacheEntry(value=value, expires_at=expires_at)

    async def delete(self, key: str) -> None:
        """Remove key from in-memory store."""
        self._store.pop(key, None)

    async def close(self) -> None:
        """Clear in-memory store."""
        self._store.clear()
