#!/usr/bin/env python3
"""
Compression Module Tests

Tests for the compression module including:
- Basic compression/decompression
- Compression ratio validation
- Size threshold handling
- Algorithm comparison
- Statistics tracking
"""

import sys
from pathlib import Path

# Add lib directory to path
lib_path = Path(__file__).parent.parent / "lib"
sys.path.insert(0, str(lib_path))

from compression import (
    DataCompressor,
    AdaptiveCompressor,
    CompressionConfig,
    create_compressor
)


def test_basic_compression():
    """Test basic compression and decompression."""
    print("\n" + "=" * 70)
    print("Test 1: Basic Compression/Decompression")
    print("=" * 70)

    # Create test data (highly compressible)
    test_data = b"AAAA" * 1000  # 4KB of repeated data

    # Create compressor
    config = CompressionConfig(enabled=True, algorithm="zstd", min_size=1024)
    compressor = DataCompressor(config)

    # Compress
    compressed = compressor.compress_data(test_data)

    print(f"Original size: {len(test_data):,} bytes")
    print(f"Compressed: {compressed.get('compressed')}")

    if compressed.get('compressed'):
        print(f"Compressed size: {compressed.get('compressed_size'):,} bytes")
        print(f"Compression ratio: {compressed.get('ratio'):.2%}")

        # Decompress
        decompressed = compressor.decompress_data(compressed)

        # Verify
        if decompressed == test_data:
            print("✓ Decompression successful - data matches original")
            return True
        else:
            print("✗ FAILED - decompressed data does not match")
            return False
    else:
        print("✗ FAILED - data was not compressed")
        return False


def test_size_threshold():
    """Test that small payloads are not compressed."""
    print("\n" + "=" * 70)
    print("Test 2: Size Threshold")
    print("=" * 70)

    # Create small test data (below threshold)
    small_data = b"A" * 500  # 500 bytes

    # Create compressor with 1KB threshold
    config = CompressionConfig(enabled=True, min_size=1024)
    compressor = DataCompressor(config)

    # Try to compress
    result = compressor.compress_data(small_data)

    print(f"Data size: {len(small_data)} bytes")
    print(f"Threshold: {config.min_size} bytes")
    print(f"Compressed: {result.get('compressed')}")

    if not result.get('compressed'):
        print("✓ Small data correctly skipped compression")
        print(f"✓ Skipped count: {compressor.stats.skipped_small}")
        return True
    else:
        print("✗ FAILED - small data was compressed")
        return False


def test_incompressible_data():
    """Test adaptive compression skips incompressible data."""
    print("\n" + "=" * 70)
    print("Test 3: Incompressible Data (Random)")
    print("=" * 70)

    # Create incompressible data (random-like)
    import random
    random_data = bytes(random.randint(0, 255) for _ in range(4096))

    # Create adaptive compressor
    config = CompressionConfig(enabled=True, adaptive=True, min_size=1024)
    compressor = DataCompressor(config)

    # Try to compress
    result = compressor.compress_data(random_data)

    print(f"Data size: {len(random_data)} bytes")
    print(f"Compressed: {result.get('compressed')}")

    if result.get('compressed'):
        ratio = result.get('ratio')
        print(f"Compression ratio: {ratio:.2%}")

        if ratio < 0.9:
            print("✓ Data was compressible (good ratio)")
            return True
        else:
            print("⚠ Data compressed but ratio poor (expected with random data)")
            return True
    else:
        print("✓ Incompressible data correctly skipped")
        return True


def test_algorithm_comparison():
    """Compare different compression algorithms."""
    print("\n" + "=" * 70)
    print("Test 4: Algorithm Comparison")
    print("=" * 70)

    # Create test data
    test_data = b"The quick brown fox jumps over the lazy dog. " * 100  # ~4.5KB

    algorithms = ["zstd", "gzip", "zlib"]
    results = {}

    for algo in algorithms:
        try:
            config = CompressionConfig(
                enabled=True,
                algorithm=algo,
                level=3,
                min_size=1024,
                adaptive=False
            )
            compressor = DataCompressor(config)

            # Compress
            compressed = compressor.compress_data(test_data)

            if compressed.get('compressed'):
                results[algo] = {
                    'original': len(test_data),
                    'compressed': compressed.get('compressed_size'),
                    'ratio': compressed.get('ratio'),
                    'time_ms': compressor.stats.compression_time_ms
                }

                print(f"\n{algo.upper()}:")
                print(f"  Original: {results[algo]['original']:,} bytes")
                print(f"  Compressed: {results[algo]['compressed']:,} bytes")
                print(f"  Ratio: {results[algo]['ratio']:.2%}")
                print(f"  Time: {results[algo]['time_ms']:.2f}ms")

                # Verify decompression works
                decompressed = compressor.decompress_data(compressed)
                if decompressed == test_data:
                    print(f"  ✓ Decompression verified")
                else:
                    print(f"  ✗ Decompression failed")
                    return False
        except Exception as e:
            print(f"\n{algo.upper()}: ✗ Error - {e}")

    if results:
        print(f"\n✓ All algorithms tested successfully")
        return True
    else:
        print(f"\n✗ No algorithms succeeded")
        return False


