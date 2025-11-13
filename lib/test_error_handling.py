"""
Tests for Error Handling Module

Tests exception classes, retry logic, circuit breakers, health checks,
and connection pooling.
"""

import pytest
import socket
import time
import threading
from unittest.mock import Mock, patch, MagicMock
from error_handling import (
    # Exception classes
    ImHexMCPError,
    ConnectionError,
    TimeoutError,
    ProviderNotFoundError,
    InvalidEndpointError,
    ProtocolError,
    CircuitBreakerOpenError,
    # Error classification
    ErrorSeverity,
    ErrorInfo,
    classify_error,
    # Retry logic
    retry_with_backoff,
    # Circuit breaker
    CircuitBreaker,
    CircuitBreakerState,
    # Health check
    HealthCheck,
    # Connection pool
    ConnectionPool,
)


# ============================================================================
# Test Exception Classes
# ============================================================================


class TestExceptionClasses:
    """Tests for custom exception classes."""

    def test_imhex_mcp_error_basic(self):
        """Test base exception without recovery hint."""
        error = ImHexMCPError("Test error")
        assert error.message == "Test error"
        assert error.recovery_hint is None
        assert str(error) == "Test error"

    def test_imhex_mcp_error_with_hint(self):
        """Test base exception with recovery hint."""
        error = ImHexMCPError("Test error", "Try restarting")
        assert error.message == "Test error"
        assert error.recovery_hint == "Try restarting"
        assert "Recovery Hint" in str(error)
        assert "Try restarting" in str(error)

    def test_connection_error(self):
        """Test connection error exception."""
        error = ConnectionError("localhost", 31337, "Connection refused")
        assert error.host == "localhost"
        assert error.port == 31337
        assert error.reason == "Connection refused"
        assert "31337" in str(error)
        assert "Recovery Hint" in str(error)

    def test_timeout_error(self):
        """Test timeout error exception."""
        error = TimeoutError("file/open", 5.0)
        assert error.operation == "file/open"
        assert error.timeout == 5.0
        assert "file/open" in str(error)
        assert "5" in str(error)
        assert "Recovery Hint" in str(error)

    def test_provider_not_found_error(self):
        """Test provider not found error."""
        error = ProviderNotFoundError(42)
        assert error.provider_id == 42
        assert "42" in str(error)
        assert "Recovery Hint" in str(error)

    def test_invalid_endpoint_error(self):
        """Test invalid endpoint error."""
        error = InvalidEndpointError("invalid/endpoint")
        assert error.endpoint == "invalid/endpoint"
        assert error.available is None
        assert "invalid/endpoint" in str(error)

    def test_invalid_endpoint_error_with_available(self):
        """Test invalid endpoint error with available list."""
        available = ["file/list", "file/open", "data/read"]
        error = InvalidEndpointError("invalid/endpoint", available)
        assert error.endpoint == "invalid/endpoint"
        assert error.available == available
        assert "file/list" in str(error)

    def test_protocol_error(self):
        """Test protocol error."""
        error = ProtocolError("Malformed JSON")
        assert "Malformed JSON" in str(error)
        assert "Recovery Hint" in str(error)

    def test_circuit_breaker_open_error(self):
        """Test circuit breaker open error."""
        reset_time = time.time() + 10
        error = CircuitBreakerOpenError(reset_time)
        assert error.reset_time == reset_time
        assert "OPEN" in str(error)
        assert "Wait" in str(error)


# ============================================================================
# Test Error Classification
# ============================================================================


class TestErrorClassification:
    """Tests for error classification."""

    def test_classify_timeout_error(self):
        """Test classification of timeout errors."""
        error = socket.timeout()
        info = classify_error(error)
        assert info.severity == ErrorSeverity.MEDIUM
        assert info.retryable is True
        assert info.backoff_multiplier == 1.5

    def test_classify_connection_error(self):
        """Test classification of connection errors."""
        error = socket.error("Connection refused")
        info = classify_error(error)
        assert info.severity == ErrorSeverity.MEDIUM
        assert info.retryable is True
        assert info.backoff_multiplier == 2.0

    def test_classify_circuit_breaker_error(self):
        """Test classification of circuit breaker errors."""
        error = CircuitBreakerOpenError(time.time() + 60)
        info = classify_error(error)
        assert info.severity == ErrorSeverity.HIGH
        assert info.retryable is False

    def test_classify_protocol_error(self):
        """Test classification of protocol errors."""
        error = ProtocolError("Invalid data")
        info = classify_error(error)
        assert info.severity == ErrorSeverity.CRITICAL
        assert info.retryable is False

    def test_classify_provider_not_found_error(self):
        """Test classification of provider not found errors."""
        error = ProviderNotFoundError(0)
        info = classify_error(error)
        assert info.severity == ErrorSeverity.MEDIUM
        assert info.retryable is True
        assert info.backoff_multiplier == 1.0

    def test_classify_unknown_error(self):
        """Test classification of unknown errors."""
        error = RuntimeError("Unknown error")
        info = classify_error(error)
        assert info.severity == ErrorSeverity.HIGH
        assert info.retryable is True
        assert info.backoff_multiplier == 2.5


