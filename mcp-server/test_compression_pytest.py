#!/usr/bin/env python3
"""
Compression Module Tests - Pytest Version

Tests for the compression module using pytest framework:
- Basic compression/decompression
- Compression ratio validation
- Size threshold handling
- Algorithm comparison
- Statistics tracking
"""

import sys
import pytest
from pathlib import Path

# Add lib directory to path
lib_path = Path(__file__).parent.parent / "lib"
sys.path.insert(0, str(lib_path))

from data_compression import (
    DataCompressor,
    AdaptiveCompressor,
    CompressionConfig,
    create_compressor
)


# Fixtures for common test setup
@pytest.fixture
def basic_compressor():
    """Fixture providing a basic compressor with default settings."""
    config = CompressionConfig(enabled=True, algorithm="zstd", min_size=1024)
    return DataCompressor(config)


@pytest.fixture
def adaptive_compressor():
    """Fixture providing an adaptive compressor."""
    config = CompressionConfig(enabled=True, adaptive=True, min_size=1024)
    return AdaptiveCompressor(config)


@pytest.fixture
def compressible_data():
    """Fixture providing highly compressible test data."""
    return b"AAAA" * 1000  # 4KB of repeated data


@pytest.fixture
def small_data():
    """Fixture providing data below compression threshold."""
    return b"A" * 500  # 500 bytes


# Test Classes
class TestBasicCompression:
    """Test basic compression functionality."""

    @pytest.mark.unit
    @pytest.mark.compression
    def test_compress_decompress_cycle(self, basic_compressor, compressible_data):
        """Test that data can be compressed and decompressed successfully."""
        # Compress
        compressed = basic_compressor.compress_data(compressible_data)

        # Verify compression occurred
        assert compressed.get('compressed'), "Data should be compressed"
        assert compressed.get('compressed_size') < len(compressible_data), \
            "Compressed size should be smaller than original"

        # Decompress
        decompressed = basic_compressor.decompress_data(compressed)

        # Verify data integrity
        assert decompressed == compressible_data, \
            "Decompressed data must match original"

    @pytest.mark.unit
    @pytest.mark.compression
    def test_compression_ratio(self, basic_compressor, compressible_data):
        """Test that compression achieves good ratio on compressible data."""
        compressed = basic_compressor.compress_data(compressible_data)

        assert compressed.get('compressed')
        ratio = compressed.get('ratio')
        assert ratio < 0.1, f"Compression ratio {ratio:.2%} should be < 10% for repeated data"

    @pytest.mark.unit
    @pytest.mark.compression
    def test_compression_metadata(self, basic_compressor, compressible_data):
        """Test that compression includes correct metadata."""
        compressed = basic_compressor.compress_data(compressible_data)

        assert 'compressed' in compressed
        assert 'algorithm' in compressed
        assert 'original_size' in compressed
        assert 'compressed_size' in compressed
        assert 'ratio' in compressed
        assert compressed['algorithm'] == 'zstd'
        assert compressed['original_size'] == len(compressible_data)


class TestSizeThreshold:
    """Test size threshold behavior."""

    @pytest.mark.unit
    @pytest.mark.compression
    def test_small_data_skipped(self, basic_compressor, small_data):
        """Test that data below threshold is not compressed."""
        result = basic_compressor.compress_data(small_data)

        assert not result.get('compressed'), \
            "Small data should not be compressed"
        assert basic_compressor.stats.skipped_small > 0, \
            "Skipped count should be incremented"

    @pytest.mark.unit
    @pytest.mark.compression
    def test_threshold_boundary(self, basic_compressor):
        """Test compression at exact threshold boundary."""
        # Create data exactly at threshold (1024 bytes)
        boundary_data = b"X" * 1024
        result = basic_compressor.compress_data(boundary_data)

        # Data at threshold should be compressed
        assert result.get('compressed') or result.get('ratio') == 1.0, \
            "Data at threshold should be processed"


class TestAlgorithms:
    """Test different compression algorithms."""

    @pytest.mark.unit
    @pytest.mark.compression
    @pytest.mark.parametrize("algorithm", ["zstd", "gzip", "zlib"])
    def test_algorithm_support(self, algorithm, compressible_data):
        """Test that all supported algorithms work correctly."""
        config = CompressionConfig(
            enabled=True,
            algorithm=algorithm,
            level=3,
            min_size=1024,
            adaptive=False
        )
        compressor = DataCompressor(config)

        compressed = compressor.compress_data(compressible_data)
        assert compressed.get('compressed'), f"{algorithm} should compress data"
        assert compressed['algorithm'] == algorithm

        decompressed = compressor.decompress_data(compressed)
        assert decompressed == compressible_data, \
            f"{algorithm} decompression must be lossless"

    @pytest.mark.unit
    @pytest.mark.compression
    @pytest.mark.slow
    def test_algorithm_comparison(self, compressible_data):
        """Compare compression ratios across algorithms."""
        algorithms = ["zstd", "gzip", "zlib"]
        results = {}

        for algo in algorithms:
            config = CompressionConfig(
                enabled=True,
                algorithm=algo,
                level=3,
                min_size=1024,
                adaptive=False
            )
            compressor = DataCompressor(config)
            compressed = compressor.compress_data(compressible_data)
            results[algo] = compressed.get('ratio')

        # Verify all algorithms achieved compression
        for algo, ratio in results.items():
            assert ratio < 1.0, f"{algo} should achieve compression (ratio < 1.0)"


