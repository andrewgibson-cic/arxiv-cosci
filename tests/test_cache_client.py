"""Tests for Redis cache client."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from packages.knowledge.cache_client import CacheClient, cache_query


@pytest.fixture
def cache_client_instance():
    """Create cache client instance for testing."""
    return CacheClient(redis_url="redis://localhost:6379", default_ttl=3600)


class TestCacheClient:
    """Test CacheClient class."""

    def test_init(self, cache_client_instance):
        """Test cache client initialization."""
        assert cache_client_instance.redis_url == "redis://localhost:6379"
        assert cache_client_instance.default_ttl == 3600
        assert cache_client_instance._client is None

    def test_init_with_defaults(self):
        """Test cache client initialization with defaults."""
        client = CacheClient()
        assert client.redis_url == "redis://localhost:6379"
        assert client.default_ttl == 3600

    def test_make_key(self, cache_client_instance):
        """Test cache key generation."""
        query = "MATCH (p:Paper) WHERE p.arxiv_id = $id RETURN p"
        params = {"id": "2024.12345"}

        key1 = cache_client_instance._make_key("papers", query, params)
        key2 = cache_client_instance._make_key("papers", query, params)

        # Same inputs should produce same key
        assert key1 == key2
        assert key1.startswith("arxiv:papers:")
        assert len(key1.split(":")[-1]) == 16  # Hash length

    def test_make_key_deterministic(self, cache_client_instance):
        """Test that cache keys are deterministic."""
        query = "MATCH (p:Paper) RETURN p"
        params1 = {"a": 1, "b": 2}
        params2 = {"b": 2, "a": 1}  # Different order

        key1 = cache_client_instance._make_key("papers", query, params1)
        key2 = cache_client_instance._make_key("papers", query, params2)

        # Should be the same because params are sorted
        assert key1 == key2

    @pytest.mark.asyncio
    async def test_connect(self, cache_client_instance):
        """Test connecting to Redis."""
        with patch("packages.knowledge.cache_client.redis.from_url") as mock_from_url:
            mock_client = AsyncMock()
            mock_from_url.return_value = mock_client

            await cache_client_instance.connect()

            assert cache_client_instance._client is mock_client
            mock_from_url.assert_called_once_with(
                "redis://localhost:6379",
                encoding="utf-8",
                decode_responses=True,
            )

    @pytest.mark.asyncio
    async def test_close(self, cache_client_instance):
        """Test closing Redis connection."""
        mock_client = AsyncMock()
        cache_client_instance._client = mock_client

        await cache_client_instance.close()

        assert cache_client_instance._client is None
        mock_client.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_cache_hit(self, cache_client_instance):
        """Test getting cached value."""
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value='{"result": "cached data"}')
        cache_client_instance._client = mock_client

        result = await cache_client_instance.get(
            "papers",
            "MATCH (p:Paper) RETURN p",
            {"id": "123"},
        )

        assert result == {"result": "cached data"}
        mock_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_cache_miss(self, cache_client_instance):
        """Test cache miss."""
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=None)
        cache_client_instance._client = mock_client

        result = await cache_client_instance.get(
            "papers",
            "MATCH (p:Paper) RETURN p",
            {"id": "123"},
        )

        assert result is None
        mock_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_with_error(self, cache_client_instance):
        """Test get with Redis error."""
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=Exception("Redis error"))
        cache_client_instance._client = mock_client

        result = await cache_client_instance.get("papers", "MATCH p RETURN p", {})

        assert result is None  # Should return None on error

    @pytest.mark.asyncio
    async def test_set(self, cache_client_instance):
        """Test setting cache value."""
        mock_client = AsyncMock()
        mock_client.setex = AsyncMock()
        cache_client_instance._client = mock_client

        success = await cache_client_instance.set(
            "papers",
            "MATCH (p:Paper) RETURN p",
            {"id": "123"},
            {"result": "data"},
            ttl=1800,
        )

        assert success is True
        mock_client.setex.assert_called_once()
        call_args = mock_client.setex.call_args
        assert call_args[0][1] == 1800  # TTL

    @pytest.mark.asyncio
    async def test_set_with_default_ttl(self, cache_client_instance):
        """Test setting cache with default TTL."""
        mock_client = AsyncMock()
        mock_client.setex = AsyncMock()
        cache_client_instance._client = mock_client

        await cache_client_instance.set(
            "papers",
            "MATCH (p:Paper) RETURN p",
            {},
            {"result": "data"},
        )

        call_args = mock_client.setex.call_args
        assert call_args[0][1] == 3600  # Default TTL

    @pytest.mark.asyncio
    async def test_set_with_error(self, cache_client_instance):
        """Test set with Redis error."""
        mock_client = AsyncMock()
        mock_client.setex = AsyncMock(side_effect=Exception("Redis error"))
        cache_client_instance._client = mock_client

        success = await cache_client_instance.set(
            "papers",
            "MATCH p RETURN p",
            {},
            {"data": "test"},
        )

        assert success is False

    @pytest.mark.asyncio
    async def test_delete(self, cache_client_instance):
        """Test deleting cache entry."""
        mock_client = AsyncMock()
        mock_client.delete = AsyncMock()
        cache_client_instance._client = mock_client

        success = await cache_client_instance.delete(
            "papers",
            "MATCH (p:Paper) RETURN p",
            {"id": "123"},
        )

        assert success is True
        mock_client.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_invalidate_prefix(self, cache_client_instance):
        """Test invalidating all keys with prefix."""
        mock_client = AsyncMock()
        
        # Mock scan_iter to return some keys
        async def mock_scan_iter(match):
            for key in ["arxiv:papers:abc123", "arxiv:papers:def456"]:
                yield key
        
        mock_client.scan_iter = mock_scan_iter
        mock_client.delete = AsyncMock(return_value=2)
        cache_client_instance._client = mock_client

        count = await cache_client_instance.invalidate_prefix("papers")

        assert count == 2
        mock_client.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_invalidate_prefix_no_keys(self, cache_client_instance):
        """Test invalidating prefix with no matching keys."""
        mock_client = AsyncMock()
        
        async def mock_scan_iter(match):
            return
            yield  # Make it a generator
        
        mock_client.scan_iter = mock_scan_iter
        cache_client_instance._client = mock_client

        count = await cache_client_instance.invalidate_prefix("papers")

        assert count == 0

    @pytest.mark.asyncio
    async def test_clear_all(self, cache_client_instance):
        """Test clearing all cache entries."""
        mock_client = AsyncMock()
        mock_client.flushdb = AsyncMock()
        cache_client_instance._client = mock_client

        success = await cache_client_instance.clear_all()

        assert success is True
        mock_client.flushdb.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_stats(self, cache_client_instance):
        """Test getting cache statistics."""
        mock_client = AsyncMock()
        mock_client.info = AsyncMock(return_value={
            "keyspace_hits": 1000,
            "keyspace_misses": 200,
        })
        mock_client.dbsize = AsyncMock(return_value=500)
        cache_client_instance._client = mock_client

        stats = await cache_client_instance.get_stats()

        assert stats["hits"] == 1000
        assert stats["misses"] == 200
        assert stats["keys"] == 500
        assert abs(stats["hit_rate"] - 0.833) < 0.01

    @pytest.mark.asyncio
    async def test_get_stats_with_error(self, cache_client_instance):
        """Test getting stats with error."""
        mock_client = AsyncMock()
        mock_client.info = AsyncMock(side_effect=Exception("Redis error"))
        cache_client_instance._client = mock_client

        stats = await cache_client_instance.get_stats()

        assert stats == {}


class TestCacheQueryDecorator:
    """Test cache_query decorator."""

    @pytest.mark.asyncio
    async def test_cache_query_decorator_cache_hit(self):
        """Test decorator with cache hit."""
        with patch("packages.knowledge.cache_client.cache_client") as mock_cache:
            mock_cache.get = AsyncMock(return_value={"result": "cached"})
            mock_cache.set = AsyncMock()

            @cache_query("papers", ttl=1800)
            async def get_paper(arxiv_id: str) -> dict:
                return {"result": "fresh", "id": arxiv_id}

            result = await get_paper("2024.12345")

            assert result == {"result": "cached"}
            mock_cache.get.assert_called_once()
            mock_cache.set.assert_not_called()

    @pytest.mark.asyncio
    async def test_cache_query_decorator_cache_miss(self):
        """Test decorator with cache miss."""
        with patch("packages.knowledge.cache_client.cache_client") as mock_cache:
            mock_cache.get = AsyncMock(return_value=None)
            mock_cache.set = AsyncMock()

            @cache_query("papers", ttl=1800)
            async def get_paper(arxiv_id: str) -> dict:
                return {"result": "fresh", "id": arxiv_id}

            result = await get_paper("2024.12345")

            assert result == {"result": "fresh", "id": "2024.12345"}
            mock_cache.get.assert_called_once()
            mock_cache.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_query_decorator_multiple_args(self):
        """Test decorator with multiple arguments."""
        with patch("packages.knowledge.cache_client.cache_client") as mock_cache:
            mock_cache.get = AsyncMock(return_value=None)
            mock_cache.set = AsyncMock()

            @cache_query("papers")
            async def search_papers(query: str, limit: int = 10) -> list:
                return [f"result_{i}" for i in range(limit)]

            result = await search_papers("quantum", limit=5)

            assert len(result) == 5
            mock_cache.get.assert_called_once()
            mock_cache.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_query_decorator_preserves_function_name(self):
        """Test that decorator preserves function metadata."""
        @cache_query("papers")
        async def get_paper(arxiv_id: str) -> dict:
            """Get a paper by ID."""
            return {"id": arxiv_id}

        assert get_paper.__name__ == "get_paper"
        assert "Get a paper by ID" in get_paper.__doc__


class TestCacheClientIntegration:
    """Integration tests for cache client."""

    @pytest.mark.asyncio
    async def test_full_cache_workflow(self, cache_client_instance):
        """Test complete cache workflow."""
        mock_client = AsyncMock()
        
        # First get returns None (cache miss)
        # Second get returns cached value (cache hit)
        mock_client.get = AsyncMock(side_effect=[None, '{"data": "cached"}'])
        mock_client.setex = AsyncMock()
        cache_client_instance._client = mock_client

        query = "MATCH (p:Paper) RETURN p"
        params = {"id": "123"}

        # First call - cache miss
        result1 = await cache_client_instance.get("papers", query, params)
        assert result1 is None

        # Set value
        await cache_client_instance.set("papers", query, params, {"data": "test"})

        # Second call - cache hit
        result2 = await cache_client_instance.get("papers", query, params)
        assert result2 == {"data": "cached"}

    @pytest.mark.asyncio
    async def test_cache_auto_connect(self, cache_client_instance):
        """Test that cache auto-connects when needed."""
        assert cache_client_instance._client is None

        with patch("packages.knowledge.cache_client.redis.from_url") as mock_from_url:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=None)
            mock_from_url.return_value = mock_client

            await cache_client_instance.get("papers", "MATCH p", {})

            # Should have auto-connected
            assert cache_client_instance._client is mock_client