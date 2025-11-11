#!/usr/bin/env python3
"""
Comprehensive Test Suite for v0.4.0 Features
Tests: Chunked Read, Binary Diffing, and Disassembly
"""

import os
import sys
import tempfile
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from server import ImHexClient, ServerConfig


def create_test_binary_with_code():
    """Create a test binary file with x86 machine code."""
    fd, filepath = tempfile.mkstemp(suffix='.bin', prefix='imhex_v040_test_')

    with os.fdopen(fd, 'wb') as f:
        # Header
        f.write(b'V040TEST')  # Magic

        # Some x86-64 machine code (simple instructions)
        # mov eax, 1
        f.write(b'\xb8\x01\x00\x00\x00')
        # mov ebx, 2
        f.write(b'\xbb\x02\x00\x00\x00')
        # add eax, ebx
        f.write(b'\x01\xd8')
        # ret
        f.write(b'\xc3')

        # Padding
        f.write(b'\x00' * 100)

        # More data for chunked reading
        for i in range(1000):
            f.write(bytes([i % 256]))

    return filepath


def create_similar_binary():
    """Create a similar binary for diff testing."""
    fd, filepath = tempfile.mkstemp(suffix='.bin', prefix='imhex_v040_diff_')

    with os.fdopen(fd, 'wb') as f:
        # Same header
        f.write(b'V040TEST')

        # Slightly different x86 code
        # mov eax, 2 (changed from 1)
        f.write(b'\xb8\x02\x00\x00\x00')
        # mov ebx, 2 (same)
        f.write(b'\xbb\x02\x00\x00\x00')
        # add eax, ebx (same)
        f.write(b'\x01\xd8')
        # ret (same)
        f.write(b'\xc3')

        # Same padding
        f.write(b'\x00' * 100)

        # Different data pattern
        for i in range(1000):
            f.write(bytes([(i + 50) % 256]))

    return filepath


