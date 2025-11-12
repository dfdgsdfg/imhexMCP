#!/usr/bin/env python3
"""
ImHex MCP Profiling and Hot Path Optimization

Provides profiling tools to identify bottlenecks and optimize critical paths.
Includes CPU profiling, memory profiling, and performance analysis utilities.
"""

import cProfile
import pstats
import io
import time
import functools
import json
import sys
from pathlib import Path
from typing import Dict, Any, Optional, Callable, List, TypeVar, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
import threading

# Add lib directory to path
sys.path.insert(0, str(Path(__file__).parent))


T = TypeVar('T')


@dataclass
class TimingResult:
    """Result of a timed operation."""
    function_name: str
    duration_ms: float
    start_time: float
    end_time: float
    success: bool
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProfileStats:
    """Aggregated profiling statistics."""
    function_name: str
    call_count: int
    total_time_ms: float
    avg_time_ms: float
    min_time_ms: float
    max_time_ms: float
    percentile_95_ms: float
    percentile_99_ms: float


class PerformanceTimer:
    """
    Context manager for timing code blocks.

    Example:
        >>> with PerformanceTimer("expensive_operation") as timer:
        ...     do_expensive_work()
        >>> print(f"Duration: {timer.duration_ms:.2f}ms")
    """

    def __init__(self, name: str = "operation", metadata: Optional[Dict[str, Any]] = None):
        self.name = name
        self.metadata = metadata or {}
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.duration_ms: float = 0.0
        self.success: bool = True
        self.error: Optional[str] = None

    def __enter__(self) -> 'PerformanceTimer':
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.perf_counter()
        self.duration_ms = (self.end_time - self.start_time) * 1000

        if exc_type is not None:
            self.success = False
            self.error = str(exc_val)

        return False  # Don't suppress exceptions

    def get_result(self) -> TimingResult:
        """Get timing result."""
        return TimingResult(
            function_name=self.name,
            duration_ms=self.duration_ms,
            start_time=self.start_time or 0.0,
            end_time=self.end_time or 0.0,
            success=self.success,
            error=self.error,
            metadata=self.metadata
        )


def profile_function(output_file: Optional[str] = None, sort_by: str = 'cumulative'):
    """
    Decorator for profiling function with cProfile.

    Args:
        output_file: Optional file to save profile stats
        sort_by: Sort criterion (time, cumulative, calls, etc.)

    Returns:
        Decorator function

    Example:
        >>> @profile_function(sort_by='time')
        ... def expensive_function():
        ...     do_work()
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            profiler = cProfile.Profile()
            profiler.enable()

            try:
                result = func(*args, **kwargs)
            finally:
                profiler.disable()

                # Print stats
                s = io.StringIO()
                ps = pstats.Stats(profiler, stream=s).sort_stats(sort_by)
                ps.print_stats(20)  # Top 20 entries
                print(f"\nProfile for {func.__name__}:")
                print(s.getvalue())

                # Save to file if specified
                if output_file:
                    ps.dump_stats(output_file)

            return result

        return wrapper

    return decorator


def time_function(func: Callable[..., T]) -> Callable[..., T]:
    """
    Decorator for timing function execution.

    Prints execution time and returns result normally.

    Args:
        func: Function to time

    Returns:
        Wrapped function

    Example:
        >>> @time_function
        ... def slow_function():
        ...     time.sleep(1)
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        end = time.perf_counter()
        duration_ms = (end - start) * 1000

        print(f"{func.__name__}: {duration_ms:.2f}ms")

        return result

    return wrapper


class _MonitoredTimer:
    """Internal context manager that records timings to a PerformanceMonitor."""

    def __init__(self, monitor: 'PerformanceMonitor', name: str, metadata: Optional[Dict[str, Any]] = None):
        self.monitor = monitor
        self.name = name
        self.metadata = metadata
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.duration_ms: float = 0.0

    def __enter__(self):
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.perf_counter()
        self.duration_ms = (self.end_time - self.start_time) * 1000

        # Record timing in monitor
        if self.duration_ms > 0:
            self.monitor.record_timing(self.name, self.duration_ms)

        return False  # Don't suppress exceptions


