#!/usr/bin/env python3
"""
ImHex MCP Endpoint Benchmarks

Comprehensive performance benchmarking suite for all ImHex MCP endpoints.
Measures latency, throughput, and resource usage across various scenarios.

Usage:
    python3 endpoint_benchmarks.py [--output FILE] [--iterations N] [--warmup N]

Example:
    python3 endpoint_benchmarks.py --output results.json --iterations 100 --warmup 10
"""

import socket
import json
import sys
import argparse
import time
import statistics
from datetime import datetime
from pathlib import Path
import tempfile
from typing import Dict, List, Optional, Any, Tuple


class ImHexBenchmark:
    """Benchmark framework for ImHex MCP endpoints."""

    def __init__(self, host: str = "localhost", port: int = 31337, timeout: int = 30) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout
        self.results: Dict[str, List[Dict[str, Any]]] = {}

    def send_request(self, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Tuple[Dict[str, Any], float]:
        """Send request to ImHex MCP and return response with timing."""
        start_time = time.perf_counter()

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            sock.connect((self.host, self.port))

            request = json.dumps({
                "endpoint": endpoint,
                "data": data or {}
            }) + "\n"

            sock.sendall(request.encode())

            response = b""
            while b"\n" not in response:
                response += sock.recv(4096)

            sock.close()

            end_time = time.perf_counter()
            latency = (end_time - start_time) * 1000  # Convert to ms

            result = json.loads(response.decode().strip())
            return result, latency

        except Exception as e:
            end_time = time.perf_counter()
            latency = (end_time - start_time) * 1000
            return {"status": "error", "data": {"error": str(e)}}, latency

    def benchmark_endpoint(self, name: str, endpoint: str, data: Optional[Dict[str, Any]] = None,
                          iterations: int = 100, warmup: int = 10) -> Dict[str, Any]:
        """Benchmark a single endpoint with multiple iterations."""
        print(f"  Benchmarking {name}...")

        latencies = []
        errors = 0

        # Warmup phase
        for _ in range(warmup):
            result, _ = self.send_request(endpoint, data)
            if result.get("status") != "success":
                errors += 1

        # Actual benchmark
        for _ in range(iterations):
            result, latency = self.send_request(endpoint, data)

            if result.get("status") == "success":
                latencies.append(latency)
            else:
                errors += 1

        if not latencies:
            return {
                "endpoint": endpoint,
                "name": name,
                "iterations": iterations,
                "errors": errors,
                "status": "failed",
                "error": "All requests failed"
            }

        # Calculate statistics
        latencies.sort()
        stats = {
            "endpoint": endpoint,
            "name": name,
            "iterations": iterations,
            "successful": len(latencies),
            "errors": errors,
            "latency_ms": {
                "min": round(min(latencies), 3),
                "max": round(max(latencies), 3),
                "mean": round(statistics.mean(latencies), 3),
                "median": round(statistics.median(latencies), 3),
                "p95": round(latencies[int(len(latencies) * 0.95)], 3),
                "p99": round(latencies[int(len(latencies) * 0.99)], 3),
                "stdev": round(statistics.stdev(latencies), 3) if len(latencies) > 1 else 0
            },
            "throughput": {
                "requests_per_second": round(1000.0 / statistics.mean(latencies), 2)
            }
        }

        return stats

    def create_test_files(self) -> Dict[str, str]:
        """Create test files of various sizes."""
        test_files: Dict[str, str] = {}

        # Small file: 1KB
        small_file = tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='_1kb.bin')
        small_file.write(b'\x90' * 1024)  # NOP sled
        small_file.close()
        test_files['small'] = small_file.name

        # Medium file: 1MB
        medium_file = tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='_1mb.bin')
        medium_file.write(b'\x00' * (1024 * 1024))
        medium_file.close()
        test_files['medium'] = medium_file.name

        # Large file: 10MB
        large_file = tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='_10mb.bin')
        # Write in chunks to avoid memory issues
        for _ in range(10):
            large_file.write(b'\xff' * (1024 * 1024))
        large_file.close()
        test_files['large'] = large_file.name

        return test_files

    def cleanup_test_files(self, test_files: Dict[str, str]) -> None:
        """Remove test files."""
        for file_path in test_files.values():
            try:
                Path(file_path).unlink()
            except:
                pass

    def run_benchmarks(self, iterations: int = 100, warmup: int = 10) -> Optional[Dict[str, List[Dict[str, Any]]]]:
        """Run complete benchmark suite."""
        print(f"\n{'='*70}")
        print(f"ImHex MCP Endpoint Benchmarks")
        print(f"  Host:       {self.host}:{self.port}")
        print(f"  Iterations: {iterations}")
        print(f"  Warmup:     {warmup}")
        print(f"{'='*70}\n")

        # Test connection
        print("[1/8] Testing connection...")
        result, latency = self.send_request("capabilities")
        if result.get("status") != "success":
            print(f"  Error: Cannot connect to ImHex MCP")
            return None

        endpoints = result.get("data", {}).get("endpoints", [])
        print(f"  ✓ Connected ({len(endpoints)} endpoints available)")

        # Create test files
        print("\n[2/8] Creating test files...")
        test_files = self.create_test_files()
        print(f"  ✓ Created {len(test_files)} test files")
        for size, path in test_files.items():
            file_size = Path(path).stat().st_size
            print(f"    - {size}: {file_size:,} bytes")

        # Category 1: Core Operations
        print("\n[3/8] Benchmarking core operations...")
        self.results['core'] = [
            self.benchmark_endpoint("capabilities", "capabilities", None, iterations, warmup),
            self.benchmark_endpoint("file/list", "file/list", None, iterations, warmup),
        ]

        # Category 2: File Operations
        print("\n[4/8] Benchmarking file operations...")

        # Open small file
        result, _ = self.send_request("file/open", {"path": test_files['small']})
        time.sleep(0.5)  # Wait for async open

        # Get provider ID
        result, _ = self.send_request("file/list")
        providers = result.get("data", {}).get("providers", [])
        provider_id = providers[0]["id"] if providers else 0

        self.results['file'] = [
            self.benchmark_endpoint("file/current", "file/current", None, iterations, warmup),
            self.benchmark_endpoint("file/info", "file/info", {"provider_id": provider_id}, iterations, warmup),
        ]

        # Category 3: Data Read Operations
        print("\n[5/8] Benchmarking data read operations...")
        self.results['data_read'] = [
            self.benchmark_endpoint(
                "data/read (64 bytes)",
                "data/read",
                {"provider_id": provider_id, "offset": 0, "size": 64},
                iterations, warmup
            ),
            self.benchmark_endpoint(
                "data/read (1KB)",
                "data/read",
                {"provider_id": provider_id, "offset": 0, "size": 1024},
                iterations, warmup
            ),
            self.benchmark_endpoint(
                "data/read (4KB)",
                "data/read",
                {"provider_id": provider_id, "offset": 0, "size": 4096},
                iterations, warmup
            ),
        ]

        # Category 4: Hashing Operations
        print("\n[6/8] Benchmarking hashing operations...")
        self.results['hashing'] = [
            self.benchmark_endpoint(
                "data/hash (MD5, 1KB)",
                "data/hash",
                {"provider_id": provider_id, "offset": 0, "size": 1024, "algorithm": "md5"},
                iterations, warmup
            ),
            self.benchmark_endpoint(
                "data/hash (SHA256, 1KB)",
                "data/hash",
                {"provider_id": provider_id, "offset": 0, "size": 1024, "algorithm": "sha256"},
                iterations, warmup
            ),
        ]

        # Category 5: Search Operations
        print("\n[7/8] Benchmarking search operations...")
        self.results['search'] = [
            self.benchmark_endpoint(
                "data/search (hex pattern)",
                "data/search",
                {"provider_id": provider_id, "pattern": "90", "type": "hex"},
                iterations // 2, warmup  # Search is slower
            ),
        ]

        # Category 6: Advanced Analysis
        print("\n[8/8] Benchmarking advanced analysis...")
        self.results['analysis'] = [
            self.benchmark_endpoint(
                "data/entropy",
                "data/entropy",
                {"provider_id": provider_id, "offset": 0, "size": 1024},
                iterations // 2, warmup
            ),
            self.benchmark_endpoint(
                "data/statistics",
                "data/statistics",
                {"provider_id": provider_id, "offset": 0, "size": 1024},
                iterations // 2, warmup
            ),
            self.benchmark_endpoint(
                "data/strings",
                "data/strings",
                {"provider_id": provider_id, "offset": 0, "size": 1024, "min_length": 4, "type": "ascii"},
                iterations // 2, warmup
            ),
        ]

        # Cleanup
        print("\nCleaning up...")
        self.send_request("file/close", {"provider_id": provider_id})
        self.cleanup_test_files(test_files)
        print("  ✓ Cleanup complete")

        return self.results

    def generate_report(self, output_file: Optional[str] = None) -> Dict[str, Any]:
        """Generate benchmark report."""
        report = {
            "benchmark_version": "1.0",
            "timestamp": datetime.now().isoformat(),
            "system": {
                "host": self.host,
                "port": self.port
            },
            "results": self.results
        }

        if output_file:
            with open(output_file, 'w') as f:
                json.dump(report, f, indent=2)
            print(f"\n✓ Report saved to: {output_file}")

        # Print summary
        self.print_summary()

        return report

    def print_summary(self) -> None:
        """Print benchmark summary."""
        print(f"\n{'='*70}")
        print(f"BENCHMARK SUMMARY")
        print(f"{'='*70}\n")

        for category, benchmarks in self.results.items():
            print(f"{category.upper()}:")
            print(f"  {'Operation':<35s} {'Mean (ms)':<12s} {'P95 (ms)':<12s} {'RPS':<10s}")
            print(f"  {'-'*68}")

            for bench in benchmarks:
                if bench.get("latency_ms"):
                    name = bench['name'][:34]
                    mean = bench['latency_ms']['mean']
                    p95 = bench['latency_ms']['p95']
                    rps = bench['throughput']['requests_per_second']
                    print(f"  {name:<35s} {mean:<12.3f} {p95:<12.3f} {rps:<10.2f}")

            print()


def main() -> None:
    parser = argparse.ArgumentParser(description="ImHex MCP endpoint benchmarks")
    parser.add_argument("--output", help="Save report to JSON file")
    parser.add_argument("--iterations", type=int, default=100, help="Number of iterations per test (default: 100)")
    parser.add_argument("--warmup", type=int, default=10, help="Number of warmup iterations (default: 10)")
    parser.add_argument("--host", default="localhost", help="ImHex MCP host (default: localhost)")
    parser.add_argument("--port", type=int, default=31337, help="ImHex MCP port (default: 31337)")

    args = parser.parse_args()

    # Run benchmarks
    benchmark = ImHexBenchmark(args.host, args.port)
    results = benchmark.run_benchmarks(args.iterations, args.warmup)

    if results is None:
        print("\nError: Failed to connect to ImHex MCP")
        print("Please ensure:")
        print("  1. ImHex is running")
        print("  2. Network Interface is enabled in Settings")
        print("  3. Port 31337 is accessible")
        sys.exit(1)

    # Generate report
    benchmark.generate_report(args.output)

    print(f"\n{'='*70}")
    print("Benchmarking complete!")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
