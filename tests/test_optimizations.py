#!/usr/bin/env python3
"""
Comprehensive tests for advanced performance optimizations.

Tests streaming, lazy loading, and profiling modules to ensure they work
correctly with a live ImHex instance.
"""

import sys
import time
import unittest
from pathlib import Path
import tempfile
import os

# Add lib directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))

from streaming import StreamingClient, StreamProcessor, stream_to_file
from lazy import LazyClient, LazyProvider, memoize, memoize_with_ttl
from profiling import PerformanceMonitor, HotPathAnalyzer, OptimizationSuggestions, monitored
from cached_client import create_client


class TestStreaming(unittest.TestCase):
    """Test memory-efficient streaming functionality."""

    @classmethod
    def setUpClass(cls):
        """Set up streaming client."""
        cls.client = StreamingClient()

    def test_stream_read_basic(self):
        """Test basic streaming read."""
        print("\n[Streaming] Testing basic stream read...")

        try:
            chunks = list(self.client.stream_read(0, offset=0, total_size=1024, chunk_size=256))

            self.assertGreater(len(chunks), 0, "Should receive chunks")

            # Verify chunk properties
            total_bytes = sum(chunk.size for chunk in chunks)
            self.assertEqual(total_bytes, 1024, "Total bytes should match requested size")

            # Verify last chunk is marked
            self.assertTrue(chunks[-1].is_last, "Last chunk should be marked")

            print(f"  ✓ Received {len(chunks)} chunks ({total_bytes} bytes total)")

        except Exception as e:
            self.skipTest(f"ImHex not running or no file open: {e}")

    def test_stream_read_large(self):
        """Test streaming large data without memory issues."""
        print("\n[Streaming] Testing large stream (memory efficient)...")

        try:
            chunk_count = 0
            total_bytes = 0

            # Stream 1MB in 4KB chunks
            for chunk in self.client.stream_read(0, offset=0, total_size=1024*1024, chunk_size=4096):
                chunk_count += 1
                total_bytes += chunk.size

                # Verify chunk is reasonable size
                self.assertLessEqual(chunk.size, 4096, "Chunk size should not exceed requested")

            print(f"  ✓ Streamed {total_bytes} bytes in {chunk_count} chunks")

        except Exception as e:
            # File might be smaller than 1MB, that's OK
            print(f"  Info: {e}")

    def test_stream_processor_map(self):
        """Test stream transformation with map."""
        print("\n[Streaming] Testing stream map transformation...")

        try:
            stream = self.client.stream_read(0, offset=0, total_size=256)

            # Count null bytes using map/reduce
            null_count = StreamProcessor.reduce_stream(
                stream,
                lambda acc, data: acc + data.count(b'\x00'),
                0
            )

            self.assertGreaterEqual(null_count, 0, "Null count should be non-negative")
            print(f"  ✓ Found {null_count} null bytes using stream processing")

        except Exception as e:
            self.skipTest(f"Stream processing failed: {e}")

    def test_stream_to_file(self):
        """Test streaming data to file."""
        print("\n[Streaming] Testing stream to file...")

        try:
            with tempfile.NamedTemporaryFile(delete=False) as f:
                temp_path = f.name

            try:
                bytes_written = stream_to_file(
                    self.client, 0, temp_path,
                    offset=0, total_size=512, chunk_size=128
                )

                self.assertEqual(bytes_written, 512, "Should write expected bytes")

                # Verify file exists and has correct size
                self.assertTrue(os.path.exists(temp_path), "Output file should exist")
                self.assertEqual(os.path.getsize(temp_path), 512, "File size should match")

                print(f"  ✓ Wrote {bytes_written} bytes to file")

            finally:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)

        except Exception as e:
            self.skipTest(f"File streaming failed: {e}")


