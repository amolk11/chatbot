"""Factory for constructing application cache adapter instances."""

import logging

from app.cache.interfaces import ICache
from app.cache.memory import InMemoryCache
from app.cache.redis import RedisCacheAdapter
from app.core.config import Settings

logger = logging.getLogger("app.cache.factory")


def create_cache_service(settings: Settings) -> ICache:
    """Instantiate appropriate ICache implementation based on configuration.

    Args:
        settings: Application Settings instance.

    Returns:
        Configured ICache adapter.
    """
    if not settings.cache_enabled:
        logger.debug("Caching is disabled; using InMemoryCache placeholder")
        return InMemoryCache()

    if settings.redis_url:
        logger.info("Initializing RedisCacheAdapter with configured REDIS_URL")
        return RedisCacheAdapter(redis_url=settings.redis_url)

    logger.warning("Caching is enabled but REDIS_URL is not set; falling back to InMemoryCache")
    return InMemoryCache()
