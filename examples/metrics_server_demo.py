#!/usr/bin/env python3
"""
Metrics Server Demo

Demonstrates the Prometheus metrics integration with ImHex MCP.
Runs a standalone metrics HTTP server that exposes metrics at http://localhost:8000/metrics

Usage:
    python examples/metrics_server_demo.py

Then visit:
    http://localhost:8000/          - Info page
    http://localhost:8000/metrics   - Prometheus metrics

Or scrape with Prometheus:
    curl http://localhost:8000/metrics
"""

import sys
import os
import time
import random
import threading

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.metrics import ImHexMCPMetrics
from lib.metrics_server import MetricsServer
from lib.config import get_config


def simulate_traffic(metrics: ImHexMCPMetrics, duration: int = 60):
    """Simulate some traffic to generate interesting metrics."""
    print(f"\nSimulating traffic for {duration} seconds...")
    print("Watch metrics at: http://localhost:8000/metrics\n")

    endpoints = [
        "file/open",
        "file/read",
        "data/strings",
        "data/hash",
        "batch/search",
    ]

    start = time.time()
    request_count = 0

    while time.time() - start < duration:
        endpoint = random.choice(endpoints)
        request_count += 1

        # Simulate a request
        metrics.active_requests.inc()
        request_start = time.time()

        # Random latency (10-500ms)
        latency = random.uniform(0.01, 0.5)
        time.sleep(latency)

        # Random success/failure (90% success)
        if random.random() < 0.9:
            status = "success"
        else:
            status = "error"
            metrics.errors.labels(error_type="SimulatedError", endpoint=endpoint).inc()

        # Record metrics
        request_duration = time.time() - request_start
        metrics.request_count.labels(endpoint=endpoint, status=status).inc()
        metrics.request_duration.labels(endpoint=endpoint).observe(request_duration)
        metrics.active_requests.dec()

        # Simulate cache operations
        if random.random() < 0.7:
            metrics.cache_operations.labels(result="hit").inc()
        else:
            metrics.cache_operations.labels(result="miss").inc()

        # Simulate compression
        if random.random() < 0.5:
            original_size = random.randint(1000, 100000)
            compressed_size = int(original_size * random.uniform(0.3, 0.8))
            compress_time = random.uniform(0.001, 0.01)

            metrics.record_compression(
                operation="compress",
                duration_seconds=compress_time,
                original_size=original_size,
                compressed_size=compressed_size,
                result="success",
            )

        # Update connection pool stats
        if request_count % 5 == 0:
            metrics.update_pool_stats(
                active=random.randint(1, 5), idle=random.randint(0, 10), total=15
            )

        # Show progress
        if request_count % 10 == 0:
            print(f"  Requests sent: {request_count}, Elapsed: {time.time() - start:.1f}s")

        # Rate limiting (don't hammer too hard)
        time.sleep(random.uniform(0.1, 0.5))

    print(f"\nSimulation complete! Sent {request_count} requests.")


def main():
    """Run the metrics server demo."""
    print("=" * 60)
    print("ImHex MCP - Prometheus Metrics Server Demo")
    print("=" * 60)

    # Load configuration
    try:
        config = get_config()
        port = config.monitoring.metrics_port
        print(f"\n✓ Configuration loaded")
        print(f"  Metrics port: {port}")
    except Exception as e:
        print(f"\n⚠ Using default configuration (config.yaml not found)")
        port = 8000

    # Create metrics instance
    metrics = ImHexMCPMetrics()
    print(f"\n✓ Metrics collectors initialized")

    # Start metrics HTTP server
    server = MetricsServer(port=port, metrics=metrics)
    server.start()

    print(f"\n✓ Metrics server started on port {port}")
    print(f"\nEndpoints:")
    print(f"  Info page:  http://localhost:{port}/")
    print(f"  Metrics:    http://localhost:{port}/metrics")

    try:
        # Run traffic simulation in background
        traffic_thread = threading.Thread(
            target=simulate_traffic, args=(metrics, 60), daemon=True
        )
        traffic_thread.start()

        # Keep main thread alive
        print(f"\nPress Ctrl+C to stop...")
        traffic_thread.join()

    except KeyboardInterrupt:
        print("\n\nShutting down...")
    finally:
        server.stop()
        print("✓ Server stopped")

    print("\nDemo complete!")


if __name__ == "__main__":
    main()