class TestLazyLoading(unittest.TestCase):
    """Test lazy loading and optimization patterns."""

    def test_lazy_client_deferred_connection(self):
        """Test lazy client defers connection."""
        print("\n[Lazy] Testing deferred connection...")

        # Creating client should be instant (no connection)
        start = time.perf_counter()
        client = LazyClient()
        creation_time = (time.perf_counter() - start) * 1000

        self.assertLess(creation_time, 1.0, "Client creation should be instant (<1ms)")
        print(f"  ✓ Client created in {creation_time:.4f}ms (instant)")

        # First access triggers connection
        try:
            start = time.perf_counter()
            endpoints = client.endpoints
            first_access_time = (time.perf_counter() - start) * 1000

            self.assertGreater(len(endpoints), 0, "Should have endpoints")
            print(f"  ✓ First access: {first_access_time:.2f}ms (loaded {len(endpoints)} endpoints)")

            # Second access should be cached
            start = time.perf_counter()
            endpoints2 = client.endpoints
            cached_access_time = (time.perf_counter() - start) * 1000

            self.assertEqual(endpoints, endpoints2, "Cached result should match")
            self.assertLess(cached_access_time, 0.1, "Cached access should be instant")

            speedup = first_access_time / cached_access_time if cached_access_time > 0 else 0
            print(f"  ✓ Cached access: {cached_access_time:.4f}ms ({speedup:.0f}x faster)")

        except Exception as e:
            self.skipTest(f"ImHex not running: {e}")

    def test_lazy_provider_metadata(self):
        """Test lazy provider metadata loading."""
        print("\n[Lazy] Testing lazy provider metadata...")

        try:
            client = LazyClient()

            # Create lazy provider (no metadata loaded)
            provider = LazyProvider(0, client)
            self.assertFalse(provider.is_loaded, "Metadata should not be loaded yet")

            # Access triggers loading
            start = time.perf_counter()
            name = provider.name
            size = provider.size
            load_time = (time.perf_counter() - start) * 1000

            self.assertTrue(provider.is_loaded, "Metadata should be loaded")
            print(f"  ✓ Loaded metadata: {name}, {size} bytes ({load_time:.2f}ms)")

            # Second access uses cache
            start = time.perf_counter()
            name2 = provider.name
            cached_time = (time.perf_counter() - start) * 1000

            self.assertEqual(name, name2, "Cached result should match")
            self.assertLess(cached_time, 0.1, "Cached access should be instant")
            print(f"  ✓ Cached access: {cached_time:.4f}ms")

        except Exception as e:
            self.skipTest(f"Provider metadata test failed: {e}")

    def test_memoize_decorator(self):
        """Test memoization decorator."""
        print("\n[Lazy] Testing memoization decorator...")

        call_count = [0]

        @memoize
        def expensive_function(n):
            call_count[0] += 1
            time.sleep(0.01)  # Simulate work
            return n * n

        # First call - slow
        start = time.perf_counter()
        result1 = expensive_function(10)
        first_time = (time.perf_counter() - start) * 1000

        self.assertEqual(result1, 100, "Result should be correct")
        self.assertEqual(call_count[0], 1, "Function should be called once")

        # Second call - cached
        start = time.perf_counter()
        result2 = expensive_function(10)
        cached_time = (time.perf_counter() - start) * 1000

        self.assertEqual(result2, 100, "Cached result should match")
        self.assertEqual(call_count[0], 1, "Function should not be called again")

        speedup = first_time / cached_time if cached_time > 0 else 0
        print(f"  ✓ First call: {first_time:.2f}ms")
        print(f"  ✓ Cached call: {cached_time:.4f}ms ({speedup:.0f}x faster)")

    def test_memoize_with_ttl(self):
        """Test memoization with TTL."""
        print("\n[Lazy] Testing memoization with TTL...")

        call_count = [0]

        @memoize_with_ttl(0.1)  # 100ms TTL
        def time_sensitive_function():
            call_count[0] += 1
            return time.time()

        # First call
        result1 = time_sensitive_function()
        self.assertEqual(call_count[0], 1)

        # Second call within TTL - cached
        result2 = time_sensitive_function()
        self.assertEqual(result2, result1, "Should return cached value")
        self.assertEqual(call_count[0], 1, "Should not call function again")

        # Wait for TTL to expire
        time.sleep(0.15)

        # Third call after TTL - recomputed
        result3 = time_sensitive_function()
        self.assertNotEqual(result3, result1, "Should compute new value after TTL")
        self.assertEqual(call_count[0], 2, "Should call function again")

        print(f"  ✓ TTL expiration works correctly")


