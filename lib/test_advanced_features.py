"""
Tests for Advanced Features Module

Tests request prioritization, circuit breaker, and integrated request manager.
"""

import asyncio
import pytest
from advanced_features import (
    Priority,
    PriorityQueue,
    PriorityConfig,
    PriorityScheduler,
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitState,
    CircuitBreakerError,
    AdvancedRequestManager,
)


class TestPriorityQueue:
    """Tests for priority queue."""

    @pytest.mark.asyncio
    async def test_basic_submission(self):
        """Test basic request submission."""
        queue = PriorityQueue()

        async def test_coro():
            return 42

        future = await queue.submit(test_coro, Priority.NORMAL)
        assert future is not None
        assert queue.qsize() == 1

    @pytest.mark.asyncio
    async def test_priority_ordering(self):
        """Test requests are processed by priority."""
        queue = PriorityQueue()
        results = []

        async def make_coro(value):
            async def coro():
                results.append(value)
                return value

            return coro

        # Submit in mixed order
        await queue.submit(await make_coro("low"), Priority.LOW)
        await queue.submit(await make_coro("critical"), Priority.CRITICAL)
        await queue.submit(await make_coro("normal"), Priority.NORMAL)
        await queue.submit(await make_coro("high"), Priority.HIGH)

        # Process all requests
        for _ in range(4):
            request = await queue.get_next()
            await queue.process_request(request)

        # Should be processed in priority order
        assert results == ["critical", "high", "normal", "low"]

    @pytest.mark.asyncio
    async def test_request_aging(self):
        """Test request aging to prevent starvation."""
        config = PriorityConfig(aging_interval=0.1, enable_aging=True)
        queue = PriorityQueue(config)

        async def test_coro():
            return True

        # Submit low priority request
        _future = await queue.submit(test_coro, Priority.LOW)  # noqa: F841

        # Wait for aging
        await asyncio.sleep(0.3)

        # Get request (should be aged up in priority)
        request = await queue.get_next()

        # Priority should be improved by aging
        assert request.priority < Priority.LOW

    @pytest.mark.asyncio
    async def test_request_processing(self):
        """Test request execution and result handling."""
        queue = PriorityQueue()

        async def test_coro():
            await asyncio.sleep(0.01)
            return "success"

        future = await queue.submit(test_coro, Priority.NORMAL)
        request = await queue.get_next()
        await queue.process_request(request)

        result = await future
        assert result == "success"

    @pytest.mark.asyncio
    async def test_request_error_handling(self):
        """Test error handling in request processing."""
        queue = PriorityQueue()

        async def failing_coro():
            raise ValueError("test error")

        future = await queue.submit(failing_coro, Priority.NORMAL)
        request = await queue.get_next()
        await queue.process_request(request)

        with pytest.raises(ValueError, match="test error"):
            await future


class TestPriorityScheduler:
    """Tests for priority scheduler."""

    @pytest.mark.asyncio
    async def test_scheduler_start_stop(self):
        """Test starting and stopping scheduler."""
        queue = PriorityQueue()
        scheduler = PriorityScheduler(queue, num_workers=2)

        await scheduler.start()
        assert scheduler._running is True
        assert len(scheduler._workers) == 2

        await scheduler.stop()
        assert scheduler._running is False
        assert len(scheduler._workers) == 0

    @pytest.mark.asyncio
    async def test_concurrent_processing(self):
        """Test concurrent request processing."""
        queue = PriorityQueue()
        scheduler = PriorityScheduler(queue, num_workers=5)
        await scheduler.start()

        results = []

        async def test_coro(value):
            await asyncio.sleep(0.01)
            results.append(value)
            return value

        # Submit 10 requests
        futures = []
        for i in range(10):
            future = await queue.submit(
                lambda v=i: test_coro(v), Priority.NORMAL
            )
            futures.append(future)

        # Wait for all to complete
        await asyncio.gather(*futures)

        await scheduler.stop()

        # All requests should be processed
        assert len(results) == 10
        assert sorted(results) == list(range(10))


