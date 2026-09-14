"""Async Redis cache adapter implementation using redis-py."""

import logging
from typing import Any

import redis.asyncio as aioredis
from redis.exceptions import RedisError

from app.cache.exceptions import CacheConnectionError, CacheError
from app.cache.interfaces import ICache

logger = logging.getLogger("app.cache.redis")


class RedisCacheAdapter(ICache):
    """Async Redis cache implementation adhering to the ICache port."""

    def __init__(
        self,
        redis_url: str,
        socket_timeout: float = 2.0,
        socket_connect_timeout: float = 2.0,
        **kwargs: Any,
    ) -> None:
        self._redis_url = redis_url
        self._client = aioredis.from_url(
            redis_url,
            socket_timeout=socket_timeout,
            socket_connect_timeout=socket_connect_timeout,
            decode_responses=True,
            **kwargs,
        )

    async def get(self, key: str) -> str | None:
        """Retrieve cached string value from Redis."""
        try:
            raw_val = await self._client.get(key)
            if raw_val is None:
                return None
            return raw_val.decode("utf-8") if isinstance(raw_val, bytes) else str(raw_val)

        except RedisError as exc:
            logger.warning("Redis GET operation failed for key '%s': %s", key, exc)
            raise CacheConnectionError(f"Redis GET failed: {exc}") from exc
        except Exception as exc:
            logger.error("Unexpected error during Redis GET for key '%s': %s", key, exc)
            raise CacheError(f"Unexpected Redis GET error: {exc}") from exc

    async def set(self, key: str, value: str, ttl: int | None = None) -> None:
        """Store string value in Redis with optional TTL."""
        try:
            if ttl is not None and ttl > 0:
                await self._client.set(name=key, value=value, ex=ttl)
            else:
                await self._client.set(name=key, value=value)
        except RedisError as exc:
            logger.warning("Redis SET operation failed for key '%s': %s", key, exc)
            raise CacheConnectionError(f"Redis SET failed: {exc}") from exc
        except Exception as exc:
            logger.error("Unexpected error during Redis SET for key '%s': %s", key, exc)
            raise CacheError(f"Unexpected Redis SET error: {exc}") from exc

    async def delete(self, key: str) -> None:
        """Delete key from Redis."""
        try:
            await self._client.delete(key)
        except RedisError as exc:
            logger.warning("Redis DELETE operation failed for key '%s': %s", key, exc)
            raise CacheConnectionError(f"Redis DELETE failed: {exc}") from exc
        except Exception as exc:
            logger.error("Unexpected error during Redis DELETE for key '%s': %s", key, exc)
            raise CacheError(f"Unexpected Redis DELETE error: {exc}") from exc

    async def close(self) -> None:
        """Close Redis connection pool gracefully."""
        try:
            await self._client.aclose()
        except Exception as exc:
            logger.warning("Error during Redis client shutdown: %s", exc)
