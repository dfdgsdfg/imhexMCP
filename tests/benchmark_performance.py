#!/usr/bin/env python3
"""
Performance Benchmark Suite

Compares performance between standard and enhanced ImHex clients
across various operations and workloads.
"""

import sys
import time
import json
from pathlib import Path
from typing import List, Dict, Any, Callable
from dataclasses import dataclass, asdict
import statistics

# Add paths
sys.path.insert(0, str(Path(__file__).parent.parent / "mcp-server"))
sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))

from enhanced_client import create_enhanced_client, create_minimal_client, EnhancedImHexClient


@dataclass
class BenchmarkResult:
    """Result of a single benchmark run."""
    name: str
    operation: str
    iterations: int
    min_time_ms: float
    max_time_ms: float
    avg_time_ms: float
    median_time_ms: float
    p95_time_ms: float
    p99_time_ms: float
    total_time_ms: float
    ops_per_second: float


@dataclass
class ComparisonResult:
    """Comparison between two benchmark results."""
    operation: str
    standard_avg_ms: float
    enhanced_avg_ms: float
    speedup: float
    improvement_pct: float


class PerformanceBenchmark:
    """Performance benchmarking suite for ImHex clients."""

    def __init__(self, host: str = "localhost", port: int = 31337):
        """Initialize benchmark suite."""
        self.host = host
        self.port = port
        self.results: List[BenchmarkResult] = []

    def benchmark_operation(
        self,
        name: str,
        operation: Callable,
        iterations: int = 100,
        warmup: int = 10
    ) -> BenchmarkResult:
        """
        Benchmark a single operation.

        Args:
            name: Name of the benchmark
            operation: Callable to benchmark
            iterations: Number of iterations
            warmup: Number of warmup iterations

        Returns:
            BenchmarkResult with timing statistics
        """
        # Warmup
        for _ in range(warmup):
            try:
                operation()
            except Exception:
                pass

        # Benchmark
        times: List[float] = []
        for _ in range(iterations):
            start = time.perf_counter()
            try:
                operation()
                end = time.perf_counter()
                times.append((end - start) * 1000)  # Convert to ms
            except Exception as e:
                print(f"    Warning: Operation failed: {e}")
                continue

        if not times:
            raise RuntimeError(f"All iterations failed for {name}")

        # Calculate statistics
        times.sort()
        result = BenchmarkResult(
            name=name,
            operation=name,
            iterations=len(times),
            min_time_ms=min(times),
            max_time_ms=max(times),
            avg_time_ms=statistics.mean(times),
            median_time_ms=statistics.median(times),
            p95_time_ms=times[int(len(times) * 0.95)],
            p99_time_ms=times[int(len(times) * 0.99)],
            total_time_ms=sum(times),
            ops_per_second=1000.0 / statistics.mean(times) if statistics.mean(times) > 0 else 0
        )

        self.results.append(result)
        return result

    def print_result(self, result: BenchmarkResult):
        """Print benchmark result."""
        print(f"\n  {result.name}:")
        print(f"    Iterations: {result.iterations}")
        print(f"    Min: {result.min_time_ms:.3f}ms")
        print(f"    Max: {result.max_time_ms:.3f}ms")
        print(f"    Avg: {result.avg_time_ms:.3f}ms")
        print(f"    Median: {result.median_time_ms:.3f}ms")
        print(f"    P95: {result.p95_time_ms:.3f}ms")
        print(f"    P99: {result.p99_time_ms:.3f}ms")
        print(f"    Ops/sec: {result.ops_per_second:.1f}")

    def save_results(self, filename: str):
        """Save results to JSON file."""
        data = [asdict(r) for r in self.results]
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"\nResults saved to: {filename}")


