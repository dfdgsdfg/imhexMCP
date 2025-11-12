#!/usr/bin/env python3
"""
Caching Performance Benchmark

Measures cache hit rate and performance improvement from LRU + TTL caching.
Target: 50-90% cache hit rate for repeated operations.
"""

import asyncio
import sys
import time
import statistics
from pathlib import Path

lib_path = Path(__file__).parent.parent / "lib"
sys.path.insert(0, str(lib_path))

from async_client import AsyncImHexClient


async def benchmark_repeated_requests(num_requests: int = 50):
    """Benchmark: Repeated identical requests (high cache hit potential)."""

    # Baseline: No caching
    async with AsyncImHexClient(
        host="localhost",
        port=31337,
        enable_cache=False
    ) as client:
        start = time.perf_counter()
        for _ in range(num_requests):
            await client.send_request("capabilities")
        no_cache_time = (time.perf_counter() - start) * 1000

    # With caching
    async with AsyncImHexClient(
        host="localhost",
        port=31337,
        enable_cache=True
    ) as client:
        start = time.perf_counter()
        for _ in range(num_requests):
            await client.send_request("capabilities")
        cached_time = (time.perf_counter() - start) * 1000

        cache_stats = await client.cache_stats()

    return {
        "no_cache_time": no_cache_time,
        "cached_time": cached_time,
        "num_requests": num_requests,
        "improvement": ((no_cache_time - cached_time) / no_cache_time) * 100,
        "speedup": no_cache_time / cached_time,
        "hit_rate": cache_stats.get("hit_rate", 0),
        "hits": cache_stats.get("hits", 0),
        "misses": cache_stats.get("misses", 0)
    }


async def benchmark_mixed_workload(num_iterations: int = 20):
    """Benchmark: Mixed workload with some repeated requests."""

    endpoints = ["capabilities", "file/list", "capabilities", "file/list", "capabilities"]

    # Baseline: No caching
    async with AsyncImHexClient(
        host="localhost",
        port=31337,
        enable_cache=False
    ) as client:
        start = time.perf_counter()
        for _ in range(num_iterations):
            for endpoint in endpoints:
                await client.send_request(endpoint)
        no_cache_time = (time.perf_counter() - start) * 1000

    # With caching
    async with AsyncImHexClient(
        host="localhost",
        port=31337,
        enable_cache=True
    ) as client:
        start = time.perf_counter()
        for _ in range(num_iterations):
            for endpoint in endpoints:
                await client.send_request(endpoint)
        cached_time = (time.perf_counter() - start) * 1000

        cache_stats = await client.cache_stats()

    total_requests = num_iterations * len(endpoints)

    return {
        "no_cache_time": no_cache_time,
        "cached_time": cached_time,
        "total_requests": total_requests,
        "improvement": ((no_cache_time - cached_time) / no_cache_time) * 100,
        "speedup": no_cache_time / cached_time,
        "hit_rate": cache_stats.get("hit_rate", 0),
        "hits": cache_stats.get("hits", 0),
        "misses": cache_stats.get("misses", 0)
    }


async def benchmark_cache_warmup():
    """Benchmark: Cache warmup time vs performance gain."""

    async with AsyncImHexClient(
        host="localhost",
        port=31337,
        enable_cache=True
    ) as client:
        # Warmup phase
        warmup_endpoints = ["capabilities", "file/list"]
        warmup_start = time.perf_counter()
        for endpoint in warmup_endpoints:
            await client.send_request(endpoint)
        warmup_time = (time.perf_counter() - warmup_start) * 1000

        # Cached phase
        cached_start = time.perf_counter()
        for _ in range(20):
            for endpoint in warmup_endpoints:
                await client.send_request(endpoint)
        cached_time = (time.perf_counter() - cached_start) * 1000

        cache_stats = await client.cache_stats()

    return {
        "warmup_time": warmup_time,
        "cached_time": cached_time,
        "avg_cached_request": cached_time / 40,
        "hit_rate": cache_stats.get("hit_rate", 0),
        "hits": cache_stats.get("hits", 0),
        "misses": cache_stats.get("misses", 0)
    }