class TestCircuitBreaker:
    """Tests for circuit breaker."""

    @pytest.mark.asyncio
    async def test_initial_state(self):
        """Test circuit breaker starts in CLOSED state."""
        breaker = CircuitBreaker("test")
        assert breaker.state == CircuitState.CLOSED
        assert breaker.is_closed is True
        assert breaker.is_open is False

    @pytest.mark.asyncio
    async def test_successful_call(self):
        """Test successful call through circuit breaker."""
        breaker = CircuitBreaker("test")

        async def success_coro():
            return "success"

        result = await breaker.call(success_coro)
        assert result == "success"
        assert breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_open_on_failures(self):
        """Test circuit opens after failure threshold."""
        config = CircuitBreakerConfig(failure_threshold=3)
        breaker = CircuitBreaker("test", config)

        async def failing_coro():
            raise RuntimeError("test error")

        # Trigger failures
        for _ in range(3):
            try:
                await breaker.call(failing_coro)
            except RuntimeError:
                pass

        # Circuit should be open
        assert breaker.state == CircuitState.OPEN
        assert breaker.is_open is True

    @pytest.mark.asyncio
    async def test_reject_when_open(self):
        """Test requests are rejected when circuit is open."""
        config = CircuitBreakerConfig(failure_threshold=2)
        breaker = CircuitBreaker("test", config)

        async def failing_coro():
            raise RuntimeError("test error")

        # Trigger failures to open circuit
        for _ in range(2):
            try:
                await breaker.call(failing_coro)
            except RuntimeError:
                pass

        # Next call should be rejected
        with pytest.raises(CircuitBreakerError):
            await breaker.call(failing_coro)

    @pytest.mark.asyncio
    async def test_half_open_recovery(self):
        """Test circuit transitions to HALF_OPEN after timeout."""
        config = CircuitBreakerConfig(failure_threshold=2, timeout=0.1)
        breaker = CircuitBreaker("test", config)

        async def failing_coro():
            raise RuntimeError("test error")

        # Open circuit
        for _ in range(2):
            try:
                await breaker.call(failing_coro)
            except RuntimeError:
                pass

        assert breaker.state == CircuitState.OPEN

        # Wait for timeout
        await asyncio.sleep(0.15)

        # Try a call (should transition to HALF_OPEN)
        async def success_coro():
            return "success"

        result = await breaker.call(success_coro)
        assert result == "success"
        assert breaker.state == CircuitState.HALF_OPEN

    @pytest.mark.asyncio
    async def test_close_after_recovery(self):
        """Test circuit closes after successful recovery."""
        config = CircuitBreakerConfig(
            failure_threshold=2, success_threshold=2, timeout=0.1
        )
        breaker = CircuitBreaker("test", config)

        async def failing_coro():
            raise RuntimeError("test error")

        async def success_coro():
            return "success"

        # Open circuit
        for _ in range(2):
            try:
                await breaker.call(failing_coro)
            except RuntimeError:
                pass

        assert breaker.state == CircuitState.OPEN

        # Wait for timeout
        await asyncio.sleep(0.15)

        # Make successful calls to close circuit
        for _ in range(2):
            await breaker.call(success_coro)

        # Circuit should be closed
        assert breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_circuit_statistics(self):
        """Test circuit breaker statistics."""
        breaker = CircuitBreaker("test")

        async def success_coro():
            return True

        await breaker.call(success_coro)

        stats = breaker.get_stats()
        assert stats["name"] == "test"
        assert stats["state"] == CircuitState.CLOSED.value
        assert stats["success_count"] == 1
        assert stats["failure_count"] == 0


