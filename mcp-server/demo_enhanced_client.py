#!/usr/bin/env python3
"""
Demonstration of Enhanced ImHex Client

Shows how to use the enhanced client with all performance optimizations
in the MCP server context.
"""

import sys
from pathlib import Path
import time

# Add mcp-server to path
sys.path.insert(0, str(Path(__file__).parent))

from enhanced_client import (
    create_enhanced_client,
    create_optimized_client,
    create_minimal_client,
    EnhancedImHexClient
)


def demo_basic_usage():
    """Demonstrate basic usage with all optimizations."""
    print("\n" + "=" * 70)
    print("Demo 1: Basic Usage with Optimizations")
    print("=" * 70)

    # Create optimized client
    client = create_optimized_client()

    try:
        # Test capabilities (lazy-loaded and cached)
        print("\n[1/4] Testing capabilities (lazy-loaded + cached)...")
        start = time.perf_counter()
        endpoints = client.lazy_endpoints
        first_time = (time.perf_counter() - start) * 1000
        print(f"  First access: {first_time:.2f}ms")
        print(f"  Available endpoints: {len(endpoints)}")

        # Second access - instant (cached)
        start = time.perf_counter()
        endpoints2 = client.lazy_endpoints
        cached_time = (time.perf_counter() - start) * 1000
        print(f"  Cached access: {cached_time:.4f}ms")
        print(f"  Speedup: {first_time/cached_time if cached_time > 0 else 0:.0f}x faster")

        # Test file listing
        print("\n[2/4] Testing file listing...")
        result = client.list_files()
        if result.get("status") == "success":
            count = result["data"]["count"]
            print(f"  Files open: {count}")
        else:
            print(f"  Info: No files open")

        # Test caching performance
        print("\n[3/4] Testing cache performance...")
        # First request - cache miss
        start = time.perf_counter()
        client.get_capabilities()
        uncached_time = (time.perf_counter() - start) * 1000

        # Second request - cache hit
        start = time.perf_counter()
        client.get_capabilities()
        cached_time = (time.perf_counter() - start) * 1000

        print(f"  Uncached request: {uncached_time:.2f}ms")
        print(f"  Cached request: {cached_time:.4f}ms")
        print(f"  Speedup: {uncached_time/cached_time if cached_time > 0 else 0:.0f}x faster")

        # Show cache stats
        print("\n[4/4] Cache statistics...")
        stats = client.get_cache_stats()
        print(f"  Hit rate: {stats['hit_rate']:.1f}%")
        print(f"  Hits: {stats['hits']}, Misses: {stats['misses']}")
        print(f"  Cache size: {stats['size']}/{stats['max_size']}")

    except Exception as e:
        print(f"  Error: {e}")
        print("  Make sure ImHex is running with Network Interface enabled")


def demo_batch_operations():
    """Demonstrate batch operations."""
    print("\n" + "=" * 70)
    print("Demo 2: Batch Operations")
    print("=" * 70)

    client = create_enhanced_client(config={
        'enable_cache': True,
        'enable_profiling': True
    })

    try:
        from batching import BatchStrategy

        # Prepare batch requests
        requests = [
            ("capabilities", None),
            ("file/list", None),
            ("capabilities", None),  # Will be cached
        ]

        # Test different strategies
        print("\n[1/3] Sequential batch...")
        start = time.perf_counter()
        responses = client.execute_batch(requests, strategy=BatchStrategy.SEQUENTIAL)
        sequential_time = (time.perf_counter() - start) * 1000
        print(f"  Time: {sequential_time:.2f}ms")
        print(f"  Successful: {sum(1 for r in responses if r.success)}/{len(responses)}")

        print("\n[2/3] Concurrent batch...")
        start = time.perf_counter()
        responses = client.execute_batch(requests, strategy=BatchStrategy.CONCURRENT)
        concurrent_time = (time.perf_counter() - start) * 1000
        print(f"  Time: {concurrent_time:.2f}ms")
        print(f"  Successful: {sum(1 for r in responses if r.success)}/{len(responses)}")
        print(f"  Speedup vs sequential: {sequential_time/concurrent_time if concurrent_time > 0 else 0:.1f}x")

        print("\n[3/3] Pipelined batch...")
        start = time.perf_counter()
        responses = client.execute_batch(requests, strategy=BatchStrategy.PIPELINED)
        pipelined_time = (time.perf_counter() - start) * 1000
        print(f"  Time: {pipelined_time:.2f}ms")
        print(f"  Successful: {sum(1 for r in responses if r.success)}/{len(responses)}")

    except Exception as e:
        print(f"  Error: {e}")


