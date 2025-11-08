#!/usr/bin/env python3
"""
Real Integration Tests for ImHex MCP Server
Tests all endpoints against an actual running ImHex instance.

Usage:
    1. Start ImHex with Network Interface enabled
    2. Optionally open a file in ImHex
    3. Run: python test_real_integration.py
"""

import sys
import json
import socket
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
import tempfile
import os

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from server import ImHexClient, ServerConfig


class Color:
    """Terminal colors for output."""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'


class IntegrationTestRunner:
    """Runner for real integration tests."""

    def __init__(self, host: str = "localhost", port: int = 31337):
        """Initialize test runner."""
        self.host = host
        self.port = port
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.test_results: List[Dict[str, Any]] = []

        self.config = ServerConfig(
            imhex_host=host,
            imhex_port=port,
            connection_timeout=5.0,
            read_timeout=10.0,
            max_retries=1
        )
        self.client = ImHexClient(self.config)

    def print_header(self, text: str):
        """Print section header."""
        print(f"\n{Color.BOLD}{Color.BLUE}{'=' * 70}{Color.END}")
        print(f"{Color.BOLD}{Color.BLUE}{text}{Color.END}")
        print(f"{Color.BOLD}{Color.BLUE}{'=' * 70}{Color.END}\n")

    def print_test(self, name: str):
        """Print test name."""
        print(f"{Color.BOLD}Testing: {name}{Color.END}")

    def print_success(self, message: str):
        """Print success message."""
        print(f"{Color.GREEN}✓ {message}{Color.END}")

    def print_error(self, message: str):
        """Print error message."""
        print(f"{Color.RED}✗ {message}{Color.END}")

    def print_warning(self, message: str):
        """Print warning message."""
        print(f"{Color.YELLOW}⚠ {message}{Color.END}")

    def print_info(self, message: str):
        """Print info message."""
        print(f"  {message}")

    def record_result(self, test_name: str, passed: bool, details: str = ""):
        """Record test result."""
        self.tests_run += 1
        if passed:
            self.tests_passed += 1
        else:
            self.tests_failed += 1

        self.test_results.append({
            "test": test_name,
            "passed": passed,
            "details": details
        })

    def test_connection(self) -> bool:
        """Test basic connection to ImHex."""
        self.print_test("Connection to ImHex")

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5.0)
            sock.connect((self.host, self.port))
            sock.close()

            self.print_success(f"Connected to ImHex at {self.host}:{self.port}")
            self.record_result("Connection", True)
            return True

        except ConnectionRefusedError:
            self.print_error("Connection refused")
            self.print_warning("Make sure ImHex is running")
            self.print_warning("Enable Network Interface in Settings → General")
            self.record_result("Connection", False, "Connection refused")
            return False

        except socket.timeout:
            self.print_error("Connection timed out")
            self.record_result("Connection", False, "Timeout")
            return False

        except Exception as e:
            self.print_error(f"Error: {e}")
            self.record_result("Connection", False, str(e))
            return False

    def test_capabilities(self) -> Optional[Dict]:
        """Test capabilities endpoint."""
        self.print_test("Capabilities Endpoint")

        try:
            response = self.client.send_command("imhex/capabilities", {})

            if response.get("status") == "success":
                data = response.get("data", {})

                # Check for required fields
                build = data.get("build", {})
                version = build.get("version", "unknown")

                self.print_success(f"ImHex version: {version}")
                self.print_info(f"Build commit: {build.get('commit', 'unknown')}")
                self.print_info(f"Build branch: {build.get('branch', 'unknown')}")

                # List available endpoints
                commands = data.get("commands", [])
                self.print_info(f"Available endpoints: {len(commands)}")
                for cmd in sorted(commands):
                    self.print_info(f"  - {cmd}")

                self.record_result("Capabilities", True, f"Version: {version}")
                return data

            else:
                error = response.get("data", {}).get("error", "Unknown error")
                self.print_error(f"Error: {error}")
                self.record_result("Capabilities", False, error)
                return None

        except Exception as e:
            self.print_error(f"Exception: {e}")
            self.record_result("Capabilities", False, str(e))
            return None

    def test_file_info(self) -> Optional[Dict]:
        """Test getting file information."""
        self.print_test("File Info Endpoint")

        try:
            response = self.client.send_command("file/info", {})

            if response.get("status") == "success":
                data = response.get("data", {})

                if data.get("has_file"):
                    self.print_success("File is open in ImHex")
                    self.print_info(f"File: {data.get('file', 'unknown')}")
                    self.print_info(f"Size: {data.get('size', 0)} bytes")
                    self.print_info(f"Name: {data.get('name', 'unknown')}")
                    self.record_result("File Info", True, f"File: {data.get('name')}")
                    return data
                else:
                    self.print_warning("No file is currently open in ImHex")
                    self.print_info("Open a file in ImHex to test file operations")
                    self.record_result("File Info", True, "No file open")
                    return None

            else:
                error = response.get("data", {}).get("error", "Unknown error")
                self.print_error(f"Error: {error}")
                self.record_result("File Info", False, error)
                return None

        except Exception as e:
            self.print_error(f"Exception: {e}")
            self.record_result("File Info", False, str(e))
            return None

    def test_data_read(self, file_info: Optional[Dict]) -> bool:
        """Test reading data from file."""
        self.print_test("Data Read Endpoint")

        if not file_info or not file_info.get("has_file"):
            self.print_warning("Skipping - no file open")
            self.record_result("Data Read", True, "Skipped - no file")
            return True

        try:
            # Read first 64 bytes
            response = self.client.send_command("data/read", {
                "offset": 0,
                "length": 64
            })

            if response.get("status") == "success":
                data = response.get("data", {})
                hex_data = data.get("data", "")

                self.print_success(f"Read {len(hex_data) // 2} bytes from offset 0")
                self.print_info(f"First 32 bytes: {hex_data[:64]}")
                self.record_result("Data Read", True, f"Read {len(hex_data) // 2} bytes")
                return True

            else:
                error = response.get("data", {}).get("error", "Unknown error")
                self.print_error(f"Error: {error}")
                self.record_result("Data Read", False, error)
                return False

        except Exception as e:
            self.print_error(f"Exception: {e}")
            self.record_result("Data Read", False, str(e))
            return False

    def test_data_inspect(self, file_info: Optional[Dict]) -> bool:
        """Test data inspection (type interpretations)."""
        self.print_test("Data Inspect Endpoint")

        if not file_info or not file_info.get("has_file"):
            self.print_warning("Skipping - no file open")
            self.record_result("Data Inspect", True, "Skipped - no file")
            return True

        try:
            response = self.client.send_command("data/inspect", {
                "offset": 0,
                "length": 16
            })

            if response.get("status") == "success":
                data = response.get("data", {})
                types = data.get("types", {})

                self.print_success(f"Inspected {data.get('length')} bytes at offset {data.get('offset')}")
                self.print_info(f"Data interpretations: {len(types)}")

                # Show some interpretations
                for type_name, value in list(types.items())[:10]:
                    self.print_info(f"  {type_name}: {value}")

                if len(types) > 10:
                    self.print_info(f"  ... and {len(types) - 10} more")

                self.record_result("Data Inspect", True, f"{len(types)} interpretations")
                return True

            else:
                error = response.get("data", {}).get("error", "Unknown error")
                self.print_error(f"Error: {error}")
                self.record_result("Data Inspect", False, error)
                return False

        except Exception as e:
            self.print_error(f"Exception: {e}")
            self.record_result("Data Inspect", False, str(e))
            return False

    def test_hash(self, file_info: Optional[Dict]) -> bool:
        """Test hash calculation."""
        self.print_test("Hash Endpoint")

        if not file_info or not file_info.get("has_file"):
            self.print_warning("Skipping - no file open")
            self.record_result("Hash", True, "Skipped - no file")
            return True

        try:
            # Calculate SHA-256 hash of first 256 bytes
            response = self.client.send_command("data/hash", {
                "offset": 0,
                "length": 256,
                "algorithm": "sha256"
            })

            if response.get("status") == "success":
                data = response.get("data", {})
                hash_value = data.get("hash", "")

                self.print_success(f"SHA-256 hash calculated")
                self.print_info(f"Algorithm: {data.get('algorithm')}")
                self.print_info(f"Hash: {hash_value}")
                self.record_result("Hash", True, f"SHA-256: {hash_value[:16]}...")
                return True

            else:
                error = response.get("data", {}).get("error", "Unknown error")
                self.print_error(f"Error: {error}")
                self.record_result("Hash", False, error)
                return False

        except Exception as e:
            self.print_error(f"Exception: {e}")
            self.record_result("Hash", False, str(e))
            return False

    def test_search(self, file_info: Optional[Dict]) -> bool:
        """Test search functionality."""
        self.print_test("Search Endpoint")

        if not file_info or not file_info.get("has_file"):
            self.print_warning("Skipping - no file open")
            self.record_result("Search", True, "Skipped - no file")
            return True

        try:
            # Search for null bytes (should be common in binary files)
            response = self.client.send_command("data/search", {
                "pattern": "00",
                "offset": 0,
                "length": 1024
            })

            if response.get("status") == "success":
                data = response.get("data", {})
                matches = data.get("matches", [])

                self.print_success(f"Search completed")
                self.print_info(f"Pattern: {data.get('pattern')}")
                self.print_info(f"Found {len(matches)} matches")

                if matches:
                    self.print_info(f"First few matches: {matches[:5]}")

                self.record_result("Search", True, f"Found {len(matches)} matches")
                return True

            else:
                error = response.get("data", {}).get("error", "Unknown error")
                self.print_error(f"Error: {error}")
                self.record_result("Search", False, error)
                return False

        except Exception as e:
            self.print_error(f"Exception: {e}")
            self.record_result("Search", False, str(e))
            return False

    def test_bookmarks_list(self) -> bool:
        """Test listing bookmarks."""
        self.print_test("Bookmarks List Endpoint")

        try:
            response = self.client.send_command("bookmarks/list", {})

            if response.get("status") == "success":
                data = response.get("data", {})
                bookmarks = data.get("bookmarks", [])

                self.print_success(f"Retrieved {len(bookmarks)} bookmarks")

                if bookmarks:
                    for i, bookmark in enumerate(bookmarks[:5]):
                        self.print_info(f"  [{i}] {bookmark.get('name', 'unnamed')}: "
                                      f"offset={bookmark.get('offset')}, "
                                      f"size={bookmark.get('size')}")
                    if len(bookmarks) > 5:
                        self.print_info(f"  ... and {len(bookmarks) - 5} more")
                else:
                    self.print_info("No bookmarks found")

                self.record_result("Bookmarks List", True, f"{len(bookmarks)} bookmarks")
                return True

            else:
                error = response.get("data", {}).get("error", "Unknown error")
                self.print_error(f"Error: {error}")
                self.record_result("Bookmarks List", False, error)
                return False

        except Exception as e:
            self.print_error(f"Exception: {e}")
            self.record_result("Bookmarks List", False, str(e))
            return False

    def test_decode(self, file_info: Optional[Dict]) -> bool:
        """Test data decoding."""
        self.print_test("Data Decode Endpoint")

        if not file_info or not file_info.get("has_file"):
            self.print_warning("Skipping - no file open")
            self.record_result("Data Decode", True, "Skipped - no file")
            return True

        try:
            response = self.client.send_command("data/decode", {
                "offset": 0,
                "length": 16,
                "encoding": "base64"
            })

            if response.get("status") == "success":
                data = response.get("data", {})

                self.print_success("Data decoded successfully")
                self.print_info(f"Encoding: {data.get('encoding')}")
                self.print_info(f"Decoded: {data.get('decoded', '')[:100]}")
                self.record_result("Data Decode", True, "Base64 decoded")
                return True

            else:
                error = response.get("data", {}).get("error", "Unknown error")
                self.print_error(f"Error: {error}")
                self.record_result("Data Decode", False, error)
                return False

        except Exception as e:
            self.print_error(f"Exception: {e}")
            self.record_result("Data Decode", False, str(e))
            return False

    def print_summary(self):
        """Print test summary."""
        self.print_header("Test Summary")

        print(f"Total tests run: {self.tests_run}")
        print(f"{Color.GREEN}Passed: {self.tests_passed}{Color.END}")
        print(f"{Color.RED}Failed: {self.tests_failed}{Color.END}")

        if self.tests_failed > 0:
            print(f"\n{Color.BOLD}Failed Tests:{Color.END}")
            for result in self.test_results:
                if not result["passed"]:
                    print(f"  {Color.RED}✗ {result['test']}{Color.END}: {result['details']}")

        print()
        if self.tests_failed == 0:
            print(f"{Color.GREEN}{Color.BOLD}All tests passed!{Color.END}")
            return 0
        else:
            print(f"{Color.RED}{Color.BOLD}Some tests failed!{Color.END}")
            return 1

    def run_all_tests(self) -> int:
        """Run all integration tests."""
        self.print_header("ImHex MCP Server - Real Integration Tests")

        print(f"Testing against: {self.host}:{self.port}")
        print()

        # Test connection first
        if not self.test_connection():
            self.print_error("\nCannot connect to ImHex. Please ensure:")
            self.print_error("  1. ImHex is running")
            self.print_error("  2. Network Interface is enabled (Settings → General)")
            self.print_error("  3. ImHex has been restarted after enabling network interface")
            return 1

        # Connect client
        try:
            self.client.connect()
        except Exception as e:
            self.print_error(f"Failed to connect client: {e}")
            return 1

        # Run all tests
        try:
            capabilities = self.test_capabilities()
            file_info = self.test_file_info()

            self.test_data_read(file_info)
            self.test_data_inspect(file_info)
            self.test_hash(file_info)
            self.test_search(file_info)
            self.test_bookmarks_list()
            self.test_decode(file_info)

        finally:
            # Disconnect
            try:
                self.client.disconnect()
            except:
                pass

        # Print summary
        return self.print_summary()


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Real integration tests for ImHex MCP Server"
    )
    parser.add_argument(
        "--host",
        default="localhost",
        help="ImHex host (default: localhost)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=31337,
        help="ImHex port (default: 31337)"
    )

    args = parser.parse_args()

    runner = IntegrationTestRunner(host=args.host, port=args.port)
    return runner.run_all_tests()


if __name__ == "__main__":
    sys.exit(main())
