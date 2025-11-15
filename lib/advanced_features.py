"""
Advanced Features for ImHex MCP

Provides request prioritization and circuit breaker patterns for resilient operation.

Features:
- Priority-based request queuing with aging
- Circuit breaker for fault tolerance
- Fair scheduling to prevent starvation
- Automatic failure recovery
"""

import asyncio
import time
from typing import Dict, Any, Optional, Callable, Awaitable, TypeVar, Generic
from dataclasses import dataclass, field
from enum import Enum, IntEnum
from collections import deque
import logging

logger = logging.getLogger(__name__)

T = TypeVar("T")


# ============================================================================
# Request Prioritization
# ============================================================================


class Priority(IntEnum):
    """Request priority levels (lower value = higher priority)."""

    CRITICAL = 0  # System-critical operations
    HIGH = 1  # User-facing operations
    NORMAL = 2  # Standard operations
    LOW = 3  # Background tasks


@dataclass(order=True)
class PrioritizedRequest(Generic[T]):
    """A request with priority and aging support."""

    priority: int
    timestamp: float = field(compare=False)
    request_id: str = field(compare=False)
    coro: Callable[[], Awaitable[T]] = field(compare=False)
    future: Optional[asyncio.Future] = field(compare=False, default=None)

    def __post_init__(self):
        """Calculate effective priority with aging."""
        # Age requests over time to prevent starvation (1 priority level per 10
        # seconds)
        age_bonus = int((time.monotonic() - self.timestamp) / 10.0)
        self.priority = max(0, self.priority - age_bonus)


@dataclass
class PriorityConfig:
    """Configuration for priority queue."""

    max_queue_size: int = 1000
    aging_interval: float = 10.0  # Seconds per priority level
    default_priority: Priority = Priority.NORMAL
    enable_aging: bool = True


class PriorityQueue:
    """
    Priority queue for requests with aging support.

    Implements fair scheduling by aging requests over time,
    preventing low-priority tasks from starving.
    """

    def __init__(self, config: Optional[PriorityConfig] = None):
        """Initialize priority queue."""
        self.config = config or PriorityConfig()
        self._queue: asyncio.PriorityQueue = asyncio.PriorityQueue(
            maxsize=self.config.max_queue_size
        )
        self._request_count = 0
        self._active_requests: Dict[str, PrioritizedRequest] = {}

    async def submit(
        self,
        coro: Callable[[], Awaitable[T]],
        priority: Optional[Priority] = None,
        request_id: Optional[str] = None,
    ) -> asyncio.Future:
        """
        Submit a request to the priority queue.

        Args:
            coro: Coroutine function to execute
            priority: Request priority level
            request_id: Optional request identifier

        Returns:
            Future that will resolve with the result
        """
        if priority is None:
            priority = self.config.default_priority

        if request_id is None:
            self._request_count += 1
            request_id = f"req_{self._request_count}"

        # Create future for result
        future: asyncio.Future[T] = asyncio.Future()

        # Create prioritized request
        request = PrioritizedRequest(
            priority=priority,
            timestamp=time.monotonic(),
            request_id=request_id,
            coro=coro,
            future=future,
        )

        # Add to queue
        await self._queue.put(request)
        self._active_requests[request_id] = request

        logger.debug(
            f"Submitted request {request_id} with priority {priority.name}"
        )

        return future

    async def get_next(self) -> Optional[PrioritizedRequest]:
        """Get next request from queue (blocks if empty)."""
        request = await self._queue.get()

        # Re-calculate priority with aging if enabled
        if self.config.enable_aging:
            age = time.monotonic() - request.timestamp
            age_bonus = int(age / self.config.aging_interval)
            request.priority = max(0, request.priority - age_bonus)

        return request

    async def process_request(self, request: PrioritizedRequest) -> None:
        """Process a single request."""
        if request.future is None:
            return

        try:
            result = await request.coro()
            request.future.set_result(result)
            logger.debug(f"Completed request {request.request_id}")
        except Exception as e:
            request.future.set_exception(e)
            logger.error(f"Request {request.request_id} failed: {e}")
        finally:
            self._active_requests.pop(request.request_id, None)

    def qsize(self) -> int:
        """Get current queue size."""
        return self._queue.qsize()

    def active_count(self) -> int:
        """Get number of active requests."""
        return len(self._active_requests)


