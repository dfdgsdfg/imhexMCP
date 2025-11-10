#!/usr/bin/env python3
"""
Comprehensive Binary Analysis Tests for ImHex MCP Integration

This script creates test binary files and performs real binary analysis
operations using the ImHex MCP interface.
"""

import os
import sys
import tempfile
import hashlib
from pathlib import Path
from typing import Optional, Dict, List
import struct

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from server import ImHexClient, ServerConfig


class BinaryAnalysisTests:
    """Real-world binary analysis tests."""

    def __init__(self):
        self.config = ServerConfig(
            imhex_host='localhost',
            imhex_port=31337,
            connection_timeout=3.0,
            read_timeout=3.0,
            max_retries=3,
            retry_delay=0.5
        )
        self.client = ImHexClient(self.config)
        self.test_file: Optional[str] = None
        self.passed = 0
        self.failed = 0

    def create_test_binary(self) -> str:
        """Create a test binary file with known data patterns."""
        # Create a temporary file
        fd, filepath = tempfile.mkstemp(suffix='.bin', prefix='imhex_test_')

        with os.fdopen(fd, 'wb') as f:
            # Header: Magic bytes "IMHX" + version
            f.write(b'IMHX')  # Magic
            f.write(struct.pack('<H', 1))  # Version (little-endian uint16)
            f.write(struct.pack('<H', 0))  # Flags

            # Data section 1: Repeating pattern
            pattern = b'\x00\x11\x22\x33\x44\x55\x66\x77\x88\x99\xAA\xBB\xCC\xDD\xEE\xFF'
            f.write(pattern * 4)  # 64 bytes

            # Data section 2: ASCII text
            text = b'Hello from ImHex MCP Integration!\x00'
            f.write(text)

            # Data section 3: Binary numbers
            for i in range(10):
                f.write(struct.pack('<I', i * 1000))  # uint32 values

            # Data section 4: Search target
            f.write(b'\xDE\xAD\xBE\xEF')  # Marker to search for

            # Padding
            f.write(b'\x00' * 50)

        print(f"Created test binary: {filepath}")
        print(f"File size: {os.path.getsize(filepath)} bytes")
        return filepath

    def print_section(self, title: str):
        """Print section header."""
        print(f"\n{'='*70}")
        print(f"{title}")
        print(f"{'='*70}\n")

    def print_test(self, name: str):
        """Print test name."""
        print(f"\n[TEST] {name}")

    def print_success(self, message: str):
        """Print success message."""
        print(f"  ✓ {message}")

    def print_error(self, message: str):
        """Print error message."""
        print(f"  ✗ {message}")

    def print_info(self, message: str):
        """Print info message."""
        print(f"    {message}")

    def test_open_file(self, filepath: str) -> bool:
        """Test opening a binary file."""
        self.print_test("Opening Test Binary File")

        try:
            response = self.client.send_command("file/open", {
                "path": filepath
            })

            if response.get("status") == "success":
                data = response.get("data", {})
                self.print_success(f"Opened file: {data.get('name', 'unknown')}")
                self.print_info(f"Size: {data.get('size', 0)} bytes")
                self.print_info(f"Writable: {data.get('writable', False)}")
                self.passed += 1
                return True
            else:
                error = response.get("data", {}).get("error", "Unknown error")
                self.print_error(f"Failed to open: {error}")
                self.failed += 1
                return False

        except Exception as e:
            self.print_error(f"Exception: {e}")
            self.failed += 1
            return False

    def test_read_header(self) -> bool:
        """Test reading the file header."""
        self.print_test("Reading File Header (Magic + Version)")

        try:
            response = self.client.send_command("data/read", {
                "offset": 0,
                "length": 8
            })

            if response.get("status") == "success":
                data = response.get("data", {})
                hex_data = data.get("data", "")

                # Parse magic bytes (first 4 bytes)
                magic_hex = hex_data[0:8]
                magic = bytes.fromhex(magic_hex).decode('ascii')

                self.print_success(f"Read {data.get('length', 0)} bytes from offset {data.get('offset', 0)}")
                self.print_info(f"Magic bytes: {magic} (hex: {magic_hex})")

                # Parse version
                version_hex = hex_data[8:12]
                version = int(version_hex, 16)
                self.print_info(f"Version: {version}")

                # Verify
                if magic == "IMHX":
                    self.print_success("Magic bytes verified!")
                    self.passed += 1
                    return True
                else:
                    self.print_error(f"Magic bytes mismatch: expected 'IMHX', got '{magic}'")
                    self.failed += 1
                    return False
            else:
                error = response.get("data", {}).get("error", "Unknown error")
                self.print_error(f"Read failed: {error}")
                self.failed += 1
                return False

        except Exception as e:
            self.print_error(f"Exception: {e}")
            self.failed += 1
            return False

    def test_data_inspect(self) -> bool:
        """Test data type inspection."""
        self.print_test("Inspecting Data Types at Offset 8")

        try:
            response = self.client.send_command("data/inspect", {
                "offset": 8,
                "length": 16
            })

            if response.get("status") == "success":
                data = response.get("data", {})
                interpretations = data.get("interpretations", {})

                self.print_success(f"Inspected {data.get('length', 0)} bytes")
                self.print_info(f"Found {len(interpretations)} type interpretations:")

                # Show some interesting interpretations
                for type_name in ['uint8', 'uint16_le', 'uint32_le', 'ascii']:
                    if type_name in interpretations:
                        value = interpretations[type_name]
                        self.print_info(f"  {type_name}: {value}")

                self.passed += 1
                return True
            else:
                error = response.get("data", {}).get("error", "Unknown error")
                self.print_error(f"Inspect failed: {error}")
                self.failed += 1
                return False

        except Exception as e:
            self.print_error(f"Exception: {e}")
            self.failed += 1
            return False

    def test_calculate_hash(self) -> bool:
        """Test hash calculation."""
        self.print_test("Calculating SHA-256 Hash")

        try:
            # Calculate hash using ImHex
            response = self.client.send_command("hash/calculate", {
                "offset": 0,
                "length": 64,
                "algorithm": "sha256"
            })

            if response.get("status") == "success":
                data = response.get("data", {})
                imhex_hash = data.get("hash", "")

                self.print_success("Hash calculated successfully")
                self.print_info(f"Algorithm: {data.get('algorithm', 'unknown')}")
                self.print_info(f"SHA-256: {imhex_hash}")

                # Verify by reading the data and calculating hash ourselves
                read_response = self.client.send_command("data/read", {
                    "offset": 0,
                    "length": 64
                })

                if read_response.get("status") == "success":
                    hex_data = read_response.get("data", {}).get("data", "")
                    binary_data = bytes.fromhex(hex_data)

                    # Calculate our own hash
                    our_hash = hashlib.sha256(binary_data).hexdigest()

                    if imhex_hash.lower() == our_hash.lower():
                        self.print_success("Hash verification passed!")
                        self.passed += 1
                        return True
                    else:
                        self.print_error(f"Hash mismatch!")
                        self.print_info(f"Expected: {our_hash}")
                        self.print_info(f"Got: {imhex_hash}")
                        self.failed += 1
                        return False
            else:
                error = response.get("data", {}).get("error", "Unknown error")
                self.print_error(f"Hash failed: {error}")
                self.failed += 1
                return False

        except Exception as e:
            self.print_error(f"Exception: {e}")
            self.failed += 1
            return False

    def test_search_pattern(self) -> bool:
        """Test searching for a byte pattern."""
        self.print_test("Searching for Pattern (DEADBEEF)")

        try:
            response = self.client.send_command("search/find", {
                "pattern": "DEADBEEF",
                "type": "hex"
            })

            if response.get("status") == "success":
                data = response.get("data", {})
                matches = data.get("matches", [])

                self.print_success(f"Search completed")
                self.print_info(f"Pattern: {data.get('pattern', 'unknown')}")
                self.print_info(f"Matches found: {len(matches)}")

                if matches:
                    for i, offset in enumerate(matches[:5]):  # Show first 5
                        self.print_info(f"  Match {i+1}: offset 0x{offset:X}")

                    self.passed += 1
                    return True
                else:
                    self.print_error("No matches found (expected at least one)")
                    self.failed += 1
                    return False
            else:
                error = response.get("data", {}).get("error", "Unknown error")
                self.print_error(f"Search failed: {error}")
                self.failed += 1
                return False

        except Exception as e:
            self.print_error(f"Exception: {e}")
            self.failed += 1
            return False

    def test_read_text_section(self) -> bool:
        """Test reading ASCII text section."""
        self.print_test("Reading ASCII Text Section")

        try:
            # Text starts at offset 72 (8 header + 64 pattern)
            response = self.client.send_command("data/read", {
                "offset": 72,
                "length": 35
            })

            if response.get("status") == "success":
                data = response.get("data", {})
                hex_data = data.get("data", "")

                # Convert hex to ASCII
                text = bytes.fromhex(hex_data).decode('ascii', errors='replace')
                # Remove null terminator
                text = text.rstrip('\x00')

                self.print_success(f"Read text: '{text}'")

                if "Hello from ImHex" in text:
                    self.print_success("Text content verified!")
                    self.passed += 1
                    return True
                else:
                    self.print_error(f"Unexpected text content")
                    self.failed += 1
                    return False
            else:
                error = response.get("data", {}).get("error", "Unknown error")
                self.print_error(f"Read failed: {error}")
                self.failed += 1
                return False

        except Exception as e:
            self.print_error(f"Exception: {e}")
            self.failed += 1
            return False

    def test_add_bookmark(self) -> bool:
        """Test adding a bookmark."""
        self.print_test("Adding Bookmark to Header")

        try:
            response = self.client.send_command("bookmark/add", {
                "offset": 0,
                "size": 8,
                "name": "File Header",
                "comment": "Magic bytes and version"
            })

            if response.get("status") == "success":
                data = response.get("data", {})
                self.print_success("Bookmark added successfully")
                self.print_info(f"Name: {data.get('name', 'unknown')}")
                self.print_info(f"Offset: 0x{data.get('offset', 0):X}")
                self.print_info(f"Size: {data.get('size', 0)} bytes")
                self.passed += 1
                return True
            else:
                error = response.get("data", {}).get("error", "Unknown error")
                self.print_error(f"Bookmark failed: {error}")
                self.failed += 1
                return False

        except Exception as e:
            self.print_error(f"Exception: {e}")
            self.failed += 1
            return False

    def test_multi_hash_comparison(self) -> bool:
        """Test calculating multiple hash algorithms."""
        self.print_test("Multi-Hash Comparison (MD5, SHA-1, SHA-256)")

        algorithms = ["md5", "sha1", "sha256"]
        hashes = {}

        try:
            for algo in algorithms:
                response = self.client.send_command("hash/calculate", {
                    "offset": 0,
                    "length": 32,
                    "algorithm": algo
                })

                if response.get("status") == "success":
                    hash_value = response.get("data", {}).get("hash", "")
                    hashes[algo] = hash_value
                else:
                    self.print_error(f"{algo.upper()} hash failed")
                    self.failed += 1
                    return False

            self.print_success("All hashes calculated successfully")
            for algo, hash_value in hashes.items():
                self.print_info(f"{algo.upper()}: {hash_value}")

            self.passed += 1
            return True

        except Exception as e:
            self.print_error(f"Exception: {e}")
            self.failed += 1
            return False

    def run_all_tests(self):
        """Run all binary analysis tests."""
        self.print_section("ImHex MCP - Comprehensive Binary Analysis Tests")

        # Create test file
        print("Preparing test environment...")
        self.test_file = self.create_test_binary()

        # Run tests
        self.print_section("Test Suite")

        # Test 1: Open file
        if not self.test_open_file(self.test_file):
            print("\n⚠ Cannot continue without opening file")
            return

        # Test 2: Read header
        self.test_read_header()

        # Test 3: Inspect data types
        self.test_data_inspect()

        # Test 4: Calculate hash
        self.test_calculate_hash()

        # Test 5: Search pattern
        self.test_search_pattern()

        # Test 6: Read text
        self.test_read_text_section()

        # Test 7: Add bookmark
        self.test_add_bookmark()

        # Test 8: Multi-hash comparison
        self.test_multi_hash_comparison()

        # Summary
        self.print_section("Test Summary")
        print(f"Total tests run: {self.passed + self.failed}")
        print(f"✓ Passed: {self.passed}")
        print(f"✗ Failed: {self.failed}")

        if self.failed == 0:
            print("\n🎉 All binary analysis tests passed!")
        else:
            print(f"\n⚠ {self.failed} test(s) failed")

        # Cleanup
        if self.test_file and os.path.exists(self.test_file):
            os.unlink(self.test_file)
            print(f"\nCleaned up test file: {self.test_file}")


if __name__ == "__main__":
    tests = BinaryAnalysisTests()
    tests.run_all_tests()
