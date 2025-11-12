#!/usr/bin/env python3
"""
Enhanced Client Quick Start Example

This example demonstrates how to get started with the EnhancedImHexClient
for improved performance in your applications.
"""

import sys
from pathlib import Path

# Add lib to path
sys.path.insert(0, str(Path(__file__).parent.parent / "mcp-server"))
sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))

from enhanced_client import create_enhanced_client, create_optimized_client, create_minimal_client


def example_1_basic_usage():
    """Example 1: Basic usage with default optimizations."""
    print("\n" + "=" * 70)
    print("Example 1: Basic Enhanced Client Usage")
    print("=" * 70)

    # Create client with default optimizations
    client = create_enhanced_client(
        host="localhost",
        port=31337,
        config={
            'enable_cache': True,
            'cache_max_size': 1000,
            'enable_profiling': False,
            'enable_lazy': True
        }
    )

    print("\nCreated enhanced client with:")
    print("  - Caching: Enabled (max 1000 entries)")
    print("  - Lazy loading: Enabled")
    print("  - Profiling: Disabled")

    try:
        # Make some requests
        print("\n[1/3] Getting capabilities...")
        caps = client.get_capabilities()
        print(f"  Status: {caps.get('status')}")
        print(f"  Endpoints: {len(caps.get('data', {}).get('endpoints', []))}")

        print("\n[2/3] Getting capabilities again (cached)...")
        caps2 = client.get_capabilities()
        print(f"  Status: {caps2.get('status')}")
        print(f"  Note: This request was served from cache!")

        print("\n[3/3] Listing files...")
        files = client.list_files()
        print(f"  Status: {files.get('status')}")
        print(f"  Files open: {files.get('data', {}).get('count', 0)}")

        # Show cache statistics
        print("\nCache Statistics:")
        cache_stats = client.get_cache_stats()
        print(f"  Hit rate: {cache_stats.get('hit_rate', 0):.1f}%")
        print(f"  Hits: {cache_stats.get('hits', 0)}")
        print(f"  Misses: {cache_stats.get('misses', 0)}")

    except Exception as e:
        print(f"\nError: {e}")
        print("Make sure ImHex is running with Network Interface enabled!")


def example_2_full_optimization():
    """Example 2: Using all optimizations for maximum performance."""
    print("\n" + "=" * 70)
    print("Example 2: Fully Optimized Client")
    print("=" * 70)

    # Create client with all optimizations enabled
    client = create_optimized_client(host="localhost", port=31337)

    print("\nCreated fully optimized client with:")
    print("  - Large cache (5000 entries)")
    print("  - Profiling enabled")
    print("  - Lazy loading enabled")
    print("  - All optimization modules active")

    try:
        # Make requests and profile them
        print("\n[1/4] Getting capabilities...")
        caps = client.get_capabilities()
        print(f"  Status: {caps.get('status')}")

        print("\n[2/4] Listing files multiple times (testing cache)...")
        for i in range(5):
            result = client.list_files()
            print(f"  Request {i+1}: {result.get('status')}")

        print("\n[3/4] Using lazy loading for endpoints...")
        endpoints = client.lazy_endpoints
        print(f"  Available endpoints: {len(endpoints)}")
        print(f"  (Loaded lazily on first access)")

        print("\n[4/4] Reading data from first provider...")
        files_data = client.list_files()
        if files_data.get('data', {}).get('count', 0) > 0:
            providers = files_data['data']['providers']
            provider_id = providers[0]['id']

            # Read some data
            data = client.read_data(provider_id, offset=0, size=64)
            print(f"  Read {data.get('data', {}).get('size', 0)} bytes")

        # Show performance report
        print("\nPerformance Report:")
        client.print_performance_report()

    except Exception as e:
        print(f"\nError: {e}")
        print("Make sure ImHex is running with a file open!")


def example_3_streaming():
    """Example 3: Memory-efficient streaming for large files."""
    print("\n" + "=" * 70)
    print("Example 3: Streaming Large Data")
    print("=" * 70)

    client = create_enhanced_client()

    try:
        # Get first provider
        files = client.list_files()
        if files.get('data', {}).get('count', 0) == 0:
            print("No files open - please open a file in ImHex first!")
            return

        provider_id = files['data']['providers'][0]['id']
        file_size = files['data']['providers'][0]['size']
        file_name = files['data']['providers'][0]['name']

        print(f"\nStreaming data from: {file_name}")
        print(f"File size: {file_size} bytes")

        # Stream data in chunks
        total_bytes = 0
        chunk_count = 0

        print("\nStreaming in 4KB chunks:")
        for chunk in client.stream_read(provider_id, offset=0, total_size=min(65536, file_size)):
            total_bytes += chunk.size
            chunk_count += 1
            progress = (total_bytes * 100) // min(65536, file_size)
            print(f"  Chunk {chunk_count}: {chunk.size} bytes (offset {chunk.offset}) - {progress}% complete")

            if chunk.is_last:
                print("  Stream complete!")
                break

        print(f"\nTotal streamed: {total_bytes} bytes in {chunk_count} chunks")
        print("Memory-efficient: Data processed in chunks, not loaded all at once!")

    except Exception as e:
        print(f"\nError: {e}")