class PriorityScheduler:
    """
    Scheduler that processes requests from priority queue.

    Manages worker tasks that process requests concurrently.
    """

    def __init__(self, queue: PriorityQueue, num_workers: int = 10):
        """Initialize scheduler."""
        self.queue = queue
        self.num_workers = num_workers
        self._workers: list[asyncio.Task] = []
        self._running = False

    async def start(self) -> None:
        """Start worker tasks."""
        if self._running:
            return

        self._running = True
        logger.info(
            f"Starting priority scheduler with {self.num_workers} workers"
        )

        for i in range(self.num_workers):
            worker = asyncio.create_task(self._worker_loop(i))
            self._workers.append(worker)

    async def stop(self) -> None:
        """Stop worker tasks."""
        if not self._running:
            return

        logger.info("Stopping priority scheduler")
        self._running = False

        # Cancel all workers
        for worker in self._workers:
            worker.cancel()

        # Wait for cancellation
        await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers.clear()

    async def _worker_loop(self, worker_id: int) -> None:
        """Worker loop that processes requests."""
        logger.debug(f"Worker {worker_id} started")

        while self._running:
            try:
                # Get next request (blocks if queue empty)
                request = await self.queue.get_next()

                if request is None:
                    continue

                # Process request
                await self.queue.process_request(request)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")
                await asyncio.sleep(0.1)

        logger.debug(f"Worker {worker_id} stopped")


# ============================================================================
# Circuit Breaker
# ============================================================================


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failures detected, rejecting requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""

    failure_threshold: int = 5  # Failures before opening circuit
    success_threshold: int = 2  # Successes in half-open to close
    timeout: float = 60.0  # Seconds before trying half-open
    window_size: int = 10  # Rolling window for failure rate


class CircuitBreakerError(Exception):
    """Exception raised when circuit breaker is open."""


