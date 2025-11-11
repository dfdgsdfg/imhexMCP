#!/usr/bin/env python3
"""
Test Suite for Multiple File Support Features
Tests file/list, file/switch, file/close, and file/compare endpoints
"""

import os
import sys
import tempfile
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from server import ImHexClient, ServerConfig


def create_test_files():
    """Create three test binary files with different content."""
    files = []

    # File 1: Pattern A (smaller file)
    fd1, file1 = tempfile.mkstemp(suffix='_test1.bin', prefix='multifile_')
    with os.fdopen(fd1, 'wb') as f:
        f.write(b'FILE1HEADER')
        f.write(b'AAAA' * 100)  # 400 bytes of AAAA
    files.append(file1)

    # File 2: Pattern B (same size, different content)
    fd2, file2 = tempfile.mkstemp(suffix='_test2.bin', prefix='multifile_')
    with os.fdopen(fd2, 'wb') as f:
        f.write(b'FILE2HEADER')
        f.write(b'BBBB' * 100)  # 400 bytes of BBBB
    files.append(file2)

    # File 3: Pattern C (different size)
    fd3, file3 = tempfile.mkstemp(suffix='_test3.bin', prefix='multifile_')
    with os.fdopen(fd3, 'wb') as f:
        f.write(b'FILE3HEADER')
        f.write(b'CCCC' * 200)  # 800 bytes of CCCC
    files.append(file3)

    return files


def main():
    """Run multiple file support tests."""
    print("="*70)
    print("ImHex MCP - Multiple File Support Tests")
    print("="*70)
    print()

    # Create test files
    test_files = create_test_files()
    print(f"Created {len(test_files)} test files:")
    for i, filepath in enumerate(test_files, 1):
        size = os.path.getsize(filepath)
        print(f"  File {i}: {filepath} ({size} bytes)")
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
    provider_ids = []

    try:
        # Connect
        client.connect()

        print("="*70)
        print("TEST 1: Open multiple files")
        print("="*70)
        print()

        # Open all three files
        for i, filepath in enumerate(test_files, 1):
            try:
                print(f"[TEST 1.{i}] Opening file {i}...")
                response = client.send_command("file/open", {"path": filepath})

                if response.get("status") == "success":
                    data = response.get("data", {})
                    size = data.get("size", 0)
                    print(f"  ✓ File {i} opened successfully")
                    print(f"    Path: {filepath}")
                    print(f"    Size: {size} bytes")
                    passed += 1
                else:
                    print(f"  ✗ Failed to open file {i}: {response}")
                    failed += 1
            except Exception as e:
                print(f"  ✗ Exception opening file {i}: {e}")
                failed += 1
            print()

        print("="*70)
        print("TEST 2: List all open files")
        print("="*70)
        print()

        try:
            print("[TEST 2] Listing all open files...")
            response = client.send_command("file/list", {})

            if response.get("status") == "success":
                data = response.get("data", {})
                files = data.get("files", [])
                count = data.get("count", 0)

                print(f"  ✓ List successful")
                print(f"    Total files open: {count}")

                for file_info in files:
                    provider_id = file_info.get("id")
                    name = file_info.get("name")
                    size = file_info.get("size")
                    is_active = file_info.get("is_active")

                    provider_ids.append(provider_id)

                    active_marker = " [ACTIVE]" if is_active else ""
                    print(f"    - ID {provider_id}: {name}{active_marker}")
                    print(f"      Size: {size:,} bytes")

                if count >= 3:
                    passed += 1
                else:
                    print(f"  ✗ Expected at least 3 files, found {count}")
                    failed += 1
            else:
                print(f"  ✗ List failed: {response}")
                failed += 1
        except Exception as e:
            print(f"  ✗ Exception: {e}")
            failed += 1
        print()

        if len(provider_ids) < 2:
            print("Not enough files open to continue tests")
            return

        print("="*70)
        print("TEST 3: Switch between files")
        print("="*70)
        print()

        # Switch to first provider
        try:
            target_id = provider_ids[0]
            print(f"[TEST 3] Switching to provider ID {target_id}...")
            response = client.send_command("file/switch", {"provider_id": target_id})

            if response.get("status") == "success":
                data = response.get("data", {})
                name = data.get("name", "")
                size = data.get("size", 0)

                print(f"  ✓ Switch successful")
                print(f"    Provider ID: {target_id}")
                print(f"    Name: {name}")
                print(f"    Size: {size:,} bytes")
                passed += 1
            else:
                print(f"  ✗ Switch failed: {response}")
                failed += 1
        except Exception as e:
            print(f"  ✗ Exception: {e}")
            failed += 1
        print()

        print("="*70)
        print("TEST 4: Compare two files")
        print("="*70)
        print()

        if len(provider_ids) >= 2:
            try:
                id1 = provider_ids[0]
                id2 = provider_ids[1]
                print(f"[TEST 4] Comparing providers {id1} and {id2}...")
                response = client.send_command("file/compare", {
                    "provider_id_1": id1,
                    "provider_id_2": id2
                })

                if response.get("status") == "success":
                    data = response.get("data", {})
                    file1 = data.get("file1", {})
                    file2 = data.get("file2", {})
                    comparison = data.get("comparison", {})

                    print(f"  ✓ Comparison successful")
                    print(f"    File 1: {file1.get('name')} ({file1.get('size'):,} bytes)")
                    print(f"    File 2: {file2.get('name')} ({file2.get('size'):,} bytes)")
                    print(f"    Bytes compared: {comparison.get('bytes_compared', 0):,}")
                    print(f"    Differences: {comparison.get('differences', 0):,}")
                    print(f"    Similarity: {comparison.get('similarity_percent', 0):.2f}%")
                    passed += 1
                else:
                    print(f"  ✗ Comparison failed: {response}")
                    failed += 1
            except Exception as e:
                print(f"  ✗ Exception: {e}")
                failed += 1
        print()

        print("="*70)
        print("TEST 5: Close a file")
        print("="*70)
        print()

        if len(provider_ids) >= 1:
            try:
                close_id = provider_ids[-1]  # Close the last one
                print(f"[TEST 5] Closing provider ID {close_id}...")
                response = client.send_command("file/close", {"provider_id": close_id})

                if response.get("status") == "success":
                    data = response.get("data", {})
                    name = data.get("name", "")

                    print(f"  ✓ Close successful")
                    print(f"    Closed: {name} (ID {close_id})")

                    # Verify file is closed by listing again
                    list_response = client.send_command("file/list", {})
                    if list_response.get("status") == "success":
                        list_data = list_response.get("data", {})
                        remaining_count = list_data.get("count", 0)
                        print(f"    Remaining files: {remaining_count}")
                        passed += 1
                    else:
                        print(f"  ✗ Could not verify file was closed")
                        failed += 1
                else:
                    print(f"  ✗ Close failed: {response}")
                    failed += 1
            except Exception as e:
                print(f"  ✗ Exception: {e}")
                failed += 1
        print()

    finally:
        # Cleanup test files
        for filepath in test_files:
            try:
                if os.path.exists(filepath):
                    os.unlink(filepath)
                    print(f"Cleaned up: {filepath}")
            except Exception as e:
                print(f"Warning: Could not delete {filepath}: {e}")
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
        print("🎉 All multiple file support tests passed!")
    else:
        print(f"⚠ {failed} test(s) failed")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
