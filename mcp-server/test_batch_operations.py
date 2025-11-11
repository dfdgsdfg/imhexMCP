#!/usr/bin/env python3
"""
Test Suite for v1.0.0 Batch Operations (Phase 1 & 2)
Tests: batch/open_directory, batch/search, batch/hash endpoints
"""

import os
import sys
import tempfile
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from server import ImHexClient, ServerConfig


def create_test_directory():
    """Create a temporary directory with test binary files."""
    test_dir = tempfile.mkdtemp(prefix='imhex_batch_test_')

    # Create various binary files
    test_files = [
        ('test1.bin', b'TEST1' + b'\x00' * 1000),
        ('test2.bin', b'TEST2' + b'\x00' * 2000),
        ('test3.exe', b'MZ' + b'\x00' * 500),  # PE executable signature
        ('test4.elf', b'\x7fELF' + b'\x00' * 800),  # ELF signature
        ('data.txt', b'This is a text file'),  # Non-binary
        ('small.bin', b'TINY'),  # Very small file
        ('large.bin', b'LARGE' + b'\x00' * 10000),  # Larger file
    ]

    created_files = []
    for filename, content in test_files:
        filepath = os.path.join(test_dir, filename)
        with open(filepath, 'wb') as f:
            f.write(content)
        created_files.append(filepath)

    return test_dir, created_files