async def benchmark_cache_with_batching():
    """Benchmark: Cache interaction with request batching."""

    # Create batch request
    batch_size = 10

    # Baseline: No caching
    async with AsyncImHexClient(
        host="localhost",
        port=31337,
        enable_cache=False,
        use_connection_pool=True
    ) as client:
        start = time.perf_counter()
        for _ in range(5):
            batcher = client.create_batcher()
            for i in range(batch_size):
                endpoint = "capabilities" if i % 2 == 0 else "file/list"
                batcher.add(endpoint=endpoint, data={})
            await client.send_batch_advanced(batcher)
        no_cache_time = (time.perf_counter() - start) * 1000

    # With caching
    async with AsyncImHexClient(
        host="localhost",
        port=31337,
        enable_cache=True,
        use_connection_pool=True
    ) as client:
        start = time.perf_counter()
        for _ in range(5):
            batcher = client.create_batcher()
            for i in range(batch_size):
                endpoint = "capabilities" if i % 2 == 0 else "file/list"
                batcher.add(endpoint=endpoint, data={})
            await client.send_batch_advanced(batcher)
        cached_time = (time.perf_counter() - start) * 1000

        cache_stats = await client.cache_stats()

    total_requests = 5 * batch_size

    return {
        "no_cache_time": no_cache_time,
        "cached_time": cached_time,
        "total_requests": total_requests,
        "improvement": ((no_cache_time - cached_time) / no_cache_time) * 100,
        "speedup": no_cache_time / cached_time,
        "hit_rate": cache_stats.get("hit_rate", 0)
    }


async def benchmark_cache_overhead():
    """Benchmark: Cache overhead for unique requests (worst case)."""

    # Baseline: No caching
    async with AsyncImHexClient(
        host="localhost",
        port=31337,
        enable_cache=False
    ) as client:
        latencies = []
        for _ in range(20):
            start = time.perf_counter()
            await client.send_request("capabilities")
            latencies.append((time.perf_counter() - start) * 1000)

        no_cache_mean = statistics.mean(latencies)
        no_cache_median = statistics.median(latencies)

    # With caching (but all cache misses)
    async with AsyncImHexClient(
        host="localhost",
        port=31337,
        enable_cache=True
    ) as client:
        latencies = []
        for i in range(20):
            # Different data each time to prevent cache hits
            start = time.perf_counter()
            await client.send_request("file/list", {"_unique": i})
            latencies.append((time.perf_counter() - start) * 1000)

        cached_mean = statistics.mean(latencies)
        cached_median = statistics.median(latencies)

    overhead_pct = ((cached_mean - no_cache_mean) / no_cache_mean) * 100

    return {
        "no_cache_mean": no_cache_mean,
        "no_cache_median": no_cache_median,
        "cached_mean": cached_mean,
        "cached_median": cached_median,
        "overhead_pct": overhead_pct
    }


