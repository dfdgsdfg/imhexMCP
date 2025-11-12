#!/usr/bin/env python3
"""
ImHex MCP Integration Tests

Comprehensive end-to-end integration tests for all ImHex MCP endpoints.
Tests ensure that all endpoints work correctly with real ImHex instance.

Usage:
    python3 test_all_endpoints.py [--host HOST] [--port PORT] [--verbose]

Requirements:
    - ImHex must be running with Network Interface enabled
    - Port 31337 must be accessible

Example:
    python3 test_all_endpoints.py --verbose
"""

import socket
import json
import sys
import argparse
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Optional, Any

# Add lib directory to path for error handling
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "lib"))

from error_handling import (
    retry_with_backoff,
    ConnectionError as ImHexConnectionError,
    HealthCheck
)


class ImHexMCPTest:
    """Integration test framework for ImHex MCP."""

    def __init__(self, host: str = "localhost", port: int = 31337, verbose: bool = False) -> None:
        self.host = host
        self.port = port
        self.verbose = verbose
        self.passed = 0
        self.failed = 0
        self.test_files: Dict[str, str] = {}
        self.provider_ids: List[int] = []

    def log(self, message: str) -> None:
        """Print message if verbose mode is enabled."""
        if self.verbose:
            print(f"  {message}")

    @retry_with_backoff(max_attempts=3, initial_delay=0.5, exponential_base=2.0)
    def send_request(self, endpoint: str, data: Optional[Dict[str, Any]] = None,
                     timeout: int = 10) -> Dict[str, Any]:
        """Send request to ImHex MCP.

        Automatically retries on transient network failures with exponential backoff.
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect((self.host, self.port))

            request = json.dumps({
                "endpoint": endpoint,
                "data": data or {}
            }) + "\n"

            sock.sendall(request.encode())

            response = b""
            while b"\n" not in response:
                response += sock.recv(4096)

            sock.close()
            return json.loads(response.decode().strip())

        except (socket.error, socket.timeout, ConnectionRefusedError) as e:
            # Check if this is the final retry attempt
            if isinstance(e, ConnectionRefusedError):
                # Let retry decorator handle it, but if all retries fail, show helpful message
                raise
            # For other network errors, let retry decorator handle them
            raise
        except Exception as e:
            return {"status": "error", "data": {"error": str(e)}}

    def assert_success(self, result: Dict[str, Any], test_name: str) -> bool:
        """Assert that result status is success."""
        if result.get("status") == "success":
            self.passed += 1
            print(f"  ✓ {test_name}")
            return True
        else:
            self.failed += 1
            error = result.get("data", {}).get("error", "Unknown error")
            print(f"  ✗ {test_name}: {error}")
            return False

    def assert_field(self, result: Dict[str, Any], field: str, test_name: str) -> bool:
        """Assert that result data contains a specific field."""
        if result.get("status") == "success" and field in result.get("data", {}):
            self.passed += 1
            print(f"  ✓ {test_name}")
            return True
        else:
            self.failed += 1
            print(f"  ✗ {test_name}: Field '{field}' not found")
            return False

    def create_test_files(self) -> None:
        """Create test files of various sizes and types."""
        self.log("Creating test files...")

        # Small binary file (1KB) with known patterns
        small = tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='_test.bin')
        # Write magic bytes + data
        small.write(b'\x7fELF')  # ELF magic
        small.write(b'\x00' * 1020)  # Padding to 1KB
        small.close()
        self.test_files['small'] = small.name

        # Medium file (10KB) with strings
        medium = tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='_test.bin')
        medium.write(b'Test String 123\x00' * 100)
        medium.write(b'\x90' * 1024)  # NOP sled
        medium.write(b'password=secret\x00')
        medium.write(b'\x00' * (10240 - medium.tell()))
        medium.close()
        self.test_files['medium'] = medium.name

        self.log(f"Created {len(self.test_files)} test files")

    def cleanup_test_files(self) -> None:
        """Remove test files."""
        for file_path in self.test_files.values():
            try:
                Path(file_path).unlink()
            except:
                pass

    def test_core_endpoints(self) -> None:
        """Test core system endpoints."""
        print("\n[1/8] Testing Core Endpoints")
        print("-" * 70)

        # Test: capabilities
        result = self.send_request("capabilities")
        if self.assert_success(result, "capabilities"):
            endpoints = result.get("data", {}).get("endpoints", [])
            self.log(f"Found {len(endpoints)} available endpoints")

        # Test: status
        result = self.send_request("status")
        self.assert_success(result, "status")

    def test_file_operations(self) -> None:
        """Test file operation endpoints."""
        print("\n[2/8] Testing File Operations")
        print("-" * 70)

        # Test: file/list (should be empty initially)
        result = self.send_request("file/list")
        if self.assert_success(result, "file/list (empty)"):
            count = result.get("data", {}).get("count", 0)
            self.log(f"Files open: {count}")

        # Test: file/open
        result = self.send_request("file/open", {"path": self.test_files['small']})
        self.assert_success(result, "file/open")

        time.sleep(0.5)  # Wait for async file open

        # Test: file/list (should have 1 file)
        result = self.send_request("file/list")
        if self.assert_success(result, "file/list (with files)"):
            providers = result.get("data", {}).get("providers", [])
            if providers:
                self.provider_ids.append(providers[0]["id"])
                self.log(f"Provider ID: {providers[0]['id']}")

        # Test: file/current
        result = self.send_request("file/current")
        if self.assert_success(result, "file/current"):
            provider_id = result.get("data", {}).get("provider_id")
            self.log(f"Current provider: {provider_id}")

        # Test: file/info
        if self.provider_ids:
            result = self.send_request("file/info", {"provider_id": self.provider_ids[0]})
            if self.assert_field(result, "size", "file/info"):
                size = result.get("data", {}).get("size")
                self.log(f"File size: {size} bytes")

    def test_data_operations(self) -> None:
        """Test data operation endpoints."""
        print("\n[3/8] Testing Data Operations")
        print("-" * 70)

        if not self.provider_ids:
            print("  ⚠ Skipping: No providers available")
            return

        provider_id = self.provider_ids[0]

        # Test: data/read
        result = self.send_request("data/read", {
            "provider_id": provider_id,
            "offset": 0,
            "size": 64
        })
        if self.assert_success(result, "data/read (64 bytes)"):
            data = result.get("data", {}).get("data", "")
            self.log(f"Read {len(data)//2} bytes")

        # Test: data/read (larger)
        result = self.send_request("data/read", {
            "provider_id": provider_id,
            "offset": 0,
            "size": 1024
        })
        self.assert_success(result, "data/read (1KB)")

        # Test: data/size
        result = self.send_request("data/size", {"provider_id": provider_id})
        if self.assert_field(result, "size", "data/size"):
            size = result.get("data", {}).get("size")
            self.log(f"Provider size: {size} bytes")

    def test_hashing_operations(self) -> None:
        """Test hashing endpoints."""
        print("\n[4/8] Testing Hashing Operations")
        print("-" * 70)

        if not self.provider_ids:
            print("  ⚠ Skipping: No providers available")
            return

        provider_id = self.provider_ids[0]

        algorithms = ["md5", "sha1", "sha256", "sha384", "sha512"]

        for algorithm in algorithms:
            result = self.send_request("data/hash", {
                "provider_id": provider_id,
                "offset": 0,
                "size": 1024,
                "algorithm": algorithm
            })
            if self.assert_field(result, "hash", f"data/hash ({algorithm})"):
                hash_value = result.get("data", {}).get("hash", "")
                self.log(f"{algorithm.upper()}: {hash_value[:16]}...")

    def test_search_operations(self) -> None:
        """Test search endpoints."""
        print("\n[5/8] Testing Search Operations")
        print("-" * 70)

        if not self.provider_ids:
            print("  ⚠ Skipping: No providers available")
            return

        provider_id = self.provider_ids[0]

        # Test: data/search (hex)
        result = self.send_request("data/search", {
            "provider_id": provider_id,
            "pattern": "00",
            "type": "hex"
        })
        if self.assert_success(result, "data/search (hex pattern)"):
            matches = result.get("data", {}).get("matches", [])
            self.log(f"Found {len(matches)} matches")

        # Test: data/search (string)
        result = self.send_request("data/search", {
            "provider_id": provider_id,
            "pattern": "ELF",
            "type": "string"
        })
        self.assert_success(result, "data/search (string pattern)")

    def test_analysis_operations(self) -> None:
        """Test advanced analysis endpoints."""
        print("\n[6/8] Testing Analysis Operations")
        print("-" * 70)

        if not self.provider_ids:
            print("  ⚠ Skipping: No providers available")
            return

        provider_id = self.provider_ids[0]

        # Test: data/entropy
        result = self.send_request("data/entropy", {
            "provider_id": provider_id,
            "offset": 0,
            "size": 1024
        })
        if self.assert_field(result, "entropy", "data/entropy"):
            entropy = result.get("data", {}).get("entropy")
            self.log(f"Entropy: {entropy:.4f}")

        # Test: data/statistics
        result = self.send_request("data/statistics", {
            "provider_id": provider_id,
            "offset": 0,
            "size": 1024
        })
        if self.assert_field(result, "byte_frequency", "data/statistics"):
            freq = result.get("data", {}).get("byte_frequency", {})
            self.log(f"Analyzed {len(freq)} byte values")

        # Test: data/strings
        result = self.send_request("data/strings", {
            "provider_id": provider_id,
            "offset": 0,
            "size": 1024,
            "min_length": 4,
            "type": "ascii"
        })
        if self.assert_success(result, "data/strings"):
            strings = result.get("data", {}).get("strings", [])
            self.log(f"Found {len(strings)} strings")

        # Test: data/magic
        result = self.send_request("data/magic", {"provider_id": provider_id})
        if self.assert_success(result, "data/magic"):
            matches = result.get("data", {}).get("matches", [])
            self.log(f"Found {len(matches)} magic signature matches")

        # Test: data/disassemble
        result = self.send_request("data/disassemble", {
            "provider_id": provider_id,
            "offset": 0,
            "size": 64,
            "architecture": "x86_64"
        })
        if self.assert_success(result, "data/disassemble"):
            instructions = result.get("data", {}).get("instructions", [])
            self.log(f"Disassembled {len(instructions)} instructions")

    def test_bookmark_operations(self) -> None:
        """Test bookmark endpoints."""
        print("\n[7/8] Testing Bookmark Operations")
        print("-" * 70)

        if not self.provider_ids:
            print("  ⚠ Skipping: No providers available")
            return

        provider_id = self.provider_ids[0]

        # Test: bookmark/list (empty)
        result = self.send_request("bookmark/list", {"provider_id": provider_id})
        self.assert_success(result, "bookmark/list (empty)")

        # Test: bookmark/add
        result = self.send_request("bookmark/add", {
            "provider_id": provider_id,
            "offset": 0,
            "size": 4,
            "name": "Test Bookmark",
            "comment": "Integration test bookmark"
        })
        self.assert_success(result, "bookmark/add")

        # Test: bookmark/list (with bookmarks)
        result = self.send_request("bookmark/list", {"provider_id": provider_id})
        if self.assert_success(result, "bookmark/list (with bookmarks)"):
            bookmarks = result.get("data", {}).get("bookmarks", [])
            self.log(f"Found {len(bookmarks)} bookmarks")

    def test_batch_operations(self) -> None:
        """Test batch operation endpoints."""
        print("\n[8/8] Testing Batch Operations")
        print("-" * 70)

        # Open second file for batch operations
        result = self.send_request("file/open", {"path": self.test_files['medium']})
        time.sleep(0.5)

        # Get all provider IDs
        result = self.send_request("file/list")
        if result.get("status") == "success":
            providers = result.get("data", {}).get("providers", [])
            provider_ids = [p["id"] for p in providers]

            if len(provider_ids) >= 2:
                # Test: batch/hash
                result = self.send_request("batch/hash", {
                    "provider_ids": provider_ids,
                    "algorithm": "sha256"
                })
                if self.assert_success(result, "batch/hash"):
                    results = result.get("data", {}).get("results", [])
                    self.log(f"Hashed {len(results)} files")

                # Test: batch/search
                result = self.send_request("batch/search", {
                    "provider_ids": provider_ids,
                    "pattern": "00",
                    "type": "hex"
                })
                if self.assert_success(result, "batch/search"):
                    results = result.get("data", {}).get("results", [])
                    self.log(f"Searched {len(results)} files")

                # Test: batch/diff
                result = self.send_request("batch/diff", {
                    "reference_id": provider_ids[0],
                    "target_ids": [provider_ids[1]]
                })
                if self.assert_success(result, "batch/diff"):
                    results = result.get("data", {}).get("results", [])
                    self.log(f"Compared {len(results)} file pairs")
            else:
                print("  ⚠ Skipping: Need at least 2 files for batch operations")

    def cleanup_providers(self) -> None:
        """Close all open providers."""
        self.log("Closing providers...")
        for provider_id in self.provider_ids:
            self.send_request("file/close", {"provider_id": provider_id})

    def run_all_tests(self) -> int:
        """Run complete integration test suite."""
        print(f"\n{'='*70}")
        print(f"ImHex MCP Integration Tests")
        print(f"  Host: {self.host}:{self.port}")
        print(f"{'='*70}")

        # Setup
        self.create_test_files()

        # Run all test categories
        self.test_core_endpoints()
        self.test_file_operations()
        self.test_data_operations()
        self.test_hashing_operations()
        self.test_search_operations()
        self.test_analysis_operations()
        self.test_bookmark_operations()
        self.test_batch_operations()

        # Cleanup
        self.cleanup_providers()
        self.cleanup_test_files()

        # Print results
        print(f"\n{'='*70}")
        print(f"INTEGRATION TEST RESULTS")
        print(f"{'='*70}")
        print(f"  Passed: {self.passed}")
        print(f"  Failed: {self.failed}")
        print(f"  Total:  {self.passed + self.failed}")

        if self.failed == 0:
            print(f"\n  ✅ All tests PASSED!")
            print(f"{'='*70}\n")
            return 0
        else:
            print(f"\n  ❌ {self.failed} test(s) FAILED")
            print(f"{'='*70}\n")
            return 1


def main() -> None:
    parser = argparse.ArgumentParser(description="ImHex MCP integration tests")
    parser.add_argument("--host", default="localhost", help="ImHex MCP host (default: localhost)")
    parser.add_argument("--port", type=int, default=31337, help="ImHex MCP port (default: 31337)")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")

    args = parser.parse_args()

    # Run tests
    tester = ImHexMCPTest(args.host, args.port, args.verbose)
    exit_code = tester.run_all_tests()

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
