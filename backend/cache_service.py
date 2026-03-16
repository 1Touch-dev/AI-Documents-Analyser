"""
Redis-based caching service for query results.
Provides 100x speedup for repeated queries.
"""

import hashlib
import json
import logging
from typing import Any, Optional

import redis
from config.settings import settings

logger = logging.getLogger(__name__)


class CacheService:
    """Redis cache for query results with automatic TTL."""

    def __init__(self):
        """Initialize Redis connection."""
        try:
            self.redis_client = redis.from_url(
                settings.redis_url,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2,
            )
            # Test connection
            self.redis_client.ping()
            self.enabled = True
            logger.info("Redis cache connected successfully")
        except Exception as e:
            logger.warning(f"Redis cache disabled: {e}")
            self.redis_client = None
            self.enabled = False

    def _generate_cache_key(
        self,
        question: str,
        model: str,
        top_k: int,
        category: Optional[str] = None,
    ) -> str:
        """Generate a unique cache key from query parameters."""
        key_data = f"{question}:{model}:{top_k}:{category or 'all'}"
        key_hash = hashlib.sha256(key_data.encode()).hexdigest()[:16]
        return f"query:{key_hash}"

    def get(
        self,
        question: str,
        model: str,
        top_k: int,
        category: Optional[str] = None,
    ) -> Optional[dict[str, Any]]:
        """
        Retrieve cached query result.

        Returns None if not found or cache is disabled.
        """
        if not self.enabled:
            return None

        try:
            cache_key = self._generate_cache_key(question, model, top_k, category)
            cached_data = self.redis_client.get(cache_key)

            if cached_data:
                logger.info(f"Cache HIT for query: {question[:50]}...")
                return json.loads(cached_data)
            else:
                logger.debug(f"Cache MISS for query: {question[:50]}...")
                return None
        except Exception as e:
            logger.error(f"Cache retrieval error: {e}")
            return None

    def set(
        self,
        question: str,
        model: str,
        top_k: int,
        result: dict[str, Any],
        category: Optional[str] = None,
        ttl: Optional[int] = None,
    ) -> bool:
        """
        Store query result in cache with TTL.

        Args:
            question: User question
            model: LLM model name
            top_k: Number of retrieved chunks
            result: Query result to cache
            category: Optional category filter
            ttl: Time-to-live in seconds (default: 1 hour)

        Returns:
            True if cached successfully, False otherwise
        """
        if not self.enabled:
            return False

        try:
            cache_key = self._generate_cache_key(question, model, top_k, category)
            ttl = ttl or settings.cache_ttl_seconds

            self.redis_client.setex(
                cache_key,
                ttl,
                json.dumps(result),
            )
            logger.debug(f"Cached query result for {ttl}s: {question[:50]}...")
            return True
        except Exception as e:
            logger.error(f"Cache storage error: {e}")
            return False

    def clear_all(self) -> bool:
        """Clear all cached queries (useful for testing or updates)."""
        if not self.enabled:
            return False

        try:
            # Find all query cache keys
            keys = list(self.redis_client.scan_iter("query:*"))
            if keys:
                self.redis_client.delete(*keys)
                logger.info(f"Cleared {len(keys)} cached queries")
            return True
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
            return False

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        if not self.enabled:
            return {"enabled": False}

        try:
            info = self.redis_client.info("stats")
            return {
                "enabled": True,
                "total_keys": self.redis_client.dbsize(),
                "hits": info.get("keyspace_hits", 0),
                "misses": info.get("keyspace_misses", 0),
                "hit_rate": (
                    info.get("keyspace_hits", 0)
                    / max(info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0), 1)
                    * 100
                ),
            }
        except Exception as e:
            logger.error(f"Cache stats error: {e}")
            return {"enabled": True, "error": str(e)}


# Singleton instance
_cache_service: Optional[CacheService] = None


def get_cache_service() -> CacheService:
    """Get or create the cache service singleton."""
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService()
    return _cache_service
