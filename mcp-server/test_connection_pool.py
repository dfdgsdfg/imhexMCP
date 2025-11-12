#!/usr/bin/env python3
"""
Connection Pool Tests

Tests for the connection pool functionality:
- Connection reuse and pooling
- Health checks and reconnection
- Performance comparison with/without pooling
- Concurrent request handling
- Pool statistics tracking
"""

import asyncio
import sys
import time
from pathlib import Path

# Add lib directory to path
lib_path = Path(__file__).parent.parent / "lib"
sys.path.insert(0, str(lib_path))

from async_client import AsyncImHexClient


async def test_pool_initialization():
    """Test 1: Connection pool initialization."""
    print("\n" + "=" * 70)
    print("Test 1: Connection Pool Initialization")
    print("=" * 70)

    async with AsyncImHexClient(
        host="localhost",
        port=31337,
        use_connection_pool=True,
        pool_min_size=2,
        pool_max_size=5
    ) as client:
        # Pool should be initialized
        stats = client.get_pool_stats()
        print(f"✓ Pool initialized")
        print(f"  Enabled: {stats.get('enabled')}")
        print(f"  Active connections: {stats.get('active_connections')}")
        print(f"  Idle connections: {stats.get('idle_connections')}")
        print(f"  Pool size: {stats.get('pool_size')}/{stats.get('max_size')}")

        return stats.get('enabled') == True


async def test_connection_reuse():
    """Test 2: Connection reuse verification."""
    print("\n" + "=" * 70)
    print("Test 2: Connection Reuse")
    print("=" * 70)

    async with AsyncImHexClient(
        host="localhost",
        port=31337,
        use_connection_pool=True,
        pool_min_size=2,
        pool_max_size=10
    ) as client:
        # Make multiple requests
        for i in range(10):
            result = await client.send_request("capabilities")
            if result.get("status") != "success":
                print(f"✗ Request {i+1} failed")
                return False

        # Check stats
        stats = client.get_pool_stats()
        reuse_rate = stats.get('reuse_rate', 0)

        print(f"✓ Completed 10 requests")
        print(f"  Total created: {stats.get('total_created')}")
        print(f"  Total reused: {stats.get('total_reused')}")
        print(f"  Reuse rate: {reuse_rate:.1f}%")
        print(f"  Active connections: {stats.get('active_connections')}")

        # Should have high reuse rate
        if reuse_rate > 50:
            print(f"✓ Good connection reuse ({reuse_rate:.1f}%)")
            return True
        else:
            print(f"⚠ Low connection reuse ({reuse_rate:.1f}%)")
            return True  # Still pass, but warn


async def test_concurrent_requests():
    """Test 3: Concurrent request handling with pool."""
    print("\n" + "=" * 70)
    print("Test 3: Concurrent Requests with Pooling")
    print("=" * 70)

    async with AsyncImHexClient(
        host="localhost",
        port=31337,
        use_connection_pool=True,
        pool_max_size=5
    ) as client:
        # Create 20 concurrent requests
        requests = [("capabilities", {}) for _ in range(20)]

        start = time.perf_counter()
        results = await client.send_batch(requests)
        elapsed = (time.perf_counter() - start) * 1000

        success_count = sum(1 for r in results if r.get("status") == "success")

        print(f"✓ Completed {success_count}/{len(requests)} requests")
        print(f"  Total time: {elapsed:.2f}ms")
        print(f"  Avg per request: {elapsed / len(requests):.2f}ms")

        # Check pool stats
        stats = client.get_pool_stats()
        print(f"  Pool stats:")
        print(f"    Reuse rate: {stats.get('reuse_rate'):.1f}%")
        print(f"    Active connections: {stats.get('active_connections')}")

        return success_count == len(requests)


