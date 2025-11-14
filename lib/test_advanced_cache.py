"""
Tests for Advanced Cache Module

Tests multi-tier caching, predictive prefetching, and pattern detection.
"""

import asyncio
import pytest
from advanced_cache import (
    CacheTier,
    CacheTierConfig,
    CachePolicy,
    MultiTierCache,
    PatternDetector,
    PredictiveCacheConfig,
)


class TestCacheTier:
    """Tests for cache tier."""

    @pytest.mark.asyncio
    async def test_basic_get_put(self):
        """Test basic get/put operations."""
        config = CacheTierConfig(max_size=10)
        tier = CacheTier("test", config)

        # Put value
        await tier.put("key1", "value1", 100)

        # Get value
        value = await tier.get("key1")
        assert value == "value1"

    @pytest.mark.asyncio
    async def test_cache_miss(self):
        """Test cache miss."""
        config = CacheTierConfig(max_size=10)
        tier = CacheTier("test", config)

        value = await tier.get("nonexistent")
        assert value is None
        assert tier.stats.misses == 1

    @pytest.mark.asyncio
    async def test_lru_eviction(self):
        """Test LRU eviction policy."""
        config = CacheTierConfig(max_size=3, policy=CachePolicy.LRU)
        tier = CacheTier("test", config)

        # Fill cache
        await tier.put("key1", "value1", 100)
        await tier.put("key2", "value2", 100)
        await tier.put("key3", "value3", 100)

        # Access key1 to make it recently used
        await tier.get("key1")

        # Add new key - should evict key2 (least recently used)
        await tier.put("key4", "value4", 100)

        # key2 should be evicted
        assert await tier.get("key2") is None
        # key1 should still be there
        assert await tier.get("key1") == "value1"

    @pytest.mark.asyncio
    async def test_size_limit_eviction(self):
        """Test eviction based on size limit."""
        config = CacheTierConfig(
            max_size=100, max_bytes=250, policy=CachePolicy.FIFO)
        tier = CacheTier("test", config)

        # Add entries totaling 300 bytes
        await tier.put("key1", "value1", 100)
        await tier.put("key2", "value2", 100)
        await tier.put("key3", "value3", 100)

        # First entry should be evicted due to size
        assert await tier.get("key1") is None
        assert await tier.get("key2") == "value2"
        assert await tier.get("key3") == "value3"

    @pytest.mark.asyncio
    async def test_ttl_expiration(self):
        """Test TTL expiration."""
        config = CacheTierConfig(max_size=10, ttl=0.1)  # 100ms TTL
        tier = CacheTier("test", config)

        await tier.put("key1", "value1", 100)

        # Should be available immediately
        assert await tier.get("key1") == "value1"

        # Wait for expiration
        await asyncio.sleep(0.15)

        # Should be expired
        assert await tier.get("key1") is None

    @pytest.mark.asyncio
    async def test_hit_rate_calculation(self):
        """Test hit rate calculation."""
        config = CacheTierConfig(max_size=10)
        tier = CacheTier("test", config)

        await tier.put("key1", "value1", 100)

        # 3 hits
        await tier.get("key1")
        await tier.get("key1")
        await tier.get("key1")

        # 2 misses
        await tier.get("key2")
        await tier.get("key3")

        # Hit rate should be 3/5 = 0.6
        assert tier.stats.hit_rate == 0.6


class TestPatternDetector:
    """Tests for pattern detector."""

    @pytest.mark.asyncio
    async def test_sequential_pattern(self):
        """Test sequential access pattern detection."""
        config = PredictiveCacheConfig(
            sequential_threshold=3, pattern_window=10)
        detector = PatternDetector(config)

        # Record sequential accesses (stride of 1)
        for i in range(5):
            await detector.record_access("file1", i)

        # Should detect sequential pattern
        pattern = await detector.detect_pattern()
        assert pattern is not None
        assert pattern.pattern_type == "sequential"
        assert pattern.stride == 1
        assert pattern.confidence > 0.7

    @pytest.mark.asyncio
    async def test_strided_pattern(self):
        """Test strided access pattern detection."""
        config = PredictiveCacheConfig(
            sequential_threshold=3, pattern_window=10)
        detector = PatternDetector(config)

        # Record strided accesses (every 500 bytes)
        for i in range(5):
            await detector.record_access("file1", i * 500)

        # Should detect strided pattern
        pattern = await detector.detect_pattern()
        assert pattern is not None
        assert pattern.pattern_type == "strided"
        assert pattern.stride == 500

    @pytest.mark.asyncio
    async def test_random_pattern(self):
        """Test random access pattern detection."""
        config = PredictiveCacheConfig(
            sequential_threshold=3, pattern_window=10)
        detector = PatternDetector(config)

        # Record random accesses
        offsets = [0, 500, 100, 900, 50]
        for offset in offsets:
            await detector.record_access("file1", offset)

        # Should detect random pattern
        pattern = await detector.detect_pattern()
        assert pattern is not None
        assert pattern.pattern_type == "random"

    @pytest.mark.asyncio
    async def test_insufficient_data(self):
        """Test with insufficient data for pattern detection."""
        config = PredictiveCacheConfig(
            sequential_threshold=5, pattern_window=10)
        detector = PatternDetector(config)

        # Record only 2 accesses (less than threshold)
        await detector.record_access("file1", 0)
        await detector.record_access("file1", 100)

        # Should not detect pattern
        pattern = await detector.detect_pattern()
        assert pattern is None