async def main():
    print("=" * 70)
    print("CACHING PERFORMANCE BENCHMARK")
    print("=" * 70)
    print("\nMeasuring cache hit rate and performance improvement")
    print("Target: 50-90% cache hit rate\n")

    # Benchmark 1: Repeated requests
    print("[1/5] Benchmarking repeated identical requests...")
    repeated_stats = await benchmark_repeated_requests(num_requests=50)

    print(f"  Without caching: {repeated_stats['no_cache_time']:.2f}ms")
    print(f"  With caching: {repeated_stats['cached_time']:.2f}ms")
    print(f"  Improvement: {repeated_stats['improvement']:.1f}%")
    print(f"  Speedup: {repeated_stats['speedup']:.2f}x")
    print(f"  Cache hit rate: {repeated_stats['hit_rate']:.1f}%")
    print(f"  Hits/Misses: {repeated_stats['hits']}/{repeated_stats['misses']}")

    # Benchmark 2: Mixed workload
    print("\n[2/5] Benchmarking mixed workload...")
    mixed_stats = await benchmark_mixed_workload(num_iterations=20)

    print(f"  Without caching: {mixed_stats['no_cache_time']:.2f}ms")
    print(f"  With caching: {mixed_stats['cached_time']:.2f}ms")
    print(f"  Total requests: {mixed_stats['total_requests']}")
    print(f"  Improvement: {mixed_stats['improvement']:.1f}%")
    print(f"  Speedup: {mixed_stats['speedup']:.2f}x")
    print(f"  Cache hit rate: {mixed_stats['hit_rate']:.1f}%")

    # Benchmark 3: Cache warmup
    print("\n[3/5] Benchmarking cache warmup...")
    warmup_stats = await benchmark_cache_warmup()

    print(f"  Warmup time: {warmup_stats['warmup_time']:.2f}ms")
    print(f"  Cached execution (40 requests): {warmup_stats['cached_time']:.2f}ms")
    print(f"  Avg per cached request: {warmup_stats['avg_cached_request']:.2f}ms")
    print(f"  Cache hit rate: {warmup_stats['hit_rate']:.1f}%")

    # Benchmark 4: Cache + Batching
    print("\n[4/5] Benchmarking cache + batching interaction...")
    batching_stats = await benchmark_cache_with_batching()

    print(f"  Without caching: {batching_stats['no_cache_time']:.2f}ms")
    print(f"  With caching: {batching_stats['cached_time']:.2f}ms")
    print(f"  Improvement: {batching_stats['improvement']:.1f}%")
    print(f"  Speedup: {batching_stats['speedup']:.2f}x")
    print(f"  Cache hit rate: {batching_stats['hit_rate']:.1f}%")

    # Benchmark 5: Cache overhead
    print("\n[5/5] Benchmarking cache overhead (worst case)...")
    overhead_stats = await benchmark_cache_overhead()

    print(f"  Mean latency (no cache): {overhead_stats['no_cache_mean']:.2f}ms")
    print(f"  Mean latency (with cache, all misses): {overhead_stats['cached_mean']:.2f}ms")
    print(f"  Cache overhead: {abs(overhead_stats['overhead_pct']):.1f}%")

    # Overall results
    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)

    avg_hit_rate = statistics.mean([
        repeated_stats['hit_rate'],
        mixed_stats['hit_rate'],
        warmup_stats['hit_rate'],
        batching_stats['hit_rate']
    ])

    avg_improvement = statistics.mean([
        repeated_stats['improvement'],
        mixed_stats['improvement'],
        batching_stats['improvement']
    ])

    print(f"\nAverage cache hit rate: {avg_hit_rate:.1f}%")
    print(f"Average performance improvement: {avg_improvement:.1f}%")
    print(f"\nDetailed results:")
    print(f"  Repeated requests: {repeated_stats['hit_rate']:.1f}% hit rate, {repeated_stats['speedup']:.2f}x speedup")
    print(f"  Mixed workload: {mixed_stats['hit_rate']:.1f}% hit rate, {mixed_stats['speedup']:.2f}x speedup")
    print(f"  Cache + Batching: {batching_stats['hit_rate']:.1f}% hit rate, {batching_stats['speedup']:.2f}x speedup")
    print(f"  Cache overhead (worst case): {abs(overhead_stats['overhead_pct']):.1f}%")

    # Verdict
    print("\n" + "-" * 70)
    if avg_hit_rate >= 50:
        print(f"✓ TARGET ACHIEVED: {avg_hit_rate:.1f}% average hit rate (target: 50-90%)")
    elif avg_hit_rate >= 40:
        print(f"✓ GOOD: {avg_hit_rate:.1f}% average hit rate (target: 50-90%)")
    elif avg_hit_rate >= 30:
        print(f"⚠ MODEST: {avg_hit_rate:.1f}% average hit rate (target: 50-90%)")
    else:
        print(f"✗ BELOW TARGET: {avg_hit_rate:.1f}% average hit rate (target: 50-90%)")

    print("=" * 70 + "\n")

    return avg_hit_rate >= 40


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
