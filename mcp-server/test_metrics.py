"""
Tests for Prometheus metrics module.

This module tests the metrics collection and export functionality including:
- Metric initialization and registration
- Request tracking with decorators
- Compression metrics recording
- Connection pool metrics
- Cache metrics
- Batch metrics
- Health check metrics
- Metrics export to Prometheus format
"""

import sys
import time
from pathlib import Path

import pytest
from prometheus_client import CollectorRegistry

# Add lib directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))

from metrics import ImHexMCPMetrics, get_metrics, initialize_metrics


class TestMetricsInitialization:
    """Test metrics initialization."""

    @pytest.mark.unit
    def test_default_initialization(self):
        """Test default metrics initialization."""
        metrics = ImHexMCPMetrics()

        assert metrics.registry is not None
        assert metrics.request_count is not None
        assert metrics.request_duration is not None
        assert metrics.active_requests is not None
        assert metrics.compression_ratio is not None
        assert metrics.bytes_transferred is not None

    @pytest.mark.unit
    def test_custom_registry(self):
        """Test initialization with custom registry."""
        registry = CollectorRegistry()
        metrics = ImHexMCPMetrics(registry=registry)

        assert metrics.registry is registry

    @pytest.mark.unit
    def test_set_info(self):
        """Test setting server info."""
        metrics = ImHexMCPMetrics()
        metrics.set_info(
            version="1.0.0",
            python_version="3.11.0",
            custom_field="test"
        )

        # Verify info was set (check metrics output)
        metrics_data = metrics.get_metrics()
        assert b"imhex_mcp_info" in metrics_data
        assert b"version=\"1.0.0\"" in metrics_data


class TestRequestMetrics:
    """Test request metrics tracking."""

    @pytest.mark.unit
    def test_request_count_increment(self):
        """Test request count increments."""
        metrics = ImHexMCPMetrics()

        # Record successful request
        metrics.request_count.labels(endpoint="test", status="success").inc()

        # Check metrics output
        metrics_data = metrics.get_metrics().decode()
        assert "imhex_mcp_requests_total" in metrics_data
        assert 'endpoint="test"' in metrics_data

    @pytest.mark.unit
    def test_active_requests_gauge(self):
        """Test active requests gauge."""
        metrics = ImHexMCPMetrics()

        assert metrics.active_requests._value._value == 0

        metrics.active_requests.inc()
        assert metrics.active_requests._value._value == 1

        metrics.active_requests.dec()
        assert metrics.active_requests._value._value == 0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_track_request_decorator_success(self):
        """Test request tracking decorator for successful requests."""
        metrics = ImHexMCPMetrics()

        @metrics.track_request('test_endpoint')
        async def test_func():
            return "success"

        result = await test_func()

        assert result == "success"

        # Check that metrics were recorded
        metrics_data = metrics.get_metrics().decode()
        assert "test_endpoint" in metrics_data

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_track_request_decorator_error(self):
        """Test request tracking decorator for failed requests."""
        metrics = ImHexMCPMetrics()

        @metrics.track_request('test_endpoint')
        async def test_func():
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            await test_func()

        # Check that error was recorded
        metrics_data = metrics.get_metrics().decode()
        assert "imhex_mcp_errors_total" in metrics_data
        assert "ValueError" in metrics_data