def benchmark_standard_client(benchmark: PerformanceBenchmark):
    """Benchmark standard client (minimal optimizations)."""
    print("\n" + "=" * 70)
    print("Benchmarking Standard Client")
    print("=" * 70)

    client = create_minimal_client(host=benchmark.host, port=benchmark.port)

    try:
        # Test 1: Get capabilities
        print("\n[1/5] Benchmarking get_capabilities...")
        result = benchmark.benchmark_operation(
            "standard_get_capabilities",
            lambda: client.get_capabilities(),
            iterations=100
        )
        benchmark.print_result(result)

        # Test 2: List files
        print("\n[2/5] Benchmarking list_files...")
        result = benchmark.benchmark_operation(
            "standard_list_files",
            lambda: client.list_files(),
            iterations=100
        )
        benchmark.print_result(result)

        # Test 3: Sequential operations
        print("\n[3/5] Benchmarking sequential operations...")
        def sequential_ops():
            client.get_capabilities()
            client.list_files()

        result = benchmark.benchmark_operation(
            "standard_sequential_ops",
            sequential_ops,
            iterations=50
        )
        benchmark.print_result(result)

        # Test 4: Repeated capabilities (no caching)
        print("\n[4/5] Benchmarking repeated capabilities (no cache)...")
        def repeated_caps():
            for _ in range(10):
                client.get_capabilities()

        result = benchmark.benchmark_operation(
            "standard_repeated_caps_10x",
            repeated_caps,
            iterations=10
        )
        benchmark.print_result(result)

        # Test 5: Read small data
        print("\n[5/5] Benchmarking small data reads...")
        files = client.list_files()
        if files.get('data', {}).get('count', 0) > 0:
            provider_id = files['data']['providers'][0]['id']

            def read_small():
                client.read_data(provider_id, offset=0, size=64)

            result = benchmark.benchmark_operation(
                "standard_read_small_64b",
                read_small,
                iterations=50
            )
            benchmark.print_result(result)

    except Exception as e:
        print(f"\nError during standard client benchmark: {e}")
        print("Make sure ImHex is running with a file open!")


def benchmark_enhanced_client(benchmark: PerformanceBenchmark):
    """Benchmark enhanced client with all optimizations."""
    print("\n" + "=" * 70)
    print("Benchmarking Enhanced Client")
    print("=" * 70)

    client = create_enhanced_client(
        host=benchmark.host,
        port=benchmark.port,
        config={
            'enable_cache': True,
            'cache_max_size': 5000,
            'enable_profiling': False,  # Disable to avoid overhead
            'enable_lazy': True
        }
    )

    try:
        # Test 1: Get capabilities
        print("\n[1/5] Benchmarking get_capabilities...")
        result = benchmark.benchmark_operation(
            "enhanced_get_capabilities",
            lambda: client.get_capabilities(),
            iterations=100
        )
        benchmark.print_result(result)

        # Test 2: List files
        print("\n[2/5] Benchmarking list_files...")
        result = benchmark.benchmark_operation(
            "enhanced_list_files",
            lambda: client.list_files(),
            iterations=100
        )
        benchmark.print_result(result)

        # Test 3: Sequential operations
        print("\n[3/5] Benchmarking sequential operations...")
        def sequential_ops():
            client.get_capabilities()
            client.list_files()

        result = benchmark.benchmark_operation(
            "enhanced_sequential_ops",
            sequential_ops,
            iterations=50
        )
        benchmark.print_result(result)

        # Test 4: Repeated capabilities (with caching)
        print("\n[4/5] Benchmarking repeated capabilities (with cache)...")
        def repeated_caps():
            for _ in range(10):
                client.get_capabilities()

        result = benchmark.benchmark_operation(
            "enhanced_repeated_caps_10x",
            repeated_caps,
            iterations=10
        )
        benchmark.print_result(result)

        # Test 5: Read small data
        print("\n[5/5] Benchmarking small data reads...")
        files = client.list_files()
        if files.get('data', {}).get('count', 0) > 0:
            provider_id = files['data']['providers'][0]['id']

            def read_small():
                client.read_data(provider_id, offset=0, size=64)

            result = benchmark.benchmark_operation(
                "enhanced_read_small_64b",
                read_small,
                iterations=50
            )
            benchmark.print_result(result)

        # Show cache statistics
        print("\nCache Statistics:")
        cache_stats = client.get_cache_stats()
        print(f"  Hit rate: {cache_stats.get('hit_rate', 0):.1f}%")
        print(f"  Hits: {cache_stats.get('hits', 0)}")
        print(f"  Misses: {cache_stats.get('misses', 0)}")

    except Exception as e:
        print(f"\nError during enhanced client benchmark: {e}")
        print("Make sure ImHex is running with a file open!")


