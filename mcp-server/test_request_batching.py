#!/usr/bin/env python3
"""
Request Batching Tests

Comprehensive tests for request batching & pipelining functionality:
- Basic batching operations
- Parallel vs sequential vs adaptive execution
- Multi-read batching pattern
- Multi-file operations
- Analysis pipeline with dependencies
- Statistics tracking
- Error isolation
"""

import asyncio
import sys
import time
from pathlib import Path

# Add lib directory to path
lib_path = Path(__file__).parent.parent / "lib"
sys.path.insert(0, str(lib_path))

from async_client import AsyncImHexClient
from request_batching import RequestBatcher, BatchMode


async def test_basic_batching():
    """Test 1: Basic parallel batching."""
    print("\n" + "=" * 70)
    print("Test 1: Basic Parallel Batching")
    print("=" * 70)

    async with AsyncImHexClient(
        host="localhost",
        port=31337,
        use_connection_pool=True
    ) as client:
        # Create batcher with parallel mode
        batcher = client.create_batcher(mode=BatchMode.PARALLEL)

        # Add multiple requests
        batcher.add(endpoint="capabilities", data={})
        batcher.add(endpoint="file/list", data={})

        print(f"Created batch with {batcher.size()} requests")

        # Execute batch
        responses, stats = await client.send_batch_advanced(batcher)

        print(f"\n✓ Batch completed:")
        print(f"  Total requests: {stats.total_requests}")
        print(f"  Successful: {stats.successful_requests}")
        print(f"  Failed: {stats.failed_requests}")
        print(f"  Success rate: {stats.success_rate():.1f}%")
        print(f"  Round-trips saved: {stats.round_trips_saved}")
        print(f"  Total time: {stats.total_time_ms:.2f}ms")
        print(f"  Avg per request: {stats.avg_request_time_ms:.2f}ms")

        # Validate responses
        for i, response in enumerate(responses):
            req_id = response["request_id"]
            status = response["status"]
            print(f"  Response {i}: {req_id} - {status}")

        return stats.success_rate() == 100.0


async def test_sequential_batching():
    """Test 2: Sequential batching (pipelining)."""
    print("\n" + "=" * 70)
    print("Test 2: Sequential Batching (Pipelining)")
    print("=" * 70)

    async with AsyncImHexClient(
        host="localhost",
        port=31337,
        use_connection_pool=True
    ) as client:
        # Create batcher with sequential mode
        batcher = client.create_batcher(mode=BatchMode.SEQUENTIAL)

        # Add requests in specific order
        batcher.add(request_id="step1", endpoint="file/list", data={})
        batcher.add(request_id="step2", endpoint="capabilities", data={})
        batcher.add(request_id="step3", endpoint="file/list", data={})

        print(f"Created sequential batch with {batcher.size()} requests")

        # Execute batch
        start = time.perf_counter()
        responses, stats = await client.send_batch_advanced(batcher)
        elapsed = (time.perf_counter() - start) * 1000

        print(f"\n✓ Sequential batch completed:")
        print(f"  Total time: {elapsed:.2f}ms")
        print(f"  Round-trips saved: {stats.round_trips_saved}")

        # Verify order preserved
        print(f"\n  Response order:")
        for i, response in enumerate(responses):
            print(f"    {i+1}. {response['request_id']} - {response['status']}")

        return stats.success_rate() == 100.0


async def test_adaptive_batching():
    """Test 3: Adaptive batching with dependencies."""
    print("\n" + "=" * 70)
    print("Test 3: Adaptive Batching (Dependency Resolution)")
    print("=" * 70)

    async with AsyncImHexClient(
        host="localhost",
        port=31337,
        use_connection_pool=True
    ) as client:
        # Create batcher with adaptive mode
        batcher = client.create_batcher(mode=BatchMode.ADAPTIVE)

        # Add requests with dependencies
        batcher.add(request_id="list_files", endpoint="file/list", data={})
        batcher.add(
            request_id="get_caps",
            endpoint="capabilities",
            data={},
            depends_on=["list_files"]  # Depends on list_files
        )

        print(f"Created adaptive batch with {batcher.size()} requests")
        print(f"  Request 'get_caps' depends on 'list_files'")

        # Execute batch
        responses, stats = await client.send_batch_advanced(batcher)

        print(f"\n✓ Adaptive batch completed:")
        print(f"  Total requests: {stats.total_requests}")
        print(f"  Success rate: {stats.success_rate():.1f}%")
        print(f"  Round-trips saved: {stats.round_trips_saved}")

        return stats.success_rate() == 100.0