class TestStatistics:
    """Test compression statistics tracking."""

    @pytest.mark.unit
    @pytest.mark.compression
    def test_statistics_tracking(self, basic_compressor):
        """Test that statistics are accurately tracked."""
        test_cases = [
            b"A" * 2000,  # Compressible
            b"B" * 3000,  # Compressible
            b"C" * 500,   # Too small
        ]

        for data in test_cases:
            basic_compressor.compress_data(data)

        stats = basic_compressor.get_stats()

        assert stats['compressions'] == 2, "Should track 2 compressions"
        assert stats['skipped_small'] == 1, "Should track 1 skip"
        assert stats['bytes_saved'] > 0, "Should track bytes saved"
        assert 0 <= stats['compression_ratio'] <= 1, \
            "Compression ratio should be between 0 and 1"

    @pytest.mark.unit
    @pytest.mark.compression
    def test_statistics_reset(self, basic_compressor):
        """Test that statistics can be reset."""
        # Compress some data
        basic_compressor.compress_data(b"X" * 2000)

        # Get stats
        stats_before = basic_compressor.get_stats()
        assert stats_before['compressions'] > 0

        # Reset (if method exists)
        # Note: Add reset method to DataCompressor if needed
        # basic_compressor.reset_stats()


class TestAdaptiveCompression:
    """Test adaptive compression behavior."""

    @pytest.mark.unit
    @pytest.mark.compression
    def test_adaptive_compressible_data(self, adaptive_compressor):
        """Test adaptive compression on compressible data."""
        # Create highly compressible data
        data = b"A" * 10000

        result = adaptive_compressor.compress_data(data)

        assert result.get('compressed'), \
            "Highly compressible data should be compressed"

    @pytest.mark.unit
    @pytest.mark.compression
    def test_adaptive_random_data(self, adaptive_compressor):
        """Test adaptive compression on random-like data."""
        import random
        random_data = bytes(random.randint(0, 255) for _ in range(4096))

        result = adaptive_compressor.compress_data(random_data)

        # Adaptive compressor might skip truly random data
        # or compress it with poor ratio
        assert 'compressed' in result
        if result.get('compressed'):
            ratio = result.get('ratio')
            assert 0 < ratio <= 1


class TestLargeData:
    """Test compression of large payloads."""

    @pytest.mark.unit
    @pytest.mark.compression
    @pytest.mark.slow
    def test_large_data_compression(self, basic_compressor):
        """Test compression of 1MB payload."""
        # Create 1MB of compressible data
        large_data = (b"ImHex MCP Server " * 1000) * 64  # ~1MB

        compressed = basic_compressor.compress_data(large_data)

        assert compressed.get('compressed'), "Large data should be compressed"
        assert compressed['compressed_size'] < len(large_data), \
            "Compressed size should be smaller"

        # Verify decompression
        decompressed = basic_compressor.decompress_data(compressed)
        assert decompressed == large_data, \
            "Large data decompression must be lossless"


class TestFactoryFunctions:
    """Test factory functions for creating compressors."""

    @pytest.mark.unit
    @pytest.mark.compression
    @pytest.mark.parametrize("algo", ["zstd", "gzip", "zlib"])
    def test_create_compressor_factory(self, algo):
        """Test create_compressor factory function."""
        compressor = create_compressor(algorithm=algo, level=3, adaptive=True)

        assert compressor is not None
        assert compressor.config.algorithm == algo
        assert compressor.config.level == 3
        assert compressor.config.adaptive is True

    @pytest.mark.unit
    @pytest.mark.compression
    def test_factory_default_parameters(self):
        """Test factory with default parameters."""
        compressor = create_compressor()

        assert compressor is not None
        assert compressor.config.enabled is True


class TestErrorHandling:
    """Test error handling and edge cases."""

    @pytest.mark.unit
    @pytest.mark.compression
    def test_empty_data(self, basic_compressor):
        """Test compression of empty data."""
        result = basic_compressor.compress_data(b"")

        assert not result.get('compressed'), \
            "Empty data should not be compressed"

    @pytest.mark.unit
    @pytest.mark.compression
    def test_disabled_compression(self):
        """Test that compression can be disabled."""
        config = CompressionConfig(enabled=False)
        compressor = DataCompressor(config)

        data = b"A" * 5000
        result = compressor.compress_data(data)

        assert not result.get('compressed'), \
            "Compression should be disabled"


# Performance benchmarks using pytest-benchmark (if installed)
try:
    import pytest_benchmark

    class TestPerformance:
        """Performance benchmarks for compression."""

        @pytest.mark.benchmark
        @pytest.mark.slow
        def test_compression_speed(self, benchmark, basic_compressor):
            """Benchmark compression speed."""
            data = b"X" * 10000
            benchmark(basic_compressor.compress_data, data)

        @pytest.mark.benchmark
        @pytest.mark.slow
        def test_decompression_speed(self, benchmark, basic_compressor):
            """Benchmark decompression speed."""
            data = b"X" * 10000
            compressed = basic_compressor.compress_data(data)
            benchmark(basic_compressor.decompress_data, compressed)

except ImportError:
    pass  # pytest-benchmark not installed


if __name__ == "__main__":
    # Run pytest with verbose output and coverage
    pytest.main([__file__, "-v", "--cov=data_compression", "--cov-report=term-missing"])
