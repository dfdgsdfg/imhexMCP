#!/usr/bin/env python3
"""
ImHex MCP Advanced Optimization Demonstrations

Demonstrates streaming, lazy loading, and profiling capabilities.
"""

import sys
import time
from pathlib import Path

# Add lib directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))

from streaming import StreamingClient, StreamProcessor, stream_to_file
from lazy import LazyClient, LazyProvider, memoize
from profiling import PerformanceMonitor, HotPathAnalyzer, OptimizationSuggestions, monitored
from cached_client import create_client


def demo_streaming():
    """Demonstrate memory-efficient streaming."""
    print("=" * 70)
    print("Streaming Demonstration")
    print("=" * 70)

    client = StreamingClient()

    # Demo 1: Stream large file in chunks
    print("\n[1/3] Streaming file data in chunks...")
    try:
        chunk_count = 0
        total_bytes = 0

        for chunk in client.stream_read(0, offset=0, total_size=4096, chunk_size=512):
            chunk_count += 1
            total_bytes += chunk.size
            print(f"  Chunk {chunk_count}: offset=0x{chunk.offset:04x}, size={chunk.size} bytes")
            if chunk.is_last:
                print(f"  ✓ Completed: {chunk_count} chunks, {total_bytes} bytes total")

    except Exception as e:
        print(f"  Info: {e}")

    # Demo 2: Stream with processing
    print("\n[2/3] Streaming with transformation...")
    try:
        stream = client.stream_read(0, offset=0, total_size=1024)

        # Count null bytes using streaming
        null_count = StreamProcessor.reduce_stream(
            stream,
            lambda acc, data: acc + data.count(b'\x00'),
            0
        )

        print(f"  ✓ Found {null_count} null bytes (without loading entire file)")

    except Exception as e:
        print(f"  Info: {e}")

    # Demo 3: Stream with progress tracking
    print("\n[3/3] Streaming with progress tracking...")
    try:
        def progress_callback(current, total):
            percent = (current * 100) // total
            if percent % 25 == 0:  # Report every 25%
                print(f"  Progress: {percent}%")

        stream = client.stream_read(0, offset=0, total_size=2048, chunk_size=512)
        tracked = StreamProcessor.progress_tracker(stream, progress_callback)

        # Process stream
        for chunk in tracked:
            pass  # Just iterate

        print("  ✓ Streaming complete!")

    except Exception as e:
        print(f"  Info: {e}")

    print()


def demo_lazy_loading():
    """Demonstrate lazy loading patterns."""
    print("=" * 70)
    print("Lazy Loading Demonstration")
    print("=" * 70)

    client = LazyClient()

    # Demo 1: Lazy capability loading
    print("\n[1/4] Lazy capability loading...")
    print("  Creating lazy client (no connection yet)...")
    start = time.perf_counter()

    # No network call until we access capabilities
    print("  Client created (instant)")

    # First access triggers loading
    print("  Accessing capabilities (triggers load)...")
    try:
        endpoints = client.endpoints
        load_time = (time.perf_counter() - start) * 1000
        print(f"  ✓ Loaded {len(endpoints)} endpoints in {load_time:.2f}ms")

        # Second access uses cache
        start = time.perf_counter()
        endpoints2 = client.endpoints
        cache_time = (time.perf_counter() - start) * 1000
        print(f"  ✓ Cached access: {cache_time:.4f}ms (instant)")

    except Exception as e:
        print(f"  Info: {e}")

    # Demo 2: Lazy provider list
    print("\n[2/4] Lazy provider list...")
    try:
        providers = client.providers

        print(f"  Provider list created (not loaded yet)")

        # Access triggers loading
        start = time.perf_counter()
        count = providers.count
        load_time = (time.perf_counter() - start) * 1000
        print(f"  ✓ Loaded {count} providers in {load_time:.2f}ms")

    except Exception as e:
        print(f"  Info: {e}")

    # Demo 3: Lazy provider metadata
    print("\n[3/4] Lazy provider metadata...")
    try:
        if providers.count > 0:
            provider = providers[0]
            print(f"  Provider object created (metadata not loaded)")

            # Access triggers loading
            start = time.perf_counter()
            name = provider.name
            size = provider.size
            load_time = (time.perf_counter() - start) * 1000

            print(f"  ✓ Loaded metadata: {name}, {size} bytes ({load_time:.2f}ms)")

            # Subsequent accesses use cache
            start = time.perf_counter()
            name2 = provider.name
            cache_time = (time.perf_counter() - start) * 1000
            print(f"  ✓ Cached metadata access: {cache_time:.4f}ms")

    except Exception as e:
        print(f"  Info: {e}")

    # Demo 4: Memoization
    print("\n[4/4] Memoization demonstration...")

    @memoize
    def expensive_computation(n):
        """Simulate expensive computation."""
        time.sleep(0.01)  # Simulate work
        return n * n

    # First call - slow
    start = time.perf_counter()
    result1 = expensive_computation(10)
    first_time = (time.perf_counter() - start) * 1000
    print(f"  First call: {first_time:.2f}ms")

    # Second call - cached
    start = time.perf_counter()
    result2 = expensive_computation(10)
    cached_time = (time.perf_counter() - start) * 1000
    print(f"  Cached call: {cached_time:.4f}ms")

    speedup = first_time / cached_time if cached_time > 0 else 0
    print(f"  ✓ Speedup: {speedup:.0f}x faster")

    print()