class CircuitBreaker:
    """
    Circuit breaker for fault tolerance.

    Implements the circuit breaker pattern to prevent cascading failures.
    Automatically transitions between CLOSED -> OPEN -> HALF_OPEN -> CLOSED
    based on success/failure rates.
    """

    def __init__(
        self, name: str, config: Optional[CircuitBreakerConfig] = None
    ):
        """Initialize circuit breaker."""
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._recent_calls: deque = deque(maxlen=self.config.window_size)
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        return self._state

    @property
    def is_closed(self) -> bool:
        """Check if circuit is closed (accepting requests)."""
        return self._state == CircuitState.CLOSED

    @property
    def is_open(self) -> bool:
        """Check if circuit is open (rejecting requests)."""
        return self._state == CircuitState.OPEN

    def _transition_to_open(self) -> None:
        """Transition to OPEN state."""
        logger.warning(
            f"Circuit breaker '{self.name}' OPEN: "
            f"{self._failure_count} failures detected"
        )
        self._state = CircuitState.OPEN
        self._last_failure_time = time.monotonic()

    def _transition_to_half_open(self) -> None:
        """Transition to HALF_OPEN state."""
        logger.info(f"Circuit breaker '{self.name}' entering HALF_OPEN state")
        self._state = CircuitState.HALF_OPEN
        self._success_count = 0
        self._failure_count = 0

    def _transition_to_closed(self) -> None:
        """Transition to CLOSED state."""
        logger.info(f"Circuit breaker '{self.name}' CLOSED: service recovered")
        self._state = CircuitState.CLOSED
        self._success_count = 0
        self._failure_count = 0
        self._recent_calls.clear()

    def _check_state_transition(self) -> None:
        """Check if state transition is needed."""
        if self._state == CircuitState.OPEN:
            # Check if timeout elapsed
            if (
                self._last_failure_time
                and time.monotonic() - self._last_failure_time
                >= self.config.timeout
            ):
                self._transition_to_half_open()

        elif self._state == CircuitState.CLOSED:
            # Check failure threshold
            if self._failure_count >= self.config.failure_threshold:
                self._transition_to_open()

        elif self._state == CircuitState.HALF_OPEN:
            # Check if enough successes to close
            if self._success_count >= self.config.success_threshold:
                self._transition_to_closed()
            # Or if failure occurs, back to open
            elif self._failure_count > 0:
                self._transition_to_open()

    async def call(self, coro: Callable[[], Awaitable[T]]) -> T:
        """
        Execute a function with circuit breaker protection.

        Args:
            coro: Coroutine function to execute

        Returns:
            Result from coroutine

        Raises:
            CircuitBreakerError: If circuit is open
        """
        async with self._lock:
            self._check_state_transition()

            if self._state == CircuitState.OPEN:
                raise CircuitBreakerError(
                    f"Circuit breaker '{self.name}' is OPEN"
                )

        # Execute function
        try:
            result = await coro()
            await self._on_success()
            return result
        except Exception:
            await self._on_failure()
            raise

    async def _on_success(self) -> None:
        """Record successful call."""
        async with self._lock:
            self._success_count += 1
            self._recent_calls.append(True)

            # Reset failure count on success
            if self._state == CircuitState.CLOSED:
                self._failure_count = 0

            self._check_state_transition()

    async def _on_failure(self) -> None:
        """Record failed call."""
        async with self._lock:
            self._failure_count += 1
            self._recent_calls.append(False)
            self._last_failure_time = time.monotonic()

            self._check_state_transition()

    def get_stats(self) -> Dict[str, Any]:
        """Get circuit breaker statistics."""
        failure_rate = 0.0
        if self._recent_calls:
            failures = sum(1 for success in self._recent_calls if not success)
            failure_rate = failures / len(self._recent_calls)

        return {
            "name": self.name,
            "state": self._state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "failure_rate": failure_rate,
            "recent_calls": len(self._recent_calls),
        }


# ============================================================================
# Integrated Advanced Client
# ============================================================================


class AdvancedRequestManager:
    """
    Combines prioritization and circuit breaker for advanced request handling.
    """

    def __init__(
        self,
        priority_config: Optional[PriorityConfig] = None,
        circuit_config: Optional[CircuitBreakerConfig] = None,
        num_workers: int = 10,
    ):
        """Initialize advanced request manager."""
        self.priority_queue = PriorityQueue(priority_config)
        self.scheduler = PriorityScheduler(self.priority_queue, num_workers)
        self.circuit_breaker = CircuitBreaker("imhex_mcp", circuit_config)
        self._started = False

    async def start(self) -> None:
        """Start request manager."""
        if self._started:
            return

        await self.scheduler.start()
        self._started = True
        logger.info("Advanced request manager started")

    async def stop(self) -> None:
        """Stop request manager."""
        if not self._started:
            return

        await self.scheduler.stop()
        self._started = False
        logger.info("Advanced request manager stopped")

    async def execute(
        self,
        coro: Callable[[], Awaitable[T]],
        priority: Priority = Priority.NORMAL,
        use_circuit_breaker: bool = True,
    ) -> T:
        """
        Execute request with prioritization and circuit breaker.

        Args:
            coro: Coroutine function to execute
            priority: Request priority
            use_circuit_breaker: Whether to use circuit breaker

        Returns:
            Result from coroutine
        """
        # Wrap with circuit breaker if enabled
        if use_circuit_breaker:

            async def protected_coro():
                return await self.circuit_breaker.call(coro)

            final_coro = protected_coro
        else:
            final_coro = coro

        # Submit to priority queue
        future = await self.priority_queue.submit(final_coro, priority)

        # Wait for result
        return await future

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics for all components."""
        return {
            "queue_size": self.priority_queue.qsize(),
            "active_requests": self.priority_queue.active_count(),
            "circuit_breaker": self.circuit_breaker.get_stats(),
        }