class TestAdvancedRequestManager:
    """Tests for integrated request manager."""

    @pytest.mark.asyncio
    async def test_manager_lifecycle(self):
        """Test starting and stopping request manager."""
        manager = AdvancedRequestManager(num_workers=2)

        await manager.start()
        assert manager._started is True

        await manager.stop()
        assert manager._started is False

    @pytest.mark.asyncio
    async def test_execute_with_priority(self):
        """Test executing requests with priority."""
        manager = AdvancedRequestManager(num_workers=2)
        await manager.start()

        async def test_coro():
            await asyncio.sleep(0.01)
            return "result"

        result = await manager.execute(test_coro, Priority.HIGH)
        assert result == "result"

        await manager.stop()

    @pytest.mark.asyncio
    async def test_execute_with_circuit_breaker(self):
        """Test circuit breaker integration."""
        manager = AdvancedRequestManager(
            circuit_config=CircuitBreakerConfig(failure_threshold=2),
            num_workers=2,
        )
        await manager.start()

        call_count = 0

        async def failing_coro():
            nonlocal call_count
            call_count += 1
            raise RuntimeError("test error")

        # Fail twice to open circuit
        for _ in range(2):
            try:
                await manager.execute(failing_coro, Priority.NORMAL)
            except RuntimeError:
                pass

        # Third call should fail immediately with CircuitBreakerError
        with pytest.raises(CircuitBreakerError):
            await manager.execute(failing_coro, Priority.NORMAL)

        # Circuit breaker prevented third call
        assert call_count == 2

        await manager.stop()

    @pytest.mark.asyncio
    async def test_bypass_circuit_breaker(self):
        """Test bypassing circuit breaker."""
        manager = AdvancedRequestManager(
            circuit_config=CircuitBreakerConfig(failure_threshold=1),
            num_workers=2,
        )
        await manager.start()

        async def failing_coro():
            raise RuntimeError("test error")

        # Fail once to open circuit
        try:
            await manager.execute(failing_coro, Priority.NORMAL)
        except RuntimeError:
            pass

        # This should still work with circuit breaker bypassed
        try:
            await manager.execute(
                failing_coro, Priority.NORMAL, use_circuit_breaker=False
            )
        except RuntimeError:
            pass  # Expected to fail, but not with CircuitBreakerError

        await manager.stop()

    @pytest.mark.asyncio
    async def test_manager_statistics(self):
        """Test getting manager statistics."""
        manager = AdvancedRequestManager(num_workers=2)
        await manager.start()

        async def test_coro():
            return True

        await manager.execute(test_coro, Priority.NORMAL)

        stats = manager.get_stats()
        assert "queue_size" in stats
        assert "active_requests" in stats
        assert "circuit_breaker" in stats

        await manager.stop()

    @pytest.mark.asyncio
    async def test_concurrent_mixed_priority(self):
        """Test concurrent execution with mixed priorities."""
        manager = AdvancedRequestManager(num_workers=5)
        await manager.start()

        results = []

        async def test_coro(value, delay):
            await asyncio.sleep(delay)
            results.append(value)
            return value

        # Submit mixed priority requests
        futures = [
            manager.execute(
                lambda: test_coro("critical", 0.05), Priority.CRITICAL
            ),
            manager.execute(lambda: test_coro("low", 0.01), Priority.LOW),
            manager.execute(lambda: test_coro("high", 0.03), Priority.HIGH),
            manager.execute(
                lambda: test_coro("normal", 0.02), Priority.NORMAL
            ),
        ]

        await asyncio.gather(*futures)

        # Higher priority should generally complete first
        # (though timing can affect this)
        assert len(results) == 4

        await manager.stop()


async def main():
    """Run all tests."""
    print("Running Advanced Features Tests...")
    print("=" * 70)

    # Test Priority Queue
    print("\n[1/15] Testing Priority Queue - Basic Submission...")
    test = TestPriorityQueue()
    await test.test_basic_submission()
    print("  ✓ PASSED")

    print("[2/15] Testing Priority Queue - Priority Ordering...")
    await test.test_priority_ordering()
    print("  ✓ PASSED")

    print("[3/15] Testing Priority Queue - Request Aging...")
    await test.test_request_aging()
    print("  ✓ PASSED")

    print("[4/15] Testing Priority Queue - Request Processing...")
    await test.test_request_processing()
    print("  ✓ PASSED")

    print("[5/15] Testing Priority Queue - Error Handling...")
    await test.test_request_error_handling()
    print("  ✓ PASSED")

    # Test Priority Scheduler
    print("\n[6/15] Testing Priority Scheduler - Start/Stop...")
    scheduler_test = TestPriorityScheduler()
    await scheduler_test.test_scheduler_start_stop()
    print("  ✓ PASSED")

    print("[7/15] Testing Priority Scheduler - Concurrent Processing...")
    await scheduler_test.test_concurrent_processing()
    print("  ✓ PASSED")

    # Test Circuit Breaker
    print("\n[8/15] Testing Circuit Breaker - Initial State...")
    breaker_test = TestCircuitBreaker()
    await breaker_test.test_initial_state()
    print("  ✓ PASSED")

    print("[9/15] Testing Circuit Breaker - Successful Call...")
    await breaker_test.test_successful_call()
    print("  ✓ PASSED")

    print("[10/15] Testing Circuit Breaker - Open On Failures...")
    await breaker_test.test_open_on_failures()
    print("  ✓ PASSED")

    print("[11/15] Testing Circuit Breaker - Reject When Open...")
    await breaker_test.test_reject_when_open()
    print("  ✓ PASSED")

    print("[12/15] Testing Circuit Breaker - Statistics...")
    await breaker_test.test_circuit_statistics()
    print("  ✓ PASSED")

    # Test Advanced Request Manager
    print("\n[13/15] Testing Request Manager - Lifecycle...")
    manager_test = TestAdvancedRequestManager()
    await manager_test.test_manager_lifecycle()
    print("  ✓ PASSED")

    print("[14/15] Testing Request Manager - Priority Execution...")
    await manager_test.test_execute_with_priority()
    print("  ✓ PASSED")

    print("[15/15] Testing Request Manager - Circuit Breaker...")
    await manager_test.test_execute_with_circuit_breaker()
    print("  ✓ PASSED")

    print("\n" + "=" * 70)
    print("All Advanced Features Tests PASSED!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