class PerformanceMonitor:
    """
    Monitor and aggregate performance metrics across multiple calls.

    Example:
        >>> monitor = PerformanceMonitor()
        >>> with monitor.time("operation1"):
        ...     do_work()
        >>> with monitor.time("operation2"):
        ...     do_more_work()
        >>> stats = monitor.get_stats()
    """

    def __init__(self):
        self._timings: Dict[str, List[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def time(self, name: str, metadata: Optional[Dict[str, Any]] = None):
        """
        Create timer for operation that records timing automatically.

        Args:
            name: Operation name
            metadata: Optional metadata

        Returns:
            Context manager
        """
        return _MonitoredTimer(self, name, metadata)

    def record_timing(self, name: str, duration_ms: float) -> None:
        """
        Manually record timing.

        Args:
            name: Operation name
            duration_ms: Duration in milliseconds
        """
        with self._lock:
            self._timings[name].append(duration_ms)

    def get_stats(self, name: Optional[str] = None) -> Dict[str, ProfileStats]:
        """
        Get aggregated statistics.

        Args:
            name: Specific operation name (None = all operations)

        Returns:
            Dictionary of profile statistics
        """
        with self._lock:
            timings = {name: self._timings[name]} if name else dict(self._timings)

        stats = {}
        for func_name, times in timings.items():
            if not times:
                continue

            sorted_times = sorted(times)
            count = len(times)

            # Calculate percentiles
            p95_idx = int(count * 0.95)
            p99_idx = int(count * 0.99)

            stats[func_name] = ProfileStats(
                function_name=func_name,
                call_count=count,
                total_time_ms=sum(times),
                avg_time_ms=sum(times) / count,
                min_time_ms=min(times),
                max_time_ms=max(times),
                percentile_95_ms=sorted_times[p95_idx] if p95_idx < count else sorted_times[-1],
                percentile_99_ms=sorted_times[p99_idx] if p99_idx < count else sorted_times[-1]
            )

        return stats

    def print_stats(self, name: Optional[str] = None, sort_by: str = 'total') -> None:
        """
        Print performance statistics.

        Args:
            name: Specific operation name
            sort_by: Sort criterion (total, avg, max, count)
        """
        stats = self.get_stats(name)

        if not stats:
            print("No performance data collected")
            return

        # Sort stats
        sort_key_map = {
            'total': lambda s: s.total_time_ms,
            'avg': lambda s: s.avg_time_ms,
            'max': lambda s: s.max_time_ms,
            'count': lambda s: s.call_count
        }

        sorted_stats = sorted(
            stats.values(),
            key=sort_key_map.get(sort_by, sort_key_map['total']),
            reverse=True
        )

        # Print table
        print("\n" + "=" * 100)
        print("Performance Statistics")
        print("=" * 100)
        print(f"{'Operation':<40} {'Calls':>8} {'Total (ms)':>12} {'Avg (ms)':>12} {'P95 (ms)':>12} {'P99 (ms)':>12}")
        print("-" * 100)

        for stat in sorted_stats:
            print(f"{stat.function_name:<40} {stat.call_count:>8} "
                  f"{stat.total_time_ms:>12.2f} {stat.avg_time_ms:>12.2f} "
                  f"{stat.percentile_95_ms:>12.2f} {stat.percentile_99_ms:>12.2f}")

        print("=" * 100)

    def export_json(self, output_file: str) -> None:
        """
        Export statistics to JSON file.

        Args:
            output_file: Output file path
        """
        stats = self.get_stats()

        data = {
            name: {
                'call_count': stat.call_count,
                'total_time_ms': stat.total_time_ms,
                'avg_time_ms': stat.avg_time_ms,
                'min_time_ms': stat.min_time_ms,
                'max_time_ms': stat.max_time_ms,
                'percentile_95_ms': stat.percentile_95_ms,
                'percentile_99_ms': stat.percentile_99_ms
            }
            for name, stat in stats.items()
        }

        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2)

    def clear(self) -> None:
        """Clear all collected timings."""
        with self._lock:
            self._timings.clear()


class _TracedTimer:
    """Internal context manager that records path traces to HotPathAnalyzer."""

    def __init__(self, analyzer: 'HotPathAnalyzer', path: str, metadata: Optional[Dict[str, Any]] = None):
        self.analyzer = analyzer
        self.path = path
        self.metadata = metadata or {}
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.duration_ms: float = 0.0

    def __enter__(self):
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.perf_counter()
        self.duration_ms = (self.end_time - self.start_time) * 1000

        # Record path execution in analyzer
        self.analyzer.record_path(self.path, self.duration_ms, self.metadata)

        return False  # Don't suppress exceptions


class HotPathAnalyzer:
    """
    Analyze and identify hot paths (frequently executed code paths).

    Example:
        >>> analyzer = HotPathAnalyzer()
        >>> with analyzer.trace("endpoint:capabilities"):
        ...     handle_capabilities_request()
        >>> hot_paths = analyzer.get_hot_paths(min_calls=10)
    """

    def __init__(self):
        self._paths: Dict[str, List[Tuple[float, Dict[str, Any]]]] = defaultdict(list)
        self._lock = threading.Lock()

    def trace(self, path: str, metadata: Optional[Dict[str, Any]] = None):
        """
        Trace execution path.

        Args:
            path: Path identifier
            metadata: Optional metadata

        Returns:
            Context manager
        """
        return _TracedTimer(self, path, metadata)

    def record_path(self, path: str, duration_ms: float, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Manually record path execution.

        Args:
            path: Path identifier
            duration_ms: Execution duration in milliseconds
            metadata: Optional metadata
        """
        with self._lock:
            self._paths[path].append((duration_ms, metadata or {}))

    def get_hot_paths(
        self,
        min_calls: int = 1,
        sort_by: str = 'total_time'
    ) -> List[Tuple[str, Dict[str, Any]]]:
        """
        Get hot paths sorted by execution frequency or time.

        Args:
            min_calls: Minimum number of calls to be considered
            sort_by: Sort criterion (total_time, call_count, avg_time)

        Returns:
            List of (path, stats) tuples
        """
        with self._lock:
            paths = dict(self._paths)

        results = []
        for path, executions in paths.items():
            if len(executions) < min_calls:
                continue

            times = [t for t, _ in executions]
            total_time = sum(times)
            call_count = len(times)
            avg_time = total_time / call_count

            stats = {
                'call_count': call_count,
                'total_time_ms': total_time,
                'avg_time_ms': avg_time,
                'min_time_ms': min(times),
                'max_time_ms': max(times)
            }

            results.append((path, stats))

        # Sort results
        sort_key_map = {
            'total_time': lambda x: x[1]['total_time_ms'],
            'call_count': lambda x: x[1]['call_count'],
            'avg_time': lambda x: x[1]['avg_time_ms']
        }

        results.sort(key=sort_key_map.get(sort_by, sort_key_map['total_time']), reverse=True)

        return results

    def print_hot_paths(self, min_calls: int = 1, top_n: int = 20) -> None:
        """
        Print hot paths analysis.

        Args:
            min_calls: Minimum calls to include
            top_n: Number of top paths to show
        """
        hot_paths = self.get_hot_paths(min_calls)[:top_n]

        print("\n" + "=" * 90)
        print("Hot Path Analysis")
        print("=" * 90)
        print(f"{'Path':<50} {'Calls':>8} {'Total (ms)':>12} {'Avg (ms)':>12}")
        print("-" * 90)

        for path, stats in hot_paths:
            print(f"{path:<50} {stats['call_count']:>8} "
                  f"{stats['total_time_ms']:>12.2f} {stats['avg_time_ms']:>12.2f}")

        print("=" * 90)


class OptimizationSuggestions:
    """
    Analyze performance data and suggest optimizations.
    """

    @staticmethod
    def analyze_stats(stats: Dict[str, ProfileStats]) -> List[str]:
        """
        Analyze statistics and generate optimization suggestions.

        Args:
            stats: Profile statistics

        Returns:
            List of suggestion strings
        """
        suggestions = []

        for name, stat in stats.items():
            # High call count suggests caching opportunity
            if stat.call_count > 100 and stat.avg_time_ms > 1.0:
                suggestions.append(
                    f"Consider caching results for '{name}' "
                    f"({stat.call_count} calls, {stat.avg_time_ms:.2f}ms avg)"
                )

            # High variance suggests optimization opportunity
            if stat.max_time_ms > stat.avg_time_ms * 5:
                suggestions.append(
                    f"High variance in '{name}' "
                    f"(max: {stat.max_time_ms:.2f}ms, avg: {stat.avg_time_ms:.2f}ms) - "
                    f"investigate edge cases"
                )

            # Slow operations
            if stat.avg_time_ms > 100:
                suggestions.append(
                    f"Slow operation '{name}' ({stat.avg_time_ms:.2f}ms avg) - "
                    f"consider batching, async, or streaming"
                )

            # High total time
            if stat.total_time_ms > 10000:  # 10 seconds
                pct = (stat.total_time_ms / sum(s.total_time_ms for s in stats.values())) * 100
                suggestions.append(
                    f"'{name}' accounts for {pct:.1f}% of total execution time - "
                    f"primary optimization target"
                )

        return suggestions

    @staticmethod
    def print_suggestions(stats: Dict[str, ProfileStats]) -> None:
        """Print optimization suggestions."""
        suggestions = OptimizationSuggestions.analyze_stats(stats)

        if not suggestions:
            print("\nNo specific optimization suggestions at this time.")
            return

        print("\n" + "=" * 80)
        print("Optimization Suggestions")
        print("=" * 80)

        for i, suggestion in enumerate(suggestions, 1):
            print(f"{i}. {suggestion}")

        print("=" * 80)


# Global performance monitor instance
_global_monitor = PerformanceMonitor()


def get_global_monitor() -> PerformanceMonitor:
    """Get global performance monitor instance."""
    return _global_monitor


def monitored(name: Optional[str] = None):
    """
    Decorator to automatically monitor function performance.

    Args:
        name: Custom name for the operation (default: function name)

    Returns:
        Decorator function

    Example:
        >>> @monitored()
        ... def expensive_function():
        ...     do_work()
        >>> get_global_monitor().print_stats()
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        operation_name = name or func.__name__

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with _global_monitor.time(operation_name):
                return func(*args, **kwargs)

        return wrapper

    return decorator


# Convenience functions for common profiling patterns

def profile_endpoint(
    client: Any,
    endpoint: str,
    data: Optional[Dict[str, Any]] = None,
    iterations: int = 100
) -> ProfileStats:
    """
    Profile specific endpoint with multiple iterations.

    Args:
        client: ImHex MCP client
        endpoint: Endpoint to profile
        data: Request data
        iterations: Number of iterations

    Returns:
        Profile statistics
    """
    monitor = PerformanceMonitor()

    for i in range(iterations):
        with monitor.time(endpoint):
            client.send_request(endpoint, data)

    stats = monitor.get_stats(endpoint)
    return stats[endpoint] if endpoint in stats else None


def compare_implementations(
    implementations: Dict[str, Callable[[], Any]],
    iterations: int = 100
) -> Dict[str, ProfileStats]:
    """
    Compare performance of different implementations.

    Args:
        implementations: Dictionary of name -> function
        iterations: Iterations per implementation

    Returns:
        Statistics for each implementation
    """
    monitor = PerformanceMonitor()

    for name, impl in implementations.items():
        for _ in range(iterations):
            with monitor.time(name):
                impl()

    return monitor.get_stats()
