#!/usr/bin/env python3
"""
ImHex MCP Error Handling Module

Provides robust error handling, retry logic, and connection management
for ImHex MCP operations.
"""

import threading
from contextlib import contextmanager
import queue
import socket
import time
import functools
from typing import Dict, List, Optional, Any, Callable, TypeVar
from dataclasses import dataclass
from enum import Enum


# Custom Exception Classes


class ImHexMCPError(Exception):
    """Base exception for all ImHex MCP errors."""

    def __init__(self, message: str, recovery_hint: Optional[str] = None):
        self.message = message
        self.recovery_hint = recovery_hint
        super().__init__(self.message)

    def __str__(self) -> str:
        if self.recovery_hint:
            return f"{self.message}\n💡 Recovery Hint: {self.recovery_hint}"
        return self.message


class ConnectionError(ImHexMCPError):
    """Raised when connection to ImHex MCP fails."""

    def __init__(self, host: str, port: int, reason: str):
        message = f"Failed to connect to ImHex MCP at {host}:{port}: {reason}"
        recovery_hint = (
            "1. Ensure ImHex is running\n"
            "2. Enable Network Interface in Settings → General\n"
            f"3. Verify port {port} is not blocked by firewall\n"
            "4. Check if another application is using the port"
        )
        super().__init__(message, recovery_hint)
        self.host = host
        self.port = port
        self.reason = reason


class TimeoutError(ImHexMCPError):
    """Raised when operation times out."""

    def __init__(self, operation: str, timeout: float):
        message = f"Operation '{operation}' timed out after {timeout}s"
        recovery_hint = (
            "1. Increase timeout value for slow operations\n"
            "2. Check system load and ImHex responsiveness\n"
            "3. Verify network latency if using remote connection"
        )
        super().__init__(message, recovery_hint)
        self.operation = operation
        self.timeout = timeout


class ProviderNotFoundError(ImHexMCPError):
    """Raised when provider ID is not found."""

    def __init__(self, provider_id: int):
        message = f"Provider ID {provider_id} not found"
        recovery_hint = (
            "1. List available providers with 'file/list' endpoint\n"
            "2. Open a file first using 'file/open' endpoint\n"
            "3. Verify the provider hasn't been closed"
        )
        super().__init__(message, recovery_hint)
        self.provider_id = provider_id


class InvalidEndpointError(ImHexMCPError):
    """Raised when endpoint doesn't exist."""

    def __init__(self, endpoint: str, available: Optional[List[str]] = None):
        message = f"Invalid endpoint: '{endpoint}'"
        recovery_hint = (
            "Check available endpoints with 'capabilities' endpoint"
        )
        if available:
            recovery_hint += f"\nAvailable: {
                ', '.join(sorted(available)[: 10])} "
        super().__init__(message, recovery_hint)
        self.endpoint = endpoint
        self.available = available


class ProtocolError(ImHexMCPError):
    """Raised when protocol-level error occurs."""

    def __init__(self, details: str):
        message = f"Protocol error: {details}"
        recovery_hint = "This may indicate version mismatch or corrupted data"
        super().__init__(message, recovery_hint)


class CircuitBreakerOpenError(ImHexMCPError):
    """Raised when circuit breaker is open."""

    def __init__(self, reset_time: float):
        wait_time = max(0, reset_time - time.time())
        message = "Circuit breaker is OPEN - service temporarily unavailable"
        recovery_hint = f"Wait {wait_time:.1f}s before retrying"
        super().__init__(message, recovery_hint)
        self.reset_time = reset_time


# Error Classification


class ErrorSeverity(Enum):
    """Error severity levels."""

    LOW = "low"  # Recoverable, can retry immediately
    MEDIUM = "medium"  # Recoverable, should backoff
    HIGH = "high"  # May be recoverable, exponential backoff
    CRITICAL = "critical"  # Not recoverable, fail fast


@dataclass
class ErrorInfo:
    """Error information for classification."""

    severity: ErrorSeverity
    retryable: bool
    backoff_multiplier: float