class TestCompressionMetrics:
    """Test compression metrics recording."""

    @pytest.mark.unit
    def test_record_compression_success(self):
        """Test recording successful compression."""
        metrics = ImHexMCPMetrics()

        metrics.record_compression(
            operation='compress',
            duration_seconds=0.001,
            original_size=1000,
            compressed_size=500,
            result='success'
        )

        # Check metrics output
        metrics_data = metrics.get_metrics().decode()
        assert "imhex_mcp_compression_duration_seconds" in metrics_data
        assert "imhex_mcp_compression_ratio" in metrics_data
        assert "imhex_mcp_compression_bytes_saved_total" in metrics_data

    @pytest.mark.unit
    def test_record_compression_skipped(self):
        """Test recording skipped compression."""
        metrics = ImHexMCPMetrics()

        metrics.record_compression(
            operation='compress',
            duration_seconds=0.001,
            original_size=500,
            result='skipped_small'
        )

        # Check that operation was counted
        metrics_data = metrics.get_metrics().decode()
        assert "skipped_small" in metrics_data

    @pytest.mark.unit
    def test_record_decompression(self):
        """Test recording decompression."""
        metrics = ImHexMCPMetrics()

        metrics.record_decompression(
            duration_seconds=0.0005,
            compressed_size=500,
            decompressed_size=1000
        )

        # Check metrics output
        metrics_data = metrics.get_metrics().decode()
        assert 'operation="decompress"' in metrics_data
        assert "imhex_mcp_bytes_transferred_total" in metrics_data

    @pytest.mark.unit
    def test_compression_ratio_tracking(self):
        """Test compression ratio histogram."""
        metrics = ImHexMCPMetrics()

        # Record multiple compressions with different ratios
        metrics.record_compression('compress', 0.001, 1000, 800, 'success')  # 0.8 ratio
        metrics.record_compression('compress', 0.001, 1000, 500, 'success')  # 0.5 ratio
        metrics.record_compression('compress', 0.001, 1000, 200, 'success')  # 0.2 ratio

        metrics_data = metrics.get_metrics().decode()
        assert "imhex_mcp_compression_ratio_bucket" in metrics_data


class TestConnectionPoolMetrics:
    """Test connection pool metrics."""

    @pytest.mark.unit
    def test_update_pool_stats(self):
        """Test updating connection pool statistics."""
        metrics = ImHexMCPMetrics()

        metrics.update_pool_stats(active=5, idle=3, total=8)

        metrics_data = metrics.get_metrics().decode()
        assert 'state="active"' in metrics_data
        assert 'state="idle"' in metrics_data
        assert 'state="total"' in metrics_data

    @pytest.mark.unit
    def test_record_pool_operation(self):
        """Test recording pool operations."""
        metrics = ImHexMCPMetrics()

        metrics.record_pool_operation(
            operation='acquire',
            result='success',
            wait_time_seconds=0.05
        )

        metrics_data = metrics.get_metrics().decode()
        assert "imhex_mcp_pool_operations_total" in metrics_data
        assert "imhex_mcp_pool_wait_duration_seconds" in metrics_data

    @pytest.mark.unit
    def test_pool_wait_time_histogram(self):
        """Test pool wait time histogram."""
        metrics = ImHexMCPMetrics()

        # Record multiple wait times
        metrics.record_pool_operation('acquire', 'success', 0.001)
        metrics.record_pool_operation('acquire', 'success', 0.01)
        metrics.record_pool_operation('acquire', 'success', 0.1)

        metrics_data = metrics.get_metrics().decode()
        assert "imhex_mcp_pool_wait_duration_seconds_bucket" in metrics_data


class TestCacheMetrics:
    """Test cache metrics."""

    @pytest.mark.unit
    def test_record_cache_hit(self):
        """Test recording cache hit."""
        metrics = ImHexMCPMetrics()

        metrics.record_cache_operation('hit', size=100, bytes_size=10000)

        metrics_data = metrics.get_metrics().decode()
        assert "imhex_mcp_cache_operations_total" in metrics_data
        assert 'result="hit"' in metrics_data

    @pytest.mark.unit
    def test_record_cache_miss(self):
        """Test recording cache miss."""
        metrics = ImHexMCPMetrics()

        metrics.record_cache_operation('miss')

        metrics_data = metrics.get_metrics().decode()
        assert 'result="miss"' in metrics_data

    @pytest.mark.unit
    def test_cache_size_gauge(self):
        """Test cache size gauge updates."""
        metrics = ImHexMCPMetrics()

        metrics.record_cache_operation('set', size=50)
        metrics.record_cache_operation('set', size=51)

        metrics_data = metrics.get_metrics().decode()
        assert "imhex_mcp_cache_size" in metrics_data