def demo_profiling():
    """Demonstrate profiling and performance monitoring."""
    print("=" * 70)
    print("Profiling Demonstration")
    print("=" * 70)

    client = create_client(cache_enabled=False)  # Disable cache for realistic timing
    monitor = PerformanceMonitor()
    analyzer = HotPathAnalyzer()

    # Demo 1: Performance monitoring
    print("\n[1/4] Performance monitoring...")
    try:
        # Perform various operations with monitoring
        for i in range(5):
            with monitor.time("capabilities"):
                client.get_capabilities()

        for i in range(10):
            with monitor.time("file/list"):
                client.list_files()

        # Get statistics
        stats = monitor.get_stats()
        print(f"  Monitored {len(stats)} operation types:")

        for name, stat in stats.items():
            print(f"    {name}:")
            print(f"      Calls: {stat.call_count}")
            print(f"      Avg: {stat.avg_time_ms:.2f}ms")
            print(f"      P95: {stat.percentile_95_ms:.2f}ms")

    except Exception as e:
        print(f"  Info: {e}")

    # Demo 2: Hot path analysis
    print("\n[2/4] Hot path analysis...")
    try:
        # Trace execution paths
        with analyzer.trace("initialization"):
            time.sleep(0.005)

        for i in range(20):
            with analyzer.trace("request_processing"):
                time.sleep(0.001)

        for i in range(5):
            with analyzer.trace("cleanup"):
                time.sleep(0.002)

        # Get hot paths
        hot_paths = analyzer.get_hot_paths(min_calls=1)
        print(f"  Identified {len(hot_paths)} execution paths:")

        for path, stats in hot_paths[:3]:
            print(f"    {path}:")
            print(f"      Calls: {stats['call_count']}")
            print(f"      Total: {stats['total_time_ms']:.2f}ms")
            print(f"      Avg: {stats['avg_time_ms']:.2f}ms")

    except Exception as e:
        print(f"  Info: {e}")

    # Demo 3: Optimization suggestions
    print("\n[3/4] Optimization suggestions...")
    try:
        # Create mock statistics for demonstration
        from profiling import ProfileStats

        mock_stats = {
            "slow_operation": ProfileStats(
                function_name="slow_operation",
                call_count=200,
                total_time_ms=5000.0,
                avg_time_ms=25.0,
                min_time_ms=20.0,
                max_time_ms=150.0,
                percentile_95_ms=30.0,
                percentile_99_ms=100.0
            ),
            "cached_operation": ProfileStats(
                function_name="cached_operation",
                call_count=50,
                total_time_ms=100.0,
                avg_time_ms=2.0,
                min_time_ms=1.5,
                max_time_ms=3.0,
                percentile_95_ms=2.5,
                percentile_99_ms=2.8
            )
        }

        suggestions = OptimizationSuggestions.analyze_stats(mock_stats)
        print(f"  Generated {len(suggestions)} suggestions:")
        for i, suggestion in enumerate(suggestions, 1):
            print(f"    {i}. {suggestion}")

    except Exception as e:
        print(f"  Info: {e}")

    # Demo 4: Monitored decorator
    print("\n[4/4] Automatic monitoring with decorator...")

    @monitored()
    def monitored_operation():
        """Operation with automatic monitoring."""
        time.sleep(0.005)
        return "result"

    # Call function multiple times
    for i in range(5):
        monitored_operation()

    # Get global monitor stats
    from profiling import get_global_monitor
    global_monitor = get_global_monitor()
    stats = global_monitor.get_stats("monitored_operation")

    if "monitored_operation" in stats:
        stat = stats["monitored_operation"]
        print(f"  ✓ Automatically monitored {stat.call_count} calls")
        print(f"    Avg: {stat.avg_time_ms:.2f}ms")
        print(f"    Total: {stat.total_time_ms:.2f}ms")

    print()