def classify_error(error: Exception) -> ErrorInfo:
    """Classify error and determine retry strategy."""

    # Timeout errors - check FIRST since socket.timeout is subclass of
    # socket.error
    if isinstance(error, socket.timeout) or isinstance(error, TimeoutError):
        return ErrorInfo(
            severity=ErrorSeverity.MEDIUM,
            retryable=True,
            backoff_multiplier=1.5,
        )

    # Connection errors - usually retryable with backoff
    if isinstance(
        error, (socket.error, ConnectionRefusedError, ConnectionResetError)
    ):
        return ErrorInfo(
            severity=ErrorSeverity.MEDIUM,
            retryable=True,
            backoff_multiplier=2.0,
        )

    # Circuit breaker - not retryable immediately
    if isinstance(error, CircuitBreakerOpenError):
        return ErrorInfo(
            severity=ErrorSeverity.HIGH,
            retryable=False,
            backoff_multiplier=1.0,
        )

    # Protocol/validation errors - not retryable
    if isinstance(error, (ProtocolError, InvalidEndpointError, ValueError)):
        return ErrorInfo(
            severity=ErrorSeverity.CRITICAL,
            retryable=False,
            backoff_multiplier=1.0,
        )

    # Provider errors - may be retryable after file opens
    if isinstance(error, ProviderNotFoundError):
        return ErrorInfo(
            severity=ErrorSeverity.MEDIUM,
            retryable=True,
            backoff_multiplier=1.0,
        )

    # Unknown errors - treat as potentially retryable but with caution
    return ErrorInfo(
        severity=ErrorSeverity.HIGH, retryable=True, backoff_multiplier=2.5
    )


# Retry Decorator with Exponential Backoff

T = TypeVar("T")


def retry_with_backoff(
    max_attempts: int = 3,
    initial_delay: float = 0.1,
    max_delay: float = 10.0,
    exponential_base: float = 2.0,
    exceptions: tuple = (socket.error, ConnectionRefusedError, socket.timeout),
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Retry decorator with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay between retries
        exponential_base: Base for exponential backoff calculation
        exceptions: Tuple of exceptions to catch and retry

    Returns:
        Decorated function with retry logic

    Example:
        @retry_with_backoff(max_attempts=3, initial_delay=0.5)
        def fetch_data():
            return request_data()
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            attempt = 0
            delay = initial_delay

            while attempt < max_attempts:
                try:
                    return func(*args, **kwargs)

                except exceptions as e:
                    attempt += 1

                    if attempt >= max_attempts:
                        # Last attempt failed, classify and re-raise
                        error_info = classify_error(e)
                        if error_info.severity == ErrorSeverity.CRITICAL:
                            raise

                        # Wrap in ImHexMCPError with recovery hint
                        if isinstance(e, socket.error):
                            raise ConnectionError(
                                "localhost", 31337, str(e)
                            ) from e
                        raise ImHexMCPError(
                            f"Operation failed after {max_attempts} attempts: {
                                str(e)}",
                            "Check network connection and ImHex status",
                        ) from e

                    # Calculate backoff delay
                    error_info = classify_error(e)
                    if error_info.retryable:
                        backoff_delay = min(
                            delay
                            * (exponential_base ** (attempt - 1))
                            * error_info.backoff_multiplier,
                            max_delay,
                        )

                        # Optional: log retry attempt
                        # print(f"Retry attempt {attempt}/{max_attempts} after {backoff_delay:.2f}s...")

                        time.sleep(backoff_delay)
                    else:
                        # Not retryable, fail immediately
                        raise

            # Should never reach here, but satisfy type checker
            raise RuntimeError("Unexpected retry loop exit")

        return wrapper

    return decorator


# Circuit Breaker Pattern


