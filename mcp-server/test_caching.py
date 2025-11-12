#!/usr/bin/env python3
"""
Advanced Caching Tests

Comprehensive tests for LRU + TTL caching functionality:
- Basic cache operations (get, set, hit, miss)
- TTL expiration
- LRU eviction
- Memory limits
- Automatic cleanup
- Cache statistics
- Cache invalidation
- Integration with AsyncImHexClient
"""

import asyncio
import sys
import time
from pathlib import Path

# Add lib directory to path
lib_path = Path(__file__).parent.parent / "lib"
sys.path.insert(0, str(lib_path))

from async_client import AsyncImHexClient
from cache import AsyncResponseCache


async def test_basic_cache_operations():
    """Test 1: Basic cache operations."""
    print("\n" + "=" * 70)
    print("Test 1: Basic Cache Operations")
    print("=" * 70)

    cache = AsyncResponseCache(max_size=100, default_ttl=300.0)
    await cache.start()

    try:
        # Test cache miss
        result = await cache.get("test_endpoint", {"key": "value"})
        print(f"  Initial cache miss: {result is None}")

        # Test cache set
        test_data = {"status": "success", "data": {"result": 42}}
        await cache.set("test_endpoint", {"key": "value"}, test_data)
        print(f"  Cached test data")

        # Test cache hit
        cached = await cache.get("test_endpoint", {"key": "value"})
        print(f"  Cache hit: {cached is not None}")
        print(f"  Data matches: {cached == test_data}")

        # Test cache stats
        stats = await cache.get_stats()
        print(f"\n  Cache statistics:")
        print(f"    Hits: {stats['hits']}")
        print(f"    Misses: {stats['misses']}")
        print(f"    Hit rate: {stats['hit_rate']:.1f}%")
        print(f"    Size: {stats['size']}")

        return stats['hits'] == 1 and stats['misses'] == 1
    finally:
        await cache.stop()


async def test_ttl_expiration():
    """Test 2: TTL expiration."""
    print("\n" + "=" * 70)
    print("Test 2: TTL Expiration")
    print("=" * 70)

    cache = AsyncResponseCache(max_size=100, default_ttl=2.0)  # 2 second TTL
    await cache.start()

    try:
        # Cache data with short TTL
        test_data = {"status": "success", "data": {"value": "expires_soon"}}
        await cache.set("short_ttl", {}, test_data, ttl=1.0)
        print(f"  Cached data with 1s TTL")

        # Verify cache hit immediately
        cached = await cache.get("short_ttl", {})
        print(f"  Immediate cache hit: {cached is not None}")

        # Wait for expiration
        print(f"  Waiting 1.5s for expiration...")
        await asyncio.sleep(1.5)

        # Verify cache miss after expiration
        expired = await cache.get("short_ttl", {})
        print(f"  Cache miss after expiration: {expired is None}")

        return cached is not None and expired is None
    finally:
        await cache.stop()


async def test_lru_eviction():
    """Test 3: LRU eviction."""
    print("\n" + "=" * 70)
    print("Test 3: LRU Eviction")
    print("=" * 70)

    cache = AsyncResponseCache(max_size=3, default_ttl=300.0)  # Only 3 entries
    await cache.start()

    try:
        # Fill cache to capacity
        for i in range(3):
            await cache.set(f"endpoint_{i}", {}, {"value": i})
        print(f"  Filled cache to capacity (3 entries)")

        # Access first entry to make it recently used
        await cache.get("endpoint_0", {})
        print(f"  Accessed endpoint_0 (now most recent)")

        # Add 4th entry, should evict endpoint_1 (least recently used)
        await cache.set("endpoint_3", {}, {"value": 3})
        print(f"  Added 4th entry (should evict endpoint_1)")

        # Verify eviction
        entry_0 = await cache.get("endpoint_0", {})  # Should exist (recently accessed)
        entry_1 = await cache.get("endpoint_1", {})  # Should be evicted
        entry_2 = await cache.get("endpoint_2", {})  # Should exist
        entry_3 = await cache.get("endpoint_3", {})  # Should exist (just added)

        print(f"\n  After eviction:")
        print(f"    endpoint_0 exists: {entry_0 is not None}")
        print(f"    endpoint_1 evicted: {entry_1 is None}")
        print(f"    endpoint_2 exists: {entry_2 is not None}")
        print(f"    endpoint_3 exists: {entry_3 is not None}")

        return (entry_0 is not None and entry_1 is None and
                entry_2 is not None and entry_3 is not None)
    finally:
        await cache.stop()