class TestMultiTierCache:
    """Tests for multi-tier cache."""

    @pytest.mark.asyncio
    async def test_basic_operation(self):
        """Test basic cache operations."""
        cache = MultiTierCache()

        # Put in L2
        await cache.put("key1", "value1", "L2")

        # Get value
        value = await cache.get("key1")
        assert value == "value1"

    @pytest.mark.asyncio
    async def test_l1_hit(self):
        """Test L1 cache hit."""
        cache = MultiTierCache()

        # Put in L1
        await cache.put("key1", "value1", "L1")

        # Should hit L1
        value = await cache.get("key1")
        assert value == "value1"
        assert cache.l1.stats.hits == 1
        assert cache.l2.stats.hits == 0

    @pytest.mark.asyncio
    async def test_l2_hit(self):
        """Test L2 cache hit."""
        cache = MultiTierCache()

        # Put in L2
        await cache.put("key1", "value1", "L2")

        # Should hit L2
        value = await cache.get("key1")
        assert value == "value1"
        assert cache.l1.stats.hits == 0
        assert cache.l2.stats.hits == 1

    @pytest.mark.asyncio
    async def test_promotion_to_l1(self):
        """Test promotion from L2 to L1."""
        l1_config = CacheTierConfig(max_size=10, promotion_threshold=2)
        l2_config = CacheTierConfig(max_size=20, promotion_threshold=2)

        cache = MultiTierCache(l1_config, l2_config)

        # Put in L2
        await cache.put("key1", "value1", "L2")

        # Access multiple times to trigger promotion
        await cache.get("key1")
        await cache.get("key1")
        await cache.get("key1")

        # Should be promoted to L1
        assert cache.l1.stats.promotions >= 1

    @pytest.mark.asyncio
    async def test_sequential_prefetch(self):
        """Test sequential prefetching."""
        # Data loader that returns fake data
        loaded_keys = []

        async def data_loader(key: str):
            loaded_keys.append(key)
            return f"data_{key}"

        predictive_config = PredictiveCacheConfig(
            enable_prefetch=True,
            prefetch_distance=3,
            sequential_threshold=3
        )

        cache = MultiTierCache(
            predictive_config=predictive_config,
            data_loader=data_loader
        )

        # Record sequential accesses to trigger prefetch
        for i in range(5):
            key = f"file_0_{i * 100}"
            await cache.put(key, f"value_{i}", "L2")
            await cache.get(key, offset=i * 100)

        # Wait for prefetch tasks
        await asyncio.sleep(0.1)

        # Should have prefetched ahead
        assert len(loaded_keys) > 0

    @pytest.mark.asyncio
    async def test_cache_warming(self):
        """Test cache warming."""
        loaded_keys = []

        async def data_loader(key: str):
            loaded_keys.append(key)
            await asyncio.sleep(0.01)  # Simulate loading delay
            return f"data_{key}"

        predictive_config = PredictiveCacheConfig(enable_warming=True)

        cache = MultiTierCache(
            predictive_config=predictive_config,
            data_loader=data_loader
        )

        # Warm cache with keys
        keys_to_warm = ["key1", "key2", "key3"]
        await cache.warm(keys_to_warm)

        # All keys should be loaded
        assert set(loaded_keys) == set(keys_to_warm)

        # Keys should be in cache
        for key in keys_to_warm:
            value = await cache.get(key)
            assert value == f"data_{key}"

    @pytest.mark.asyncio
    async def test_cache_statistics(self):
        """Test cache statistics."""
        cache = MultiTierCache()

        # Put some values
        await cache.put("key1", "value1", "L1")
        await cache.put("key2", "value2", "L2")

        # Get values
        await cache.get("key1")
        await cache.get("key2")
        await cache.get("nonexistent")

        # Get stats
        stats = cache.get_stats()

        assert "l1" in stats
        assert "l2" in stats
        assert "total_hit_rate" in stats
        assert stats["l1"]["hits"] == 1
        assert stats["l2"]["hits"] == 1

    @pytest.mark.asyncio
    async def test_cache_clear(self):
        """Test clearing cache."""
        cache = MultiTierCache()

        # Add values
        await cache.put("key1", "value1", "L1")
        await cache.put("key2", "value2", "L2")

        # Clear cache
        await cache.clear()

        # Cache should be empty
        assert await cache.get("key1") is None
        assert await cache.get("key2") is None
        assert cache.l1.stats.total_bytes == 0
        assert cache.l2.stats.total_bytes == 0

    @pytest.mark.asyncio
    async def test_concurrent_access(self):
        """Test concurrent cache access."""
        cache = MultiTierCache()

        # Put initial values
        for i in range(10):
            await cache.put(f"key{i}", f"value{i}", "L2")

        # Concurrent gets
        tasks = []
        for i in range(10):
            tasks.append(cache.get(f"key{i % 5}"))

        results = await asyncio.gather(*tasks)

        # All results should be valid
        assert all(r is not None for r in results)

    @pytest.mark.asyncio
    async def test_data_loader_on_miss(self):
        """Test data loader is called on cache miss."""
        loaded = False

        async def data_loader(key: str):
            nonlocal loaded
            loaded = True
            return f"loaded_{key}"

        cache = MultiTierCache(data_loader=data_loader)

        # Get non-existent key
        value = await cache.get("new_key")

        # Should have loaded data
        assert loaded
        assert value == "loaded_new_key"

        # Should now be in cache
        loaded = False
        value = await cache.get("new_key")
        assert not loaded  # Should not load again
        assert value == "loaded_new_key"