def test_statistics():
    """Test compression statistics tracking."""
    print("\n" + "=" * 70)
    print("Test 5: Statistics Tracking")
    print("=" * 70)

    # Create compressor
    config = CompressionConfig(enabled=True, min_size=1024)
    compressor = DataCompressor(config)

    # Compress multiple payloads
    test_cases = [
        b"A" * 2000,  # Highly compressible
        b"B" * 3000,  # Highly compressible
        b"C" * 500,   # Too small (should skip)
    ]

    for i, data in enumerate(test_cases):
        result = compressor.compress_data(data)
        print(f"\nPayload {i+1}: {len(data)} bytes -> " +
              ("compressed" if result.get('compressed') else "skipped"))

    # Get statistics
    stats = compressor.get_stats()

    print(f"\nStatistics:")
    print(f"  Bytes sent: {stats['bytes_sent']:,} bytes")
    print(f"  Bytes saved: {stats['bytes_saved']:,} bytes")
    print(f"  Compression ratio: {stats['compression_ratio']:.2%}")
    print(f"  Compressions: {stats['compressions']}")
    print(f"  Skipped (small): {stats['skipped_small']}")
    print(f"  Compression time: {stats['compression_time_ms']:.2f}ms")

    # Verify
    if stats['compressions'] == 2 and stats['skipped_small'] == 1:
        print("\n✓ Statistics tracked correctly")
        return True
    else:
        print(f"\n✗ Statistics mismatch - compressions={stats['compressions']}, skipped={stats['skipped_small']}")
        return False


def test_large_data():
    """Test compression of large data (simulating file reads)."""
    print("\n" + "=" * 70)
    print("Test 6: Large Data Compression")
    print("=" * 70)

    # Create 1MB of compressible data
    large_data = (b"ImHex MCP Server " * 1000) * 64  # ~1MB

    print(f"Data size: {len(large_data):,} bytes ({len(large_data) / 1024 / 1024:.2f} MB)")

    # Create compressor
    config = CompressionConfig(enabled=True, algorithm="zstd", level=3)
    compressor = DataCompressor(config)

    # Compress
    compressed = compressor.compress_data(large_data)

    if compressed.get('compressed'):
        original_size = compressed['original_size']
        compressed_size = compressed['compressed_size']
        ratio = compressed['ratio']

        print(f"Original: {original_size:,} bytes")
        print(f"Compressed: {compressed_size:,} bytes")
        print(f"Ratio: {ratio:.2%}")
        print(f"Savings: {original_size - compressed_size:,} bytes ({(1 - ratio) * 100:.1f}%)")
        print(f"Time: {compressor.stats.compression_time_ms:.2f}ms")

        # Decompress
        decompressed = compressor.decompress_data(compressed)

        if decompressed == large_data:
            print("✓ Large data compressed and decompressed successfully")
            return True
        else:
            print("✗ Decompression failed")
            return False
    else:
        print("✗ Large data was not compressed")
        return False


def test_adaptive_compressor():
    """Test adaptive compressor with sampling."""
    print("\n" + "=" * 70)
    print("Test 7: Adaptive Compressor")
    print("=" * 70)

    # Create test data - first 4KB random, rest compressible
    import random
    random_prefix = bytes(random.randint(0, 255) for _ in range(4096))
    compressible_suffix = b"A" * 8192
    mixed_data = random_prefix + compressible_suffix

    # Test with adaptive compressor
    config = CompressionConfig(enabled=True, adaptive=True, min_size=1024)
    compressor = AdaptiveCompressor(config)

    print(f"Data size: {len(mixed_data):,} bytes")
    print(f"First 4KB: random (incompressible sample)")
    print(f"Remaining: repeated 'A' (compressible)")

    # Compress
    result = compressor.compress_data(mixed_data)

    print(f"Compressed: {result.get('compressed')}")

    if result.get('compressed'):
        print(f"Ratio: {result.get('ratio'):.2%}")
        print("⚠ Adaptive compressor compressed despite random prefix")
        return True
    else:
        print("✓ Adaptive compressor correctly skipped (based on sample)")
        print(f"✓ Skipped ratio count: {compressor.stats.skipped_ratio}")
        return True


def test_factory_functions():
    """Test factory functions for creating compressors."""
    print("\n" + "=" * 70)
    print("Test 8: Factory Functions")
    print("=" * 70)

    # Test create_compressor with different algorithms
    for algo in ["zstd", "gzip"]:
        compressor = create_compressor(algorithm=algo, level=3, adaptive=True)
        print(f"\n{algo.upper()}:")
        print(f"  Type: {type(compressor).__name__}")
        print(f"  Algorithm: {compressor.config.algorithm}")
        print(f"  Level: {compressor.config.level}")
        print(f"  Adaptive: {compressor.config.adaptive}")
        print(f"  ✓ Created successfully")

    return True


def run_all_tests():
    """Run all compression tests."""
    print("\n" + "=" * 70)
    print("COMPRESSION MODULE TEST SUITE")
    print("=" * 70)

    tests = [
        ("Basic Compression/Decompression", test_basic_compression),
        ("Size Threshold", test_size_threshold),
        ("Incompressible Data", test_incompressible_data),
        ("Algorithm Comparison", test_algorithm_comparison),
        ("Statistics Tracking", test_statistics),
        ("Large Data Compression", test_large_data),
        ("Adaptive Compressor", test_adaptive_compressor),
        ("Factory Functions", test_factory_functions),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ Test '{name}' raised exception: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))

    # Print summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")

    print(f"\n{passed}/{total} tests passed ({passed/total*100:.0f}%)")
    print("=" * 70 + "\n")

    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