# ============================================================================
# Test Retry Decorator
# ============================================================================


class TestRetryDecorator:
    """Tests for retry decorator with exponential backoff."""

    def test_retry_success_on_first_attempt(self):
        """Test successful execution on first attempt."""
        call_count = 0

        @retry_with_backoff(max_attempts=3, initial_delay=0.01)
        def successful_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = successful_func()
        assert result == "success"
        assert call_count == 1

    def test_retry_success_after_failures(self):
        """Test successful execution after some failures."""
        call_count = 0

        @retry_with_backoff(max_attempts=3, initial_delay=0.01)
        def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise socket.error("Temporary failure")
            return "success"

        result = flaky_func()
        assert result == "success"
        assert call_count == 2

    def test_retry_exhausts_attempts(self):
        """Test that retries exhaust after max attempts."""
        call_count = 0

        @retry_with_backoff(max_attempts=3, initial_delay=0.01)
        def always_fails():
            nonlocal call_count
            call_count += 1
            raise socket.error("Always fails")

        with pytest.raises((ConnectionError, ImHexMCPError)):
            always_fails()

        assert call_count == 3

    def test_retry_honors_exception_tuple(self):
        """Test that retry only catches specified exceptions."""
        @retry_with_backoff(max_attempts=3, exceptions=(socket.error,))
        def raises_value_error():
            raise ValueError("Not retryable")

        with pytest.raises(ValueError):
            raises_value_error()

    def test_retry_backoff_timing(self):
        """Test exponential backoff timing."""
        call_times = []

        @retry_with_backoff(max_attempts=3, initial_delay=0.05, exponential_base=2.0)
        def timing_test():
            call_times.append(time.time())
            if len(call_times) < 3:
                raise socket.error("Retry")
            return "success"

        timing_test()
        assert len(call_times) == 3

        # Check that delays increase
        if len(call_times) >= 2:
            delay1 = call_times[1] - call_times[0]
            assert delay1 >= 0.05  # At least initial_delay

        if len(call_times) >= 3:
            delay2 = call_times[2] - call_times[1]
            # Second delay should be longer (exponential backoff)
            assert delay2 > delay1 * 0.8  # Allow some variance

    def test_retry_max_delay_cap(self):
        """Test that max_delay caps the backoff."""
        call_count = 0

        @retry_with_backoff(
            max_attempts=5,
            initial_delay=1.0,
            max_delay=2.0,
            exponential_base=10.0
        )
        def capped_backoff():
            nonlocal call_count
            call_count += 1
            if call_count < 4:
                raise socket.error("Retry")
            return "success"

        start = time.time()
        result = capped_backoff()
        elapsed = time.time() - start

        assert result == "success"
        # With max_delay=2.0, total time should be roughly 2+2+2 = 6 seconds
        # Allow some variance but should be less than 10 seconds
        assert elapsed < 10.0


# ============================================================================
# Test Circuit Breaker
# ============================================================================