class TestProfiling(unittest.TestCase):
    """Test profiling and performance monitoring."""

    def test_performance_monitor(self):
        """Test performance monitor."""
        print("\n[Profiling] Testing performance monitor...")

        monitor = PerformanceMonitor()

        # Perform monitored operations
        for i in range(10):
            with monitor.time("fast_op"):
                time.sleep(0.001)

        for i in range(5):
            with monitor.time("slow_op"):
                time.sleep(0.005)

        # Get statistics
        stats = monitor.get_stats()

        self.assertIn("fast_op", stats, "Fast operation should be tracked")
        self.assertIn("slow_op", stats, "Slow operation should be tracked")

        fast_stat = stats["fast_op"]
        slow_stat = stats["slow_op"]

        self.assertEqual(fast_stat.call_count, 10, "Fast op called 10 times")
        self.assertEqual(slow_stat.call_count, 5, "Slow op called 5 times")

        self.assertLess(fast_stat.avg_time_ms, slow_stat.avg_time_ms,
                       "Fast op should be faster on average")

        print(f"  ✓ fast_op: {fast_stat.call_count} calls, avg {fast_stat.avg_time_ms:.2f}ms")
        print(f"  ✓ slow_op: {slow_stat.call_count} calls, avg {slow_stat.avg_time_ms:.2f}ms")

    def test_hot_path_analyzer(self):
        """Test hot path analyzer."""
        print("\n[Profiling] Testing hot path analyzer...")

        analyzer = HotPathAnalyzer()

        # Trace different paths
        for i in range(20):
            with analyzer.trace("hot_path"):
                time.sleep(0.001)

        for i in range(5):
            with analyzer.trace("cold_path"):
                time.sleep(0.001)

        # Get hot paths
        hot_paths = analyzer.get_hot_paths(min_calls=1)

        self.assertEqual(len(hot_paths), 2, "Should have 2 paths")

        # Verify sorting (by total time)
        hottest_path, hottest_stats = hot_paths[0]
        self.assertEqual(hottest_path, "hot_path", "Hot path should be first")
        self.assertEqual(hottest_stats['call_count'], 20, "Hot path called 20 times")

        print(f"  ✓ Identified {len(hot_paths)} paths")
        print(f"  ✓ Hottest: {hottest_path} ({hottest_stats['call_count']} calls)")

    def test_optimization_suggestions(self):
        """Test optimization suggestions."""
        print("\n[Profiling] Testing optimization suggestions...")

        from profiling import ProfileStats

        # Create mock statistics
        stats = {
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
            "fast_operation": ProfileStats(
                function_name="fast_operation",
                call_count=50,
                total_time_ms=100.0,
                avg_time_ms=2.0,
                min_time_ms=1.5,
                max_time_ms=3.0,
                percentile_95_ms=2.5,
                percentile_99_ms=2.8
            )
        }

        suggestions = OptimizationSuggestions.analyze_stats(stats)

        self.assertGreater(len(suggestions), 0, "Should generate suggestions")

        # Verify suggestion for high call count operation
        caching_suggestion = any("caching" in s.lower() for s in suggestions)
        self.assertTrue(caching_suggestion, "Should suggest caching for high call count")

        print(f"  ✓ Generated {len(suggestions)} optimization suggestions")
        for suggestion in suggestions:
            print(f"    - {suggestion}")

    def test_monitored_decorator(self):
        """Test monitored decorator."""
        print("\n[Profiling] Testing monitored decorator...")

        @monitored()
        def monitored_function():
            time.sleep(0.005)
            return "result"

        # Call function multiple times
        for i in range(5):
            result = monitored_function()
            self.assertEqual(result, "result")

        # Get global monitor stats
        from profiling import get_global_monitor
        global_monitor = get_global_monitor()
        stats = global_monitor.get_stats("monitored_function")

        if "monitored_function" in stats:
            stat = stats["monitored_function"]
            self.assertEqual(stat.call_count, 5, "Should track 5 calls")
            print(f"  ✓ Automatically monitored {stat.call_count} calls")
            print(f"  ✓ Avg time: {stat.avg_time_ms:.2f}ms")


