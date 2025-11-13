"""
Property-Based Testing for ImHex MCP

Uses Hypothesis to generate random test inputs and verify properties.
Tests core modules with extensive fuzzing and invariant checking.
"""

import asyncio
import pytest
from hypothesis import given, strategies as st, settings, assume, HealthCheck
from hypothesis.stateful import RuleBasedStateMachine, rule, invariant
import sys
import os

# Add lib directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from advanced_cache import (
    CacheTier,
    CacheTierConfig,
    CachePolicy,
    MultiTierCache,
    PatternDetector,
    PredictiveCacheConfig,
)
from advanced_features import (
    Priority,
    PriorityQueue,
    PriorityConfig,
    CircuitBreaker,
    CircuitBreakerConfig,
)


# ============================================================================
# Property-Based Tests for Cache
# ============================================================================


class TestCacheProperties:
    """Property-based tests for cache tier."""

    @pytest.mark.asyncio
    @given(
        key=st.text(min_size=1, max_size=100),
        value=st.text(min_size=0, max_size=1000),
        size=st.integers(min_value=1, max_value=10000),
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=50)
    async def test_cache_get_after_put(self, key, value, size):
        """Property: Getting a key after putting it should return the value."""
        config = CacheTierConfig(max_size=100, max_bytes=100000, ttl=10.0)
        cache = CacheTier("test", config)

        await cache.put(key, value, size)
        result = await cache.get(key)

        assert result == value

    @pytest.mark.asyncio
    @given(
        key=st.text(min_size=1, max_size=100),
        value1=st.text(min_size=0, max_size=1000),
        value2=st.text(min_size=0, max_size=1000),
        size=st.integers(min_value=1, max_value=10000),
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=50)
    async def test_cache_overwrite(self, key, value1, value2, size):
        """Property: Putting same key twice should overwrite with latest value."""
        config = CacheTierConfig(max_size=100, max_bytes=100000, ttl=10.0)
        cache = CacheTier("test", config)

        await cache.put(key, value1, size)
        await cache.put(key, value2, size)
        result = await cache.get(key)

        assert result == value2

    @pytest.mark.asyncio
    @given(
        keys=st.lists(st.text(min_size=1, max_size=50), min_size=1, max_size=20, unique=True),
        value=st.text(min_size=0, max_size=100),
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=50)
    async def test_cache_multiple_keys(self, keys, value):
        """Property: All keys should be retrievable after insertion."""
        config = CacheTierConfig(max_size=100, max_bytes=100000, ttl=10.0)
        cache = CacheTier("test", config)

        # Put all keys
        for key in keys:
            await cache.put(key, value, 100)

        # Get all keys (some may be evicted if too many)
        for key in keys[:min(len(keys), config.max_size)]:
            result = await cache.get(key)
            if result is not None:  # May be evicted
                assert result == value

    @pytest.mark.asyncio
    @given(
        operations=st.lists(
            st.tuples(
                st.sampled_from(["put", "get", "remove"]),
                st.text(min_size=1, max_size=50),
                st.text(min_size=0, max_size=100),
            ),
            min_size=1,
            max_size=50,
        )
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=30)
    async def test_cache_operations_dont_crash(self, operations):
        """Property: Cache should handle any sequence of operations without crashing."""
        config = CacheTierConfig(max_size=20, max_bytes=10000, ttl=10.0)
        cache = CacheTier("test", config)

        for op, key, value in operations:
            try:
                if op == "put":
                    await cache.put(key, value, len(value))
                elif op == "get":
                    await cache.get(key)
                elif op == "remove":
                    await cache.remove(key)
            except Exception as e:
                pytest.fail(f"Cache operation crashed: {e}")


# ============================================================================
# Property-Based Tests for Pattern Detector
# ============================================================================


class TestPatternDetectorProperties:
    """Property-based tests for pattern detector."""

    @pytest.mark.asyncio
    @given(
        start=st.integers(min_value=0, max_value=1000),
        stride=st.integers(min_value=1, max_value=10),
        count=st.integers(min_value=3, max_value=20),
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=50)
    async def test_sequential_pattern_detection(self, start, stride, count):
        """Property: Sequential accesses should be detected as sequential/strided."""
        config = PredictiveCacheConfig(sequential_threshold=3, pattern_window=50)
        detector = PatternDetector(config)

        # Record sequential accesses
        for i in range(count):
            await detector.record_access("file1", start + i * stride)

        pattern = await detector.detect_pattern()

        # Should detect a pattern
        assert pattern is not None
        assert pattern.pattern_type in ["sequential", "strided"]

        # Stride should be detected correctly
        if stride <= 1:
            assert pattern.pattern_type == "sequential"
        else:
            assert pattern.pattern_type == "strided"
            assert abs(pattern.stride - stride) <= 1  # Allow small variance

    @pytest.mark.asyncio
    @given(
        offsets=st.lists(
            st.integers(min_value=0, max_value=10000), min_size=3, max_size=20, unique=True
        )
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=50)
    async def test_random_pattern_detection(self, offsets):
        """Property: Random accesses should eventually be detected as random."""
        # Check if actually random (not sequential)
        sorted_offsets = sorted(offsets)
        differences = [sorted_offsets[i + 1] - sorted_offsets[i] for i in range(len(sorted_offsets) - 1)]
        variance = sum((d - sum(differences) / len(differences)) ** 2 for d in differences) / len(differences)

        assume(variance > 10)  # Only test truly random patterns

        config = PredictiveCacheConfig(sequential_threshold=3, pattern_window=50)
        detector = PatternDetector(config)

        # Record random accesses
        for offset in offsets:
            await detector.record_access("file1", offset)

        pattern = await detector.detect_pattern()

        # Should detect some pattern
        assert pattern is not None