def example_4_batch_operations():
    """Example 4: Batching multiple requests for better throughput."""
    print("\n" + "=" * 70)
    print("Example 4: Batch Operations")
    print("=" * 70)

    client = create_enhanced_client()

    try:
        # Build a batch of requests
        from batching import BatchStrategy

        requests = [
            ("capabilities", None),
            ("file/list", None),
        ]

        # Get file info for each open file
        files = client.list_files()
        if files.get('data', {}).get('count', 0) > 0:
            for provider in files['data']['providers']:
                requests.append(("file/info", {"provider_id": provider['id']}))

        print(f"\nExecuting batch of {len(requests)} requests...")
        print("Requests:")
        for endpoint, data in requests:
            print(f"  - {endpoint}" + (f" ({data})" if data else ""))

        # Execute batch with concurrent strategy
        print("\nUsing CONCURRENT strategy (parallel execution)...")
        results = client.execute_batch(requests, strategy=BatchStrategy.CONCURRENT)

        print(f"\nCompleted {len(results)} requests!")
        for i, result in enumerate(results):
            if result.success:
                print(f"  [{i+1}] Success: {result.request.endpoint}")
            else:
                print(f"  [{i+1}] Failed: {result.request.endpoint} - {result.error}")

        print("\nBatch execution is much faster than sequential requests!")

    except Exception as e:
        print(f"\nError: {e}")


def example_5_configuration_profiles():
    """Example 5: Different configuration profiles for different use cases."""
    print("\n" + "=" * 70)
    print("Example 5: Configuration Profiles")
    print("=" * 70)

    # High-throughput profile (for batch processing)
    print("\n[Profile 1] High-Throughput:")
    print("  Use case: Processing many files, batch operations")
    print("  Configuration:")
    print("    - Large cache (10000 entries)")
    print("    - Profiling disabled (max speed)")
    print("    - Lazy loading enabled")

    high_throughput = create_enhanced_client(config={
        'enable_cache': True,
        'cache_max_size': 10000,
        'enable_profiling': False,
        'enable_lazy': True
    })

    # Low-latency profile (for interactive use)
    print("\n[Profile 2] Low-Latency:")
    print("  Use case: Interactive analysis, quick responses")
    print("  Configuration:")
    print("    - Small cache (100 entries, fast lookup)")
    print("    - Profiling disabled")
    print("    - Lazy loading enabled")

    low_latency = create_enhanced_client(config={
        'enable_cache': True,
        'cache_max_size': 100,
        'enable_profiling': False,
        'enable_lazy': True
    })

    # Debug profile (for development)
    print("\n[Profile 3] Debug/Development:")
    print("  Use case: Development, testing, debugging")
    print("  Configuration:")
    print("    - No cache (always fresh data)")
    print("    - Profiling enabled (find bottlenecks)")
    print("    - Lazy loading disabled (immediate feedback)")

    debug = create_enhanced_client(config={
        'enable_cache': False,
        'enable_profiling': True,
        'enable_lazy': False
    })

    # Minimal profile (compatibility mode)
    print("\n[Profile 4] Minimal/Compatibility:")
    print("  Use case: Maximum compatibility, minimal overhead")
    print("  Configuration:")
    print("    - All optimizations disabled")
    print("    - Behaves like basic client")

    minimal = create_minimal_client()

    print("\nChoose the right profile for your use case!")


def main():
    """Run all examples."""
    print("\n" + "=" * 70)
    print("Enhanced ImHex Client - Quick Start Examples")
    print("=" * 70)
    print("\nThis script demonstrates various ways to use the EnhancedImHexClient")
    print("for improved performance in your applications.")

    # Run examples
    try:
        example_1_basic_usage()
        example_2_full_optimization()
        example_3_streaming()
        example_4_batch_operations()
        example_5_configuration_profiles()

        print("\n" + "=" * 70)
        print("Examples Complete!")
        print("=" * 70)
        print("\nNext Steps:")
        print("  1. Read lib/README.md for detailed module documentation")
        print("  2. Check docs/INTEGRATION_GUIDE.md for production integration")
        print("  3. Explore examples/optimization_demo.py for advanced usage")
        print("  4. Run tests/test_optimizations.py to validate your setup")

    except KeyboardInterrupt:
        print("\n\nExamples interrupted by user.")


if __name__ == "__main__":
    main()