async def main():
    """Run all tests."""
    print("Running Advanced Cache Tests...")
    print("=" * 70)

    # Test Cache Tier
    print("\n[1/15] Testing Cache Tier - Basic Get/Put...")
    test = TestCacheTier()
    await test.test_basic_get_put()
    print("  ✓ PASSED")

    print("[2/15] Testing Cache Tier - Cache Miss...")
    await test.test_cache_miss()
    print("  ✓ PASSED")

    print("[3/15] Testing Cache Tier - LRU Eviction...")
    await test.test_lru_eviction()
    print("  ✓ PASSED")

    print("[4/15] Testing Cache Tier - Size Limit Eviction...")
    await test.test_size_limit_eviction()
    print("  ✓ PASSED")

    print("[5/15] Testing Cache Tier - TTL Expiration...")
    await test.test_ttl_expiration()
    print("  ✓ PASSED")

    print("[6/15] Testing Cache Tier - Hit Rate Calculation...")
    await test.test_hit_rate_calculation()
    print("  ✓ PASSED")

    # Test Pattern Detector
    print("\n[7/15] Testing Pattern Detector - Sequential Pattern...")
    pattern_test = TestPatternDetector()
    await pattern_test.test_sequential_pattern()
    print("  ✓ PASSED")

    print("[8/15] Testing Pattern Detector - Strided Pattern...")
    await pattern_test.test_strided_pattern()
    print("  ✓ PASSED")

    print("[9/15] Testing Pattern Detector - Random Pattern...")
    await pattern_test.test_random_pattern()
    print("  ✓ PASSED")

    # Test Multi-Tier Cache
    print("\n[10/15] Testing Multi-Tier Cache - Basic Operation...")
    cache_test = TestMultiTierCache()
    await cache_test.test_basic_operation()
    print("  ✓ PASSED")

    print("[11/15] Testing Multi-Tier Cache - L1 Hit...")
    await cache_test.test_l1_hit()
    print("  ✓ PASSED")

    print("[12/15] Testing Multi-Tier Cache - L2 Hit...")
    await cache_test.test_l2_hit()
    print("  ✓ PASSED")

    print("[13/15] Testing Multi-Tier Cache - Promotion to L1...")
    await cache_test.test_promotion_to_l1()
    print("  ✓ PASSED")

    print("[14/15] Testing Multi-Tier Cache - Cache Warming...")
    await cache_test.test_cache_warming()
    print("  ✓ PASSED")

    print("[15/15] Testing Multi-Tier Cache - Data Loader on Miss...")
    await cache_test.test_data_loader_on_miss()
    print("  ✓ PASSED")

    print("\n" + "=" * 70)
    print("All Advanced Cache Tests PASSED!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
