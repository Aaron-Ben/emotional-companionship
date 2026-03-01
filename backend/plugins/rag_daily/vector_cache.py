"""
Vector Cache Module for RAG Daily Plugin.

Implements LRU cache with persistent storage for embedding vectors.
Reduces API calls by caching frequently used vectors.
"""

import hashlib
import json
import time
from typing import Dict, List, Optional, Any
from pathlib import Path
from collections import OrderedDict
import numpy as np
import logging

logger = logging.getLogger(__name__)


class VectorCache:
    """
    LRU cache for embedding vectors with persistent storage.

    Features:
    - LRU eviction policy
    - Persistent JSON storage
    - Hash-based key generation
    - TTL support for cache entries
    - Statistics tracking
    """

    DEFAULT_CACHE_SIZE = 1000
    DEFAULT_TTL = 86400  # 24 hours in seconds

    def __init__(
        self,
        cache_size: int = DEFAULT_CACHE_SIZE,
        cache_dir: Optional[Path] = None,
        ttl: int = DEFAULT_TTL,
    ):
        """
        Initialize the vector cache.

        Args:
            cache_size: Maximum number of entries in cache
            cache_dir: Directory for persistent cache file
            ttl: Time-to-live for cache entries in seconds
        """
        self.cache_size = cache_size
        self.ttl = ttl

        # Set up cache directory
        if cache_dir is None:
            cache_dir = Path(__file__).parent / ".vector_cache"
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / "vector_cache.json"

        # LRU cache: OrderedDict[key] -> (value, timestamp)
        self._cache: OrderedDict[str, tuple[List[float], float]] = OrderedDict()

        # Statistics
        self._hits = 0
        self._misses = 0
        self._evictions = 0

        # Load from disk
        self._load_from_disk()

    def _generate_key(self, text: str, model: str = "default") -> str:
        """
        Generate a cache key from text and model.

        Args:
            text: Input text
            model: Model name

        Returns:
            Cache key (hash)
        """
        content = f"{model}:{text}"
        return hashlib.sha256(content.encode()).hexdigest()

    def get(
        self,
        text: str,
        model: str = "default",
    ) -> Optional[List[float]]:
        """
        Get a vector from cache.

        Args:
            text: Input text
            model: Model name

        Returns:
            Cached vector or None if not found/expired
        """
        key = self._generate_key(text, model)

        if key in self._cache:
            vector, timestamp = self._cache[key]

            # Check TTL
            if time.time() - timestamp > self.ttl:
                # Expired
                del self._cache[key]
                self._misses += 1
                logger.debug(f"[VectorCache] Cache expired for key: {key[:16]}...")
                return None

            # Move to end (most recently used)
            self._cache.move_to_end(key)
            self._hits += 1
            return vector

        self._misses += 1
        return None

    def put(
        self,
        text: str,
        vector: List[float],
        model: str = "default",
    ) -> None:
        """
        Put a vector into cache.

        Args:
            text: Input text
            vector: Vector to cache
            model: Model name
        """
        key = self._generate_key(text, model)

        # Check if we need to evict
        if key not in self._cache and len(self._cache) >= self.cache_size:
            # Evict least recently used
            self._cache.popitem(last=False)
            self._evictions += 1

        # Add to cache
        self._cache[key] = (vector, time.time())
        self._cache.move_to_end(key)

        # Periodically save to disk (every 100 puts)
        if (self._hits + self._misses) % 100 == 0:
            self._save_to_disk()

    def get_batch(
        self,
        texts: List[str],
        model: str = "default",
    ) -> List[Optional[List[float]]]:
        """
        Get multiple vectors from cache.

        Args:
            texts: List of input texts
            model: Model name

        Returns:
            List of cached vectors (None for misses)
        """
        results = []
        for text in texts:
            results.append(self.get(text, model))
        return results

    def put_batch(
        self,
        texts: List[str],
        vectors: List[List[float]],
        model: str = "default",
    ) -> None:
        """
        Put multiple vectors into cache.

        Args:
            texts: List of input texts
            vectors: List of vectors to cache
            model: Model name
        """
        if len(texts) != len(vectors):
            raise ValueError("Texts and vectors must have same length")

        for text, vector in zip(texts, vectors):
            self.put(text, vector, model)

    def invalidate(
        self,
        text: Optional[str] = None,
        model: str = "default",
    ) -> None:
        """
        Invalidate cache entries.

        Args:
            text: Specific text to invalidate, or None for all entries
            model: Model name
        """
        if text is None:
            # Clear all
            count = len(self._cache)
            self._cache.clear()
            logger.info(f"[VectorCache] Cleared {count} cache entries")
        else:
            # Clear specific entry
            key = self._generate_key(text, model)
            if key in self._cache:
                del self._cache[key]
                logger.debug(f"[VectorCache] Invalidated key: {key[:16]}...")

        self._save_to_disk()

    def cleanup_expired(self) -> int:
        """
        Remove expired entries from cache.

        Returns:
            Number of entries removed
        """
        current_time = time.time()
        expired_keys = []

        for key, (_, timestamp) in self._cache.items():
            if current_time - timestamp > self.ttl:
                expired_keys.append(key)

        for key in expired_keys:
            del self._cache[key]

        if expired_keys:
            logger.info(f"[VectorCache] Cleaned up {len(expired_keys)} expired entries")
            self._save_to_disk()

        return len(expired_keys)

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        total_requests = self._hits + self._misses
        hit_rate = self._hits / total_requests if total_requests > 0 else 0

        return {
            "size": len(self._cache),
            "max_size": self.cache_size,
            "hits": self._hits,
            "misses": self._misses,
            "evictions": self._evictions,
            "hit_rate": hit_rate,
            "ttl": self.ttl,
        }

    def reset_stats(self) -> None:
        """Reset statistics counters."""
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    def _load_from_disk(self) -> None:
        """Load cache from disk."""
        if not self.cache_file.exists():
            return

        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Restore cache
            for key, (vector, timestamp) in data.get("cache", {}).items():
                # Only load non-expired entries
                if time.time() - timestamp <= self.ttl:
                    self._cache[key] = (vector, timestamp)

            # Restore stats
            stats = data.get("stats", {})
            self._hits = stats.get("hits", 0)
            self._misses = stats.get("misses", 0)
            self._evictions = stats.get("evictions", 0)

            logger.info(f"[VectorCache] Loaded {len(self._cache)} entries from disk")

        except Exception as e:
            logger.warning(f"[VectorCache] Failed to load cache from disk: {e}")

    def _save_to_disk(self) -> None:
        """Save cache to disk."""
        try:
            data = {
                "cache": {k: v for k, v in self._cache.items()},
                "stats": {
                    "hits": self._hits,
                    "misses": self._misses,
                    "evictions": self._evictions,
                },
                "version": 1,
            }

            # Write to temp file first
            temp_file = self.cache_file.with_suffix(".tmp")
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False)

            # Atomic rename
            temp_file.replace(self.cache_file)

        except Exception as e:
            logger.warning(f"[VectorCache] Failed to save cache to disk: {e}")

    def clear(self) -> None:
        """Clear all cache entries and save to disk."""
        self._cache.clear()
        self.reset_stats()
        self._save_to_disk()
        logger.info("[VectorCache] Cache cleared")

    def __len__(self) -> int:
        """Return current cache size."""
        return len(self._cache)

    def __contains__(self, text: str) -> bool:
        """Check if text is in cache."""
        key = self._generate_key(text)
        return key in self._cache


