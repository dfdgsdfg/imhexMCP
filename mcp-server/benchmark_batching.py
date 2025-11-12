#!/usr/bin/env python3
"""
Request Batching Performance Benchmark

Measures the round-trip reduction achieved by request batching & pipelining.
Target: 40-60% reduction in total time for batch operations.
"""

import asyncio
import sys
import time
import statistics
from pathlib import Path

lib_path = Path(__file__).parent.parent / "lib"
sys.path.insert(0, str(lib_path))

from async_client import AsyncImHexClient
from request_batching import BatchMode


async def benchmark_individual_requests(num_requests: int = 20):
    """Benchmark: Send requests individually (baseline)."""

    async with AsyncImHexClient(
        host="localhost",
        port=31337,
        use_connection_pool=True
    ) as client:
        latencies = []

        for _ in range(num_requests):
            start = time.perf_counter()
            await client.send_request("file/list")
            elapsed = (time.perf_counter() - start) * 1000
            latencies.append(elapsed)

        return {
            "mean": statistics.mean(latencies),
            "median": statistics.median(latencies),
            "total": sum(latencies),
            "num_requests": num_requests
        }


async def benchmark_parallel_batching(num_requests: int = 20):
    """Benchmark: Send requests in parallel batch."""

    async with AsyncImHexClient(
        host="localhost",
        port=31337,
        use_connection_pool=True
    ) as client:
        # Create batch
        batcher = client.create_batcher(mode=BatchMode.PARALLEL)

        for _ in range(num_requests):
            batcher.add(endpoint="file/list", data={})

        # Execute batch
        start = time.perf_counter()
        responses, stats = await client.send_batch_advanced(batcher)
        elapsed = (time.perf_counter() - start) * 1000

        return {
            "mean": elapsed / num_requests,
            "median": elapsed / num_requests,
            "total": elapsed,
            "num_requests": num_requests,
            "success_rate": stats.success_rate(),
            "round_trips_saved": stats.round_trips_saved
        }


async def benchmark_multi_read(num_regions: int = 20):
    """Benchmark: Multi-read pattern (reading multiple regions)."""

    async with AsyncImHexClient(
        host="localhost",
        port=31337,
        use_connection_pool=True
    ) as client:
        # Check if files are open
        file_list = await client.send_request("file/list")
        files_open = file_list.get("data", {}).get("count", 0)

        if files_open == 0:
            return None  # Skip if no files open

        # Benchmark individual reads
        offsets = list(range(0, num_regions * 256, 256))
        individual_times = []

        for offset in offsets:
            start = time.perf_counter()
            await client.send_request("data/read", {
                "provider_id": 0,
                "offset": offset,
                "size": 64
            })
            elapsed = (time.perf_counter() - start) * 1000
            individual_times.append(elapsed)

        individual_total = sum(individual_times)

        # Benchmark batched reads
        start = time.perf_counter()
        chunks, stats = await client.batch_multi_read(0, offsets, 64)
        batched_total = (time.perf_counter() - start) * 1000

        return {
            "individual_total": individual_total,
            "batched_total": batched_total,
            "num_regions": num_regions,
            "improvement": ((individual_total - batched_total) / individual_total) * 100,
            "round_trips_saved": stats.round_trips_saved
        }


async def benchmark_sequential_pipeline(num_requests: int = 10):
    """Benchmark: Sequential pipeline vs individual sequential requests."""

    async with AsyncImHexClient(
        host="localhost",
        port=31337,
        use_connection_pool=True
    ) as client:
        # Benchmark individual sequential requests
        start = time.perf_counter()
        for _ in range(num_requests):
            await client.send_request("file/list")
        individual_total = (time.perf_counter() - start) * 1000

        # Benchmark pipelined sequential requests
        batcher = client.create_batcher(mode=BatchMode.SEQUENTIAL)
        for i in range(num_requests):
            batcher.add(request_id=f"req_{i}", endpoint="file/list", data={})

        start = time.perf_counter()
        responses, stats = await client.send_batch_advanced(batcher)
        pipelined_total = (time.perf_counter() - start) * 1000

        return {
            "individual_total": individual_total,
            "pipelined_total": pipelined_total,
            "num_requests": num_requests,
            "improvement": ((individual_total - pipelined_total) / individual_total) * 100,
            "round_trips_saved": stats.round_trips_saved
        }