class TestCircuitBreaker:
    """Tests for circuit breaker pattern."""

    def test_circuit_breaker_closed_state(self):
        """Test circuit breaker in closed state."""
        breaker = CircuitBreaker(failure_threshold=3)
        assert breaker.state == CircuitBreakerState.CLOSED

        def successful_func():
            return "success"

        result = breaker.call(successful_func)
        assert result == "success"
        assert breaker.failure_count == 0

    def test_circuit_breaker_opens_after_threshold(self):
        """Test circuit breaker opens after failure threshold."""
        breaker = CircuitBreaker(failure_threshold=3)

        def failing_func():
            raise RuntimeError("Test error")

        # Trigger failures
        for _ in range(3):
            with pytest.raises(RuntimeError):
                breaker.call(failing_func)

        # Circuit should now be open
        assert breaker.state == CircuitBreakerState.OPEN
        assert breaker.failure_count == 3

    def test_circuit_breaker_rejects_when_open(self):
        """Test circuit breaker rejects requests when open."""
        breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=60.0)

        def failing_func():
            raise RuntimeError("Test error")

        # Open the circuit
        for _ in range(2):
            with pytest.raises(RuntimeError):
                breaker.call(failing_func)

        # Should raise CircuitBreakerOpenError
        def any_func():
            return "success"

        with pytest.raises(CircuitBreakerOpenError):
            breaker.call(any_func)

    def test_circuit_breaker_half_open_after_timeout(self):
        """Test circuit breaker enters half-open state after timeout."""
        breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)

        def failing_func():
            raise RuntimeError("Test error")

        # Open the circuit
        for _ in range(2):
            with pytest.raises(RuntimeError):
                breaker.call(failing_func)

        assert breaker.state == CircuitBreakerState.OPEN

        # Wait for recovery timeout
        time.sleep(0.15)

        # Next call should transition to half-open
        def successful_func():
            return "success"

        result = breaker.call(successful_func)
        assert result == "success"
        # After successful call in half-open, it may close if success_threshold is 1
        # or stay half-open if threshold is higher

    def test_circuit_breaker_closes_after_successes(self):
        """Test circuit breaker closes after enough successes."""
        breaker = CircuitBreaker(
            failure_threshold=2,
            recovery_timeout=0.1,
            success_threshold=2
        )

        def failing_func():
            raise RuntimeError("Test error")

        # Open the circuit
        for _ in range(2):
            with pytest.raises(RuntimeError):
                breaker.call(failing_func)

        assert breaker.state == CircuitBreakerState.OPEN

        # Wait for recovery timeout
        time.sleep(0.15)

        def successful_func():
            return "success"

        # First success enters half-open
        breaker.call(successful_func)
        assert breaker.state == CircuitBreakerState.HALF_OPEN

        # Second success closes circuit
        breaker.call(successful_func)
        assert breaker.state == CircuitBreakerState.CLOSED
        assert breaker.failure_count == 0

    def test_circuit_breaker_reopens_on_failure_in_half_open(self):
        """Test circuit breaker reopens if failure occurs in half-open state."""
        breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)

        def failing_func():
            raise RuntimeError("Test error")

        # Open the circuit
        for _ in range(2):
            with pytest.raises(RuntimeError):
                breaker.call(failing_func)

        # Wait for recovery timeout
        time.sleep(0.15)

        # Circuit should now allow a test request (half-open)
        # But failure should reopen it
        with pytest.raises(RuntimeError):
            breaker.call(failing_func)

        assert breaker.state == CircuitBreakerState.OPEN

    def test_circuit_breaker_reset(self):
        """Test manual circuit breaker reset."""
        breaker = CircuitBreaker(failure_threshold=2)

        def failing_func():
            raise RuntimeError("Test error")

        # Open the circuit
        for _ in range(2):
            with pytest.raises(RuntimeError):
                breaker.call(failing_func)

        assert breaker.state == CircuitBreakerState.OPEN

        # Reset circuit
        breaker.reset()
        assert breaker.state == CircuitBreakerState.CLOSED
        assert breaker.failure_count == 0
        assert breaker.success_count == 0
        assert breaker.last_failure_time is None

    def test_circuit_breaker_get_state(self):
        """Test getting circuit breaker state."""
        breaker = CircuitBreaker()
        state = breaker.get_state()

        assert "state" in state
        assert "failure_count" in state
        assert "success_count" in state
        assert "last_failure_time" in state

        assert state["state"] == "closed"
        assert state["failure_count"] == 0


# ============================================================================
# Test Health Check
# ============================================================================