class CircuitBreakerState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """
    Circuit breaker pattern implementation.

    Prevents cascading failures by temporarily blocking requests
    to a failing service.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        success_threshold: int = 2,
    ):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before attempting recovery
            success_threshold: Consecutive successes needed to close circuit
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold

        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[float] = None

    def call(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """Execute function through circuit breaker."""

        if self.state == CircuitBreakerState.OPEN:
            # Check if recovery timeout has elapsed
            if (
                self.last_failure_time
                and time.time() - self.last_failure_time
                >= self.recovery_timeout
            ):
                self.state = CircuitBreakerState.HALF_OPEN
                self.success_count = 0
            else:
                raise CircuitBreakerOpenError(
                    self.last_failure_time + self.recovery_timeout
                    if self.last_failure_time
                    else time.time()
                )

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result

        except Exception:
            self._on_failure()
            raise

    def _on_success(self) -> None:
        """Handle successful call."""
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                self.state = CircuitBreakerState.CLOSED
                self.failure_count = 0
                self.success_count = 0
        elif self.state == CircuitBreakerState.CLOSED:
            self.failure_count = 0

    def _on_failure(self) -> None:
        """Handle failed call."""
        self.last_failure_time = time.time()

        if self.state == CircuitBreakerState.HALF_OPEN:
            self.state = CircuitBreakerState.OPEN
            self.success_count = 0
        elif self.state == CircuitBreakerState.CLOSED:
            self.failure_count += 1
            if self.failure_count >= self.failure_threshold:
                self.state = CircuitBreakerState.OPEN

    def reset(self) -> None:
        """Manually reset circuit breaker."""
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None

    def get_state(self) -> Dict[str, Any]:
        """Get current circuit breaker state."""
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": self.last_failure_time,
        }


# Health Check


class HealthCheck:
    """
    Health check for ImHex MCP connection.
    """

    def __init__(self, host: str = "localhost", port: int = 31337):
        self.host = host
        self.port = port
        self.last_check: Optional[float] = None
        self.last_status: bool = False

    def check(self, timeout: float = 2.0) -> bool:
        """
        Check if ImHex MCP is reachable.

        Returns:
            True if healthy, False otherwise
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect((self.host, self.port))
            sock.close()

            self.last_check = time.time()
            self.last_status = True
            return True

        except (socket.error, socket.timeout):
            self.last_check = time.time()
            self.last_status = False
            return False

    def get_status(self) -> Dict[str, Any]:
        """Get health check status."""
        return {
            "healthy": self.last_status,
            "last_check": self.last_check,
            "age": time.time() - self.last_check if self.last_check else None,
        }


# Connection Pooling


class ConnectionPool:
    """
    Connection pool for ImHex MCP.

    Reuses connections to reduce overhead and improve performance.
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 31337,
        max_connections: int = 5,
        timeout: float = 10.0,
    ):
        """
        Initialize connection pool.

        Args:
            host: ImHex MCP host
            port: ImHex MCP port
            max_connections: Maximum number of pooled connections
            timeout: Socket timeout in seconds
        """
        self.host = host
        self.port = port
        self.max_connections = max_connections
        self.timeout = timeout

        self._pool: queue.Queue = queue.Queue(maxsize=max_connections)
        self._lock = threading.Lock()
        self._created_connections = 0

    def _create_connection(self) -> socket.socket:
        """Create a new socket connection."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)
        sock.connect((self.host, self.port))
        return sock

    @contextmanager
    def get_connection(self):
        """
        Get connection from pool (context manager).

        Usage:
            with pool.get_connection() as sock:
                # use socket
        """
        sock = None
        try:
            # Try to get existing connection from pool
            try:
                sock = self._pool.get_nowait()
            except queue.Empty:
                # Pool is empty, create new connection if under limit
                with self._lock:
                    if self._created_connections < self.max_connections:
                        sock = self._create_connection()
                        self._created_connections += 1
                    else:
                        # Wait for available connection
                        sock = self._pool.get(timeout=self.timeout)

            yield sock

        finally:
            # Return connection to pool if still valid
            if sock:
                try:
                    # Test if connection is still alive
                    sock.setblocking(False)
                    sock.recv(1, socket.MSG_PEEK)
                    sock.setblocking(True)

                    # Connection is still good, return to pool
                    try:
                        self._pool.put_nowait(sock)
                    except queue.Full:
                        # Pool is full, close connection
                        sock.close()
                        with self._lock:
                            self._created_connections -= 1

                except (socket.error, socket.timeout):
                    # Connection is dead, close it
                    sock.close()
                    with self._lock:
                        self._created_connections -= 1

    def close_all(self) -> None:
        """Close all connections in pool."""
        while not self._pool.empty():
            try:
                sock = self._pool.get_nowait()
                sock.close()
            except queue.Empty:
                break

        with self._lock:
            self._created_connections = 0

    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics."""
        return {
            "available": self._pool.qsize(),
            "total_created": self._created_connections,
            "max_connections": self.max_connections,
        }
