#!/usr/bin/env python3
"""
Unit tests for ImHex MCP caching module.

Tests response caching, TTL expiration, LRU eviction, and cache statistics.
"""

import unittest
import time
import sys
from pathlib import Path
import threading
from typing import Dict, Any

# Add lib directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))

from cache import (
    ResponseCache,
    CachePolicy,
    CacheEntry,
    CacheStats,
    CachingStrategy
)


class TestCacheEntry(unittest.TestCase):
    """Tests for CacheEntry class."""

    def test_entry_creation(self):
        """Test creating cache entry."""
        entry = CacheEntry(
            key="test_key",
            value={"data": "test"},
            created_at=time.time(),
            last_accessed=time.time(),
            access_count=0,
            ttl=60.0
        )

        self.assertEqual(entry.key, "test_key")
        self.assertEqual(entry.value, {"data": "test"})
        self.assertFalse(entry.is_expired())

    def test_entry_expiration(self):
        """Test entry TTL expiration."""
        entry = CacheEntry(
            key="test_key",
            value="test",
            created_at=time.time() - 61,  # 61 seconds ago
            last_accessed=time.time(),
            access_count=0,
            ttl=60.0  # 60 second TTL
        )

        self.assertTrue(entry.is_expired())

    def test_entry_no_expiration(self):
        """Test entry with no TTL never expires."""
        entry = CacheEntry(
            key="test_key",
            value="test",
            created_at=time.time() - 1000,  # Very old
            last_accessed=time.time(),
            access_count=0,
            ttl=None  # No expiration
        )

        self.assertFalse(entry.is_expired())

    def test_entry_touch(self):
        """Test entry touch updates metadata."""
        entry = CacheEntry(
            key="test_key",
            value="test",
            created_at=time.time(),
            last_accessed=time.time() - 10,
            access_count=5,
            ttl=None
        )

        old_access_time = entry.last_accessed
        old_count = entry.access_count

        time.sleep(0.01)
        entry.touch()

        self.assertGreater(entry.last_accessed, old_access_time)
        self.assertEqual(entry.access_count, old_count + 1)


class TestCacheStats(unittest.TestCase):
    """Tests for CacheStats class."""

    def test_hit_rate_calculation(self):
        """Test cache hit rate calculation."""
        stats = CacheStats(hits=80, misses=20)
        self.assertEqual(stats.hit_rate(), 80.0)

    def test_hit_rate_zero_requests(self):
        """Test hit rate with no requests."""
        stats = CacheStats()
        self.assertEqual(stats.hit_rate(), 0.0)

    def test_stats_to_dict(self):
        """Test stats conversion to dictionary."""
        stats = CacheStats(
            hits=100,
            misses=25,
            evictions=5,
            expired=3,
            size=50,
            max_size=100
        )

        data = stats.to_dict()
        self.assertEqual(data["hits"], 100)
        self.assertEqual(data["misses"], 25)
        self.assertEqual(data["evictions"], 5)
        self.assertEqual(data["expired"], 3)
        self.assertEqual(data["size"], 50)
        self.assertEqual(data["max_size"], 100)
        self.assertEqual(data["hit_rate"], 80.0)


