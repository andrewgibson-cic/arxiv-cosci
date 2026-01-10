"""Redis caching layer for Neo4j query results.

Provides caching for frequent graph queries to reduce database load
and improve response times.
"""

import hashlib
import json
import os
from typing import Any

import redis.asyncio as redis
import structlog

logger = structlog.get_logger()

# Default cache settings
DEFAULT_REDIS_URL = "redis://localhost:6379"
DEFAULT_TTL = 3600  # 1 hour


class CacheClient:
    """Async Redis cache client for Neo4j query results."""

    def __init__(
        self,
        redis_url: str | None = None,
        default_ttl: int = DEFAULT_TTL,
    ) -> None:
        """Initialize cache client.

        Args:
            redis_url: Redis connection URL
            default_ttl: Default time-to-live in seconds
        """
        self.redis_url = redis_url or os.getenv("REDIS_URL", DEFAULT_REDIS_URL)
        self.default_ttl = default_ttl
        self._client: redis.Redis | None = None

    async def connect(self) -> None:
        """Connect to Redis."""
        if not self._client:
            self._client = await redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
            logger.info("redis_connected", url=self.redis_url)

    async def close(self) -> None:
        """Close Redis connection."""
        if self._client:
            await self._client.aclose()
            self._client = None
            logger.info("redis_closed")

    def _make_key(self, prefix: str, query: str, params: dict[str, Any] | None = None) -> str:
        """Generate cache key from query and parameters.

        Args:
            prefix: Key prefix (e.g., "papers", "citations")
            query: Cypher query string
            params: Query parameters

        Returns:
            Cache key
        """
        # Create deterministic hash of query + params
        content = query + json.dumps(params or {}, sort_keys=True)
        hash_value = hashlib.sha256(content.encode()).hexdigest()[:16]
        return f"arxiv:{prefix}:{hash_value}"

    async def get(
        self,
        prefix: str,
        query: str,
        params: dict[str, Any] | None = None,
    ) -> Any | None:
        """Get cached query result.

        Args:
            prefix: Key prefix
            query: Cypher query
            params: Query parameters

        Returns:
            Cached result or None if not found
        """
        if not self._client:
            await self.connect()

        key = self._make_key(prefix, query, params)

        try:
            cached = await self._client.get(key)  # type: ignore
            if cached:
                logger.debug("cache_hit", key=key)
                return json.loads(cached)
            logger.debug("cache_miss", key=key)
            return None
        except Exception as e:
            logger.warning("cache_get_error", error=str(e), key=key)
            return None

    async def set(
        self,
        prefix: str,
        query: str,
        params: dict[str, Any] | None,
        value: Any,
        ttl: int | None = None,
    ) -> bool:
        """Cache query result.

        Args:
            prefix: Key prefix
            query: Cypher query
            params: Query parameters
            value: Result to cache
            ttl: Time-to-live in seconds (uses default if None)

        Returns:
            True if cached successfully
        """
        if not self._client:
            await self.connect()

        key = self._make_key(prefix, query, params)
        ttl = ttl or self.default_ttl

        try:
            serialized = json.dumps(value)
            await self._client.setex(key, ttl, serialized)  # type: ignore
            logger.debug("cache_set", key=key, ttl=ttl)
            return True
        except Exception as e:
            logger.warning("cache_set_error", error=str(e), key=key)
            return False

    async def delete(self, prefix: str, query: str, params: dict[str, Any] | None = None) -> bool:
        """Delete cached query result.

        Args:
            prefix: Key prefix
            query: Cypher query
            params: Query parameters

        Returns:
            True if deleted
        """
        if not self._client:
            await self.connect()

        key = self._make_key(prefix, query, params)

        try:
            await self._client.delete(key)  # type: ignore
            logger.debug("cache_delete", key=key)
            return True
        except Exception as e:
            logger.warning("cache_delete_error", error=str(e), key=key)
            return False

    async def invalidate_prefix(self, prefix: str) -> int:
        """Invalidate all cache keys with given prefix.

        Args:
            prefix: Key prefix to invalidate

        Returns:
            Number of keys deleted
        """
        if not self._client:
            await self.connect()

        pattern = f"arxiv:{prefix}:*"

        try:
            keys = []
            async for key in self._client.scan_iter(match=pattern):  # type: ignore
                keys.append(key)

            if keys:
                count = await self._client.delete(*keys)  # type: ignore
                logger.info("cache_invalidated", prefix=prefix, count=count)
                return count
            return 0
        except Exception as e:
            logger.warning("cache_invalidate_error", error=str(e), prefix=prefix)
            return 0

    async def clear_all(self) -> bool:
        """Clear all cache entries.

        Returns:
            True if successful
        """
        if not self._client:
            await self.connect()

        try:
            await self._client.flushdb()  # type: ignore
            logger.info("cache_cleared")
            return True
        except Exception as e:
            logger.warning("cache_clear_error", error=str(e))
            return False

    async def get_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        if not self._client:
            await self.connect()

        try:
            info = await self._client.info("stats")  # type: ignore
            return {
                "hits": info.get("keyspace_hits", 0),
                "misses": info.get("keyspace_misses", 0),
                "hit_rate": (
                    info.get("keyspace_hits", 0)
                    / max(info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0), 1)
                ),
                "keys": await self._client.dbsize(),  # type: ignore
            }
        except Exception as e:
            logger.warning("cache_stats_error", error=str(e))
            return {}


# Global cache client instance
cache_client = CacheClient()


def cache_query(
    prefix: str,
    ttl: int | None = None,
):
    """Decorator to cache async function results.

    Args:
        prefix: Cache key prefix
        ttl: Time-to-live in seconds

    Example:
        @cache_query("papers", ttl=1800)
        async def get_paper(arxiv_id: str) -> dict:
            # Query Neo4j
            ...
    """
    from functools import wraps

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Create cache key from function name and arguments
            query_str = f"{func.__name__}:{args}:{kwargs}"
            params = {"args": str(args), "kwargs": str(kwargs)}

            # Try to get from cache
            cached = await cache_client.get(prefix, query_str, params)
            if cached is not None:
                return cached

            # Execute function
            result = await func(*args, **kwargs)

            # Cache result
            await cache_client.set(prefix, query_str, params, result, ttl)

            return result

        return wrapper

    return decorator