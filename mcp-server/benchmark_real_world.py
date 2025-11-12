#!/usr/bin/env python3
"""
Real-World Binary Analysis Workload Benchmark

Simulates realistic binary analysis workflows to measure performance
improvements from optimizations:
- Compression (60-80% bandwidth reduction expected)
- Async/concurrent operations (25-60% improvement expected)
- Caching and lazy loading

Test scenarios:
1. Multiple file operations (open, info, close)
2. Sequential data reads (small and large)
3. Random access pattern reads
4. Batch operations (concurrent reads)
5. Pattern searching simulation
6. Hash calculation simulation (multiple reads)
"""

import sys
import time
import statistics
from pathlib import Path
from typing import Dict, Any, List, Tuple
import asyncio

# Add lib directory to path
lib_path = Path(__file__).parent.parent / "lib"
sys.path.insert(0, str(lib_path))

from imhex_client import ImHexClient
from enhanced_client import EnhancedImHexClient, create_enhanced_client
from async_client import AsyncImHexClient, AsyncEnhancedImHexClient


class BenchmarkResult:
    """Container for benchmark results."""

    def __init__(self, name: str):
        self.name = name
        self.times: List[float] = []
        self.bytes_transferred: int = 0
        self.errors: int = 0

    def add_measurement(self, time_ms: float, bytes_count: int = 0):
        """Add a timing measurement."""
        self.times.append(time_ms)
        self.bytes_transferred += bytes_count

    def add_error(self):
        """Record an error."""
        self.errors += 1

    def get_stats(self) -> Dict[str, Any]:
        """Get statistical summary."""
        if not self.times:
            return {
                "name": self.name,
                "error": "No measurements"
            }

        sorted_times = sorted(self.times)

        return {
            "name": self.name,
            "count": len(self.times),
            "total_time_ms": sum(self.times),
            "avg_time_ms": statistics.mean(self.times),
            "median_time_ms": statistics.median(self.times),
            "min_time_ms": min(self.times),
            "max_time_ms": max(self.times),
            "p95_time_ms": sorted_times[int(len(sorted_times) * 0.95)] if len(sorted_times) > 1 else sorted_times[0],
            "p99_time_ms": sorted_times[int(len(sorted_times) * 0.99)] if len(sorted_times) > 1 else sorted_times[0],
            "bytes_transferred": self.bytes_transferred,
            "throughput_mbps": (self.bytes_transferred / (sum(self.times) / 1000) / 1024 / 1024) if sum(self.times) > 0 else 0,
            "errors": self.errors
        }