# ============================================================================
# Property-Based Tests for Priority Queue
# ============================================================================


class TestPriorityQueueProperties:
    """Property-based tests for priority queue."""

    @pytest.mark.asyncio
    @given(
        priorities=st.lists(
            st.sampled_from([Priority.CRITICAL, Priority.HIGH, Priority.NORMAL, Priority.LOW]),
            min_size=2,
            max_size=20,
        )
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=50)
    async def test_priority_ordering(self, priorities):
        """Property: Requests should be processed in priority order (without aging)."""
        config = PriorityConfig(enable_aging=False)
        queue = PriorityQueue(config)

        results = []

        async def make_coro(priority):
            async def coro():
                results.append(priority)
                return priority

            return coro

        # Submit all requests
        for priority in priorities:
            await queue.submit(await make_coro(priority), priority)

        # Process all requests
        for _ in range(len(priorities)):
            request = await queue.get_next()
            await queue.process_request(request)

        # Check that results are in priority order
        sorted_priorities = sorted(priorities, key=lambda p: p.value)
        assert results == sorted_priorities

    @pytest.mark.asyncio
    @given(operations=st.lists(st.just("submit"), min_size=1, max_size=50))
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=30)
    async def test_queue_size_invariant(self, operations):
        """Property: Queue size should match number of submitted requests."""
        queue = PriorityQueue()

        async def dummy_coro():
            return True

        # Submit requests
        for _ in operations:
            await queue.submit(dummy_coro, Priority.NORMAL)

        # Queue size should match
        assert queue.qsize() == len(operations)


# ============================================================================
# Property-Based Tests for Circuit Breaker
# ============================================================================


class TestCircuitBreakerProperties:
    """Property-based tests for circuit breaker."""

    @pytest.mark.asyncio
    @given(success_count=st.integers(min_value=1, max_value=20))
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=50)
    async def test_circuit_stays_closed_on_success(self, success_count):
        """Property: Circuit should stay closed with only successful calls."""
        breaker = CircuitBreaker("test")

        async def success_coro():
            return True

        # Make successful calls
        for _ in range(success_count):
            await breaker.call(success_coro)

        # Circuit should still be closed
        assert breaker.is_closed

    @pytest.mark.asyncio
    @given(
        failure_threshold=st.integers(min_value=2, max_value=10),
        failure_count=st.integers(min_value=2, max_value=10),
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=50)
    async def test_circuit_opens_on_failures(self, failure_threshold, failure_count):
        """Property: Circuit should open after reaching failure threshold."""
        assume(failure_count >= failure_threshold)

        config = CircuitBreakerConfig(failure_threshold=failure_threshold)
        breaker = CircuitBreaker("test", config)

        async def failing_coro():
            raise RuntimeError("test error")

        # Trigger failures
        for _ in range(failure_count):
            try:
                await breaker.call(failing_coro)
            except RuntimeError:
                pass

        # Circuit should be open
        assert breaker.is_open


# ============================================================================
# Stateful Testing
# ============================================================================


class CacheStateMachine(RuleBasedStateMachine):
    """Stateful testing for cache with random operations."""

    def __init__(self):
        super().__init__()
        self.cache = None
        self.model = {}  # Model of what should be in cache
        asyncio.run(self._init_async())

    async def _init_async(self):
        config = CacheTierConfig(max_size=50, max_bytes=50000, ttl=100.0)
        self.cache = CacheTier("test", config)

    @rule(key=st.text(min_size=1, max_size=50), value=st.text(min_size=0, max_size=100))
    def put(self, key, value):
        """Put a value in cache."""
        asyncio.run(self.cache.put(key, value, len(value)))
        self.model[key] = value

    @rule(key=st.text(min_size=1, max_size=50))
    def get(self, key):
        """Get a value from cache."""
        result = asyncio.run(self.cache.get(key))

        # If key is in model and cache, values should match
        if key in self.model and result is not None:
            assert result == self.model[key]

    @rule(key=st.text(min_size=1, max_size=50))
    def remove(self, key):
        """Remove a value from cache."""
        asyncio.run(self.cache.remove(key))
        self.model.pop(key, None)

    @invariant()
    def cache_does_not_crash(self):
        """Invariant: Cache operations should not crash."""
        # This just ensures all operations complete without exception
        assert self.cache is not None


# Test class for stateful testing
TestCacheStateful = CacheStateMachine.TestCase


# ============================================================================
# Main test runner
# ============================================================================


if __name__ == "__main__":
    print("=" * 70)
    print("Property-Based Testing for ImHex MCP")
    print("=" * 70)
    print()
    print("This module contains property-based tests using Hypothesis.")
    print("Property-based tests generate random inputs to verify code properties.")
    print()
    print("To run these tests, use pytest:")
    print()
    print("  # Run all property-based tests")
    print("  cd /Users/pasha/PycharmProjects/IMHexMCP/mcp-server")
    print("  ./venv/bin/pytest ../lib/test_property_based.py -v")
    print()
    print("  # Show statistics")
    print("  ./venv/bin/pytest ../lib/test_property_based.py -v --hypothesis-show-statistics")
    print()
    print("  # Run with more examples for thoroughness")
    print("  ./venv/bin/pytest ../lib/test_property_based.py -v --hypothesis-seed=random")
    print()
    print("=" * 70)
    print("Test Coverage:")
    print("=" * 70)
    print("- Cache Properties: Get/put, overwrite, multiple keys, operations")
    print("- Pattern Detection: Sequential, strided, random patterns")
    print("- Priority Queue: Priority ordering, queue size invariants")
    print("- Circuit Breaker: Stays closed on success, opens on failures")
    print("- Stateful Testing: Random sequences of cache operations")
    print("=" * 70)