def main():
    """Run batch operations tests."""
    print("="*70)
    print("ImHex MCP v1.0.0 - Batch Operations Tests (Phase 1 & 2)")
    print("="*70)
    print()

    # Create test files
    test_dir, test_files = create_test_directory()
    print(f"Created test directory: {test_dir}")
    print(f"Created {len(test_files)} test files")
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

        print("="*70)
        print("TEST 1: BATCH OPEN ALL FILES")
        print("="*70)
        print()

        print("[TEST 1.1] Open all files with wildcard pattern")
        try:
            response = client.send_command("batch/open_directory", {
                "directory": test_dir,
                "pattern": "*",
                "max_files": 100
            })

            if response.get("status") == "success":
                data = response.get("data", {})
                print(f"  ✓ Batch open successful")
                print(f"    Files found: {data.get('files_found')}")
                print(f"    Successfully opened: {data.get('total_opened')}")
                print(f"    Skipped: {data.get('skipped')}")

                if data.get('total_opened') == 7:
                    print(f"  ✓ All 7 files opened")
                    passed += 1
                else:
                    print(f"  ✗ Expected 7 files, got {data.get('total_opened')}")
                    failed += 1
            else:
                print(f"  ✗ Batch open failed: {response}")
                failed += 1
        except Exception as e:
            print(f"  ✗ Exception: {e}")
            failed += 1
        print()

        print("="*70)
        print("TEST 2: PATTERN MATCHING")
        print("="*70)
        print()

        # Close all files first
        print("[SETUP] Closing all open files...")
        file_list = client.send_command("file/list", {})
        if file_list.get("status") == "success":
            files = file_list.get("data", {}).get("files", [])
            for file_info in files:
                client.send_command("file/close", {"provider_id": file_info["id"]})
        print()

        print("[TEST 2.1] Open only .bin files")
        try:
            response = client.send_command("batch/open_directory", {
                "directory": test_dir,
                "pattern": "*.bin"
            })

            if response.get("status") == "success":
                data = response.get("data", {})
                bin_count = data.get('total_opened')
                print(f"  ✓ Pattern match successful")
                print(f"    Files found: {data.get('files_found')}")
                print(f"    Opened .bin files: {bin_count}")

                if bin_count == 4:  # test1, test2, small, large
                    print(f"  ✓ Correct count (4 .bin files)")
                    passed += 1
                else:
                    print(f"  ✗ Expected 4 .bin files, got {bin_count}")
                    failed += 1
            else:
                print(f"  ✗ Pattern match failed: {response}")
                failed += 1
        except Exception as e:
            print(f"  ✗ Exception: {e}")
            failed += 1
        print()

        print("="*70)
        print("TEST 3: FILE SIZE FILTERING")
        print("="*70)
        print()

        # Close all files first
        print("[SETUP] Closing all open files...")
        file_list = client.send_command("file/list", {})
        if file_list.get("status") == "success":
            files = file_list.get("data", {}).get("files", [])
            for file_info in files:
                client.send_command("file/close", {"provider_id": file_info["id"]})
        print()

        print("[TEST 3.1] Open files larger than 500 bytes")
        try:
            response = client.send_command("batch/open_directory", {
                "directory": test_dir,
                "pattern": "*",
                "filters": {
                    "min_size": 500
                }
            })

            if response.get("status") == "success":
                data = response.get("data", {})
                opened = data.get('total_opened')
                print(f"  ✓ Size filter successful")
                print(f"    Files found: {data.get('files_found')}")
                print(f"    Opened (>500 bytes): {opened}")

                # Should get test1.bin (1005), test2.bin (2005), test3.exe (502),
                # test4.elf (804), large.bin (10005)
                if opened >= 5:
                    print(f"  ✓ At least 5 large files opened")
                    passed += 1
                else:
                    print(f"  ✗ Expected at least 5 files, got {opened}")
                    failed += 1
            else:
                print(f"  ✗ Size filter failed: {response}")
                failed += 1
        except Exception as e:
            print(f"  ✗ Exception: {e}")
            failed += 1
        print()

        print("="*70)
        print("TEST 4: EXTENSION FILTERING")
        print("="*70)
        print()

        # Close all files first
        print("[SETUP] Closing all open files...")
        file_list = client.send_command("file/list", {})
        if file_list.get("status") == "success":
            files = file_list.get("data", {}).get("files", [])
            for file_info in files:
                client.send_command("file/close", {"provider_id": file_info["id"]})
        print()

        print("[TEST 4.1] Open only .exe and .elf files")
        try:
            response = client.send_command("batch/open_directory", {
                "directory": test_dir,
                "pattern": "*",
                "filters": {
                    "extensions": [".exe", ".elf"]
                }
            })

            if response.get("status") == "success":
                data = response.get("data", {})
                opened = data.get('total_opened')
                print(f"  ✓ Extension filter successful")
                print(f"    Files found: {data.get('files_found')}")
                print(f"    Opened (.exe/.elf): {opened}")

                if opened == 2:  # test3.exe and test4.elf
                    print(f"  ✓ Correct count (2 files)")
                    passed += 1
                else:
                    print(f"  ✗ Expected 2 files, got {opened}")
                    failed += 1
            else:
                print(f"  ✗ Extension filter failed: {response}")
                failed += 1
        except Exception as e:
            print(f"  ✗ Exception: {e}")
            failed += 1
        print()

        print("="*70)
        print("TEST 5: MAX FILES LIMIT")
        print("="*70)
        print()

        # Close all files first
        print("[SETUP] Closing all open files...")
        file_list = client.send_command("file/list", {})
        if file_list.get("status") == "success":
            files = file_list.get("data", {}).get("files", [])
            for file_info in files:
                client.send_command("file/close", {"provider_id": file_info["id"]})
        print()

        print("[TEST 5.1] Limit to max 3 files")
        try:
            response = client.send_command("batch/open_directory", {
                "directory": test_dir,
                "pattern": "*",
                "max_files": 3
            })

            if response.get("status") == "success":
                data = response.get("data", {})
                opened = data.get('total_opened')
                print(f"  ✓ Max files limit respected")
                print(f"    Files found: {data.get('files_found')}")
                print(f"    Opened (max 3): {opened}")

                if opened <= 3:
                    print(f"  ✓ Limit enforced correctly")
                    passed += 1
                else:
                    print(f"  ✗ Expected ≤3 files, got {opened}")
                    failed += 1
            else:
                print(f"  ✗ Max files test failed: {response}")
                failed += 1
        except Exception as e:
            print(f"  ✗ Exception: {e}")
            failed += 1
        print()

        print("="*70)
        print("TEST 6: COMBINED FILTERS")
        print("="*70)
        print()

        # Close all files first
        print("[SETUP] Closing all open files...")
        file_list = client.send_command("file/list", {})
        if file_list.get("status") == "success":
            files = file_list.get("data", {}).get("files", [])
            for file_info in files:
                client.send_command("file/close", {"provider_id": file_info["id"]})
        print()

        print("[TEST 6.1] Pattern + size filter + extension filter")
        try:
            response = client.send_command("batch/open_directory", {
                "directory": test_dir,
                "pattern": "*",
                "filters": {
                    "min_size": 1000,
                    "extensions": [".bin"]
                }
            })

            if response.get("status") == "success":
                data = response.get("data", {})
                opened = data.get('total_opened')
                print(f"  ✓ Combined filters successful")
                print(f"    Files found: {data.get('files_found')}")
                print(f"    Opened (>1000 bytes + .bin): {opened}")

                # Should get test1.bin (1005), test2.bin (2005), large.bin (10005)
                if opened == 3:
                    print(f"  ✓ Correct count (3 files)")
                    passed += 1
                else:
                    print(f"  ✗ Expected 3 files, got {opened}")
                    failed += 1
            else:
                print(f"  ✗ Combined filters failed: {response}")
                failed += 1
        except Exception as e:
            print(f"  ✗ Exception: {e}")
            failed += 1
        print()

        print("="*70)
        print("TEST 7: BATCH SEARCH - SINGLE PATTERN")
        print("="*70)
        print()

        # Setup: Reopen all files for Phase 2 tests
        print("[SETUP] Reopening all files for Phase 2 tests...")
        client.send_command("batch/open_directory", {
            "directory": test_dir,
            "pattern": "*",
            "max_files": 100
        })
        print()

        print("[TEST 7.1] Search for 'TEST' string across all open files")
        try:
            response = client.send_command("batch/search", {
                "patterns": [
                    {"value": "TEST", "type": "string"}
                ],
                "max_matches_per_file": 100
            })

            if response.get("status") == "success":
                data = response.get("data", {})
                summary = data.get("summary", {})
                results = data.get("results", [])

                print(f"  ✓ Batch search successful")
                print(f"    Files searched: {summary.get('files_searched')}")
                print(f"    Total matches: {summary.get('total_matches')}")

                # Count files with matches
                files_with_matches = sum(1 for r in results if r.get('total_matches', 0) > 0)

                if files_with_matches >= 2:  # Should find TEST1 and TEST2
                    print(f"  ✓ Found matches in {files_with_matches} files")
                    passed += 1
                else:
                    print(f"  ✗ Expected matches in at least 2 files, got {files_with_matches}")
                    failed += 1
            else:
                print(f"  ✗ Batch search failed: {response}")
                failed += 1
        except Exception as e:
            print(f"  ✗ Exception: {e}")
            failed += 1
        print()

        print("="*70)
        print("TEST 8: BATCH SEARCH - MULTIPLE PATTERNS")
        print("="*70)
        print()

        print("[TEST 8.1] Search for multiple patterns (hex + string)")
        try:
            response = client.send_command("batch/search", {
                "patterns": [
                    {"value": "4D5A", "type": "hex"},  # PE signature
                    {"value": "7F454C46", "type": "hex"},  # ELF signature
                    {"value": "TEST", "type": "string"}
                ],
                "max_matches_per_file": 100
            })

            if response.get("status") == "success":
                data = response.get("data", {})
                summary = data.get("summary", {})
                results = data.get("results", [])

                print(f"  ✓ Multi-pattern search successful")
                print(f"    Files searched: {summary.get('files_searched')}")
                print(f"    Patterns: {summary.get('patterns_searched')}")
                print(f"    Total matches: {summary.get('total_matches')}")

                # Should find PE signature in test3.exe, ELF in test4.elf, and TEST in test1/test2
                if summary.get('total_matches', 0) >= 4:  # At least 4 matches across patterns
                    print(f"  ✓ Found expected matches (PE, ELF, TEST patterns)")
                    passed += 1
                else:
                    print(f"  ✗ Expected at least 4 matches, got {summary.get('total_matches', 0)}")
                    failed += 1
            else:
                print(f"  ✗ Multi-pattern search failed: {response}")
                failed += 1
        except Exception as e:
            print(f"  ✗ Exception: {e}")
            failed += 1
        print()

        print("="*70)
        print("TEST 9: BATCH HASH - SINGLE ALGORITHM")
        print("="*70)
        print()

        print("[TEST 9.1] Calculate SHA256 for all open files")
        try:
            response = client.send_command("batch/hash", {
                "algorithms": ["sha256"]
            })

            if response.get("status") == "success":
                data = response.get("data", {})
                hashes = data.get("hashes", [])
                total = data.get("total_files", 0)

                print(f"  ✓ Batch hash successful")
                print(f"    Files hashed: {total}")

                # Verify all files have sha256 hash
                all_have_sha256 = all('sha256' in h.get('hashes', {}) for h in hashes)

                if all_have_sha256 and total == 7:  # Should have hashed all 7 files
                    print(f"  ✓ All 7 files have SHA256 hash")

                    # Show first hash as example
                    if hashes:
                        first = hashes[0]
                        print(f"    Example: {first.get('file')} -> {first.get('hashes', {}).get('sha256', '')[:16]}...")

                    passed += 1
                else:
                    print(f"  ✗ Expected 7 files with SHA256, got {total}")
                    failed += 1
            else:
                print(f"  ✗ Batch hash failed: {response}")
                failed += 1
        except Exception as e:
            print(f"  ✗ Exception: {e}")
            failed += 1
        print()

        print("="*70)
        print("TEST 10: BATCH HASH - MULTIPLE ALGORITHMS")
        print("="*70)
        print()

        print("[TEST 10.1] Calculate MD5 and SHA256 for all files")
        try:
            response = client.send_command("batch/hash", {
                "algorithms": ["md5", "sha256"]
            })

            if response.get("status") == "success":
                data = response.get("data", {})
                hashes = data.get("hashes", [])
                total = data.get("total_files", 0)

                print(f"  ✓ Multi-algorithm hash successful")
                print(f"    Files hashed: {total}")
                print(f"    Algorithms: md5, sha256")

                # Verify all files have both hashes
                all_have_both = all(
                    'md5' in h.get('hashes', {}) and 'sha256' in h.get('hashes', {})
                    for h in hashes
                )

                if all_have_both and total == 7:
                    print(f"  ✓ All 7 files have both MD5 and SHA256 hashes")
                    passed += 1
                else:
                    print(f"  ✗ Expected 7 files with both hashes, got {total}")
                    failed += 1
            else:
                print(f"  ✗ Multi-algorithm hash failed: {response}")
                failed += 1
        except Exception as e:
            print(f"  ✗ Exception: {e}")
            failed += 1
        print()

    finally:
        # Cleanup
        print("Cleaning up test directory...")
        for filepath in test_files:
            if os.path.exists(filepath):
                os.unlink(filepath)
        if os.path.exists(test_dir):
            os.rmdir(test_dir)
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
        print("🎉 All batch operation tests passed!")
    else:
        print(f"⚠ {failed} test(s) failed")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
