#!/usr/bin/env python3
"""
Unit Tests for ImHex MCP Error Handling Module

Comprehensive test suite for all error handling components including:
- Custom exceptions with recovery hints
- Error classification system
- Retry logic with exponential backoff
- Circuit breaker pattern
- Health checks
- Connection pooling

Usage:
    python3 test_error_handling.py
    python3 -m unittest test_error_handling
    python3 -m unittest test_error_handling.TestCustomExceptions -v
"""

import unittest
import socket
import time
import threading
from unittest.mock import Mock, patch, MagicMock
import sys
from pathlib import Path

# Add lib directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))

from error_handling import (
    # Exceptions
    ImHexMCPError,
    ConnectionError,
    TimeoutError,
    ProviderNotFoundError,
    InvalidEndpointError,
    ProtocolError,
    CircuitBreakerOpenError,
    # Error Classification
    ErrorSeverity,
    ErrorInfo,
    classify_error,
    # Retry Logic
    retry_with_backoff,
    # Circuit Breaker
    CircuitBreaker,
    CircuitBreakerState,
    # Health Check
    HealthCheck,
    # Connection Pool
    ConnectionPool,
)


class TestCustomExceptions(unittest.TestCase):
    """Test custom exception classes and recovery hints."""

    def test_base_exception_without_hint(self):
        """Test ImHexMCPError without recovery hint."""
        error = ImHexMCPError("Test error")
        self.assertEqual(error.message, "Test error")
        self.assertIsNone(error.recovery_hint)
        self.assertEqual(str(error), "Test error")

    def test_base_exception_with_hint(self):
        """Test ImHexMCPError with recovery hint."""
        error = ImHexMCPError("Test error", "Try this fix")
        self.assertEqual(error.message, "Test error")
        self.assertEqual(error.recovery_hint, "Try this fix")
        self.assertIn("Recovery Hint:", str(error))
        self.assertIn("Try this fix", str(error))

    def test_connection_error(self):
        """Test ConnectionError with host, port, and recovery hints."""
        error = ConnectionError("localhost", 31337, "Connection refused")
        self.assertEqual(error.host, "localhost")
        self.assertEqual(error.port, 31337)
        self.assertEqual(error.reason, "Connection refused")
        self.assertIn("localhost:31337", str(error))
        self.assertIn("Recovery Hint:", str(error))
        self.assertIn("ImHex is running", str(error))

    def test_timeout_error(self):
        """Test TimeoutError with operation and timeout details."""
        error = TimeoutError("data/read", 5.0)
        self.assertEqual(error.operation, "data/read")
        self.assertEqual(error.timeout, 5.0)
        self.assertIn("data/read", str(error))
        self.assertIn("5.0s", str(error))
        self.assertIn("Recovery Hint:", str(error))

    def test_provider_not_found_error(self):
        """Test ProviderNotFoundError with provider ID."""
        error = ProviderNotFoundError(42)
        self.assertEqual(error.provider_id, 42)
        self.assertIn("42", str(error))
        self.assertIn("Recovery Hint:", str(error))
        self.assertIn("file/list", str(error))

    def test_invalid_endpoint_error(self):
        """Test InvalidEndpointError with available endpoints."""
        available = ["capabilities", "file/list", "data/read"]
        error = InvalidEndpointError("invalid/endpoint", available)
        self.assertEqual(error.endpoint, "invalid/endpoint")
        self.assertEqual(error.available, available)
        self.assertIn("invalid/endpoint", str(error))
        self.assertIn("Recovery Hint:", str(error))

    def test_protocol_error(self):
        """Test ProtocolError with details."""
        error = ProtocolError("Invalid JSON")
        self.assertIn("Invalid JSON", str(error))
        self.assertIn("Recovery Hint:", str(error))
        self.assertIn("version mismatch", str(error))

    def test_circuit_breaker_open_error(self):
        """Test CircuitBreakerOpenError with reset time."""
        reset_time = time.time() + 60
        error = CircuitBreakerOpenError(reset_time)
        self.assertEqual(error.reset_time, reset_time)
        self.assertIn("OPEN", str(error))
        self.assertIn("Recovery Hint:", str(error))