class RealWorldBenchmark:
    """Real-world binary analysis workload benchmark."""

    def __init__(self, host: str = "localhost", port: int = 31337):
        self.host = host
        self.port = port
        self.results: Dict[str, BenchmarkResult] = {}

    def _get_provider_id(self, client) -> int:
        """Get first available provider ID."""
        response = client.send_request("file/list")
        if response.get("status") != "success":
            raise Exception(f"Failed to get file list: {response}")

        providers = response.get("data", {}).get("providers", [])
        if not providers:
            raise Exception("No files open in ImHex")

        return providers[0]["id"]

    def benchmark_file_operations(self, client, iterations: int = 50) -> BenchmarkResult:
        """
        Benchmark: File operations (list, info, capabilities).

        Simulates browsing files and checking metadata.
        """
        result = BenchmarkResult("File Operations")

        try:
            provider_id = self._get_provider_id(client)

            for _ in range(iterations):
                # List files
                start = time.perf_counter()
                response = client.send_request("file/list")
                elapsed = (time.perf_counter() - start) * 1000

                if response.get("status") == "success":
                    result.add_measurement(elapsed)
                else:
                    result.add_error()

                # Get file info
                start = time.perf_counter()
                response = client.send_request("file/info", {"provider_id": provider_id})
                elapsed = (time.perf_counter() - start) * 1000

                if response.get("status") == "success":
                    result.add_measurement(elapsed)
                else:
                    result.add_error()

                # Get capabilities
                start = time.perf_counter()
                response = client.send_request("capabilities")
                elapsed = (time.perf_counter() - start) * 1000

                if response.get("status") == "success":
                    result.add_measurement(elapsed)
                else:
                    result.add_error()

        except Exception as e:
            print(f"Error in file operations benchmark: {e}")
            result.add_error()

        return result

    def benchmark_sequential_reads_small(self, client, iterations: int = 100) -> BenchmarkResult:
        """
        Benchmark: Sequential small reads (256 bytes).

        Simulates reading file headers, structures, etc.
        """
        result = BenchmarkResult("Sequential Small Reads (256B)")

        try:
            provider_id = self._get_provider_id(client)

            offset = 0
            read_size = 256

            for _ in range(iterations):
                start = time.perf_counter()
                response = client.send_request("data/read", {
                    "provider_id": provider_id,
                    "offset": offset,
                    "size": read_size
                })
                elapsed = (time.perf_counter() - start) * 1000

                if response.get("status") == "success":
                    data_hex = response.get("data", {}).get("data", "")
                    bytes_read = len(data_hex) // 2  # Hex string is 2 chars per byte
                    result.add_measurement(elapsed, bytes_read)
                    offset += read_size
                else:
                    result.add_error()

        except Exception as e:
            print(f"Error in sequential small reads: {e}")
            result.add_error()

        return result

    def benchmark_sequential_reads_large(self, client, iterations: int = 20) -> BenchmarkResult:
        """
        Benchmark: Sequential large reads (64KB).

        Simulates reading file sections, segments, etc.
        """
        result = BenchmarkResult("Sequential Large Reads (64KB)")

        try:
            provider_id = self._get_provider_id(client)

            offset = 0
            read_size = 65536  # 64KB

            for _ in range(iterations):
                start = time.perf_counter()
                response = client.send_request("data/read", {
                    "provider_id": provider_id,
                    "offset": offset,
                    "size": read_size
                })
                elapsed = (time.perf_counter() - start) * 1000

                if response.get("status") == "success":
                    data_hex = response.get("data", {}).get("data", "")
                    bytes_read = len(data_hex) // 2
                    result.add_measurement(elapsed, bytes_read)
                    offset += read_size
                else:
                    result.add_error()

        except Exception as e:
            print(f"Error in sequential large reads: {e}")
            result.add_error()

        return result

    def benchmark_random_access(self, client, iterations: int = 50) -> BenchmarkResult:
        """
        Benchmark: Random access reads (4KB).

        Simulates jumping to different file locations (e.g., following pointers).
        """
        result = BenchmarkResult("Random Access Reads (4KB)")

        try:
            provider_id = self._get_provider_id(client)

            # Get file size
            info_response = client.send_request("file/info", {"provider_id": provider_id})
            if info_response.get("status") != "success":
                raise Exception("Failed to get file size")
            file_size = info_response.get("data", {}).get("size", 0)

            if file_size < 4096:
                print("File too small for random access test")
                return result

            import random
            read_size = 4096

            for _ in range(iterations):
                # Random offset (aligned to 4KB boundary)
                offset = random.randint(0, (file_size - read_size) // 4096) * 4096

                start = time.perf_counter()
                response = client.send_request("data/read", {
                    "provider_id": provider_id,
                    "offset": offset,
                    "size": read_size
                })
                elapsed = (time.perf_counter() - start) * 1000

                if response.get("status") == "success":
                    data_hex = response.get("data", {}).get("data", "")
                    bytes_read = len(data_hex) // 2
                    result.add_measurement(elapsed, bytes_read)
                else:
                    result.add_error()

        except Exception as e:
            print(f"Error in random access: {e}")
            result.add_error()

        return result

    def benchmark_hash_calculation_simulation(self, client, chunk_count: int = 10) -> BenchmarkResult:
        """
        Benchmark: Hash calculation (multiple sequential reads).

        Simulates calculating hash over file region (e.g., MD5, SHA256).
        """
        result = BenchmarkResult("Hash Calculation Simulation")

        try:
            provider_id = self._get_provider_id(client)

            offset = 0
            chunk_size = 8192  # 8KB chunks

            start = time.perf_counter()
            for _ in range(chunk_count):
                response = client.send_request("data/read", {
                    "provider_id": provider_id,
                    "offset": offset,
                    "size": chunk_size
                })

                if response.get("status") == "success":
                    data_hex = response.get("data", {}).get("data", "")
                    bytes_read = len(data_hex) // 2
                    result.bytes_transferred += bytes_read
                    offset += chunk_size
                else:
                    result.add_error()
                    break

            elapsed = (time.perf_counter() - start) * 1000
            result.add_measurement(elapsed)

        except Exception as e:
            print(f"Error in hash calculation: {e}")
            result.add_error()

        return result

    async def benchmark_concurrent_reads_async(self, iterations: int = 20) -> BenchmarkResult:
        """
        Benchmark: Concurrent reads using async client.

        Simulates parallel analysis tasks (e.g., searching multiple regions).
        """
        result = BenchmarkResult("Concurrent Reads (Async)")

        try:
            client = AsyncImHexClient(host=self.host, port=self.port, max_concurrent=10)

            # Get provider ID
            response = await client.send_request("file/list")
            if response.get("status") != "success":
                raise Exception("Failed to get file list")
            providers = response.get("data", {}).get("providers", [])
            if not providers:
                raise Exception("No files open")
            provider_id = providers[0]["id"]

            # Create batch of read requests at different offsets
            batch_size = 5
            read_size = 4096

            for batch in range(iterations // batch_size):
                requests = [
                    ("data/read", {
                        "provider_id": provider_id,
                        "offset": (batch * batch_size + i) * read_size,
                        "size": read_size
                    })
                    for i in range(batch_size)
                ]

                start = time.perf_counter()
                results = await client.send_batch(requests, return_exceptions=True)
                elapsed = (time.perf_counter() - start) * 1000

                # Count successful reads
                success_count = 0
                bytes_read = 0
                for r in results:
                    if isinstance(r, dict) and r.get("status") == "success":
                        success_count += 1
                        data_hex = r.get("data", {}).get("data", "")
                        bytes_read += len(data_hex) // 2
                    else:
                        result.add_error()

                if success_count > 0:
                    result.add_measurement(elapsed, bytes_read)

        except Exception as e:
            print(f"Error in concurrent reads: {e}")
            import traceback
            traceback.print_exc()
            result.add_error()

        return result

    def run_suite(self, client, client_name: str) -> Dict[str, BenchmarkResult]:
        """Run complete benchmark suite."""
        print(f"\n{'=' * 70}")
        print(f"Running benchmark suite: {client_name}")
        print(f"{'=' * 70}")

        results = {}

        # Test 1: File operations
        print(f"\n[1/6] File operations...")
        results["file_ops"] = self.benchmark_file_operations(client, iterations=50)
        print(f"  ✓ {len(results['file_ops'].times)} measurements")

        # Test 2: Sequential small reads
        print(f"[2/6] Sequential small reads (256B)...")
        results["seq_small"] = self.benchmark_sequential_reads_small(client, iterations=100)
        print(f"  ✓ {len(results['seq_small'].times)} measurements")

        # Test 3: Sequential large reads
        print(f"[3/6] Sequential large reads (64KB)...")
        results["seq_large"] = self.benchmark_sequential_reads_large(client, iterations=20)
        print(f"  ✓ {len(results['seq_large'].times)} measurements")

        # Test 4: Random access
        print(f"[4/6] Random access reads (4KB)...")
        results["random"] = self.benchmark_random_access(client, iterations=50)
        print(f"  ✓ {len(results['random'].times)} measurements")

        # Test 5: Hash calculation simulation
        print(f"[5/6] Hash calculation simulation...")
        results["hash_sim"] = self.benchmark_hash_calculation_simulation(client, chunk_count=10)
        print(f"  ✓ {len(results['hash_sim'].times)} measurements")

        # Test 6: Concurrent reads (async only)
        if hasattr(client, '__aenter__'):
            print(f"[6/6] Concurrent reads (async)...")
            try:
                loop = asyncio.get_event_loop()
                results["concurrent"] = loop.run_until_complete(
                    self.benchmark_concurrent_reads_async(iterations=20)
                )
                print(f"  ✓ {len(results['concurrent'].times)} measurements")
            except Exception as e:
                print(f"  ✗ Skipped (error: {e})")
        else:
            print(f"[6/6] Concurrent reads - Skipped (not async client)")

        return results


def print_comparison_table(baseline: Dict[str, BenchmarkResult],
                          optimized: Dict[str, BenchmarkResult],
                          compressed: Dict[str, BenchmarkResult]):
    """Print comparison table of results."""
    print(f"\n{'=' * 100}")
    print("PERFORMANCE COMPARISON")
    print(f"{'=' * 100}")
    print(f"{'Benchmark':<30} {'Baseline (ms)':<15} {'Optimized (ms)':<15} {'Compressed (ms)':<15} {'Improvement':<15}")
    print(f"{'-' * 100}")

    for key in baseline.keys():
        baseline_stats = baseline[key].get_stats()
        optimized_stats = optimized[key].get_stats()
        compressed_stats = compressed[key].get_stats()

        baseline_avg = baseline_stats.get("avg_time_ms", 0)
        optimized_avg = optimized_stats.get("avg_time_ms", 0)
        compressed_avg = compressed_stats.get("avg_time_ms", 0)

        if baseline_avg > 0:
            improvement = ((baseline_avg - compressed_avg) / baseline_avg) * 100
            improvement_str = f"{improvement:+.1f}%"
        else:
            improvement_str = "N/A"

        print(f"{baseline_stats['name']:<30} {baseline_avg:>14.2f} {optimized_avg:>14.2f} "
              f"{compressed_avg:>14.2f} {improvement_str:>14}")

    print(f"{'-' * 100}")

    # Calculate bandwidth savings
    baseline_bytes = sum(r.bytes_transferred for r in baseline.values())
    optimized_bytes = sum(r.bytes_transferred for r in optimized.values())
    compressed_bytes = sum(r.bytes_transferred for r in compressed.values())

    print(f"\nData Transfer:")
    print(f"  Baseline:    {baseline_bytes:>10,} bytes ({baseline_bytes / 1024 / 1024:.2f} MB)")
    print(f"  Optimized:   {optimized_bytes:>10,} bytes ({optimized_bytes / 1024 / 1024:.2f} MB)")
    print(f"  Compressed:  {compressed_bytes:>10,} bytes ({compressed_bytes / 1024 / 1024:.2f} MB)")

    if baseline_bytes > 0:
        bandwidth_savings = ((baseline_bytes - compressed_bytes) / baseline_bytes) * 100
        print(f"  Bandwidth Savings: {bandwidth_savings:.1f}%")

    print(f"{'=' * 100}\n")


def main():
    """Run real-world benchmark suite."""
    print("\n" + "=" * 100)
    print("REAL-WORLD BINARY ANALYSIS WORKLOAD BENCHMARK")
    print("=" * 100)
    print("\nThis benchmark simulates realistic binary analysis workflows:")
    print("  • Multiple file operations (open, info, close)")
    print("  • Sequential data reads (small and large)")
    print("  • Random access pattern reads")
    print("  • Hash calculation simulation")
    print("  • Concurrent batch operations")
    print("\nMeasuring performance with three configurations:")
    print("  1. Standard client (baseline)")
    print("  2. Enhanced client with optimizations (cache + lazy loading)")
    print("  3. Enhanced client with optimizations + compression")

    benchmark = RealWorldBenchmark()

    # Configuration 1: Standard client (baseline)
    print("\n" + "=" * 100)
    print("CONFIGURATION 1: Standard Client (Baseline)")
    print("=" * 100)
    standard_client = ImHexClient(host="localhost", port=31337, timeout=30)
    baseline_results = benchmark.run_suite(standard_client, "Standard Client")

    # Configuration 2: Enhanced client with optimizations
    print("\n" + "=" * 100)
    print("CONFIGURATION 2: Enhanced Client (Optimizations)")
    print("=" * 100)
    optimized_client = create_enhanced_client(
        host="localhost",
        port=31337,
        config={
            'enable_cache': True,
            'cache_max_size': 1000,
            'enable_profiling': True,
            'enable_lazy': True,
            'enable_compression': False
        }
    )
    optimized_results = benchmark.run_suite(optimized_client, "Enhanced Client (Optimized)")

    # Configuration 3: Enhanced client with compression
    print("\n" + "=" * 100)
    print("CONFIGURATION 3: Enhanced Client (Optimized + Compression)")
    print("=" * 100)
    compressed_client = create_enhanced_client(
        host="localhost",
        port=31337,
        config={
            'enable_cache': True,
            'cache_max_size': 1000,
            'enable_profiling': True,
            'enable_lazy': True,
            'enable_compression': True,
            'compression_algorithm': 'zstd',
            'compression_level': 3,
            'compression_min_size': 1024
        }
    )
    compressed_results = benchmark.run_suite(compressed_client, "Enhanced Client (Optimized + Compressed)")

    # Print comparison
    print_comparison_table(baseline_results, optimized_results, compressed_results)

    # Print detailed stats for each configuration
    print("\n" + "=" * 100)
    print("DETAILED STATISTICS")
    print("=" * 100)

    for config_name, results in [
        ("Standard Client", baseline_results),
        ("Enhanced (Optimized)", optimized_results),
        ("Enhanced (Optimized + Compressed)", compressed_results)
    ]:
        print(f"\n{config_name}:")
        print("-" * 100)

        for key, result in results.items():
            stats = result.get_stats()
            if "error" not in stats:
                print(f"\n  {stats['name']}:")
                print(f"    Measurements: {stats['count']}")
                print(f"    Avg time: {stats['avg_time_ms']:.2f}ms")
                print(f"    Median: {stats['median_time_ms']:.2f}ms")
                print(f"    P95: {stats['p95_time_ms']:.2f}ms")
                print(f"    Min/Max: {stats['min_time_ms']:.2f}ms / {stats['max_time_ms']:.2f}ms")
                print(f"    Throughput: {stats['throughput_mbps']:.2f} MB/s")
                print(f"    Errors: {stats['errors']}")

    print("\n" + "=" * 100)
    print("BENCHMARK COMPLETE")
    print("=" * 100 + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