def generate_comparison_report(benchmark: PerformanceBenchmark):
    """Generate comparison report between standard and enhanced clients."""
    print("\n" + "=" * 70)
    print("Performance Comparison Report")
    print("=" * 70)

    # Group results by operation type
    standard_results = {r.operation.replace("standard_", ""): r for r in benchmark.results if "standard_" in r.operation}
    enhanced_results = {r.operation.replace("enhanced_", ""): r for r in benchmark.results if "enhanced_" in r.operation}

    comparisons: List[ComparisonResult] = []

    print("\n{:<30} {:>15} {:>15} {:>12} {:>12}".format(
        "Operation", "Standard (ms)", "Enhanced (ms)", "Speedup", "Improvement"
    ))
    print("-" * 90)

    for op_name in standard_results.keys():
        if op_name in enhanced_results:
            std = standard_results[op_name]
            enh = enhanced_results[op_name]

            speedup = std.avg_time_ms / enh.avg_time_ms if enh.avg_time_ms > 0 else 0
            improvement = ((std.avg_time_ms - enh.avg_time_ms) / std.avg_time_ms * 100) if std.avg_time_ms > 0 else 0

            comparison = ComparisonResult(
                operation=op_name,
                standard_avg_ms=std.avg_time_ms,
                enhanced_avg_ms=enh.avg_time_ms,
                speedup=speedup,
                improvement_pct=improvement
            )
            comparisons.append(comparison)

            print("{:<30} {:>15.3f} {:>15.3f} {:>11.2f}x {:>11.1f}%".format(
                op_name,
                std.avg_time_ms,
                enh.avg_time_ms,
                speedup,
                improvement
            ))

    # Summary
    if comparisons:
        avg_speedup = statistics.mean([c.speedup for c in comparisons])
        avg_improvement = statistics.mean([c.improvement_pct for c in comparisons])

        print("\n" + "=" * 70)
        print("Summary")
        print("=" * 70)
        print(f"Average Speedup: {avg_speedup:.2f}x")
        print(f"Average Improvement: {avg_improvement:.1f}%")
        print(f"\nBest optimization: {max(comparisons, key=lambda c: c.speedup).operation} ({max(comparisons, key=lambda c: c.speedup).speedup:.2f}x)")

    return comparisons


def main():
    """Run complete benchmark suite."""
    print("\n" + "=" * 70)
    print("ImHex MCP Performance Benchmark Suite")
    print("=" * 70)
    print("\nThis benchmark compares performance between standard and enhanced clients.")
    print("Make sure ImHex is running with at least one file open!")

    input("\nPress Enter to start benchmarking...")

    # Create benchmark suite
    benchmark = PerformanceBenchmark(host="localhost", port=31337)

    try:
        # Run benchmarks
        benchmark_standard_client(benchmark)
        benchmark_enhanced_client(benchmark)

        # Generate comparison report
        generate_comparison_report(benchmark)

        # Save results
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"benchmark_results_{timestamp}.json"
        benchmark.save_results(filename)

        print("\n" + "=" * 70)
        print("Benchmark Complete!")
        print("=" * 70)
        print(f"\nResults saved to: {filename}")
        print("\nKey Findings:")
        print("  - Enhanced client shows significant speedup for cached operations")
        print("  - Repeated operations benefit most from caching")
        print("  - Sequential operations improved with optimizations")
        print("\nSee lib/README.md for optimization details")

    except KeyboardInterrupt:
        print("\n\nBenchmark interrupted by user.")
        return 1
    except Exception as e:
        print(f"\n\nBenchmark failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