async def test_memory_limits():
    """Test 4: Memory-based eviction."""
    print("\n" + "=" * 70)
    print("Test 4: Memory-Based Eviction")
    print("=" * 70)

    # Small memory limit (1KB)
    cache = AsyncResponseCache(max_size=1000, max_memory_mb=0.001)
    await cache.start()

    try:
        # Add entries until memory limit reached
        entries_added = 0
        for i in range(10):
            large_data = {"status": "success", "data": {"value": "x" * 100}}  # ~100 bytes
            await cache.set(f"large_{i}", {}, large_data)
            entries_added += 1

        stats = await cache.get_stats()
        print(f"  Added {entries_added} entries")
        print(f"  Cache size: {stats['size']} (limited by memory)")
        print(f"  Memory usage: {stats['memory_bytes']} bytes")
        print(f"  Memory limit enforced: {stats['size'] < entries_added}")

        return stats['size'] < entries_added
    finally:
        await cache.stop()


async def test_cache_invalidation():
    """Test 5: Cache invalidation."""
    print("\n" + "=" * 70)
    print("Test 5: Cache Invalidation")
    print("=" * 70)

    cache = AsyncResponseCache(max_size=100, default_ttl=300.0)
    await cache.start()

    try:
        # Add multiple entries
        await cache.set("endpoint_a", {"id": 1}, {"value": "a1"})
        await cache.set("endpoint_a", {"id": 2}, {"value": "a2"})
        await cache.set("endpoint_b", {}, {"value": "b"})
        print(f"  Added 3 cache entries")

        # Invalidate specific entry
        await cache.invalidate("endpoint_a", {"id": 1})
        print(f"  Invalidated endpoint_a with id=1")

        # Verify selective invalidation
        a1 = await cache.get("endpoint_a", {"id": 1})
        a2 = await cache.get("endpoint_a", {"id": 2})
        b = await cache.get("endpoint_b", {})

        print(f"\n  After invalidation:")
        print(f"    endpoint_a (id=1) invalidated: {a1 is None}")
        print(f"    endpoint_a (id=2) still cached: {a2 is not None}")
        print(f"    endpoint_b still cached: {b is not None}")

        # Test full clear
        await cache.clear()
        print(f"\n  Cleared entire cache")

        a2_after = await cache.get("endpoint_a", {"id": 2})
        b_after = await cache.get("endpoint_b", {})
        print(f"  All entries cleared: {a2_after is None and b_after is None}")

        return a1 is None and a2 is not None and b is not None and a2_after is None
    finally:
        await cache.stop()


async def test_automatic_cleanup():
    """Test 6: Automatic background cleanup."""
    print("\n" + "=" * 70)
    print("Test 6: Automatic Background Cleanup")
    print("=" * 70)

    cache = AsyncResponseCache(
        max_size=100,
        default_ttl=1.0,  # 1 second TTL
        enable_auto_cleanup=True
    )
    await cache.start()

    try:
        # Add entries with short TTL
        for i in range(5):
            await cache.set(f"temp_{i}", {}, {"value": i}, ttl=1.0)
        print(f"  Added 5 entries with 1s TTL")

        stats_before = await cache.get_stats()
        print(f"  Cache size before expiration: {stats_before['size']}")

        # Wait for expiration + cleanup
        print(f"  Waiting 2s for automatic cleanup...")
        await asyncio.sleep(2)

        stats_after = await cache.get_stats()
        print(f"  Cache size after cleanup: {stats_after['size']}")
        print(f"  Expired entries removed: {stats_after['expired']}")

        return stats_after['size'] == 0 and stats_after['expired'] > 0
    finally:
        await cache.stop()


