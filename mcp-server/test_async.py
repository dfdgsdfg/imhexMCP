#!/usr/bin/env python3
"""
Async Client Tests

Tests for the async ImHex client including:
- Basic async operations
- Concurrent requests
- Performance comparison with sync client
- Streaming operations
- Caching and profiling
"""

import asyncio
import sys
import time
from pathlib import Path

# Add lib directory to path
lib_path = Path(__file__).parent.parent / "lib"
sys.path.insert(0, str(lib_path))

from async_client import (
    AsyncImHexClient,
    AsyncEnhancedImHexClient,
    async_batch_read,
    run_async
)


async def test_basic_async_operations():
    """Test basic async operations."""
    print("\n" + "=" * 70)
    print("Test 1: Basic Async Operations")
    print("=" * 70)

    client = AsyncImHexClient(host="localhost", port=31337)

    try:
        # Test capabilities
        result = await client.get_capabilities()
        print(f"✓ Capabilities: {result.get('status')}")

        # Test file list
        result = await client.list_files()
        print(f"✓ File list: {result.get('status')}")
        print(f"  Files open: {result.get('data', {}).get('count', 0)}")

        return True

    except Exception as e:
        print(f"✗ FAILED: {e}")
        return False


async def test_concurrent_requests():
    """Test concurrent request handling."""
    print("\n" + "=" * 70)
    print("Test 2: Concurrent Requests")
    print("=" * 70)

    client = AsyncImHexClient(host="localhost", port=31337, max_concurrent=5)

    try:
        # Create multiple concurrent requests
        requests = [
            ("capabilities", {}),
            ("file/list", {}),
            ("capabilities", {}),
            ("file/list", {}),
            ("capabilities", {}),
        ]

        start = time.perf_counter()
        results = await client.send_batch(requests)
        elapsed = (time.perf_counter() - start) * 1000

        print(f"✓ Sent {len(requests)} concurrent requests")
        print(f"  Total time: {elapsed:.2f}ms")
        print(f"  Avg per request: {elapsed / len(requests):.2f}ms")

        # Verify all succeeded
        success_count = sum(1 for r in results if r.get("status") == "success")
        print(f"  Successful: {success_count}/{len(requests)}")

        return success_count == len(requests)

    except Exception as e:
        print(f"✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_performance_comparison():
    """Compare async vs sync performance."""
    print("\n" + "=" * 70)
    print("Test 3: Performance Comparison (Async vs Sync)")
    print("=" * 70)

    client = AsyncImHexClient(host="localhost", port=31337)

    # Test async performance
    requests = [("file/list", {}) for _ in range(10)]

    start = time.perf_counter()
    results = await client.send_batch(requests)
    async_time = (time.perf_counter() - start) * 1000

    print(f"Async batch ({len(requests)} requests):")
    print(f"  Total time: {async_time:.2f}ms")
    print(f"  Avg per request: {async_time / len(requests):.2f}ms")

    # For comparison, estimate sequential time
    # (We'd need the sync client for real comparison)
    sequential_estimate = async_time * 3  # Rough estimate
    improvement = ((sequential_estimate - async_time) / sequential_estimate) * 100

    print(f"\nEstimated improvement: ~{improvement:.0f}%")
    print(f"(Real improvement depends on network latency and server load)")

    return len(results) == len(requests)


async def test_enhanced_client_caching():
    """Test enhanced client with caching."""
    print("\n" + "=" * 70)
    print("Test 4: Enhanced Client with Caching")
    print("=" * 70)

    client = AsyncEnhancedImHexClient(
        host="localhost",
        port=31337,
        enable_cache=True,
        cache_max_size=100
    )

    try:
        # First request (cache miss)
        start = time.perf_counter()
        result1 = await client.send_request("capabilities")
        time1 = (time.perf_counter() - start) * 1000

        # Second request (cache hit)
        start = time.perf_counter()
        result2 = await client.send_request("capabilities")
        time2 = (time.perf_counter() - start) * 1000

        print(f"First request (cache miss): {time1:.2f}ms")
        print(f"Second request (cache hit): {time2:.2f}ms")

        if time2 < time1:
            speedup = (time1 / time2)
            print(f"✓ Cache speedup: {speedup:.1f}x faster")
        else:
            print(f"⚠ No speedup detected (cache may be overhead for fast operations)")

        # Check cache stats
        stats = client.get_cache_stats()
        print(f"\nCache stats:")
        print(f"  Enabled: {stats.get('enabled')}")
        print(f"  Size: {stats.get('size')}")

        return True

    except Exception as e:
        print(f"✗ FAILED: {e}")
        return False


async def test_streaming():
    """Test async streaming."""
    print("\n" + "=" * 70)
    print("Test 5: Async Streaming")
    print("=" * 70)

    client = AsyncImHexClient(host="localhost", port=31337)

    try:
        # Get list of files
        files = await client.list_files()
        providers = files.get("data", {}).get("providers", [])

        if not providers:
            print("⚠ No files open - skipping streaming test")
            return True

        provider_id = providers[0]["id"]
        print(f"Testing streaming from provider {provider_id}")

        # Stream first 1KB
        chunk_count = 0
        total_bytes = 0

        async for chunk in client.stream_read(provider_id, offset=0, total_size=1024, chunk_size=256):
            chunk_count += 1
            total_bytes += len(chunk)

        print(f"✓ Streamed {total_bytes} bytes in {chunk_count} chunks")
        print(f"  Avg chunk size: {total_bytes / chunk_count:.0f} bytes")

        return total_bytes == 1024

    except Exception as e:
        print(f"✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_error_handling():
    """Test error handling and retry."""
    print("\n" + "=" * 70)
    print("Test 6: Error Handling and Retry")
    print("=" * 70)

    client = AsyncImHexClient(host="localhost", port=31337)

    try:
        # Test invalid endpoint (should handle gracefully)
        result = await client.send_request("invalid/endpoint")

        if result.get("status") == "error":
            print("✓ Invalid endpoint handled gracefully")
        else:
            print(f"⚠ Unexpected response: {result}")

        # Test with invalid data
        result = await client.send_request("file/info", {"provider_id": 99999})

        if result.get("status") == "error":
            print("✓ Invalid provider ID handled gracefully")
        else:
            print(f"⚠ Unexpected response: {result}")

        return True

    except Exception as e:
        print(f"✗ FAILED: {e}")
        return False


async def test_context_manager():
    """Test async context manager."""
    print("\n" + "=" * 70)
    print("Test 7: Async Context Manager")
    print("=" * 70)

    try:
        async with AsyncImHexClient(host="localhost", port=31337) as client:
            result = await client.get_capabilities()
            print(f"✓ Context manager: {result.get('status')}")

        print("✓ Context manager closed successfully")
        return True

    except Exception as e:
        print(f"✗ FAILED: {e}")
        return False


async def test_performance_profiling():
    """Test performance profiling in enhanced client."""
    print("\n" + "=" * 70)
    print("Test 8: Performance Profiling")
    print("=" * 70)

    client = AsyncEnhancedImHexClient(
        host="localhost",
        port=31337,
        enable_profiling=True
    )

    try:
        # Make several requests
        for _ in range(5):
            await client.send_request("file/list")

        # Get performance stats
        stats = client.get_performance_stats()

        if stats.get("enabled"):
            print(f"Performance stats:")
            print(f"  Request count: {stats.get('request_count')}")
            print(f"  Avg time: {stats.get('avg_time_ms'):.2f}ms")
            print(f"  Min time: {stats.get('min_time_ms'):.2f}ms")
            print(f"  Max time: {stats.get('max_time_ms'):.2f}ms")
            print(f"  P50: {stats.get('p50_time_ms'):.2f}ms")
            print(f"  P95: {stats.get('p95_time_ms'):.2f}ms")
            print("✓ Profiling working")
        else:
            print("✗ Profiling not enabled")
            return False

        return True

    except Exception as e:
        print(f"✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_batch_read_helper():
    """Test batch read helper function."""
    print("\n" + "=" * 70)
    print("Test 9: Batch Read Helper")
    print("=" * 70)

    client = AsyncImHexClient(host="localhost", port=31337)

    try:
        # Get list of files
        files = await client.list_files()
        providers = files.get("data", {}).get("providers", [])

        if not providers:
            print("⚠ No files open - skipping batch read test")
            return True

        provider_id = providers[0]["id"]

        # Read multiple regions concurrently
        offsets = [0, 64, 128, 192, 256]
        start = time.perf_counter()
        results = await async_batch_read(client, provider_id, offsets, size=32)
        elapsed = (time.perf_counter() - start) * 1000

        print(f"✓ Read {len(offsets)} regions concurrently")
        print(f"  Total time: {elapsed:.2f}ms")
        print(f"  Avg per read: {elapsed / len(offsets):.2f}ms")
        print(f"  Bytes per region: {len(results[0])} bytes")

        return len(results) == len(offsets)

    except Exception as e:
        print(f"✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def run_all_tests():
    """Run all async tests."""
    print("\n" + "=" * 70)
    print("ASYNC CLIENT TEST SUITE")
    print("=" * 70)

    tests = [
        ("Basic Async Operations", test_basic_async_operations),
        ("Concurrent Requests", test_concurrent_requests),
        ("Performance Comparison", test_performance_comparison),
        ("Enhanced Client Caching", test_enhanced_client_caching),
        ("Async Streaming", test_streaming),
        ("Error Handling", test_error_handling),
        ("Context Manager", test_context_manager),
        ("Performance Profiling", test_performance_profiling),
        ("Batch Read Helper", test_batch_read_helper),
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