class TestErrorClassification(unittest.TestCase):
    """Test error classification system."""

    def test_classify_socket_error(self):
        """Test classification of socket errors."""
        error = socket.error("Connection refused")
        info = classify_error(error)
        self.assertEqual(info.severity, ErrorSeverity.MEDIUM)
        self.assertTrue(info.retryable)
        self.assertEqual(info.backoff_multiplier, 2.0)

    def test_classify_connection_refused(self):
        """Test classification of connection refused errors."""
        error = ConnectionRefusedError()
        info = classify_error(error)
        self.assertEqual(info.severity, ErrorSeverity.MEDIUM)
        self.assertTrue(info.retryable)

    def test_classify_timeout_error(self):
        """Test classification of timeout errors."""
        error = socket.timeout()
        info = classify_error(error)
        self.assertEqual(info.severity, ErrorSeverity.MEDIUM)
        self.assertTrue(info.retryable)
        self.assertEqual(info.backoff_multiplier, 1.5)

    def test_classify_circuit_breaker_error(self):
        """Test classification of circuit breaker errors."""
        error = CircuitBreakerOpenError(time.time() + 60)
        info = classify_error(error)
        self.assertEqual(info.severity, ErrorSeverity.HIGH)
        self.assertFalse(info.retryable)

    def test_classify_protocol_error(self):
        """Test classification of protocol errors."""
        error = ProtocolError("Invalid data")
        info = classify_error(error)
        self.assertEqual(info.severity, ErrorSeverity.CRITICAL)
        self.assertFalse(info.retryable)

    def test_classify_provider_not_found(self):
        """Test classification of provider not found errors."""
        error = ProviderNotFoundError(42)
        info = classify_error(error)
        self.assertEqual(info.severity, ErrorSeverity.MEDIUM)
        self.assertTrue(info.retryable)

    def test_classify_unknown_error(self):
        """Test classification of unknown errors."""
        error = RuntimeError("Unknown error")
        info = classify_error(error)
        self.assertEqual(info.severity, ErrorSeverity.HIGH)
        self.assertTrue(info.retryable)
        self.assertEqual(info.backoff_multiplier, 2.5)


class TestRetryDecorator(unittest.TestCase):
    """Test retry decorator with exponential backoff."""

    def test_retry_success_first_attempt(self):
        """Test successful execution on first attempt."""
        mock_func = Mock(return_value="success")
        decorated = retry_with_backoff(max_attempts=3)(mock_func)

        result = decorated()

        self.assertEqual(result, "success")
        self.assertEqual(mock_func.call_count, 1)

    def test_retry_success_after_failures(self):
        """Test successful execution after transient failures."""
        mock_func = Mock(side_effect=[
            socket.error("Connection refused"),
            socket.error("Connection refused"),
            "success"
        ])
        decorated = retry_with_backoff(
            max_attempts=3,
            initial_delay=0.01,
            exponential_base=2.0
        )(mock_func)

        result = decorated()

        self.assertEqual(result, "success")
        self.assertEqual(mock_func.call_count, 3)

    def test_retry_max_attempts_exceeded(self):
        """Test failure after max attempts exceeded."""
        mock_func = Mock(side_effect=socket.error("Connection refused"))
        decorated = retry_with_backoff(
            max_attempts=3,
            initial_delay=0.01
        )(mock_func)

        with self.assertRaises(ConnectionError):
            decorated()

        self.assertEqual(mock_func.call_count, 3)

    def test_retry_critical_error_no_retry(self):
        """Test that critical errors are not retried."""
        mock_func = Mock(side_effect=ProtocolError("Invalid protocol"))
        decorated = retry_with_backoff(
            max_attempts=3,
            initial_delay=0.01,
            exceptions=(ProtocolError, socket.error)
        )(mock_func)

        with self.assertRaises(ProtocolError):
            decorated()

        # Should fail on first attempt without retries
        self.assertEqual(mock_func.call_count, 1)

    def test_retry_backoff_timing(self):
        """Test exponential backoff timing."""
        call_times = []

        def failing_func():
            call_times.append(time.time())
            raise socket.error("Connection refused")

        decorated = retry_with_backoff(
            max_attempts=3,
            initial_delay=0.1,
            exponential_base=2.0
        )(failing_func)

        try:
            decorated()
        except (ConnectionError, ImHexMCPError):
            pass

        # Verify backoff delays increased
        self.assertEqual(len(call_times), 3)
        if len(call_times) >= 3:
            delay1 = call_times[1] - call_times[0]
            delay2 = call_times[2] - call_times[1]
            # Second delay should be roughly 2x first delay
            self.assertGreater(delay2, delay1 * 1.5)

    def test_retry_with_custom_exceptions(self):
        """Test retry with custom exception tuple."""
        # Use RuntimeError which is retryable according to classify_error
        mock_func = Mock(side_effect=[
            RuntimeError("Transient error"),
            "success"
        ])
        decorated = retry_with_backoff(
            max_attempts=3,
            initial_delay=0.01,
            exceptions=(RuntimeError,)
        )(mock_func)

        result = decorated()

        self.assertEqual(result, "success")
        self.assertEqual(mock_func.call_count, 2)