def demo_combined_optimizations():
    """Demonstrate combining all optimizations."""
    print("=" * 70)
    print("Combined Optimizations Demonstration")
    print("=" * 70)

    print("\n[1/2] Lazy + Caching + Monitoring...")

    monitor = PerformanceMonitor()

    # Create lazy client (deferred connection)
    with monitor.time("client_creation"):
        client = LazyClient()

    print(f"  ✓ Client created")

    # First access with lazy loading and monitoring
    with monitor.time("first_access"):
        try:
            endpoints = client.endpoints
            print(f"  ✓ First access: loaded {len(endpoints)} endpoints")
        except Exception as e:
            print(f"  Info: {e}")

    # Second access (cached)
    with monitor.time("cached_access"):
        try:
            endpoints = client.endpoints
            print(f"  ✓ Cached access: instant")
        except Exception as e:
            print(f"  Info: {e}")

    # Print timing comparison
    stats = monitor.get_stats()
    if "first_access" in stats and "cached_access" in stats:
        first = stats["first_access"].avg_time_ms
        cached = stats["cached_access"].avg_time_ms
        speedup = first / cached if cached > 0 else 0
        print(f"  ✓ Speedup: {speedup:.0f}x faster with caching")

    print("\n[2/2] Streaming + Monitoring + Processing...")

    # Stream data with monitoring
    try:
        stream_client = StreamingClient()

        with monitor.time("stream_processing"):
            # Stream and process data
            stream = stream_client.stream_read(0, offset=0, total_size=2048)

            # Count specific byte patterns
            pattern_count = StreamProcessor.reduce_stream(
                stream,
                lambda acc, data: acc + data.count(b'\x00'),
                0
            )

        stream_stats = monitor.get_stats("stream_processing")
        if "stream_processing" in stream_stats:
            timing = stream_stats["stream_processing"].avg_time_ms
            print(f"  ✓ Streamed and processed 2048 bytes in {timing:.2f}ms")
            print(f"  ✓ Found {pattern_count} null bytes (memory-efficient)")

    except Exception as e:
        print(f"  Info: {e}")

    print()


def main():
    """Run all demonstrations."""
    try:
        print("\n" + "=" * 70)
        print("ImHex MCP Advanced Optimization Demonstrations")
        print("=" * 70)
        print()

        # Run demonstrations
        demo_streaming()
        demo_lazy_loading()
        demo_profiling()
        demo_combined_optimizations()

        print("=" * 70)
        print("All demonstrations complete!")
        print("=" * 70)

    except KeyboardInterrupt:
        print("\nDemonstration interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}")
        print("\nPlease ensure:")
        print("  1. ImHex is running")
        print("  2. Network Interface is enabled in Settings")
        print("  3. Port 31337 is accessible")
        print("  4. At least one file is open in ImHex")
        sys.exit(1)


if __name__ == "__main__":
    main()