class CachedEmbeddingService:
    """
    Wrapper around embedding service with caching.

    Automatically caches embedding results and returns cached
    values when available.
    """

    def __init__(
        self,
        embedding_service: Any,
        cache_size: int = VectorCache.DEFAULT_CACHE_SIZE,
        cache_dir: Optional[Path] = None,
        ttl: int = VectorCache.DEFAULT_TTL,
    ):
        """
        Initialize cached embedding service.

        Args:
            embedding_service: Underlying embedding service
            cache_size: Maximum cache size
            cache_dir: Cache directory
            ttl: Cache TTL in seconds
        """
        self.embedding_service = embedding_service
        self.cache = VectorCache(
            cache_size=cache_size,
            cache_dir=cache_dir,
            ttl=ttl,
        )

    async def get_single_embedding(
        self,
        text: str,
        model: str = "default",
    ) -> Optional[List[float]]:
        """
        Get single embedding with caching.

        Args:
            text: Input text
            model: Model name

        Returns:
            Embedding vector
        """
        # Check cache
        cached = self.cache.get(text, model)
        if cached is not None:
            return cached

        # Cache miss - get from service
        vector = await self.embedding_service.get_single_embedding(text)

        if vector is not None:
            self.cache.put(text, vector, model)

        return vector

    async def get_embeddings_batch(
        self,
        texts: List[str],
        model: str = "default",
    ) -> List[List[float]]:
        """
        Get batch embeddings with caching.

        Args:
            texts: Input texts
            model: Model name

        Returns:
            List of embedding vectors
        """
        results = []
        missed_indices = []
        missed_texts = []

        # Check cache for each text
        for i, text in enumerate(texts):
            cached = self.cache.get(text, model)
            if cached is not None:
                results.append(cached)
            else:
                results.append(None)  # Placeholder
                missed_indices.append(i)
                missed_texts.append(text)

        # Fetch misses in batch
        if missed_texts:
            missed_vectors = await self.embedding_service.get_embeddings_batch(missed_texts)

            # Fill in results and cache
            for idx, text, vector in zip(missed_indices, missed_texts, missed_vectors):
                results[idx] = vector
                self.cache.put(text, vector, model)

        return results

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return self.cache.get_stats()

    def clear_cache(self) -> None:
        """Clear the cache."""
        self.cache.clear()
