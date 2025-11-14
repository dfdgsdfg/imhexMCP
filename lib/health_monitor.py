"""
Health Check and Monitoring Module

Provides health checks, metrics collection, and monitoring capabilities
for the ImHex MCP server.
"""

import time
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass, field, asdict
from datetime import timedelta
from enum import Enum
import threading

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health check status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheck:
    """Result of a health check."""
    name: str
    status: HealthStatus
    message: str
    timestamp: float = field(default_factory=time.time)
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = asdict(self)
        result['status'] = self.status.value
        return result


@dataclass
class Metrics:
    """System metrics."""
    # Request metrics
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0

    # Timing metrics
    total_request_time_ms: float = 0.0
    min_request_time_ms: float = float('inf')
    max_request_time_ms: float = 0.0

    # Cache metrics (if enabled)
    cache_hits: int = 0
    cache_misses: int = 0
    cache_size: int = 0

    # Connection metrics
    active_connections: int = 0
    total_connections: int = 0
    connection_failures: int = 0

    # Error metrics
    timeouts: int = 0
    connection_errors: int = 0
    other_errors: int = 0

    # Timestamp
    start_time: float = field(default_factory=time.time)
    last_request_time: float = 0.0

    def avg_request_time_ms(self) -> float:
        """Calculate average request time."""
        if self.total_requests == 0:
            return 0.0
        return self.total_request_time_ms / self.total_requests

    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_requests == 0:
            return 0.0
        return (self.successful_requests / self.total_requests) * 100

    def error_rate(self) -> float:
        """Calculate error rate."""
        if self.total_requests == 0:
            return 0.0
        return (self.failed_requests / self.total_requests) * 100

    def cache_hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.cache_hits + self.cache_misses
        if total == 0:
            return 0.0
        return (self.cache_hits / total) * 100

    def uptime_seconds(self) -> float:
        """Calculate uptime in seconds."""
        return time.time() - self.start_time

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with calculated fields."""
        result = asdict(self)
        result['avg_request_time_ms'] = self.avg_request_time_ms()
        result['success_rate'] = self.success_rate()
        result['error_rate'] = self.error_rate()
        result['cache_hit_rate'] = self.cache_hit_rate()
        result['uptime_seconds'] = self.uptime_seconds()
        return result


class HealthMonitor:
    """Health monitoring and metrics collection."""

    def __init__(self):
        self.metrics = Metrics()
        self.health_checks: Dict[str, HealthCheck] = {}
        self._lock = threading.Lock()
        logger.info("Health monitor initialized")

    # === Health Checks ===

    def check_imhex_connection(self, client) -> HealthCheck:
        """Check ImHex connection health."""
        try:
            start = time.time()
            # Try to get capabilities
            response = client.send_command("capabilities")
            duration_ms = (time.time() - start) * 1000

            if response.get("status") == "success":
                return HealthCheck(
                    name="imhex_connection",
                    status=HealthStatus.HEALTHY,
                    message=f"Connected to ImHex (response time: {duration_ms:.1f}ms)",
                    details={
                        "response_time_ms": duration_ms,
                        "endpoints": len(response.get("data", {}).get("endpoints", []))
                    }
                )
            else:
                return HealthCheck(
                    name="imhex_connection",
                    status=HealthStatus.DEGRADED,
                    message="ImHex responded but with error",
                    details={"response": response}
                )
        except ConnectionError as e:
            return HealthCheck(
                name="imhex_connection",
                status=HealthStatus.UNHEALTHY,
                message=f"Cannot connect to ImHex: {e}",
                details={"error": str(e)}
            )
        except Exception as e:
            return HealthCheck(
                name="imhex_connection",
                status=HealthStatus.UNHEALTHY,
                message=f"Health check failed: {e}",
                details={"error": str(e), "type": type(e).__name__}
            )

    def check_cache_health(self, client) -> HealthCheck:
        """Check cache health (if enhanced client)."""
        try:
            if hasattr(client, 'get_cache_stats'):
                stats = client.get_cache_stats()
                hit_rate = stats.get('hit_rate', 0)

                if hit_rate < 50:
                    status = HealthStatus.DEGRADED
                    message = f"Low cache hit rate: {hit_rate:.1f}%"
                else:
                    status = HealthStatus.HEALTHY
                    message = f"Cache healthy (hit rate: {hit_rate:.1f}%)"

                return HealthCheck(
                    name="cache_health",
                    status=status,
                    message=message,
                    details=stats
                )
            else:
                return HealthCheck(
                    name="cache_health",
                    status=HealthStatus.UNKNOWN,
                    message="Cache not available (standard client)",
                    details={}
                )
        except Exception as e:
            return HealthCheck(
                name="cache_health",
                status=HealthStatus.UNKNOWN,
                message=f"Cannot check cache: {e}",
                details={"error": str(e)}
            )

    def check_metrics_health(self) -> HealthCheck:
        """Check overall metrics health."""
        with self._lock:
            error_rate = self.metrics.error_rate()
            avg_time = self.metrics.avg_request_time_ms()

            # Determine status based on metrics
            if error_rate > 20:
                status = HealthStatus.UNHEALTHY
                message = f"High error rate: {error_rate:.1f}%"
            elif error_rate > 5:
                status = HealthStatus.DEGRADED
                message = f"Elevated error rate: {error_rate:.1f}%"
            elif avg_time > 1000:
                status = HealthStatus.DEGRADED
                message = f"High latency: {avg_time:.1f}ms average"
            else:
                status = HealthStatus.HEALTHY
                message = f"Metrics healthy (error rate: {
                    error_rate: .1f} %, avg latency: {
                    avg_time: .1f} ms) "

            return HealthCheck(
                name="metrics",
                status=status,
                message=message,
                details={
                    "total_requests": self.metrics.total_requests,
                    "error_rate": error_rate,
                    "avg_latency_ms": avg_time
                }
            )

    def run_all_checks(self, client) -> Dict[str, HealthCheck]:
        """Run all health checks."""
        checks = {
            "imhex_connection": self.check_imhex_connection(client),
            "cache": self.check_cache_health(client),
            "metrics": self.check_metrics_health()
        }

        with self._lock:
            self.health_checks = checks

        return checks

    def get_overall_status(self) -> HealthStatus:
        """Get overall system health status."""
        with self._lock:
            if not self.health_checks:
                return HealthStatus.UNKNOWN

            statuses = [check.status for check in self.health_checks.values()]

            if HealthStatus.UNHEALTHY in statuses:
                return HealthStatus.UNHEALTHY
            elif HealthStatus.DEGRADED in statuses:
                return HealthStatus.DEGRADED
            elif all(s == HealthStatus.HEALTHY for s in statuses):
                return HealthStatus.HEALTHY
            else:
                return HealthStatus.UNKNOWN

    # === Metrics Recording ===

    def record_request(self, success: bool, duration_ms: float):
        """Record a request."""
        with self._lock:
            self.metrics.total_requests += 1
            self.metrics.last_request_time = time.time()

            if success:
                self.metrics.successful_requests += 1
            else:
                self.metrics.failed_requests += 1

            self.metrics.total_request_time_ms += duration_ms
            self.metrics.min_request_time_ms = min(
                self.metrics.min_request_time_ms, duration_ms)
            self.metrics.max_request_time_ms = max(
                self.metrics.max_request_time_ms, duration_ms)

    def record_cache_hit(self):
        """Record a cache hit."""
        with self._lock:
            self.metrics.cache_hits += 1

    def record_cache_miss(self):
        """Record a cache miss."""
        with self._lock:
            self.metrics.cache_misses += 1

    def record_connection_attempt(self, success: bool):
        """Record a connection attempt."""
        with self._lock:
            self.metrics.total_connections += 1
            if success:
                self.metrics.active_connections += 1
            else:
                self.metrics.connection_failures += 1

    def record_error(self, error_type: str):
        """Record an error."""
        with self._lock:
            if error_type == "timeout":
                self.metrics.timeouts += 1
            elif error_type == "connection":
                self.metrics.connection_errors += 1
            else:
                self.metrics.other_errors += 1

    # === Reporting ===

    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics."""
        with self._lock:
            return self.metrics.to_dict()

    def get_health_report(self) -> Dict[str, Any]:
        """Get complete health report."""
        with self._lock:
            overall_status = self.get_overall_status()

            return {
                "status": overall_status.value,
                "timestamp": time.time(),
                "uptime_seconds": self.metrics.uptime_seconds(),
                "checks": {name: check.to_dict() for name, check in self.health_checks.items()},
                "metrics": self.metrics.to_dict()
            }

    def get_prometheus_metrics(self) -> str:
        """Export metrics in Prometheus format."""
        with self._lock:
            metrics = self.metrics
            lines = []

            # Request metrics
            lines.append(
                "# HELP imhex_requests_total Total number of requests")
            lines.append("# TYPE imhex_requests_total counter")
            lines.append(f"imhex_requests_total {metrics.total_requests}")

            lines.append(
                "# HELP imhex_requests_successful Successful requests")
            lines.append("# TYPE imhex_requests_successful counter")
            lines.append(
                f"imhex_requests_successful {metrics.successful_requests}")

            lines.append("# HELP imhex_requests_failed Failed requests")
            lines.append("# TYPE imhex_requests_failed counter")
            lines.append(f"imhex_requests_failed {metrics.failed_requests}")

            # Timing metrics
            lines.append(
                "# HELP imhex_request_duration_seconds Request duration")
            lines.append("# TYPE imhex_request_duration_seconds summary")
            lines.append(
                f"imhex_request_duration_seconds_sum {metrics.total_request_time_ms / 1000}")
            lines.append(
                f"imhex_request_duration_seconds_count {metrics.total_requests}")

            # Cache metrics
            lines.append("# HELP imhex_cache_hits Cache hits")
            lines.append("# TYPE imhex_cache_hits counter")
            lines.append(f"imhex_cache_hits {metrics.cache_hits}")

            lines.append("# HELP imhex_cache_misses Cache misses")
            lines.append("# TYPE imhex_cache_misses counter")
            lines.append(f"imhex_cache_misses {metrics.cache_misses}")

            # Connection metrics
            lines.append("# HELP imhex_connections_total Total connections")
            lines.append("# TYPE imhex_connections_total counter")
            lines.append(
                f"imhex_connections_total {metrics.total_connections}")

            lines.append("# HELP imhex_connections_active Active connections")
            lines.append("# TYPE imhex_connections_active gauge")
            lines.append(
                f"imhex_connections_active {metrics.active_connections}")

            # Error metrics
            lines.append("# HELP imhex_errors_timeout Timeout errors")
            lines.append("# TYPE imhex_errors_timeout counter")
            lines.append(f"imhex_errors_timeout {metrics.timeouts}")

            lines.append("# HELP imhex_errors_connection Connection errors")
            lines.append("# TYPE imhex_errors_connection counter")
            lines.append(
                f"imhex_errors_connection {metrics.connection_errors}")

            # Uptime
            lines.append("# HELP imhex_uptime_seconds Uptime in seconds")
            lines.append("# TYPE imhex_uptime_seconds gauge")
            lines.append(f"imhex_uptime_seconds {metrics.uptime_seconds()}")

            return "\n".join(lines) + "\n"

    def print_summary(self):
        """Print metrics summary."""
        with self._lock:
            print("\n" + "=" * 70)
            print("ImHex MCP Server - Health and Metrics Summary")
            print("=" * 70)

            # Uptime
            uptime = self.metrics.uptime_seconds()
            uptime_str = str(timedelta(seconds=int(uptime)))
            print(f"\nUptime: {uptime_str}")

            # Request metrics
            print("\nRequests:")
            print(f"  Total: {self.metrics.total_requests}")
            print(f"  Successful: {self.metrics.successful_requests}")
            print(f"  Failed: {self.metrics.failed_requests}")
            print(f"  Success Rate: {self.metrics.success_rate():.1f}%")
            print(f"  Error Rate: {self.metrics.error_rate():.1f}%")

            # Timing
            if self.metrics.total_requests > 0:
                print("\nLatency:")
                print(f"  Average: {self.metrics.avg_request_time_ms():.1f}ms")
                print(f"  Min: {self.metrics.min_request_time_ms:.1f}ms")
                print(f"  Max: {self.metrics.max_request_time_ms:.1f}ms")

            # Cache
            if self.metrics.cache_hits + self.metrics.cache_misses > 0:
                print("\nCache:")
                print(f"  Hits: {self.metrics.cache_hits}")
                print(f"  Misses: {self.metrics.cache_misses}")
                print(f"  Hit Rate: {self.metrics.cache_hit_rate():.1f}%")

            # Connections
            print("\nConnections:")
            print(f"  Total: {self.metrics.total_connections}")
            print(f"  Active: {self.metrics.active_connections}")
            print(f"  Failures: {self.metrics.connection_failures}")

            # Errors
            if self.metrics.timeouts + self.metrics.connection_errors + self.metrics.other_errors > 0:
                print("\nErrors:")
                if self.metrics.timeouts > 0:
                    print(f"  Timeouts: {self.metrics.timeouts}")
                if self.metrics.connection_errors > 0:
                    print(
                        f"  Connection Errors: {self.metrics.connection_errors}")
                if self.metrics.other_errors > 0:
                    print(f"  Other Errors: {self.metrics.other_errors}")

            # Health status
            print(
                f"\nOverall Status: {self.get_overall_status().value.upper()}")

            print("=" * 70 + "\n")

    def reset_metrics(self):
        """Reset all metrics."""
        with self._lock:
            self.metrics = Metrics()
            self.health_checks = {}
            logger.info("Metrics reset")


# Global health monitor instance
_monitor: Optional[HealthMonitor] = None
_monitor_lock = threading.Lock()


def get_health_monitor() -> HealthMonitor:
    """Get global health monitor instance (singleton)."""
    global _monitor

    if _monitor is None:
        with _monitor_lock:
            if _monitor is None:
                _monitor = HealthMonitor()

    return _monitor
