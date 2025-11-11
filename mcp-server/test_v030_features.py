#!/usr/bin/env python3
"""
Comprehensive Test Suite for v0.3.0 Features
Tests data export and advanced search capabilities
"""

import os
import sys
import tempfile
import csv
import json
import base64
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from server import ImHexClient, ServerConfig


def create_test_binary():
    """Create a test binary file with known patterns."""
    fd, filepath = tempfile.mkstemp(suffix='.bin', prefix='imhex_v030_test_')

    with os.fdopen(fd, 'wb') as f:
        # Header
        f.write(b'TESTV030')  # Magic

        # Pattern section 1: Repeated patterns for multi-search
        f.write(b'AAAA' * 10)  # Pattern A (40 bytes)
        f.write(b'BBBB' * 10)  # Pattern B (40 bytes)
        f.write(b'CCCC' * 10)  # Pattern C (40 bytes)

        # Text section for regex testing
        f.write(b'Email: test@example.com\n')
        f.write(b'Phone: 555-1234\n')
        f.write(b'URL: https://github.com/jmpnop/imhexMCP\n')
        f.write(b'IPv4: 192.168.1.1\n')

        # Binary markers
        f.write(b'\xDE\xAD\xBE\xEF')  # DEADBEEF marker
        f.write(b'\xCA\xFE\xBA\xBE')  # CAFEBABE marker

        # Padding with nulls
        f.write(b'\x00' * 100)

        # More patterns for pagination testing
        for i in range(50):
            f.write(b'TEST')  # Will have many matches
            f.write(b'\x00' * 4)

    return filepath