class TestBatchMetrics:
    """Test batch processing metrics."""

    @pytest.mark.unit
    def test_record_batch(self):
        """Test recording batch metrics."""
        metrics = ImHexMCPMetrics()

        metrics.record_batch(batch_size=10, wait_time_seconds=0.005)

        metrics_data = metrics.get_metrics().decode()
        assert "imhex_mcp_batch_size" in metrics_data
        assert "imhex_mcp_batch_wait_duration_seconds" in metrics_data

    @pytest.mark.unit
    def test_batch_size_histogram(self):
        """Test batch size histogram."""
        metrics = ImHexMCPMetrics()

        # Record various batch sizes
        metrics.record_batch(1, 0.001)
        metrics.record_batch(5, 0.005)
        metrics.record_batch(20, 0.01)
        metrics.record_batch(50, 0.02)

        metrics_data = metrics.get_metrics().decode()
        assert "imhex_mcp_batch_size_bucket" in metrics_data


class TestHealthMetrics:
    """Test health monitoring metrics."""

    @pytest.mark.unit
    def test_record_health_check_healthy(self):
        """Test recording healthy status."""
        metrics = ImHexMCPMetrics()

        metrics.record_health_check(healthy=True)

        metrics_data = metrics.get_metrics().decode()
        assert "imhex_mcp_health_checks_total" in metrics_data
        assert 'status="healthy"' in metrics_data

    @pytest.mark.unit
    def test_record_health_check_unhealthy(self):
        """Test recording unhealthy status."""
        metrics = ImHexMCPMetrics()

        metrics.record_health_check(healthy=False)

        metrics_data = metrics.get_metrics().decode()
        assert 'status="unhealthy"' in metrics_data

    @pytest.mark.unit
    def test_last_health_check_timestamp(self):
        """Test last health check timestamp."""
        metrics = ImHexMCPMetrics()

        before = time.time()
        metrics.record_health_check(healthy=True)
        after = time.time()

        metrics_data = metrics.get_metrics().decode()
        assert "imhex_mcp_last_health_check_timestamp" in metrics_data


class TestErrorMetrics:
    """Test error tracking metrics."""

    @pytest.mark.unit
    def test_record_error(self):
        """Test recording an error."""
        metrics = ImHexMCPMetrics()

        metrics.record_error('ValueError', 'test_endpoint')

        metrics_data = metrics.get_metrics().decode()
        assert "imhex_mcp_errors_total" in metrics_data
        assert 'error_type="ValueError"' in metrics_data
        assert 'endpoint="test_endpoint"' in metrics_data


class TestMetricsExport:
    """Test metrics export functionality."""

    @pytest.mark.unit
    def test_get_metrics_format(self):
        """Test metrics export format."""
        metrics = ImHexMCPMetrics()

        # Record some metrics
        metrics.request_count.labels(endpoint="test", status="success").inc()

        metrics_data = metrics.get_metrics()

        assert isinstance(metrics_data, bytes)
        assert b"# HELP" in metrics_data
        assert b"# TYPE" in metrics_data

    @pytest.mark.unit
    def test_get_content_type(self):
        """Test content type for metrics."""
        metrics = ImHexMCPMetrics()

        content_type = metrics.get_content_type()

        assert content_type.startswith("text/plain")


class TestGlobalMetrics:
    """Test global metrics singleton."""

    @pytest.mark.unit
    def test_get_metrics_singleton(self):
        """Test global metrics singleton."""
        # Reset global metrics
        import metrics as metrics_module
        metrics_module._metrics = None

        metrics1 = get_metrics()
        metrics2 = get_metrics()

        assert metrics1 is metrics2

    @pytest.mark.unit
    def test_initialize_metrics(self):
        """Test initialize_metrics helper."""
        # Reset global metrics
        import metrics as metrics_module
        metrics_module._metrics = None

        metrics = initialize_metrics(version="2.0.0", custom="value")

        assert metrics is not None

        metrics_data = metrics.get_metrics().decode()
        assert "version=\"2.0.0\"" in metrics_data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