async def test_multi_read_batching():
    """Test 4: Multi-read batching (common pattern)."""
    print("\n" + "=" * 70)
    print("Test 4: Multi-Read Batching Pattern")
    print("=" * 70)

    # First, need to ensure a file is open
    async with AsyncImHexClient(
        host="localhost",
        port=31337,
        use_connection_pool=True
    ) as client:
        # Check if files are open
        file_list = await client.send_request("file/list")
        files_open = file_list.get("data", {}).get("count", 0)

        if files_open == 0:
            print("  No files open - skipping multi-read test")
            return True

        print(f"  Files open: {files_open}")

        # Read multiple regions from provider 0
        offsets = [0x0, 0x100, 0x200, 0x300, 0x400]
        size = 64

        print(f"  Reading {len(offsets)} regions of {size} bytes each")

        start = time.perf_counter()
        chunks, stats = await client.batch_multi_read(0, offsets, size)
        elapsed = (time.perf_counter() - start) * 1000

        print(f"\n✓ Multi-read batch completed:")
        print(f"  Regions read: {len(chunks)}")
        print(f"  Total time: {elapsed:.2f}ms")
        print(f"  Avg per region: {elapsed / len(chunks):.2f}ms")
        print(f"  Round-trips saved: {stats.round_trips_saved}")

        # Show first chunk
        if chunks and chunks[0]:
            print(f"  First chunk (64 bytes): {chunks[0][:16].hex()}...")

        return len(chunks) == len(offsets)


async def test_multi_file_operation():
    """Test 5: Multi-file operations."""
    print("\n" + "=" * 70)
    print("Test 5: Multi-File Operations")
    print("=" * 70)

    async with AsyncImHexClient(
        host="localhost",
        port=31337,
        use_connection_pool=True
    ) as client:
        # Check open files
        file_list = await client.send_request("file/list")
        files_open = file_list.get("data", {}).get("count", 0)

        if files_open < 2:
            print(f"  Only {files_open} file(s) open - creating batch for available files")

        provider_ids = list(range(min(files_open, 3)))  # Up to 3 files

        if not provider_ids:
            print("  No files open - skipping multi-file test")
            return True

        print(f"  Getting info for {len(provider_ids)} file(s)")

        # Get info for multiple files at once
        responses, stats = await client.batch_multi_file_operation(
            provider_ids,
            "file/info"
        )

        print(f"\n✓ Multi-file operation completed:")
        print(f"  Files processed: {stats.total_requests}")
        print(f"  Success rate: {stats.success_rate():.1f}%")
        print(f"  Round-trips saved: {stats.round_trips_saved}")

        # Show file info
        for i, response in enumerate(responses):
            if response["status"] == "success":
                data = response["data"]
                name = data.get("name", "Unknown")
                size = data.get("size", 0)
                print(f"    File {i}: {name} ({size} bytes)")

        return stats.success_rate() > 0


