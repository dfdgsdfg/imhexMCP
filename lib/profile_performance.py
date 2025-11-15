#!/usr/bin/env python3
"""
Performance profiling script for ImHex MCP library.

Profiles key operations to identify bottlenecks:
- AsyncImHexClient operations
- Connection pooling
- Caching
- Compression
- Request batching
"""

import cProfile
import pstats
import io
import asyncio
import sys
from pathlib import Path

# Add lib to path
sys.path.insert(0, str(Path(__file__).parent))

from async_client import AsyncImHexClient
from connection_pool import ConnectionPool
from cache import AsyncResponseCache
from data_compression import DataCompressor, CompressionConfig
from request_batching import RequestBatcher, BatchMode


async def profile_async_client():
    """Profile AsyncImHexClient basic operations."""
    print("\n=== Profiling AsyncImHexClient ===")

    # Create client with all features enabled
    client = AsyncImHexClient(
        host="localhost",
        port=31337,
        use_connection_pool=True,
        enable_cache=True,
        enable_compression=True,
    )

    # Note: These are mock operations without actual ImHex server
    # In real profiling, we'd connect to actual server

    # Simulate cache operations
    cache = client._cache
    if cache:
        for i in range(1000):
            endpoint = f"test/endpoint_{i % 10}"
            data = {"id": i}
            value = {"data": f"value_{i}" * 100}
            await cache.set(endpoint, data, value)

        for i in range(1000):
            endpoint = f"test/endpoint_{i % 10}"
            data = {"id": i}
            await cache.get(endpoint, data)

    print(f"Cache operations completed: 1000 sets, 1000 gets")


def profile_compression():
    """Profile data compression operations."""
    print("\n=== Profiling Data Compression ===")

    config = CompressionConfig(
        algorithm="zlib",
        level=6,
        min_size=1024,
    )
    compressor = DataCompressor(config)

    # Test data
    small_data = b"x" * 512
    medium_data = b"y" * 4096
    large_data = b"z" * 65536

    # Compression tests
    for size, data in [("small", small_data), ("medium", medium_data), ("large", large_data)]:
        for _ in range(100):
            compressed = compressor.compress_data(data)
            if compressed.get("compressed"):
                decompressed = compressor.decompress_data(compressed)
                assert decompressed == data

    stats = compressor.get_stats()
    print(f"Compression stats: {stats}")


async def profile_caching():
    """Profile caching operations with various workloads."""
    print("\n=== Profiling Caching ===")

    cache = AsyncResponseCache(max_size=10000, max_memory_mb=100.0)

    # Sequential writes
    for i in range(5000):
        endpoint = f"endpoint_{i % 100}"
        data = {"id": i}
        value = {"data": "x" * 200}
        await cache.set(endpoint, data, value)

    # Sequential reads (cache hits)
    for i in range(5000):
        endpoint = f"endpoint_{i % 100}"
        data = {"id": i}
        await cache.get(endpoint, data)

    # Random reads (mix of hits and misses)
    import random
    for i in range(2000):
        endpoint = f"endpoint_{random.randint(0, 150) % 100}"
        data = {"id": random.randint(0, 7000)}
        await cache.get(endpoint, data)

    stats = await cache.get_stats()
    print(f"Cache stats: hits={stats.get('hits', 0)}, misses={stats.get('misses', 0)}")


async def profile_batching():
    """Profile request batching."""
    print("\n=== Profiling Request Batching ===")

    # Simple batching simulation with parallel mode
    from request_batching import BatchRequest

    # Create batch requests
    requests = []
    for i in range(500):
        req = BatchRequest(
            endpoint=f"endpoint_{i % 10}",
            data={"id": i},
        )
        requests.append(req)

    # Process in parallel batches of 100
    async def process_batch(batch):
        await asyncio.sleep(0.001)  # Simulate processing
        return [{"status": "success", "data": {}} for _ in batch]

    # Process all batches
    batch_size = 100
    results = []
    for i in range(0, len(requests), batch_size):
        batch = requests[i:i + batch_size]
        batch_results = await process_batch(batch)
        results.extend(batch_results)

    print(f"Batching complete: {len(results)} requests processed in {len(requests) // batch_size + 1} batches")


def run_profiling():
    """Run all profiling tests."""
    print("=" * 60)
    print("Performance Profiling - ImHex MCP Library")
    print("=" * 60)

    # Create profiler
    profiler = cProfile.Profile()

    # Profile sync operations
    profiler.enable()
    profile_compression()
    profiler.disable()

    # Profile async operations
    profiler.enable()
    asyncio.run(profile_async_client())
    asyncio.run(profile_caching())
    # Skip batching profile for now - focus on caching and compression
    profiler.disable()

    # Print statistics
    print("\n" + "=" * 60)
    print("Profiling Results")
    print("=" * 60)

    s = io.StringIO()
    ps = pstats.Stats(profiler, stream=s)

    # Sort by cumulative time
    ps.sort_stats(pstats.SortKey.CUMULATIVE)

    print("\n### Top 30 functions by cumulative time ###")
    ps.print_stats(30)
    print(s.getvalue())

    s = io.StringIO()
    ps = pstats.Stats(profiler, stream=s)

    # Sort by total time
    ps.sort_stats(pstats.SortKey.TIME)

    print("\n### Top 30 functions by total time ###")
    ps.print_stats(30)
    print(s.getvalue())

    # Save detailed stats to file
    output_file = Path(__file__).parent / "profile_results.txt"
    with open(output_file, 'w') as f:
        ps = pstats.Stats(profiler, stream=f)
        ps.sort_stats(pstats.SortKey.CUMULATIVE)
        ps.print_stats()

    print(f"\n✓ Detailed profiling results saved to: {output_file}")

    return profiler


if __name__ == "__main__":
    profiler = run_profiling()
    print("\n" + "=" * 60)
    print("Profiling Complete!")
    print("=" * 60)