class TestResponseCache(unittest.TestCase):
    """Tests for ResponseCache class."""

    def setUp(self):
        """Set up test cache."""
        self.cache = ResponseCache(max_size=10, default_ttl=60.0)

    def test_cache_set_and_get(self):
        """Test basic cache set and get operations."""
        self.cache.set("capabilities", None, {"endpoints": ["test"]})
        result = self.cache.get("capabilities", None)

        self.assertIsNotNone(result)
        self.assertEqual(result["endpoints"], ["test"])

    def test_cache_miss(self):
        """Test cache miss returns None."""
        result = self.cache.get("nonexistent", None)
        self.assertIsNone(result)

    def test_cache_with_data_parameters(self):
        """Test caching with request data parameters."""
        data = {"provider_id": 0, "offset": 0, "size": 1024}
        self.cache.set("data/read", data, b"test_data")

        result = self.cache.get("data/read", data)
        self.assertEqual(result, b"test_data")

    def test_cache_different_parameters(self):
        """Test different parameters create different cache keys."""
        self.cache.set("data/read", {"offset": 0}, "data1")
        self.cache.set("data/read", {"offset": 100}, "data2")

        result1 = self.cache.get("data/read", {"offset": 0})
        result2 = self.cache.get("data/read", {"offset": 100})

        self.assertEqual(result1, "data1")
        self.assertEqual(result2, "data2")

    def test_cache_ttl_expiration(self):
        """Test cache entry expires after TTL."""
        self.cache.set("test", None, "value", ttl=0.1)  # 100ms TTL

        # Should be cached immediately
        result = self.cache.get("test", None)
        self.assertEqual(result, "value")

        # Wait for expiration
        time.sleep(0.15)

        # Should be expired
        result = self.cache.get("test", None)
        self.assertIsNone(result)

    def test_cache_lru_eviction(self):
        """Test LRU eviction when cache is full."""
        # Fill cache to capacity
        for i in range(10):
            self.cache.set(f"endpoint_{i}", None, f"value_{i}")

        # Access endpoint_0 to make it recently used
        self.cache.get("endpoint_0", None)

        # Add new item, should evict endpoint_1 (least recently used)
        self.cache.set("new_endpoint", None, "new_value")

        # endpoint_0 should still exist (was accessed recently)
        self.assertIsNotNone(self.cache.get("endpoint_0", None))

        # endpoint_1 should be evicted
        self.assertIsNone(self.cache.get("endpoint_1", None))

        # new_endpoint should exist
        self.assertIsNotNone(self.cache.get("new_endpoint", None))

    def test_cache_stats_hits(self):
        """Test cache hit statistics."""
        self.cache.set("test", None, "value")

        # First get - hit
        self.cache.get("test", None)

        stats = self.cache.get_stats()
        self.assertEqual(stats["hits"], 1)
        self.assertEqual(stats["misses"], 0)

    def test_cache_stats_misses(self):
        """Test cache miss statistics."""
        # Get non-existent key - miss
        self.cache.get("nonexistent", None)

        stats = self.cache.get_stats()
        self.assertEqual(stats["hits"], 0)
        self.assertEqual(stats["misses"], 1)

    def test_cache_stats_evictions(self):
        """Test eviction statistics."""
        # Fill cache beyond capacity
        for i in range(11):
            self.cache.set(f"endpoint_{i}", None, f"value_{i}")

        stats = self.cache.get_stats()
        self.assertEqual(stats["evictions"], 1)

    def test_cache_stats_expired(self):
        """Test expired entry statistics."""
        self.cache.set("test", None, "value", ttl=0.05)
        time.sleep(0.1)

        # Try to get expired entry
        self.cache.get("test", None)

        stats = self.cache.get_stats()
        self.assertEqual(stats["expired"], 1)

    def test_cache_invalidate_all(self):
        """Test invalidating all cache entries."""
        self.cache.set("test1", None, "value1")
        self.cache.set("test2", None, "value2")

        count = self.cache.invalidate()

        self.assertEqual(count, 2)
        self.assertIsNone(self.cache.get("test1", None))
        self.assertIsNone(self.cache.get("test2", None))

    def test_cache_invalidate_specific(self):
        """Test invalidating specific cache entry."""
        self.cache.set("test", {"id": 1}, "value1")
        self.cache.set("test", {"id": 2}, "value2")

        count = self.cache.invalidate("test", {"id": 1})

        self.assertEqual(count, 1)
        self.assertIsNone(self.cache.get("test", {"id": 1}))
        self.assertIsNotNone(self.cache.get("test", {"id": 2}))

    def test_cache_clear(self):
        """Test clearing all cache entries."""
        self.cache.set("test1", None, "value1")
        self.cache.set("test2", None, "value2")

        self.cache.clear()

        stats = self.cache.get_stats()
        self.assertEqual(stats["size"], 0)
        self.assertIsNone(self.cache.get("test1", None))

    def test_cache_cleanup_expired(self):
        """Test cleanup of expired entries."""
        # Add some entries with short TTL
        self.cache.set("test1", None, "value1", ttl=0.05)
        self.cache.set("test2", None, "value2", ttl=0.05)
        self.cache.set("test3", None, "value3", ttl=60.0)  # Won't expire

        time.sleep(0.1)

        count = self.cache.cleanup_expired()

        self.assertEqual(count, 2)
        self.assertIsNone(self.cache.get("test1", None))
        self.assertIsNone(self.cache.get("test2", None))
        self.assertIsNotNone(self.cache.get("test3", None))

    def test_cache_get_entry_info(self):
        """Test getting entry metadata."""
        self.cache.set("test", None, "value", ttl=60.0)

        info = self.cache.get_entry_info("test", None)

        self.assertIsNotNone(info)
        self.assertIn("key", info)
        self.assertIn("created_at", info)
        self.assertIn("last_accessed", info)
        self.assertIn("access_count", info)
        self.assertIn("ttl", info)
        self.assertIn("age", info)
        self.assertIn("expires_in", info)
        self.assertFalse(info["is_expired"])

    def test_cache_get_all_entries(self):
        """Test getting all entry metadata."""
        self.cache.set("test1", None, "value1")
        self.cache.set("test2", None, "value2")

        entries = self.cache.get_all_entries()

        self.assertEqual(len(entries), 2)
        self.assertIn("key", entries[0])
        self.assertIn("created_at", entries[0])

    def test_cache_thread_safety(self):
        """Test cache is thread-safe."""
        results = []

        def worker(thread_id: int):
            for i in range(100):
                key = f"thread_{thread_id}_key_{i}"
                self.cache.set(key, None, f"value_{i}")
                value = self.cache.get(key, None)
                results.append(value is not None)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All operations should have succeeded
        self.assertTrue(all(results))

    def test_cache_reset_stats(self):
        """Test resetting cache statistics."""
        self.cache.set("test", None, "value")
        self.cache.get("test", None)
        self.cache.get("nonexistent", None)

        self.cache.reset_stats()

        stats = self.cache.get_stats()
        self.assertEqual(stats["hits"], 0)
        self.assertEqual(stats["misses"], 0)
        self.assertEqual(stats["evictions"], 0)
        self.assertEqual(stats["expired"], 0)
        # Size should not be reset
        self.assertEqual(stats["size"], 1)

    def test_cache_no_ttl(self):
        """Test cache with no TTL (session-scoped)."""
        cache = ResponseCache(max_size=10, default_ttl=None)
        cache.set("test", None, "value")

        # Should never expire
        time.sleep(0.1)
        result = cache.get("test", None)
        self.assertEqual(result, "value")