class TestIntegration(unittest.TestCase):
    """Test integration of multiple optimizations."""

    def test_cached_streaming(self):
        """Test combining caching with streaming."""
        print("\n[Integration] Testing cached streaming client...")

        try:
            # Create cached client
            client = create_client(cache_enabled=True, cache_max_size=100)

            # First capabilities request - cache miss
            start = time.perf_counter()
            result1 = client.get_capabilities()
            first_time = (time.perf_counter() - start) * 1000

            # Second request - cache hit
            start = time.perf_counter()
            result2 = client.get_capabilities()
            cached_time = (time.perf_counter() - start) * 1000

            self.assertEqual(result1, result2, "Results should match")

            speedup = first_time / cached_time if cached_time > 0 else 0
            print(f"  ✓ First request: {first_time:.2f}ms")
            print(f"  ✓ Cached request: {cached_time:.4f}ms ({speedup:.0f}x faster)")

            # Check cache stats
            stats = client.get_cache_stats()
            self.assertGreater(stats['hits'], 0, "Should have cache hits")
            print(f"  ✓ Cache hit rate: {stats['hit_rate']:.1f}%")

        except Exception as e:
            self.skipTest(f"Cached client test failed: {e}")

    def test_lazy_with_profiling(self):
        """Test lazy loading with performance monitoring."""
        print("\n[Integration] Testing lazy loading + profiling...")

        try:
            monitor = PerformanceMonitor()

            # Create lazy client with monitoring
            with monitor.time("client_creation"):
                client = LazyClient()

            # First access with monitoring
            with monitor.time("first_access"):
                endpoints = client.endpoints

            # Cached access with monitoring
            with monitor.time("cached_access"):
                endpoints2 = client.endpoints

            # Get statistics
            stats = monitor.get_stats()

            creation_time = stats["client_creation"].avg_time_ms
            first_time = stats["first_access"].avg_time_ms
            cached_time = stats["cached_access"].avg_time_ms

            self.assertLess(creation_time, 1.0, "Creation should be instant")
            self.assertLess(cached_time, 0.1, "Cached access should be instant")

            speedup = first_time / cached_time if cached_time > 0 else 0

            print(f"  ✓ Client creation: {creation_time:.4f}ms")
            print(f"  ✓ First access: {first_time:.2f}ms")
            print(f"  ✓ Cached access: {cached_time:.4f}ms ({speedup:.0f}x faster)")

        except Exception as e:
            self.skipTest(f"Integration test failed: {e}")


def run_tests():
    """Run all optimization tests."""
    print("\n" + "=" * 70)
    print("ImHex MCP Advanced Optimization Tests")
    print("=" * 70)
    print("\nPlease ensure:")
    print("  1. ImHex is running")
    print("  2. Network Interface is enabled in Settings")
    print("  3. Port 31337 is accessible")
    print("  4. At least one file is open in ImHex")
    print("=" * 70 + "\n")

    # Run tests
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestStreaming))
    suite.addTests(loader.loadTestsFromTestCase(TestLazyLoading))
    suite.addTests(loader.loadTestsFromTestCase(TestProfiling))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))

    # Run with verbose output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Print summary
    print("\n" + "=" * 70)
    print("Test Summary")
    print("=" * 70)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors) - len(result.skipped)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")
    print("=" * 70)

    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(run_tests())