def demo_streaming():
    """Demonstrate streaming for large data."""
    print("\n" + "=" * 70)
    print("Demo 3: Memory-Efficient Streaming")
    print("=" * 70)

    client = create_enhanced_client()

    try:
        print("\n[1/3] Streaming file data in chunks...")
        chunk_count = 0
        total_bytes = 0

        for chunk in client.stream_read(0, offset=0, total_size=4096, chunk_size=512):
            chunk_count += 1
            total_bytes += chunk.size
            print(f"  Chunk {chunk_count}: offset=0x{chunk.offset:04x}, size={chunk.size} bytes")

        print(f"  Total: {chunk_count} chunks, {total_bytes} bytes")

        print("\n[2/3] Comparing streaming vs regular read...")
        # Regular read
        start = time.perf_counter()
        result = client.read_data(0, 0, 1024, use_streaming=False)
        regular_time = (time.perf_counter() - start) * 1000

        # Streaming read
        start = time.perf_counter()
        result = client.read_data(0, 0, 1024, use_streaming=True)
        streaming_time = (time.perf_counter() - start) * 1000

        print(f"  Regular read: {regular_time:.2f}ms")
        print(f"  Streaming read: {streaming_time:.2f}ms")

        print("\n[3/3] Stream to file...")
        import tempfile
        import os

        with tempfile.NamedTemporaryFile(delete=False) as f:
            temp_path = f.name

        try:
            bytes_written = client.stream_to_file(0, temp_path, offset=0, total_size=2048)
            file_size = os.path.getsize(temp_path)
            print(f"  Wrote {bytes_written} bytes to {temp_path}")
            print(f"  File size: {file_size} bytes")
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    except Exception as e:
        print(f"  Info: {e}")


def demo_performance_report():
    """Demonstrate performance reporting."""
    print("\n" + "=" * 70)
    print("Demo 4: Performance Profiling")
    print("=" * 70)

    # Use context manager to auto-print report
    with create_optimized_client() as client:
        print("\n[1/2] Performing various operations with profiling...")

        # Perform operations
        for i in range(5):
            client.get_capabilities()

        for i in range(10):
            client.list_files()

        # Get lazy endpoints
        endpoints = client.lazy_endpoints

        print(f"  Performed 15 cached operations + 1 lazy load")

        print("\n[2/2] Performance statistics...")
        perf_stats = client.get_performance_stats()

        if perf_stats.get("enabled"):
            for op_name, stats in perf_stats["operations"].items():
                print(f"  {op_name}:")
                print(f"    Calls: {stats['call_count']}")
                print(f"    Avg: {stats['avg_time_ms']:.2f}ms")
                print(f"    P95: {stats['p95_time_ms']:.2f}ms")

        # Report will be printed automatically on exit


def demo_custom_configuration():
    """Demonstrate custom client configuration."""
    print("\n" + "=" * 70)
    print("Demo 5: Custom Configuration")
    print("=" * 70)

    # High-throughput configuration
    print("\n[1/3] High-throughput configuration...")
    client1 = create_enhanced_client(config={
        'enable_cache': True,
        'cache_max_size': 5000,  # Large cache
        'enable_profiling': False,
        'enable_lazy': True
    })
    print("  Large cache (5000 entries), profiling disabled for speed")

    # Low-latency configuration
    print("\n[2/3] Low-latency configuration...")
    client2 = create_enhanced_client(config={
        'enable_cache': True,
        'cache_max_size': 100,  # Small, fast cache
        'enable_profiling': False,
        'enable_lazy': True,
        'timeout': 5  # Short timeout
    })
    print("  Small cache (100 entries), short timeout for quick response")

    # Debugging configuration
    print("\n[3/3] Debugging configuration...")
    client3 = create_enhanced_client(config={
        'enable_cache': False,  # No cache for fresh data
        'enable_profiling': True,  # Detailed profiling
        'enable_lazy': False  # Immediate loading
    })
    print("  No cache, full profiling, immediate loading for debugging")


def main():
    """Run all demonstrations."""
    print("\n" + "=" * 70)
    print("Enhanced ImHex Client Demonstration")
    print("=" * 70)
    print("\nThis demo shows the performance optimizations integrated into")
    print("the enhanced client for the MCP server.")
    print("\nPlease ensure:")
    print("  1. ImHex is running")
    print("  2. Network Interface is enabled in Settings")
    print("  3. Port 31337 is accessible")
    print("=" * 70)

    try:
        # Run demonstrations
        demo_basic_usage()
        demo_batch_operations()
        demo_streaming()
        demo_performance_report()
        demo_custom_configuration()

        print("\n" + "=" * 70)
        print("All demonstrations complete!")
        print("=" * 70)

    except KeyboardInterrupt:
        print("\n\nDemonstration interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nError: {e}")
        print("\nPlease ensure ImHex is running with Network Interface enabled")
        sys.exit(1)


if __name__ == "__main__":
    main()
