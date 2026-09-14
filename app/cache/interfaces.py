"""Cache port interface definition following hexagonal architecture."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class ICache(Protocol):
    """Abstract cache port defining asynchronous key-value cache operations."""

    async def get(self, key: str) -> str | None:
        """Retrieve a cached string value by key.

        Args:
            key: Unique cache key.

        Returns:
            Cached string payload if found and unexpired, None otherwise.
        """
        ...

    async def set(self, key: str, value: str, ttl: int | None = None) -> None:
        """Store a string value in cache with an optional Time-To-Live.

        Args:
            key: Unique cache key.
            value: String value payload to store.
            ttl: Optional Time-To-Live in seconds.
        """
        ...

    async def delete(self, key: str) -> None:
        """Remove a cached key if present.

        Args:
            key: Cache key to evict.
        """
        ...

    async def close(self) -> None:
        """Gracefully release and close underlying cache resources."""
        ...
