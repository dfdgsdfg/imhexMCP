"""
Prometheus Metrics for ImHex MCP

Provides comprehensive metrics collection and export for monitoring:
- Request counts and latencies by endpoint
- Compression performance and ratios
- Connection pool utilization
- Cache hit/miss rates
- Error rates and types
- System health indicators

Metrics are exposed on a configurable HTTP endpoint for Prometheus scraping.
"""

import time
import logging
from typing import Dict, Any, Optional, Callable
from functools import wraps
from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    Summary,
    Info,
    CollectorRegistry,
    generate_latest,
    CONTENT_TYPE_LATEST,
)

logger = logging.getLogger(__name__)


class ImHexMCPMetrics:
    """Centralized metrics collection for ImHex MCP."""

    def __init__(self, registry: Optional[CollectorRegistry] = None):
        """Initialize metrics collectors.

        Args:
            registry: Prometheus registry (defaults to global registry)
        """
        self.registry = registry or CollectorRegistry()

        # Request metrics
        self.request_count = Counter(
            'imhex_mcp_requests_total',
            'Total number of requests by endpoint',
            ['endpoint', 'status'],
            registry=self.registry
        )

        self.request_duration = Histogram(
            'imhex_mcp_request_duration_seconds',
            'Request duration in seconds by endpoint',
            ['endpoint'],
            buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
            registry=self.registry
        )

        self.active_requests = Gauge(
            'imhex_mcp_active_requests',
            'Number of currently active requests',
            registry=self.registry
        )

        # Compression metrics
        self.compression_ratio = Histogram(
            'imhex_mcp_compression_ratio',
            'Compression ratio (compressed/original)',
            buckets=(0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0),
            registry=self.registry
        )

        self.compression_time = Histogram(
            'imhex_mcp_compression_duration_seconds',
            'Compression operation duration',
            ['operation'],  # compress, decompress
            buckets=(0.0001, 0.0005, 0.001, 0.005, 0.01, 0.05, 0.1),
            registry=self.registry
        )

        self.bytes_transferred = Counter(
            'imhex_mcp_bytes_transferred_total',
            'Total bytes transferred',
            ['direction', 'compressed'],  # direction: sent/received, compressed: yes/no
            registry=self.registry
        )

        self.bytes_saved = Counter(
            'imhex_mcp_compression_bytes_saved_total',
            'Total bytes saved through compression',
            registry=self.registry
        )

        self.compression_operations = Counter(
            'imhex_mcp_compression_operations_total',
            'Compression operations by type and result',
            ['operation', 'result'],  # operation: compress/decompress, result: success/skipped_small/skipped_ratio/failed
            registry=self.registry
        )

        # Connection pool metrics
        self.pool_connections = Gauge(
            'imhex_mcp_pool_connections',
            'Connection pool statistics',
            ['state'],  # active, idle, total
            registry=self.registry
        )

        self.pool_operations = Counter(
            'imhex_mcp_pool_operations_total',
            'Connection pool operations',
            ['operation', 'result'],  # operation: acquire/release, result: success/timeout/error
            registry=self.registry
        )

        self.pool_wait_time = Histogram(
            'imhex_mcp_pool_wait_duration_seconds',
            'Time spent waiting for pool connection',
            buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0),
            registry=self.registry
        )

        # Cache metrics
        self.cache_operations = Counter(
            'imhex_mcp_cache_operations_total',
            'Cache operations by result',
            ['result'],  # hit, miss, set, evict
            registry=self.registry
        )

        self.cache_size = Gauge(
            'imhex_mcp_cache_size',
            'Current number of items in cache',
            registry=self.registry
        )

        self.cache_bytes = Gauge(
            'imhex_mcp_cache_bytes',
            'Approximate cache size in bytes',
            registry=self.registry
        )

        # Error metrics
        self.errors = Counter(
            'imhex_mcp_errors_total',
            'Total errors by type and endpoint',
            ['error_type', 'endpoint'],
            registry=self.registry
        )

        # Batching metrics
        self.batch_size = Histogram(
            'imhex_mcp_batch_size',
            'Number of requests in batch',
            buckets=(1, 2, 5, 10, 20, 50, 100),
            registry=self.registry
        )

        self.batch_wait_time = Histogram(
            'imhex_mcp_batch_wait_duration_seconds',
            'Time requests waited in batch window',
            buckets=(0.001, 0.005, 0.01, 0.02, 0.05, 0.1),
            registry=self.registry
        )

        # System info
        self.info = Info(
            'imhex_mcp',
            'ImHex MCP server information',
            registry=self.registry
        )

        # Health metrics
        self.health_checks = Counter(
            'imhex_mcp_health_checks_total',
            'Health check results',
            ['status'],  # healthy, unhealthy
            registry=self.registry
        )

        self.last_health_check = Gauge(
            'imhex_mcp_last_health_check_timestamp',
            'Timestamp of last health check',
            registry=self.registry
        )

        logger.info("Prometheus metrics initialized")

    def set_info(self, version: str, python_version: str, **kwargs: Any) -> None:
        """Set server information.

        Args:
            version: Server version
            python_version: Python version
            **kwargs: Additional info fields
        """
        info_dict = {
            'version': version,
            'python_version': python_version,
            **kwargs
        }
        self.info.info(info_dict)

    def track_request(self, endpoint: str) -> Callable:
        """Decorator to track request metrics.

        Args:
            endpoint: Endpoint name

        Returns:
            Decorator function

        Example:
            @metrics.track_request('file/read')
            async def handle_file_read(data):
                ...
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args: Any, **kwargs: Any) -> Any:
                self.active_requests.inc()
                start_time = time.perf_counter()
                status = 'success'

                try:
                    result = await func(*args, **kwargs)
                    return result
                except Exception as e:
                    status = 'error'
                    error_type = type(e).__name__
                    self.errors.labels(error_type=error_type, endpoint=endpoint).inc()
                    raise
                finally:
                    duration = time.perf_counter() - start_time
                    self.request_count.labels(endpoint=endpoint, status=status).inc()
                    self.request_duration.labels(endpoint=endpoint).observe(duration)
                    self.active_requests.dec()

            return wrapper
        return decorator

    def record_compression(
        self,
        operation: str,
        duration_seconds: float,
        original_size: int,
        compressed_size: Optional[int] = None,
        result: str = 'success'
    ) -> None:
        """Record compression metrics.

        Args:
            operation: 'compress' or 'decompress'
            duration_seconds: Operation duration
            original_size: Original data size
            compressed_size: Compressed size (for compression operations)
            result: Operation result (success/skipped_small/skipped_ratio/failed)
        """
        self.compression_time.labels(operation=operation).observe(duration_seconds)
        self.compression_operations.labels(operation=operation, result=result).inc()

        if compressed_size is not None and result == 'success':
            ratio = compressed_size / original_size if original_size > 0 else 1.0
            self.compression_ratio.observe(ratio)

            bytes_saved = original_size - compressed_size
            if bytes_saved > 0:
                self.bytes_saved.inc(bytes_saved)

            # Track sent bytes
            self.bytes_transferred.labels(
                direction='sent',
                compressed='yes' if compressed_size < original_size else 'no'
            ).inc(compressed_size)

    def record_decompression(
        self,
        duration_seconds: float,
        compressed_size: int,
        decompressed_size: int
    ) -> None:
        """Record decompression metrics.

        Args:
            duration_seconds: Operation duration
            compressed_size: Compressed data size
            decompressed_size: Decompressed data size
        """
        self.compression_time.labels(operation='decompress').observe(duration_seconds)
        self.compression_operations.labels(operation='decompress', result='success').inc()

        # Track received bytes
        self.bytes_transferred.labels(
            direction='received',
            compressed='yes'
        ).inc(compressed_size)

    def update_pool_stats(
        self,
        active: int,
        idle: int,
        total: int
    ) -> None:
        """Update connection pool statistics.

        Args:
            active: Number of active connections
            idle: Number of idle connections
            total: Total connections in pool
        """
        self.pool_connections.labels(state='active').set(active)
        self.pool_connections.labels(state='idle').set(idle)
        self.pool_connections.labels(state='total').set(total)

    def record_pool_operation(
        self,
        operation: str,
        result: str,
        wait_time_seconds: Optional[float] = None
    ) -> None:
        """Record connection pool operation.

        Args:
            operation: 'acquire' or 'release'
            result: Operation result (success/timeout/error)
            wait_time_seconds: Time waited for connection (for acquire)
        """
        self.pool_operations.labels(operation=operation, result=result).inc()

        if wait_time_seconds is not None and operation == 'acquire':
            self.pool_wait_time.observe(wait_time_seconds)

    def record_cache_operation(
        self,
        result: str,
        size: Optional[int] = None,
        bytes_size: Optional[int] = None
    ) -> None:
        """Record cache operation.

        Args:
            result: Operation result (hit/miss/set/evict)
            size: Current cache size (number of items)
            bytes_size: Approximate cache size in bytes
        """
        self.cache_operations.labels(result=result).inc()

        if size is not None:
            self.cache_size.set(size)

        if bytes_size is not None:
            self.cache_bytes.set(bytes_size)

    def record_batch(
        self,
        batch_size: int,
        wait_time_seconds: float
    ) -> None:
        """Record batch metrics.

        Args:
            batch_size: Number of requests in batch
            wait_time_seconds: Time requests waited in batch window
        """
        self.batch_size.observe(batch_size)
        self.batch_wait_time.observe(wait_time_seconds)

    def record_health_check(self, healthy: bool) -> None:
        """Record health check result.

        Args:
            healthy: Whether system is healthy
        """
        status = 'healthy' if healthy else 'unhealthy'
        self.health_checks.labels(status=status).inc()
        self.last_health_check.set(time.time())

    def record_error(self, error_type: str, endpoint: str) -> None:
        """Record an error.

        Args:
            error_type: Type/class of error
            endpoint: Endpoint where error occurred
        """
        self.errors.labels(error_type=error_type, endpoint=endpoint).inc()

    def get_metrics(self) -> bytes:
        """Get metrics in Prometheus format.

        Returns:
            Metrics data as bytes
        """
        return generate_latest(self.registry)

    def get_content_type(self) -> str:
        """Get content type for metrics response.

        Returns:
            Content type string
        """
        return CONTENT_TYPE_LATEST


# Global metrics instance
_metrics: Optional[ImHexMCPMetrics] = None


def get_metrics() -> ImHexMCPMetrics:
    """Get global metrics instance (singleton).

    Returns:
        Global metrics instance
    """
    global _metrics
    if _metrics is None:
        _metrics = ImHexMCPMetrics()
    return _metrics


def initialize_metrics(version: str = "1.0.0", **kwargs: Any) -> ImHexMCPMetrics:
    """Initialize global metrics with server info.

    Args:
        version: Server version
        **kwargs: Additional info fields

    Returns:
        Initialized metrics instance
    """
    import sys

    metrics = get_metrics()
    metrics.set_info(
        version=version,
        python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        **kwargs
    )
    return metrics