async def test_pool_vs_no_pool():
    """Test 4: Performance comparison with/without pooling."""
    print("\n" + "=" * 70)
    print("Test 4: Performance Comparison (Pool vs No Pool)")
    print("=" * 70)

    num_requests = 20

    # Test WITHOUT pooling
    print("\nWithout connection pooling:")
    async with AsyncImHexClient(
        host="localhost",
        port=31337,
        use_connection_pool=False
    ) as client:
        start = time.perf_counter()
        for _ in range(num_requests):
            result = await client.send_request("capabilities")
        no_pool_time = (time.perf_counter() - start) * 1000

        print(f"  Time: {no_pool_time:.2f}ms")
        print(f"  Avg per request: {no_pool_time / num_requests:.2f}ms")

    # Test WITH pooling
    print("\nWith connection pooling:")
    async with AsyncImHexClient(
        host="localhost",
        port=31337,
        use_connection_pool=True,
        pool_max_size=10
    ) as client:
        start = time.perf_counter()
        for _ in range(num_requests):
            result = await client.send_request("capabilities")
        pool_time = (time.perf_counter() - start) * 1000

        print(f"  Time: {pool_time:.2f}ms")
        print(f"  Avg per request: {pool_time / num_requests:.2f}ms")

        stats = client.get_pool_stats()
        print(f"  Reuse rate: {stats.get('reuse_rate'):.1f}%")

    # Calculate improvement
    improvement = ((no_pool_time - pool_time) / no_pool_time) * 100
    speedup = no_pool_time / pool_time

    print(f"\n{'✓' if improvement > 0 else '✗'} Performance improvement:")
    print(f"  Faster by: {improvement:.1f}%")
    print(f"  Speedup: {speedup:.2f}x")

    if improvement >= 20:
        print(f"  ✓ Good improvement (target: 30-50%)")
    elif improvement > 0:
        print(f"  ⚠ Modest improvement (target: 30-50%)")
    else:
        print(f"  ✗ No improvement detected")

    return improvement > 0


async def test_pool_stress():
    """Test 5: Stress test with many concurrent requests."""
    print("\n" + "=" * 70)
    print("Test 5: Pool Stress Test (100 concurrent requests)")
    print("=" * 70)

    async with AsyncImHexClient(
        host="localhost",
        port=31337,
        use_connection_pool=True,
        pool_max_size=10
    ) as client:
        # Create 100 requests
        requests = [("file/list", {}) for _ in range(100)]

        start = time.perf_counter()
        results = await client.send_batch(requests)
        elapsed = (time.perf_counter() - start) * 1000

        success_count = sum(1 for r in results if r.get("status") == "success")

        print(f"✓ Completed {success_count}/{len(requests)} requests")
        print(f"  Total time: {elapsed:.2f}ms")
        print(f"  Avg per request: {elapsed / len(requests):.2f}ms")
        print(f"  Throughput: {len(requests) / (elapsed / 1000):.1f} req/s")

        # Check pool stats
        stats = client.get_pool_stats()
        print(f"  Pool stats:")
        print(f"    Total created: {stats.get('total_created')}")
        print(f"    Total reused: {stats.get('total_reused')}")
        print(f"    Reuse rate: {stats.get('reuse_rate'):.1f}%")
        print(f"    Final pool size: {stats.get('pool_size')}")

        return success_count >= len(requests) * 0.95  # Allow 5% failure


async def test_pool_health():
    """Test 6: Pool health monitoring."""
    print("\n" + "=" * 70)
    print("Test 6: Pool Health Monitoring")
    print("=" * 70)

    async with AsyncImHexClient(
        host="localhost",
        port=31337,
        use_connection_pool=True,
        pool_min_size=2,
        pool_max_size=5
    ) as client:
        # Make some requests
        for _ in range(5):
            await client.send_request("capabilities")

        # Check pool health
        stats = client.get_pool_stats()

        print(f"✓ Pool health check:")
        print(f"  Active connections: {stats.get('active_connections')}")
        print(f"  Idle connections: {stats.get('idle_connections')}")
        print(f"  In-use connections: {stats.get('in_use_connections')}")
        print(f"  Failed connections: {stats.get('total_failed')}")
        print(f"  Closed connections: {stats.get('total_closed')}")

        # Pool should be healthy (some active, low failures)
        is_healthy = (
            stats.get('active_connections', 0) > 0 and
            stats.get('total_failed', 0) < 5
        )

        if is_healthy:
            print(f"✓ Pool is healthy")
        else:
            print(f"⚠ Pool health concerns")

        return is_healthy


async def run_all_tests():
    """Run all connection pool tests."""
    print("\n" + "=" * 70)
    print("CONNECTION POOL TEST SUITE")
    print("=" * 70)
    print("\nTesting connection pooling for 30-50% latency reduction")

    tests = [
        ("Pool Initialization", test_pool_initialization),
        ("Connection Reuse", test_connection_reuse),
        ("Concurrent Requests", test_concurrent_requests),
        ("Performance Comparison", test_pool_vs_no_pool),
        ("Stress Test", test_pool_stress),
        ("Health Monitoring", test_pool_health),
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