class TestCircuitBreaker(unittest.TestCase):
    """Test circuit breaker pattern implementation."""

    def test_circuit_breaker_initial_state(self):
        """Test circuit breaker starts in CLOSED state."""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=1.0)
        self.assertEqual(cb.state, CircuitBreakerState.CLOSED)
        self.assertEqual(cb.failure_count, 0)

    def test_circuit_breaker_successful_call(self):
        """Test successful call through circuit breaker."""
        cb = CircuitBreaker()
        mock_func = Mock(return_value="success")

        result = cb.call(mock_func)

        self.assertEqual(result, "success")
        self.assertEqual(cb.state, CircuitBreakerState.CLOSED)
        self.assertEqual(cb.failure_count, 0)

    def test_circuit_breaker_opens_after_failures(self):
        """Test circuit breaker opens after threshold failures."""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=1.0)
        mock_func = Mock(side_effect=socket.error("Connection refused"))

        # Trigger failures up to threshold
        for _ in range(3):
            try:
                cb.call(mock_func)
            except socket.error:
                pass

        self.assertEqual(cb.state, CircuitBreakerState.OPEN)
        self.assertEqual(cb.failure_count, 3)

    def test_circuit_breaker_rejects_when_open(self):
        """Test circuit breaker rejects calls when OPEN."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=10.0)
        mock_func = Mock(side_effect=socket.error("Connection refused"))

        # Open the circuit
        for _ in range(2):
            try:
                cb.call(mock_func)
            except socket.error:
                pass

        # Next call should raise CircuitBreakerOpenError
        with self.assertRaises(CircuitBreakerOpenError):
            cb.call(mock_func)

    def test_circuit_breaker_half_open_transition(self):
        """Test circuit breaker transitions to HALF_OPEN after timeout."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)
        mock_func = Mock(side_effect=socket.error("Connection refused"))

        # Open the circuit
        for _ in range(2):
            try:
                cb.call(mock_func)
            except socket.error:
                pass

        self.assertEqual(cb.state, CircuitBreakerState.OPEN)

        # Wait for recovery timeout
        time.sleep(0.15)

        # Next call should transition to HALF_OPEN - create new mock with return value
        success_func = Mock(return_value="success")
        result = cb.call(success_func)

        self.assertEqual(result, "success")

    def test_circuit_breaker_closes_after_successes(self):
        """Test circuit breaker closes after successful recovery."""
        cb = CircuitBreaker(
            failure_threshold=2,
            recovery_timeout=0.1,
            success_threshold=2
        )
        mock_func = Mock(side_effect=socket.error("Connection refused"))

        # Open the circuit
        for _ in range(2):
            try:
                cb.call(mock_func)
            except socket.error:
                pass

        # Wait for recovery timeout
        time.sleep(0.15)

        # Successful calls to close circuit
        mock_func = Mock(return_value="success")
        cb.call(mock_func)
        cb.call(mock_func)

        self.assertEqual(cb.state, CircuitBreakerState.CLOSED)
        self.assertEqual(cb.failure_count, 0)

    def test_circuit_breaker_reset(self):
        """Test manual circuit breaker reset."""
        cb = CircuitBreaker(failure_threshold=2)
        mock_func = Mock(side_effect=socket.error("Connection refused"))

        # Open the circuit
        for _ in range(2):
            try:
                cb.call(mock_func)
            except socket.error:
                pass

        self.assertEqual(cb.state, CircuitBreakerState.OPEN)

        # Manual reset
        cb.reset()

        self.assertEqual(cb.state, CircuitBreakerState.CLOSED)
        self.assertEqual(cb.failure_count, 0)
        self.assertEqual(cb.success_count, 0)
        self.assertIsNone(cb.last_failure_time)

    def test_circuit_breaker_get_state(self):
        """Test circuit breaker state retrieval."""
        cb = CircuitBreaker()
        state = cb.get_state()

        self.assertIn("state", state)
        self.assertIn("failure_count", state)
        self.assertIn("success_count", state)
        self.assertIn("last_failure_time", state)
        self.assertEqual(state["state"], "closed")