class TestCachingStrategy(unittest.TestCase):
    """Tests for CachingStrategy class."""

    def test_stable_endpoint_ttl(self):
        """Test TTL for stable endpoints."""
        ttl = CachingStrategy.get_ttl_for_endpoint("capabilities")
        self.assertEqual(ttl, 300.0)

    def test_moderate_endpoint_ttl(self):
        """Test TTL for moderate endpoints."""
        ttl = CachingStrategy.get_ttl_for_endpoint("file/list")
        self.assertEqual(ttl, 60.0)

    def test_volatile_endpoint_ttl(self):
        """Test TTL for volatile endpoints."""
        ttl = CachingStrategy.get_ttl_for_endpoint("data/read")
        self.assertEqual(ttl, 10.0)

    def test_unknown_endpoint_default_ttl(self):
        """Test unknown endpoint gets moderate TTL."""
        ttl = CachingStrategy.get_ttl_for_endpoint("unknown/endpoint")
        self.assertEqual(ttl, 60.0)


class TestCacheIntegration(unittest.TestCase):
    """Integration tests for cache behavior."""

    def test_realistic_usage_pattern(self):
        """Test realistic cache usage pattern."""
        cache = ResponseCache(max_size=100, default_ttl=60.0)

        # Simulate repeated requests to same endpoints
        for _ in range(10):
            cache.set("capabilities", None, {"endpoints": []})
            result = cache.get("capabilities", None)
            self.assertIsNotNone(result)

        # Should have many cache hits
        stats = cache.get_stats()
        self.assertGreater(stats["hits"], 5)

    def test_mixed_endpoint_caching(self):
        """Test caching different endpoint types."""
        cache = ResponseCache(max_size=50)

        # Cache various endpoints
        endpoints = [
            ("capabilities", None, {"endpoints": []}),
            ("file/list", None, {"count": 0}),
            ("data/read", {"offset": 0}, b"data"),
            ("data/hash", {"algorithm": "md5"}, "abc123"),
        ]

        for endpoint, data, value in endpoints:
            cache.set(endpoint, data, value)

        # All should be retrievable
        for endpoint, data, expected in endpoints:
            result = cache.get(endpoint, data)
            self.assertEqual(result, expected)

    def test_cache_behavior_under_load(self):
        """Test cache behavior with many operations."""
        cache = ResponseCache(max_size=50, default_ttl=60.0)

        # Add many entries
        for i in range(100):
            cache.set(f"endpoint_{i}", None, f"value_{i}")

        # Cache size should not exceed max_size
        stats = cache.get_stats()
        self.assertLessEqual(stats["size"], 50)

        # Should have evictions
        self.assertGreater(stats["evictions"], 0)


def run_tests():
    """Run all cache tests."""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestCacheEntry))
    suite.addTests(loader.loadTestsFromTestCase(TestCacheStats))
    suite.addTests(loader.loadTestsFromTestCase(TestResponseCache))
    suite.addTests(loader.loadTestsFromTestCase(TestCachingStrategy))
    suite.addTests(loader.loadTestsFromTestCase(TestCacheIntegration))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