def main():
    """Run comprehensive v0.3.0 feature tests."""
    print("="*70)
    print("ImHex MCP v0.3.0 - Comprehensive Feature Tests")
    print("="*70)
    print()

    # Create test file
    test_file = create_test_binary()
    print(f"Created test binary: {test_file}")
    print(f"File size: {os.path.getsize(test_file)} bytes")
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
        # Connect and open file
        client.connect()

        print("[SETUP] Opening test file...")
        response = client.send_command("file/open", {"path": test_file})
        if response.get("status") != "success":
            print(f"  ✗ Failed to open file: {response}")
            return
        print("  ✓ File opened successfully")
        print()

        print("="*70)
        print("DATA EXPORT TESTS")
        print("="*70)
        print()

        # Test 1: Binary export
        print("[TEST 1] Data Export - Binary Format")
        try:
            export_file = tempfile.mktemp(suffix='.bin')
            response = client.send_command("data/export", {
                "offset": 0,
                "length": 100,
                "output_path": export_file,
                "format": "binary"
            })

            if response.get("status") == "success":
                if os.path.exists(export_file):
                    size = os.path.getsize(export_file)
                    print(f"  ✓ Binary export successful")
                    print(f"    Output: {export_file}")
                    print(f"    Size: {size} bytes")
                    os.unlink(export_file)
                    passed += 1
                else:
                    print(f"  ✗ Export file not created")
                    failed += 1
            else:
                print(f"  ✗ Export failed: {response}")
                failed += 1
        except Exception as e:
            print(f"  ✗ Exception: {e}")
            failed += 1
        print()

        # Test 2: Hex export
        print("[TEST 2] Data Export - Hex Format")
        try:
            export_file = tempfile.mktemp(suffix='.hex')
            response = client.send_command("data/export", {
                "offset": 0,
                "length": 64,
                "output_path": export_file,
                "format": "hex"
            })

            if response.get("status") == "success":
                if os.path.exists(export_file):
                    with open(export_file, 'r') as f:
                        content = f.read()
                    print(f"  ✓ Hex export successful")
                    print(f"    Output: {export_file}")
                    print(f"    Lines: {len(content.splitlines())}")
                    print(f"    First line: {content.splitlines()[0][:40]}...")
                    os.unlink(export_file)
                    passed += 1
                else:
                    print(f"  ✗ Export file not created")
                    failed += 1
            else:
                print(f"  ✗ Export failed: {response}")
                failed += 1
        except Exception as e:
            print(f"  ✗ Exception: {e}")
            failed += 1
        print()

        # Test 3: Base64 export
        print("[TEST 3] Data Export - Base64 Format")
        try:
            export_file = tempfile.mktemp(suffix='.b64')
            response = client.send_command("data/export", {
                "offset": 0,
                "length": 64,
                "output_path": export_file,
                "format": "base64"
            })

            if response.get("status") == "success":
                if os.path.exists(export_file):
                    with open(export_file, 'r') as f:
                        content = f.read()
                    # Try to decode to verify valid base64
                    try:
                        decoded = base64.b64decode(content.replace('\n', ''))
                        print(f"  ✓ Base64 export successful")
                        print(f"    Output: {export_file}")
                        print(f"    Decoded size: {len(decoded)} bytes")
                        os.unlink(export_file)
                        passed += 1
                    except Exception:
                        print(f"  ✗ Invalid base64 content")
                        failed += 1
                else:
                    print(f"  ✗ Export file not created")
                    failed += 1
            else:
                print(f"  ✗ Export failed: {response}")
                failed += 1
        except Exception as e:
            print(f"  ✗ Exception: {e}")
            failed += 1
        print()

        print("="*70)
        print("ADVANCED SEARCH TESTS")
        print("="*70)
        print()

        # Test 4: Basic search (baseline)
        print("[TEST 4] Search - Basic Pattern")
        try:
            response = client.send_command("search/find", {
                "pattern": "AAAA",
                "type": "text"
            })

            if response.get("status") == "success":
                data = response.get("data", {})
                matches = data.get("matches", [])
                total = data.get("total_matches", 0)
                print(f"  ✓ Search successful")
                print(f"    Pattern: AAAA")
                print(f"    Total matches: {total}")
                print(f"    First match: 0x{matches[0]:X}" if matches else "    No matches")
                passed += 1
            else:
                print(f"  ✗ Search failed: {response}")
                failed += 1
        except Exception as e:
            print(f"  ✗ Exception: {e}")
            failed += 1
        print()

        # Test 5: Regex search
        print("[TEST 5] Search - Regex Pattern (Email)")
        try:
            response = client.send_command("search/find", {
                "pattern": r"[a-z]+@[a-z]+\.[a-z]+",
                "type": "regex"
            })

            if response.get("status") == "success":
                data = response.get("data", {})
                matches = data.get("matches", [])
                total = data.get("total_matches", 0)
                print(f"  ✓ Regex search successful")
                print(f"    Pattern: [a-z]+@[a-z]+\\.[a-z]+")
                print(f"    Total matches: {total}")
                if total > 0:
                    print(f"    First match at: 0x{matches[0]:X}")
                passed += 1
            else:
                print(f"  ✗ Regex search failed: {response}")
                failed += 1
        except Exception as e:
            print(f"  ✗ Exception: {e}")
            failed += 1
        print()

        # Test 6: Search pagination
        print("[TEST 6] Search - Pagination")
        try:
            # First page
            response1 = client.send_command("search/find", {
                "pattern": "TEST",
                "type": "text",
                "offset": 0,
                "limit": 10
            })

            # Second page
            response2 = client.send_command("search/find", {
                "pattern": "TEST",
                "type": "text",
                "offset": 10,
                "limit": 10
            })

            if (response1.get("status") == "success" and
                response2.get("status") == "success"):
                data1 = response1.get("data", {})
                data2 = response2.get("data", {})

                matches1 = data1.get("matches", [])
                matches2 = data2.get("matches", [])
                total = data1.get("total_matches", 0)
                has_more1 = data1.get("has_more", False)

                print(f"  ✓ Pagination successful")
                print(f"    Total matches: {total}")
                print(f"    Page 1: {len(matches1)} results")
                print(f"    Page 2: {len(matches2)} results")
                print(f"    Has more: {has_more1}")
                passed += 1
            else:
                print(f"  ✗ Pagination failed")
                failed += 1
        except Exception as e:
            print(f"  ✗ Exception: {e}")
            failed += 1
        print()

        # Test 7: Multi-pattern search
        print("[TEST 7] Search - Multi-Pattern")
        try:
            response = client.send_command("search/multi", {
                "patterns": [
                    {"pattern": "AAAA", "type": "text"},
                    {"pattern": "BBBB", "type": "text"},
                    {"pattern": "CCCC", "type": "text"}
                ],
                "limit": 1000
            })

            if response.get("status") == "success":
                data = response.get("data", {})
                patterns = data.get("patterns", [])
                total_patterns = data.get("total_patterns", 0)

                print(f"  ✓ Multi-pattern search successful")
                print(f"    Patterns searched: {total_patterns}")
                for i, pattern_result in enumerate(patterns, 1):
                    pattern = pattern_result.get("pattern", "")
                    count = pattern_result.get("count", 0)
                    print(f"    Pattern {i} '{pattern}': {count} matches")
                passed += 1
            else:
                print(f"  ✗ Multi-pattern search failed: {response}")
                failed += 1
        except Exception as e:
            print(f"  ✗ Exception: {e}")
            failed += 1
        print()

        print("="*70)
        print("SEARCH EXPORT TESTS")
        print("="*70)
        print()

        # Test 8: Export search results to JSON
        print("[TEST 8] Export Search Results - JSON")
        try:
            # First, do a search
            search_response = client.send_command("search/find", {
                "pattern": "DEADBEEF",
                "type": "hex"
            })

            if search_response.get("status") == "success":
                matches = search_response.get("data", {}).get("matches", [])

                if matches:
                    export_file = tempfile.mktemp(suffix='.json')
                    export_response = client.send_command("search/export", {
                        "matches": matches,
                        "output_path": export_file,
                        "format": "json",
                        "context_bytes": 16
                    })

                    if export_response.get("status") == "success":
                        if os.path.exists(export_file):
                            with open(export_file, 'r') as f:
                                exported_data = json.load(f)

                            print(f"  ✓ JSON export successful")
                            print(f"    Output: {export_file}")
                            print(f"    Matches: {exported_data.get('match_count', 0)}")
                            print(f"    File size: {exported_data.get('file_size', 0)} bytes")
                            os.unlink(export_file)
                            passed += 1
                        else:
                            print(f"  ✗ Export file not created")
                            failed += 1
                    else:
                        print(f"  ✗ Export failed: {export_response}")
                        failed += 1
                else:
                    print(f"  ✗ No matches found for export test")
                    failed += 1
            else:
                print(f"  ✗ Search failed: {search_response}")
                failed += 1
        except Exception as e:
            print(f"  ✗ Exception: {e}")
            failed += 1
        print()

        # Test 9: Export search results to CSV
        print("[TEST 9] Export Search Results - CSV")
        try:
            # Do a search
            search_response = client.send_command("search/find", {
                "pattern": "TEST",
                "type": "text",
                "limit": 5
            })

            if search_response.get("status") == "success":
                matches = search_response.get("data", {}).get("matches", [])

                if matches:
                    export_file = tempfile.mktemp(suffix='.csv')
                    export_response = client.send_command("search/export", {
                        "matches": matches,
                        "output_path": export_file,
                        "format": "csv",
                        "context_bytes": 8
                    })

                    if export_response.get("status") == "success":
                        if os.path.exists(export_file):
                            with open(export_file, 'r') as f:
                                reader = csv.reader(f)
                                rows = list(reader)

                            print(f"  ✓ CSV export successful")
                            print(f"    Output: {export_file}")
                            print(f"    Rows: {len(rows)} (including header)")
                            print(f"    Columns: {len(rows[0]) if rows else 0}")
                            os.unlink(export_file)
                            passed += 1
                        else:
                            print(f"  ✗ Export file not created")
                            failed += 1
                    else:
                        print(f"  ✗ Export failed: {export_response}")
                        failed += 1
                else:
                    print(f"  ✗ No matches found for export test")
                    failed += 1
            else:
                print(f"  ✗ Search failed: {search_response}")
                failed += 1
        except Exception as e:
            print(f"  ✗ Exception: {e}")
            failed += 1
        print()

    finally:
        # Cleanup
        if os.path.exists(test_file):
            os.unlink(test_file)
            print(f"Cleaned up test file: {test_file}")
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
        print("🎉 All v0.3.0 feature tests passed!")
    else:
        print(f"⚠ {failed} test(s) failed")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