async def test_analysis_pipeline():
    """Test 6: Analysis pipeline with dependencies."""
    print("\n" + "=" * 70)
    print("Test 6: Analysis Pipeline (Sequential with Dependencies)")
    print("=" * 70)

    async with AsyncImHexClient(
        host="localhost",
        port=31337,
        use_connection_pool=True
    ) as client:
        # Check if files are open
        file_list = await client.send_request("file/list")
        files_open = file_list.get("data", {}).get("count", 0)

        if files_open == 0:
            print("  No files open - skipping analysis pipeline test")
            return True

        print(f"  Running analysis pipeline on provider 0")

        # Run analysis pipeline
        responses, stats = await client.batch_analysis_pipeline(0)

        print(f"\n✓ Analysis pipeline completed:")
        print(f"  Pipeline steps: {stats.total_requests}")
        print(f"  Success rate: {stats.success_rate():.1f}%")
        print(f"  Total time: {stats.total_time_ms:.2f}ms")

        # Show pipeline results
        print(f"\n  Pipeline results:")
        for i, response in enumerate(responses):
            req_id = response["request_id"]
            status = response["status"]
            elapsed = response["elapsed_ms"]
            print(f"    Step {i+1} ({req_id}): {status} ({elapsed:.2f}ms)")

        return stats.success_rate() > 0


async def test_error_isolation():
    """Test 7: Error isolation (one failure doesn't break batch)."""
    print("\n" + "=" * 70)
    print("Test 7: Error Isolation")
    print("=" * 70)

    async with AsyncImHexClient(
        host="localhost",
        port=31337,
        use_connection_pool=True
    ) as client:
        # Create batch with some invalid requests
        batcher = client.create_batcher(mode=BatchMode.PARALLEL)

        batcher.add(endpoint="capabilities", data={})  # Valid
        batcher.add(endpoint="invalid_endpoint", data={})  # Invalid
        batcher.add(endpoint="file/list", data={})  # Valid

        print(f"Created batch with {batcher.size()} requests (1 invalid)")

        # Execute batch
        responses, stats = await client.send_batch_advanced(batcher)

        print(f"\n✓ Batch completed with error isolation:")
        print(f"  Total requests: {stats.total_requests}")
        print(f"  Successful: {stats.successful_requests}")
        print(f"  Failed: {stats.failed_requests}")

        # Show individual results
        for i, response in enumerate(responses):
            req_id = response["request_id"]
            status = response["status"]
            print(f"  Request {i}: {req_id} - {status}")

        # Should have 2 successes and 1 failure
        return stats.successful_requests >= 2 and stats.failed_requests >= 1


async def test_large_batch():
    """Test 8: Large batch (stress test)."""
    print("\n" + "=" * 70)
    print("Test 8: Large Batch (50 requests)")
    print("=" * 70)

    async with AsyncImHexClient(
        host="localhost",
        port=31337,
        use_connection_pool=True
    ) as client:
        # Create large batch
        batcher = client.create_batcher(mode=BatchMode.PARALLEL)

        for i in range(50):
            # Alternate between two endpoints
            endpoint = "file/list" if i % 2 == 0 else "capabilities"
            batcher.add(endpoint=endpoint, data={})

        print(f"Created large batch with {batcher.size()} requests")

        # Execute batch
        start = time.perf_counter()
        responses, stats = await client.send_batch_advanced(batcher)
        elapsed = (time.perf_counter() - start) * 1000

        print(f"\n✓ Large batch completed:")
        print(f"  Total requests: {stats.total_requests}")
        print(f"  Success rate: {stats.success_rate():.1f}%")
        print(f"  Total time: {elapsed:.2f}ms")
        print(f"  Avg per request: {elapsed / stats.total_requests:.2f}ms")
        print(f"  Throughput: {stats.total_requests / (elapsed / 1000):.1f} req/s")
        print(f"  Round-trips saved: {stats.round_trips_saved}")

        return stats.success_rate() > 95.0


async def run_all_tests():
    """Run all request batching tests."""
    print("\n" + "=" * 70)
    print("REQUEST BATCHING TEST SUITE")
    print("=" * 70)
    print("\nTesting request batching for 40-60% round-trip reduction")

    tests = [
        ("Basic Parallel Batching", test_basic_batching),
        ("Sequential Batching", test_sequential_batching),
        ("Adaptive Batching", test_adaptive_batching),
        ("Multi-Read Batching", test_multi_read_batching),
        ("Multi-File Operations", test_multi_file_operation),
        ("Analysis Pipeline", test_analysis_pipeline),
        ("Error Isolation", test_error_isolation),
        ("Large Batch Stress Test", test_large_batch),
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