async def test_client_integration():
    """Test 7: Integration with AsyncImHexClient."""
    print("\n" + "=" * 70)
    print("Test 7: AsyncImHexClient Integration")
    print("=" * 70)

    async with AsyncImHexClient(
        host="localhost",
        port=31337,
        enable_cache=True,
        cache_max_size=100
    ) as client:
        # First request (cache miss)
        start = time.perf_counter()
        response1 = await client.send_request("capabilities")
        time1 = (time.perf_counter() - start) * 1000
        print(f"  First request (cache miss): {time1:.2f}ms")

        # Second request (cache hit)
        start = time.perf_counter()
        response2 = await client.send_request("capabilities")
        time2 = (time.perf_counter() - start) * 1000
        print(f"  Second request (cache hit): {time2:.2f}ms")

        # Verify cache hit is faster
        speedup = time1 / time2 if time2 > 0 else 0
        print(f"  Speedup from caching: {speedup:.1f}x")
        print(f"  Data matches: {response1 == response2}")

        # Get cache stats
        stats = await client.cache_stats()
        print(f"\n  Cache statistics:")
        print(f"    Hits: {stats.get('hits', 0)}")
        print(f"    Misses: {stats.get('misses', 0)}")
        print(f"    Hit rate: {stats.get('hit_rate', 0):.1f}%")

        return response1 == response2 and stats.get('hits', 0) >= 1


async def test_cache_control_methods():
    """Test 8: Cache control methods."""
    print("\n" + "=" * 70)
    print("Test 8: Cache Control Methods")
    print("=" * 70)

    async with AsyncImHexClient(
        host="localhost",
        port=31337,
        enable_cache=True
    ) as client:
        # Populate cache
        await client.send_request("capabilities")
        await client.send_request("file/list")
        print(f"  Populated cache with 2 requests")

        stats = await client.cache_stats()
        print(f"  Cache size: {stats.get('size', 0)}")

        # Test selective invalidation
        await client.cache_invalidate("capabilities")
        print(f"  Invalidated 'capabilities' endpoint")

        # Test full clear
        await client.cache_clear()
        print(f"  Cleared entire cache")

        stats_after = await client.cache_stats()
        print(f"  Cache size after clear: {stats_after.get('size', 0)}")

        return stats_after.get('size', 0) == 0


async def test_cache_with_batching():
    """Test 9: Cache interaction with request batching."""
    print("\n" + "=" * 70)
    print("Test 9: Cache + Batching Integration")
    print("=" * 70)

    async with AsyncImHexClient(
        host="localhost",
        port=31337,
        enable_cache=True,
        use_connection_pool=True
    ) as client:
        # First batch (populate cache)
        batcher1 = client.create_batcher()
        batcher1.add(endpoint="capabilities", data={})
        batcher1.add(endpoint="file/list", data={})

        start = time.perf_counter()
        responses1, stats1 = await client.send_batch_advanced(batcher1)
        time1 = (time.perf_counter() - start) * 1000
        print(f"  First batch (cache miss): {time1:.2f}ms")

        # Second batch (cache hit)
        batcher2 = client.create_batcher()
        batcher2.add(endpoint="capabilities", data={})
        batcher2.add(endpoint="file/list", data={})

        start = time.perf_counter()
        responses2, stats2 = await client.send_batch_advanced(batcher2)
        time2 = (time.perf_counter() - start) * 1000
        print(f"  Second batch (cache hit): {time2:.2f}ms")

        speedup = time1 / time2 if time2 > 0 else 0
        print(f"  Speedup from caching: {speedup:.1f}x")

        # Get cache stats
        cache_stats = await client.cache_stats()
        print(f"\n  Cache statistics:")
        print(f"    Hit rate: {cache_stats.get('hit_rate', 0):.1f}%")

        return len(responses2) == 2 and cache_stats.get('hit_rate', 0) > 0


async def run_all_tests():
    """Run all caching tests."""
    print("\n" + "=" * 70)
    print("ADVANCED CACHING TEST SUITE")
    print("=" * 70)
    print("\nTesting LRU + TTL caching for 50-90% cache hit rate")

    tests = [
        ("Basic Cache Operations", test_basic_cache_operations),
        ("TTL Expiration", test_ttl_expiration),
        ("LRU Eviction", test_lru_eviction),
        ("Memory Limits", test_memory_limits),
        ("Cache Invalidation", test_cache_invalidation),
        ("Automatic Cleanup", test_automatic_cleanup),
        ("Client Integration", test_client_integration),
        ("Cache Control Methods", test_cache_control_methods),
        ("Cache + Batching Integration", test_cache_with_batching),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = await test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ Test '{name}' raised exception: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))

    # Print summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")

    print(f"\n{passed}/{total} tests passed ({passed/total*100:.0f}%)")
    print("=" * 70 + "\n")

    return passed == total


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