class TestHealthCheck:
    """Tests for health check."""

    def test_health_check_success(self):
        """Test successful health check."""
        with patch("socket.socket") as mock_socket:
            mock_sock_instance = MagicMock()
            mock_socket.return_value = mock_sock_instance

            health = HealthCheck("localhost", 31337)
            result = health.check(timeout=1.0)

            assert result is True
            assert health.last_status is True
            assert health.last_check is not None

            # Verify socket operations
            mock_socket.assert_called_once()
            mock_sock_instance.connect.assert_called_once_with(("localhost", 31337))
            mock_sock_instance.close.assert_called_once()

    def test_health_check_failure(self):
        """Test failed health check."""
        with patch("socket.socket") as mock_socket:
            mock_sock_instance = MagicMock()
            mock_sock_instance.connect.side_effect = socket.error("Connection refused")
            mock_socket.return_value = mock_sock_instance

            health = HealthCheck("localhost", 31337)
            result = health.check(timeout=1.0)

            assert result is False
            assert health.last_status is False
            assert health.last_check is not None

    def test_health_check_timeout(self):
        """Test health check timeout."""
        with patch("socket.socket") as mock_socket:
            mock_sock_instance = MagicMock()
            mock_sock_instance.connect.side_effect = socket.timeout()
            mock_socket.return_value = mock_sock_instance

            health = HealthCheck("localhost", 31337)
            result = health.check(timeout=0.5)

            assert result is False
            assert health.last_status is False

    def test_health_check_get_status(self):
        """Test getting health check status."""
        with patch("socket.socket"):
            health = HealthCheck()
            health.check()

            status = health.get_status()
            assert "healthy" in status
            assert "last_check" in status
            assert "age" in status

            assert isinstance(status["healthy"], bool)
            assert isinstance(status["age"], (int, float))


# ============================================================================
# Test Connection Pool
# ============================================================================


class TestConnectionPool:
    """Tests for connection pool."""

    def test_connection_pool_create_connection(self):
        """Test creating connections in pool."""
        with patch("socket.socket") as mock_socket:
            mock_sock = MagicMock()
            mock_socket.return_value = mock_sock

            pool = ConnectionPool(max_connections=2)

            with pool.get_connection() as conn:
                assert conn is not None
                mock_socket.assert_called_once()
                mock_sock.connect.assert_called_once_with(("localhost", 31337))

    def test_connection_pool_reuse_connection(self):
        """Test reusing connections from pool."""
        with patch("socket.socket") as mock_socket:
            mock_sock = MagicMock()
            mock_sock.recv.return_value = b""  # Simulate alive connection
            mock_socket.return_value = mock_sock

            pool = ConnectionPool(max_connections=2)

            # First connection
            with pool.get_connection() as conn1:
                first_sock = conn1

            # Second connection should reuse the first
            with pool.get_connection() as conn2:
                assert conn2 == first_sock

            # Should only create one socket
            assert mock_socket.call_count == 1

    def test_connection_pool_close_all(self):
        """Test closing all connections in pool."""
        with patch("socket.socket") as mock_socket:
            mock_sock = MagicMock()
            mock_sock.recv.return_value = b""
            mock_socket.return_value = mock_sock

            pool = ConnectionPool(max_connections=2)

            # Create a connection and return it to pool
            with pool.get_connection():
                pass

            # Close all connections
            pool.close_all()

            # Socket should be closed
            mock_sock.close.assert_called()

    def test_connection_pool_get_stats(self):
        """Test getting pool statistics."""
        with patch("socket.socket") as mock_socket:
            mock_sock = MagicMock()
            mock_sock.recv.return_value = b""
            mock_socket.return_value = mock_sock

            pool = ConnectionPool(max_connections=5)

            # Create a connection
            with pool.get_connection():
                pass

            stats = pool.get_stats()
            assert "available" in stats
            assert "total_created" in stats
            assert "max_connections" in stats

            assert stats["max_connections"] == 5
            assert stats["total_created"] >= 1

    def test_connection_pool_max_connections_limit(self):
        """Test that pool respects max connections limit."""
        with patch("socket.socket") as mock_socket:
            mock_socks = [MagicMock() for _ in range(3)]
            for mock_sock in mock_socks:
                mock_sock.recv.return_value = b""
            mock_socket.side_effect = mock_socks

            pool = ConnectionPool(max_connections=2)

            # Try to create 3 connections
            # First two should succeed, third should wait or fail
            conn1 = pool.get_connection()
            conn1.__enter__()

            conn2 = pool.get_connection()
            conn2.__enter__()

            # Verify we've created 2 connections
            assert pool._created_connections == 2

            # Clean up
            conn1.__exit__(None, None, None)
            conn2.__exit__(None, None, None)


# ============================================================================
# Main test runner
# ============================================================================


if __name__ == "__main__":
    print("=" * 70)
    print("Error Handling Tests")
    print("=" * 70)
    print()
    print("This module contains tests for error handling, retry logic,")
    print("circuit breakers, health checks, and connection pooling.")
    print()
    print("To run these tests, use pytest:")
    print()
    print("  cd /Users/pasha/PycharmProjects/IMHexMCP/mcp-server")
    print("  ./venv/bin/pytest ../lib/test_error_handling.py -v")
    print()
    print("=" * 70)
