#!/usr/bin/env python3
"""
ImHex MCP Profiler

Memory and CPU profiling tool for ImHex MCP operations.
Monitors resource usage during endpoint execution.

Usage:
    python3 profile_imhex.py --command "data/hash" --iterations 100

Example:
    python3 profile_imhex.py --command "data/read" --params '{"provider_id":0,"offset":0,"size":1024}' --duration 60

Requirements:
    - psutil library: pip3 install psutil
    - ImHex running with Network Interface enabled
"""

import socket
import json
import sys
import argparse
import time
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

# Add lib directory to path for error handling
sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))

from error_handling import (
    retry_with_backoff,
    ConnectionError as ImHexConnectionError,
    HealthCheck
)

try:
    import psutil
except ImportError:
    print("Error: psutil library required")
    print("Install with: pip3 install psutil")
    sys.exit(1)


class ImHexProfiler:
    """Resource profiling tool for ImHex MCP."""

    def __init__(self, host: str = "localhost", port: int = 31337) -> None:
        self.host = host
        self.port = port
        self.imhex_process: Optional[psutil.Process] = None
        self.samples: List[Dict[str, Any]] = []

    def find_imhex_process(self) -> Optional[psutil.Process]:
        """Find running ImHex process."""
        for proc in psutil.process_iter(['pid', 'name', 'exe']):
            try:
                if 'imhex' in proc.info['name'].lower():
                    return proc
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return None

    @retry_with_backoff(max_attempts=3, initial_delay=0.5, exponential_base=2.0)
    def send_request(self, endpoint: str, data: Optional[Dict[str, Any]] = None,
                     timeout: int = 10) -> Dict[str, Any]:
        """Send request to ImHex MCP with automatic retry on failure."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
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
            return json.loads(response.decode().strip())

        except (socket.error, socket.timeout, ConnectionRefusedError) as e:
            # These will be caught by retry decorator
            raise
        except Exception as e:
            return {"status": "error", "data": {"error": str(e)}}

    def sample_process(self) -> Optional[Dict[str, Any]]:
        """Take a resource usage sample."""
        if not self.imhex_process:
            return None

        try:
            # Get CPU and memory usage
            cpu_percent = self.imhex_process.cpu_percent(interval=0.1)
            memory_info = self.imhex_process.memory_info()

            sample = {
                "timestamp": time.time(),
                "cpu_percent": cpu_percent,
                "memory_rss_mb": memory_info.rss / (1024 * 1024),
                "memory_vms_mb": memory_info.vms / (1024 * 1024),
                "num_threads": self.imhex_process.num_threads(),
            }

            # Try to get more detailed info (may not be available on all platforms)
            try:
                io_counters = self.imhex_process.io_counters()
                sample["io_read_bytes"] = io_counters.read_bytes
                sample["io_write_bytes"] = io_counters.write_bytes
            except:
                pass

            return sample

        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return None

    def profile_operation(self, endpoint: str, data: Optional[Dict[str, Any]] = None,
                          iterations: int = 1, sample_interval: float = 0.1) -> Optional[Dict[str, Any]]:
        """Profile a specific operation with resource monitoring."""
        print(f"\n{'='*70}")
        print(f"Profiling Operation: {endpoint}")
        print(f"  Iterations: {iterations}")
        print(f"  Sample Interval: {sample_interval}s")
        print(f"{'='*70}\n")

        # Find ImHex process
        self.imhex_process = self.find_imhex_process()
        if not self.imhex_process:
            print("Error: ImHex process not found")
            print("Please ensure ImHex is running")
            return None

        print(f"Found ImHex process (PID: {self.imhex_process.pid})")

        # Baseline sample
        print("Taking baseline sample...")
        baseline = self.sample_process()
        if not baseline:
            print("Error: Could not sample process")
            return None

        print(f"  Baseline CPU: {baseline['cpu_percent']:.1f}%")
        print(f"  Baseline Memory: {baseline['memory_rss_mb']:.1f} MB\n")

        # Run operation and sample
        print(f"Running {iterations} iterations...")
        self.samples = []
        operation_start = time.time()

        for i in range(iterations):
            # Sample before operation
            sample_before = self.sample_process()

            # Execute operation
            op_start = time.time()
            result = self.send_request(endpoint, data)
            op_duration = time.time() - op_start

            # Sample after operation
            sample_after = self.sample_process()

            if sample_before and sample_after:
                self.samples.append({
                    "iteration": i,
                    "duration": op_duration,
                    "cpu_before": sample_before["cpu_percent"],
                    "cpu_after": sample_after["cpu_percent"],
                    "mem_before": sample_before["memory_rss_mb"],
                    "mem_after": sample_after["memory_rss_mb"],
                    "success": result.get("status") == "success"
                })

            # Sample during interval
            time.sleep(sample_interval)

            if (i + 1) % 10 == 0:
                print(f"  Progress: {i+1}/{iterations}")

        operation_duration = time.time() - operation_start
        print(f"\nCompleted in {operation_duration:.2f}s\n")

        # Analyze results
        return self.analyze_profile()

    def analyze_profile(self) -> Optional[Dict[str, Any]]:
        """Analyze profiling results."""
        if not self.samples:
            print("No samples collected")
            return None

        successful = [s for s in self.samples if s["success"]]
        failed = [s for s in self.samples if not s["success"]]

        # Calculate statistics
        durations = [s["duration"] for s in successful]
        cpu_deltas = [s["cpu_after"] - s["cpu_before"] for s in successful]
        mem_deltas = [s["mem_after"] - s["mem_before"] for s in successful]

        if not durations:
            print("No successful operations to analyze")
            return None

        durations.sort()
        cpu_deltas.sort()
        mem_deltas.sort()

        analysis = {
            "total_operations": len(self.samples),
            "successful": len(successful),
            "failed": len(failed),
            "duration": {
                "min": min(durations),
                "max": max(durations),
                "mean": sum(durations) / len(durations),
                "median": durations[len(durations)//2],
                "p95": durations[int(len(durations) * 0.95)],
                "p99": durations[int(len(durations) * 0.99)],
            },
            "cpu_delta_percent": {
                "min": min(cpu_deltas),
                "max": max(cpu_deltas),
                "mean": sum(cpu_deltas) / len(cpu_deltas),
                "median": cpu_deltas[len(cpu_deltas)//2],
            },
            "memory_delta_mb": {
                "min": min(mem_deltas),
                "max": max(mem_deltas),
                "mean": sum(mem_deltas) / len(mem_deltas),
                "median": mem_deltas[len(mem_deltas)//2],
            }
        }

        self.print_analysis(analysis)
        return analysis

    def print_analysis(self, analysis: Dict[str, Any]) -> None:
        """Print profiling analysis."""
        print(f"{'='*70}")
        print(f"PROFILING ANALYSIS")
        print(f"{'='*70}\n")

        print(f"Operations:")
        print(f"  Total:      {analysis['total_operations']}")
        print(f"  Successful: {analysis['successful']}")
        print(f"  Failed:     {analysis['failed']}")

        print(f"\nOperation Duration (seconds):")
        print(f"  Min:    {analysis['duration']['min']:.6f}s")
        print(f"  Max:    {analysis['duration']['max']:.6f}s")
        print(f"  Mean:   {analysis['duration']['mean']:.6f}s")
        print(f"  Median: {analysis['duration']['median']:.6f}s")
        print(f"  P95:    {analysis['duration']['p95']:.6f}s")
        print(f"  P99:    {analysis['duration']['p99']:.6f}s")

        print(f"\nCPU Delta (%):")
        print(f"  Min:    {analysis['cpu_delta_percent']['min']:+.2f}%")
        print(f"  Max:    {analysis['cpu_delta_percent']['max']:+.2f}%")
        print(f"  Mean:   {analysis['cpu_delta_percent']['mean']:+.2f}%")
        print(f"  Median: {analysis['cpu_delta_percent']['median']:+.2f}%")

        print(f"\nMemory Delta (MB):")
        print(f"  Min:    {analysis['memory_delta_mb']['min']:+.3f} MB")
        print(f"  Max:    {analysis['memory_delta_mb']['max']:+.3f} MB")
        print(f"  Mean:   {analysis['memory_delta_mb']['mean']:+.3f} MB")
        print(f"  Median: {analysis['memory_delta_mb']['median']:+.3f} MB")

        # Memory leak detection
        if analysis['memory_delta_mb']['mean'] > 1.0:
            print(f"\n⚠ WARNING: Average memory increase of {analysis['memory_delta_mb']['mean']:.2f} MB")
            print("  Possible memory leak detected")

        print(f"\n{'='*70}\n")

    def continuous_monitor(self, duration: int = 60, interval: float = 1.0) -> None:
        """Continuously monitor ImHex resource usage."""
        print(f"\n{'='*70}")
        print(f"Continuous Resource Monitoring")
        print(f"  Duration: {duration}s")
        print(f"  Interval: {interval}s")
        print(f"{'='*70}\n")

        # Find ImHex process
        self.imhex_process = self.find_imhex_process()
        if not self.imhex_process:
            print("Error: ImHex process not found")
            return None

        print(f"Monitoring ImHex (PID: {self.imhex_process.pid})\n")
        print(f"{'Time':<10s} {'CPU %':<10s} {'Memory MB':<12s} {'Threads':<10s}")
        print(f"{'-'*42}")

        start_time = time.time()
        samples = []

        while time.time() - start_time < duration:
            sample = self.sample_process()
            if sample:
                samples.append(sample)

                elapsed = time.time() - start_time
                print(f"{elapsed:>8.1f}s  "
                      f"{sample['cpu_percent']:>6.1f}%  "
                      f"{sample['memory_rss_mb']:>10.1f} MB  "
                      f"{sample['num_threads']:>8d}")

            time.sleep(interval)

        # Summary
        if samples:
            cpu_avg = sum(s['cpu_percent'] for s in samples) / len(samples)
            mem_avg = sum(s['memory_rss_mb'] for s in samples) / len(samples)
            mem_min = min(s['memory_rss_mb'] for s in samples)
            mem_max = max(s['memory_rss_mb'] for s in samples)

            print(f"\n{'='*70}")
            print(f"MONITORING SUMMARY")
            print(f"{'='*70}")
            print(f"  Average CPU: {cpu_avg:.1f}%")
            print(f"  Average Memory: {mem_avg:.1f} MB")
            print(f"  Memory Range: {mem_min:.1f} - {mem_max:.1f} MB")
            print(f"  Samples Collected: {len(samples)}")
            print(f"{'='*70}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="ImHex MCP profiler")
    parser.add_argument("--host", default="localhost", help="ImHex MCP host")
    parser.add_argument("--port", type=int, default=31337, help="ImHex MCP port")

    subparsers = parser.add_subparsers(dest="mode", help="Profiling mode")

    # Operation profiling mode
    op_parser = subparsers.add_parser("operation", help="Profile specific operation")
    op_parser.add_argument("--endpoint", required=True, help="Endpoint to profile")
    op_parser.add_argument("--params", help="JSON parameters for endpoint")
    op_parser.add_argument("--iterations", type=int, default=100, help="Number of iterations")
    op_parser.add_argument("--interval", type=float, default=0.1, help="Sample interval (seconds)")

    # Continuous monitoring mode
    mon_parser = subparsers.add_parser("monitor", help="Continuous resource monitoring")
    mon_parser.add_argument("--duration", type=int, default=60, help="Monitoring duration (seconds)")
    mon_parser.add_argument("--interval", type=float, default=1.0, help="Sample interval (seconds)")

    args = parser.parse_args()

    if not args.mode:
        parser.print_help()
        sys.exit(1)

    profiler = ImHexProfiler(args.host, args.port)

    if args.mode == "operation":
        # Parse parameters
        params = None
        if args.params:
            try:
                params = json.loads(args.params)
            except json.JSONDecodeError:
                print(f"Error: Invalid JSON parameters: {args.params}")
                sys.exit(1)

        profiler.profile_operation(
            args.endpoint,
            params,
            args.iterations,
            args.interval
        )

    elif args.mode == "monitor":
        profiler.continuous_monitor(args.duration, args.interval)


if __name__ == "__main__":
    main()