def main():
    """Run comprehensive v0.4.0 feature tests."""
    print("="*70)
    print("ImHex MCP v0.4.0 - Comprehensive Feature Tests")
    print("="*70)
    print()

    # Create test files
    test_file = create_test_binary_with_code()
    diff_file = create_similar_binary()
    print(f"Created test file 1: {test_file} ({os.path.getsize(test_file)} bytes)")
    print(f"Created test file 2: {diff_file} ({os.path.getsize(diff_file)} bytes)")
    print()

    # Create client
    config = ServerConfig(
        imhex_host='localhost',
        imhex_port=31337,
        connection_timeout=10.0,
        read_timeout=30.0,
        max_retries=3,
        retry_delay=0.5
    )
    client = ImHexClient(config)

    passed = 0
    failed = 0

    try:
        # Connect
        client.connect()

        # Open first test file
        print("[SETUP] Opening test file 1...")
        response = client.send_command("file/open", {"path": test_file})
        if response.get("status") != "success":
            print(f"  ✗ Failed to open file 1: {response}")
            return
        print("  ✓ File 1 opened successfully")
        print()

        print("="*70)
        print("TEST 1: CHUNKED READ")
        print("="*70)
        print()

        # Test chunked reading
        print("[TEST 1.1] Chunked Read - First chunk (hex encoding)")
        try:
            response = client.send_command("data/read_chunked", {
                "offset": 0,
                "length": 500,
                "chunk_size": 100,
                "chunk_index": 0,
                "encoding": "hex"
            })

            if response.get("status") == "success":
                data = response.get("data", {})
                print(f"  ✓ Chunked read successful")
                print(f"    Chunk index: {data.get('chunk_index')}")
                print(f"    Chunk size: {data.get('chunk_size')} bytes")
                print(f"    Total chunks: {data.get('total_chunks')}")
                print(f"    Has more: {data.get('has_more')}")
                print(f"    Data preview: {data.get('data', '')[:40]}...")
                passed += 1
            else:
                print(f"  ✗ Chunked read failed: {response}")
                failed += 1
        except Exception as e:
            print(f"  ✗ Exception: {e}")
            failed += 1
        print()

        # Test base64 encoding
        print("[TEST 1.2] Chunked Read - Second chunk (base64 encoding)")
        try:
            response = client.send_command("data/read_chunked", {
                "offset": 0,
                "length": 500,
                "chunk_size": 100,
                "chunk_index": 1,
                "encoding": "base64"
            })

            if response.get("status") == "success":
                data = response.get("data", {})
                print(f"  ✓ Chunked read (base64) successful")
                print(f"    Chunk offset: 0x{data.get('chunk_offset'):X}")
                print(f"    Bytes remaining: {data.get('bytes_remaining')}")
                passed += 1
            else:
                print(f"  ✗ Chunked read failed: {response}")
                failed += 1
        except Exception as e:
            print(f"  ✗ Exception: {e}")
            failed += 1
        print()

        print("="*70)
        print("TEST 2: DISASSEMBLY")
        print("="*70)
        print()

        # Test disassembly
        print("[TEST 2.1] Disassemble x86-64 code")
        try:
            response = client.send_command("disasm/disassemble", {
                "offset": 8,  # After 'V040TEST' header
                "length": 64,
                "architecture": "x86_64"
            })

            if response.get("status") == "success":
                data = response.get("data", {})
                instructions = data.get("instructions", [])
                print(f"  ✓ Disassembly successful")
                print(f"    Architecture: {data.get('architecture')}")
                print(f"    Instructions: {data.get('instruction_count')}")
                print(f"    Bytes disassembled: {data.get('bytes_disassembled')}")

                # Show first few instructions
                print(f"    First instructions:")
                for instr in instructions[:5]:
                    print(f"      0x{instr.get('offset'):X}: {instr.get('mnemonic'):10} {instr.get('operands')}")

                passed += 1
            else:
                print(f"  ✗ Disassembly failed: {response}")
                failed += 1
        except Exception as e:
            print(f"  ✗ Exception: {e}")
            failed += 1
        print()

        print("="*70)
        print("TEST 3: BINARY DIFFING")
        print("="*70)
        print()

        # Open second file for diff
        print("[SETUP] Opening test file 2 for comparison...")
        response = client.send_command("file/open", {"path": diff_file})
        if response.get("status") != "success":
            print(f"  ✗ Failed to open file 2: {response}")
        else:
            print("  ✓ File 2 opened successfully")

            # Get file list to find provider IDs
            print("[SETUP] Getting provider IDs...")
            response = client.send_command("file/list", {})
            if response.get("status") == "success":
                files = response.get("data", {}).get("files", [])
                print(f"  ✓ Found {len(files)} open files")

                if len(files) >= 2:
                    provider1 = files[0]["id"]
                    provider2 = files[1]["id"]
                    print(f"    Provider 1 ID: {provider1}")
                    print(f"    Provider 2 ID: {provider2}")
                    print()

                    # Test binary diff
                    print("[TEST 3.1] Binary Diff - Simple Algorithm")
                    try:
                        response = client.send_command("diff/analyze", {
                            "provider_id_1": provider1,
                            "provider_id_2": provider2,
                            "algorithm": "simple"
                        })

                        if response.get("status") == "success":
                            data = response.get("data", {})
                            regions = data.get("regions", [])
                            print(f"  ✓ Binary diff successful")
                            print(f"    Algorithm: {data.get('algorithm')}")
                            print(f"    File 1 size: {data.get('provider1_size')} bytes")
                            print(f"    File 2 size: {data.get('provider2_size')} bytes")
                            print(f"    Diff regions: {data.get('region_count')}")

                            # Show first few regions
                            if regions:
                                print(f"    First diff regions:")
                                for region in regions[:5]:
                                    print(f"      0x{region.get('start'):X}-0x{region.get('end'):X}: {region.get('type')} ({region.get('size')} bytes)")

                            passed += 1
                        else:
                            print(f"  ✗ Binary diff failed: {response}")
                            failed += 1
                    except Exception as e:
                        print(f"  ✗ Exception: {e}")
                        failed += 1
                else:
                    print(f"  ✗ Not enough files open for diff test")
                    failed += 1
            else:
                print(f"  ✗ Failed to list files: {response}")
                failed += 1
        print()

    finally:
        # Cleanup
        if os.path.exists(test_file):
            os.unlink(test_file)
            print(f"Cleaned up: {test_file}")
        if os.path.exists(diff_file):
            os.unlink(diff_file)
            print(f"Cleaned up: {diff_file}")
        print()

    # Summary
    print("="*70)
    print("Test Summary")
    print("="*70)
    print(f"Total tests run: {passed + failed}")
    print(f"✓ Passed: {passed}")
    print(f"✗ Failed: {failed}")
    print()

    if failed == 0:
        print("🎉 All v0.4.0 feature tests passed!")
    else:
        print(f"⚠ {failed} test(s) failed")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
