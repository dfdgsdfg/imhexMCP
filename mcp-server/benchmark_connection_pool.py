#!/usr/bin/env python3
"""
Connection Pool Performance Benchmark

Measures the latency reduction achieved by connection pooling.
Target: 30-50% improvement by eliminating TCP handshake overhead.
"""

import asyncio
import sys
import time
import statistics
from pathlib import Path

lib_path = Path(__file__).parent.parent / "lib"
sys.path.insert(0, str(lib_path))

from async_client import AsyncImHexClient


async def benchmark_latency(use_pool: bool, num_requests: int = 50):
    """Benchmark request latency with/without connection pooling."""

    async with AsyncImHexClient(
        host="localhost",
        port=31337,
        use_connection_pool=use_pool,
        pool_max_size=10
    ) as client:
        latencies = []

        for _ in range(num_requests):
            start = time.perf_counter()
            await client.send_request("capabilities")
            elapsed = (time.perf_counter() - start) * 1000
            latencies.append(elapsed)

        return {
            "mean": statistics.mean(latencies),
            "median": statistics.median(latencies),
            "min": min(latencies),
            "max": max(latencies),
            "p95": sorted(latencies)[int(len(latencies) * 0.95)],
            "pool_enabled": use_pool,
            "num_requests": num_requests
        }


async def main():
    print("=" * 70)
    print("CONNECTION POOL PERFORMANCE BENCHMARK")
    print("=" * 70)
    print("\nMeasuring latency reduction from connection pooling")
    print("Target: 30-50% improvement\n")

    # Benchmark WITHOUT pooling
    print("Benchmarking WITHOUT connection pooling...")
    no_pool_stats = await benchmark_latency(use_pool=False, num_requests=50)

    print(f"  Mean latency:   {no_pool_stats['mean']:.2f}ms")
    print(f"  Median latency: {no_pool_stats['median']:.2f}ms")
    print(f"  P95 latency:    {no_pool_stats['p95']:.2f}ms")
    print(f"  Range:          {no_pool_stats['min']:.2f}ms - {no_pool_stats['max']:.2f}ms")

    # Benchmark WITH pooling
    print("\nBenchmarking WITH connection pooling...")
    pool_stats = await benchmark_latency(use_pool=True, num_requests=50)

    print(f"  Mean latency:   {pool_stats['mean']:.2f}ms")
    print(f"  Median latency: {pool_stats['median']:.2f}ms")
    print(f"  P95 latency:    {pool_stats['p95']:.2f}ms")
    print(f"  Range:          {pool_stats['min']:.2f}ms - {pool_stats['max']:.2f}ms")

    # Calculate improvement
    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)

    mean_improvement = ((no_pool_stats['mean'] - pool_stats['mean']) / no_pool_stats['mean']) * 100
    median_improvement = ((no_pool_stats['median'] - pool_stats['median']) / no_pool_stats['median']) * 100
    p95_improvement = ((no_pool_stats['p95'] - pool_stats['p95']) / no_pool_stats['p95']) * 100

    print(f"Mean latency reduction:   {mean_improvement:+.1f}% ({no_pool_stats['mean']:.2f}ms → {pool_stats['mean']:.2f}ms)")
    print(f"Median latency reduction: {median_improvement:+.1f}% ({no_pool_stats['median']:.2f}ms → {pool_stats['median']:.2f}ms)")
    print(f"P95 latency reduction:    {p95_improvement:+.1f}% ({no_pool_stats['p95']:.2f}ms → {pool_stats['p95']:.2f}ms)")

    # Verdict
    print("\n" + "-" * 70)
    if mean_improvement >= 30:
        print(f"✓ TARGET ACHIEVED: {mean_improvement:.1f}% improvement (target: 30-50%)")
    elif mean_improvement >= 20:
        print(f"✓ GOOD: {mean_improvement:.1f}% improvement (target: 30-50%)")
    elif mean_improvement > 0:
        print(f"⚠ MODEST: {mean_improvement:.1f}% improvement (target: 30-50%)")
    else:
        print(f"✗ NO IMPROVEMENT: {mean_improvement:.1f}%")

    print("=" * 70 + "\n")

    return mean_improvement >= 20


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