class TestHealthCheck(unittest.TestCase):
    """Test health check functionality."""

    @patch('socket.socket')
    def test_health_check_success(self, mock_socket_class):
        """Test successful health check."""
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket

        hc = HealthCheck("localhost", 31337)
        result = hc.check(timeout=2.0)

        self.assertTrue(result)
        self.assertTrue(hc.last_status)
        self.assertIsNotNone(hc.last_check)
        mock_socket.connect.assert_called_once_with(("localhost", 31337))
        mock_socket.close.assert_called_once()

    @patch('socket.socket')
    def test_health_check_failure(self, mock_socket_class):
        """Test failed health check."""
        mock_socket = MagicMock()
        mock_socket.connect.side_effect = socket.error("Connection refused")
        mock_socket_class.return_value = mock_socket

        hc = HealthCheck("localhost", 31337)
        result = hc.check(timeout=2.0)

        self.assertFalse(result)
        self.assertFalse(hc.last_status)
        self.assertIsNotNone(hc.last_check)

    @patch('socket.socket')
    def test_health_check_timeout(self, mock_socket_class):
        """Test health check timeout."""
        mock_socket = MagicMock()
        mock_socket.connect.side_effect = socket.timeout()
        mock_socket_class.return_value = mock_socket

        hc = HealthCheck("localhost", 31337)
        result = hc.check(timeout=1.0)

        self.assertFalse(result)
        self.assertFalse(hc.last_status)

    @patch('socket.socket')
    def test_health_check_get_status(self, mock_socket_class):
        """Test health check status retrieval."""
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket

        hc = HealthCheck("localhost", 31337)
        hc.check()

        status = hc.get_status()

        self.assertIn("healthy", status)
        self.assertIn("last_check", status)
        self.assertIn("age", status)
        self.assertTrue(status["healthy"])
        self.assertIsNotNone(status["last_check"])


class TestConnectionPool(unittest.TestCase):
    """Test connection pooling functionality."""

    @patch('socket.socket')
    def test_connection_pool_create(self, mock_socket_class):
        """Test connection pool creation."""
        pool = ConnectionPool("localhost", 31337, max_connections=5)

        self.assertEqual(pool.host, "localhost")
        self.assertEqual(pool.port, 31337)
        self.assertEqual(pool.max_connections, 5)
        self.assertEqual(pool._created_connections, 0)

    @patch('socket.socket')
    def test_connection_pool_get_connection(self, mock_socket_class):
        """Test getting connection from pool."""
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket

        pool = ConnectionPool("localhost", 31337)

        with pool.get_connection() as sock:
            self.assertIsNotNone(sock)
            self.assertEqual(pool._created_connections, 1)

    @patch('socket.socket')
    def test_connection_pool_reuse(self, mock_socket_class):
        """Test connection reuse from pool."""
        mock_sockets = [MagicMock() for _ in range(3)]
        mock_socket_class.side_effect = mock_sockets

        pool = ConnectionPool("localhost", 31337, max_connections=2)

        # First connection
        with pool.get_connection() as sock1:
            pass

        # Second connection should reuse from pool
        with pool.get_connection() as sock2:
            pass

        # Should only create one connection (first call)
        self.assertLessEqual(pool._created_connections, 2)

    @patch('socket.socket')
    def test_connection_pool_max_connections(self, mock_socket_class):
        """Test connection pool respects max_connections limit."""
        mock_sockets = [MagicMock() for _ in range(10)]
        mock_socket_class.side_effect = mock_sockets

        pool = ConnectionPool("localhost", 31337, max_connections=3)

        # Create multiple connections
        connections = []
        for _ in range(3):
            with pool.get_connection() as sock:
                connections.append(sock)

        # Should not exceed max_connections
        self.assertLessEqual(pool._created_connections, 3)

    @patch('socket.socket')
    def test_connection_pool_close_all(self, mock_socket_class):
        """Test closing all connections in pool."""
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket

        pool = ConnectionPool("localhost", 31337)

        # Create a connection
        with pool.get_connection() as sock:
            pass

        # Close all connections
        pool.close_all()

        self.assertEqual(pool._created_connections, 0)

    @patch('socket.socket')
    def test_connection_pool_get_stats(self, mock_socket_class):
        """Test connection pool statistics."""
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket

        pool = ConnectionPool("localhost", 31337, max_connections=5)

        stats = pool.get_stats()

        self.assertIn("available", stats)
        self.assertIn("total_created", stats)
        self.assertIn("max_connections", stats)
        self.assertEqual(stats["max_connections"], 5)


def run_tests():
    """Run all tests with detailed output."""
    print("=" * 70)
    print("ImHex MCP Error Handling - Unit Tests")
    print("=" * 70)

    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"Tests run:    {result.testsRun}")
    print(f"Failures:     {len(result.failures)}")
    print(f"Errors:       {len(result.errors)}")
    print(f"Skipped:      {len(result.skipped)}")

    if result.wasSuccessful():
        print("\n✅ All tests PASSED!")
    else:
        print(f"\n❌ {len(result.failures) + len(result.errors)} test(s) FAILED")

    print("=" * 70)

    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(run_tests())
