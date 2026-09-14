"""Caching infrastructure layer package root."""

from app.cache.exceptions import CacheConnectionError, CacheError, CacheSerializationError
from app.cache.factory import create_cache_service
from app.cache.interfaces import ICache
from app.cache.keys import build_chat_cache_key
from app.cache.memory import InMemoryCache
from app.cache.redis import RedisCacheAdapter

__all__ = [
    "CacheConnectionError",
    "CacheError",
    "CacheSerializationError",
    "ICache",
    "InMemoryCache",
    "RedisCacheAdapter",
    "build_chat_cache_key",
    "create_cache_service",
]