async def main():
    print("=" * 70)
    print("REQUEST BATCHING PERFORMANCE BENCHMARK")
    print("=" * 70)
    print("\nMeasuring round-trip reduction from request batching")
    print("Target: 40-60% improvement in total time\\n")

    # Benchmark 1: Parallel batching
    print("[1/4] Benchmarking parallel batching...")
    individual_stats = await benchmark_individual_requests(num_requests=20)
    batched_stats = await benchmark_parallel_batching(num_requests=20)

    print(f"  Individual requests (baseline):")
    print(f"    Total time: {individual_stats['total']:.2f}ms")
    print(f"    Avg per request: {individual_stats['mean']:.2f}ms")

    print(f"\\n  Parallel batch:")
    print(f"    Total time: {batched_stats['total']:.2f}ms")
    print(f"    Avg per request: {batched_stats['mean']:.2f}ms")
    print(f"    Success rate: {batched_stats['success_rate']:.1f}%")
    print(f"    Round-trips saved: {batched_stats['round_trips_saved']}")

    parallel_improvement = ((individual_stats['total'] - batched_stats['total']) / individual_stats['total']) * 100
    parallel_speedup = individual_stats['total'] / batched_stats['total']

    print(f"\\n  Performance improvement:")
    print(f"    Time reduction: {parallel_improvement:.1f}%")
    print(f"    Speedup: {parallel_speedup:.2f}x")

    # Benchmark 2: Multi-read pattern
    print("\\n[2/4] Benchmarking multi-read pattern...")
    multi_read_stats = await benchmark_multi_read(num_regions=20)

    if multi_read_stats:
        print(f"  Individual reads (baseline):")
        print(f"    Total time: {multi_read_stats['individual_total']:.2f}ms")

        print(f"\\n  Batched multi-read:")
        print(f"    Total time: {multi_read_stats['batched_total']:.2f}ms")
        print(f"    Round-trips saved: {multi_read_stats['round_trips_saved']}")

        print(f"\\n  Performance improvement:")
        print(f"    Time reduction: {multi_read_stats['improvement']:.1f}%")
        print(f"    Speedup: {multi_read_stats['individual_total'] / multi_read_stats['batched_total']:.2f}x")
    else:
        print("  Skipped (no files open)")

    # Benchmark 3: Sequential pipelining
    print("\\n[3/4] Benchmarking sequential pipelining...")
    pipeline_stats = await benchmark_sequential_pipeline(num_requests=10)

    print(f"  Individual sequential requests:")
    print(f"    Total time: {pipeline_stats['individual_total']:.2f}ms")

    print(f"\\n  Pipelined sequential:")
    print(f"    Total time: {pipeline_stats['pipelined_total']:.2f}ms")
    print(f"    Round-trips saved: {pipeline_stats['round_trips_saved']}")

    print(f"\\n  Performance improvement:")
    print(f"    Time reduction: {pipeline_stats['improvement']:.1f}%")
    print(f"    Speedup: {pipeline_stats['individual_total'] / pipeline_stats['pipelined_total']:.2f}x")

    # Benchmark 4: Large batch stress test
    print("\\n[4/4] Benchmarking large batch (50 requests)...")
    large_individual = await benchmark_individual_requests(num_requests=50)
    large_batched = await benchmark_parallel_batching(num_requests=50)

    large_improvement = ((large_individual['total'] - large_batched['total']) / large_individual['total']) * 100
    large_speedup = large_individual['total'] / large_batched['total']

    print(f"  Individual: {large_individual['total']:.2f}ms")
    print(f"  Batched: {large_batched['total']:.2f}ms")
    print(f"  Improvement: {large_improvement:.1f}% ({large_speedup:.2f}x speedup)")
    print(f"  Round-trips saved: {large_batched['round_trips_saved']}")

    # Overall results
    print("\\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)

    avg_improvement = statistics.mean([
        parallel_improvement,
        multi_read_stats['improvement'] if multi_read_stats else parallel_improvement,
        pipeline_stats['improvement'],
        large_improvement
    ])

    print(f"\\nAverage time reduction across benchmarks: {avg_improvement:.1f}%")
    print(f"Parallel batching: {parallel_improvement:.1f}% reduction ({individual_stats['total']:.2f}ms → {batched_stats['total']:.2f}ms)")
    if multi_read_stats:
        print(f"Multi-read pattern: {multi_read_stats['improvement']:.1f}% reduction")
    print(f"Sequential pipelining: {pipeline_stats['improvement']:.1f}% reduction")
    print(f"Large batch (50 requests): {large_improvement:.1f}% reduction")

    # Verdict
    print("\\n" + "-" * 70)
    if avg_improvement >= 40:
        print(f"✓ TARGET ACHIEVED: {avg_improvement:.1f}% average reduction (target: 40-60%)")
    elif avg_improvement >= 30:
        print(f"✓ GOOD: {avg_improvement:.1f}% average reduction (target: 40-60%)")
    elif avg_improvement >= 20:
        print(f"⚠ MODEST: {avg_improvement:.1f}% average reduction (target: 40-60%)")
    else:
        print(f"✗ BELOW TARGET: {avg_improvement:.1f}% average reduction (target: 40-60%)")

    print("=" * 70 + "\\n")

    return avg_improvement >= 30


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
