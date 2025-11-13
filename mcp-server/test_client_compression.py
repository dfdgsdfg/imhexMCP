#!/usr/bin/env python3
"""
AsyncImHexClient Compression Integration Test

Tests the compression integration in AsyncImHexClient:
- Client initialization with compression
- Binary data compression/decompression
- Compression statistics
"""

import sys
import asyncio
from pathlib import Path

# Add lib directory to path
lib_path = Path(__file__).parent.parent / "lib"
sys.path.insert(0, str(lib_path))

from async_client import AsyncImHexClient
from data_compression import DataCompressor


async def test_client_compression():
    """Test AsyncImHexClient compression integration."""
    print("=" * 70)
    print("AsyncImHexClient Compression Integration Test")
    print("=" * 70)

    # Test 1: Create client with compression enabled
    print("\n[1/4] Creating AsyncImHexClient with compression enabled...")
    client = AsyncImHexClient(
        host="localhost",
        port=31337,
        enable_compression=True,
        compression_algorithm="zstd",
        compression_level=3,
        compression_min_size=100
    )
    print("  ✓ Client created successfully")

    # Test 2: Check compression stats
    print("\n[2/4] Checking compression statistics...")
    stats = client.compression_stats()
    print(f"  Compression enabled: {stats.get('enabled', False)}")
    print(f"  Compressions performed: {stats.get('compressions', 0)}")
    print(f"  Decompressions performed: {stats.get('decompressions', 0)}")

    # Test 3: Compress hex-encoded binary data
    print("\n[3/4] Testing binary data compression...")

    # Create 4KB of compressible hex data (repeating pattern)
    test_data = ("00" * 1024) + ("ff" * 1024) + ("aa" * 1024) + ("55" * 1024)
    original_size = len(test_data) // 2  # Convert hex chars to bytes
    print(f"  Original data: {original_size} bytes (as hex: {len(test_data)} chars)")

    # Compress
    compressed = client.compress_binary_data(test_data)
    print(f"  Compressed: {compressed.get('compressed', False)}")

    if compressed.get('compressed'):
        compressed_size = compressed.get('compressed_size', 0)
        ratio = compressed.get('ratio', 1.0)
        savings = ((1 - ratio) * 100)
        print(f"  Compressed size: {compressed_size} bytes")
        print(f"  Compression ratio: {ratio:.4f}")
        print(f"  Space savings: {savings:.1f}%")

    # Test 4: Decompress back
    print("\n[4/4] Testing binary data decompression...")
    decompressed_hex = client.decompress_binary_data(compressed)
    decompressed_size = len(decompressed_hex) // 2
    print(f"  Decompressed size: {decompressed_size} bytes")
    print(f"  Data matches original: {decompressed_hex == test_data}")

    # Final stats
    print("\n" + "-" * 70)
    print("Final Compression Statistics:")
    final_stats = client.compression_stats()
    print(f"  Compressions: {final_stats.get('compressions', 0)}")
    print(f"  Decompressions: {final_stats.get('decompressions', 0)}")
    print(f"  Bytes saved: {final_stats.get('bytes_saved', 0)}")
    print(f"  Compression ratio: {final_stats.get('compression_ratio', 0):.2%}")
    print("=" * 70)

    return decompressed_hex == test_data


async def test_client_without_compression():
    """Test AsyncImHexClient with compression disabled."""
    print("\n\nTesting client with compression DISABLED...")

    client = AsyncImHexClient(
        host="localhost",
        port=31337,
        enable_compression=False
    )

    stats = client.compression_stats()
    print(f"  Compression enabled: {stats.get('enabled', False)}")
    print(f"  Message: {stats.get('message', 'N/A')}")

    return not stats.get('enabled', True)


async def main():
    """Run all tests."""

    # Test with compression enabled
    test1_passed = await test_client_compression()

    # Test with compression disabled
    test2_passed = await test_client_without_compression()

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"  Compression integration: {'✓ PASS' if test1_passed else '✗ FAIL'}")
    print(f"  Compression disabled mode: {'✓ PASS' if test2_passed else '✗ FAIL'}")

    all_passed = test1_passed and test2_passed
    print(f"\nOverall: {'✓ ALL TESTS PASSED' if all_passed else '✗ SOME TESTS FAILED'}")
    print("=" * 70)

    return all_passed


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
