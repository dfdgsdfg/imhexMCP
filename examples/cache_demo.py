#!/usr/bin/env python3
"""
ImHex MCP Cache Demonstration

Shows the performance benefits of response caching for repeated operations.
"""

import sys
import time
from pathlib import Path

# Add lib directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))

from cached_client import create_client


def demo_cache_performance():
    """Demonstrate cache performance improvements."""
    print("=" * 70)
    print("ImHex MCP Cache Performance Demo")
    print("=" * 70)

    # Create clients with and without caching
    print("\nCreating clients...")
    cached_client = create_client(cache_enabled=True)
    uncached_client = create_client(cache_enabled=False)

    # Test 1: Repeated capabilities requests
    print("\n[1/3] Testing repeated capabilities requests...")
    print("  Without cache:")

    start = time.perf_counter()
    for _ in range(10):
        result = uncached_client.get_capabilities()
    uncached_time = time.perf_counter() - start

    print(f"    10 requests: {uncached_time*1000:.2f}ms")

    print("  With cache:")
    start = time.perf_counter()
    for _ in range(10):
        result = cached_client.get_capabilities()
    cached_time = time.perf_counter() - start

    print(f"    10 requests: {cached_time*1000:.2f}ms")
    speedup = uncached_time / cached_time if cached_time > 0 else 0
    print(f"    Speedup: {speedup:.1f}x faster")

    # Test 2: Repeated file list requests
    print("\n[2/3] Testing repeated file/list requests...")
    print("  Without cache:")

    start = time.perf_counter()
    for _ in range(10):
        result = uncached_client.list_files()
    uncached_time = time.perf_counter() - start

    print(f"    10 requests: {uncached_time*1000:.2f}ms")

    print("  With cache:")
    start = time.perf_counter()
    for _ in range(10):
        result = cached_client.list_files()
    cached_time = time.perf_counter() - start

    print(f"    10 requests: {cached_time*1000:.2f}ms")
    speedup = uncached_time / cached_time if cached_time > 0 else 0
    print(f"    Speedup: {speedup:.1f}x faster")

    # Test 3: Show cache statistics
    print("\n[3/3] Cache statistics:")
    stats = cached_client.get_cache_stats()
    if stats:
        print(f"    Hits:      {stats['hits']}")
        print(f"    Misses:    {stats['misses']}")
        print(f"    Hit rate:  {stats['hit_rate']:.1f}%")
        print(f"    Size:      {stats['size']}/{stats['max_size']} entries")
        print(f"    Evictions: {stats['evictions']}")

    print("\n" + "=" * 70)
    print("Demo complete!")
    print("=" * 70)


def demo_cache_invalidation():
    """Demonstrate cache invalidation."""
    print("\n" + "=" * 70)
    print("ImHex MCP Cache Invalidation Demo")
    print("=" * 70)

    client = create_client(cache_enabled=True)

    # Make initial request (cache miss)
    print("\n[1/3] Initial request (cache miss)...")
    result = client.get_capabilities()
    stats = client.get_cache_stats()
    print(f"  Status: {result.get('status')}")
    print(f"  Cache: {stats['hits']} hits, {stats['misses']} misses")

    # Repeat request (cache hit)
    print("\n[2/3] Repeated request (cache hit)...")
    result = client.get_capabilities()
    stats = client.get_cache_stats()
    print(f"  Status: {result.get('status')}")
    print(f"  Cache: {stats['hits']} hits, {stats['misses']} misses")

    # Invalidate and request again (cache miss)
    print("\n[3/3] After invalidation (cache miss)...")
    client.invalidate_endpoint("capabilities")
    result = client.get_capabilities()
    stats = client.get_cache_stats()
    print(f"  Status: {result.get('status')}")
    print(f"  Cache: {stats['hits']} hits, {stats['misses']} misses")

    print("\n" + "=" * 70)


def demo_ttl_strategies():
    """Demonstrate TTL strategies for different endpoints."""
    print("\n" + "=" * 70)
    print("ImHex MCP TTL Strategy Demo")
    print("=" * 70)

    from cache import CachingStrategy

    # Show TTL for different endpoint types
    print("\nEndpoint TTL strategies:")

    stable = ["capabilities", "file/info"]
    moderate = ["file/list", "file/current"]
    volatile = ["data/read", "data/search", "data/statistics"]

    print("\n  Stable endpoints (5 min TTL):")
    for endpoint in stable:
        ttl = CachingStrategy.get_ttl_for_endpoint(endpoint)
        print(f"    {endpoint:20s} -> {ttl:.0f}s")

    print("\n  Moderate endpoints (1 min TTL):")
    for endpoint in moderate:
        ttl = CachingStrategy.get_ttl_for_endpoint(endpoint)
        print(f"    {endpoint:20s} -> {ttl:.0f}s")

    print("\n  Volatile endpoints (10 sec TTL):")
    for endpoint in volatile:
        ttl = CachingStrategy.get_ttl_for_endpoint(endpoint)
        print(f"    {endpoint:20s} -> {ttl:.0f}s")

    print("\n" + "=" * 70)


def main():
    """Run all demonstrations."""
    try:
        # Performance comparison
        demo_cache_performance()

        # Invalidation
        demo_cache_invalidation()

        # TTL strategies
        demo_ttl_strategies()

    except Exception as e:
        print(f"\nError: {e}")
        print("\nPlease ensure:")
        print("  1. ImHex is running")
        print("  2. Network Interface is enabled in Settings")
        print("  3. Port 31337 is accessible")
        sys.exit(1)


if __name__ == "__main__":
    main()
