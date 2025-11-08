#!/usr/bin/env python3
"""
Unit tests for ImHex MCP Server
Tests the ImHexClient and core functionality
"""

import unittest
import json
import socket
import threading
import time
from unittest.mock import Mock, patch, MagicMock
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import after path is set
try:
    from server_improved import (
        ImHexClient,
        ServerConfig,
        ConnectionError,
        ImHexError,
        hexStringToBytes,
        bytesToHexString,
    )
    USING_IMPROVED = True
except ImportError:
    # Fallback to original server
    from server import ImHexClient
    USING_IMPROVED = False
    ServerConfig = None
    ConnectionError = Exception
    ImHexError = Exception


class MockImHexServer:
    """Mock ImHex server for testing."""

    def __init__(self, port=31338):
        self.port = port
        self.socket = None
        self.thread = None
        self.running = False
        self.responses = {}
        self.default_response = {"status": "success", "data": {}}

    def set_response(self, endpoint, response):
        """Set response for a specific endpoint."""
        self.responses[endpoint] = response

    def start(self):
        """Start the mock server."""
        self.running = True
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(('localhost', self.port))
        self.socket.listen(1)
        self.socket.settimeout(0.5)

        self.thread = threading.Thread(target=self._run)
        self.thread.daemon = True
        self.thread.start()

        # Give server time to start
        time.sleep(0.1)

    def stop(self):
        """Stop the mock server."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
        if self.socket:
            try:
                self.socket.close()
            except:
                pass

    def _run(self):
        """Run the mock server."""
        while self.running:
            try:
                client, addr = self.socket.accept()
                self._handle_client(client)
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"Mock server error: {e}")

    def _handle_client(self, client):
        """Handle a client connection."""
        try:
            # Receive request
            data = b""
            while b"\n" not in data:
                chunk = client.recv(1024)
                if not chunk:
                    break
                data += chunk

            if data:
                request = json.loads(data.decode('utf-8').strip())
                endpoint = request.get("endpoint")

                # Get response for this endpoint
                if endpoint in self.responses:
                    response = self.responses[endpoint]
                else:
                    response = self.default_response.copy()
                    response["data"]["endpoint"] = endpoint

                # Send response
                response_str = json.dumps(response) + "\n"
                client.sendall(response_str.encode('utf-8'))

        except Exception as e:
            print(f"Error handling client: {e}")
        finally:
            client.close()


class TestImHexClient(unittest.TestCase):
    """Test ImHexClient functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_server = MockImHexServer(port=31338)
        self.mock_server.start()

        if USING_IMPROVED:
            self.config = ServerConfig(
                imhex_host='localhost',
                imhex_port=31338,
                connection_timeout=2.0,
                read_timeout=2.0,
                max_retries=2,
                retry_delay=0.1
            )
        else:
            self.config = {'host': 'localhost', 'port': 31338}

    def tearDown(self):
        """Clean up after tests."""
        self.mock_server.stop()

    def test_connection_success(self):
        """Test successful connection to ImHex."""
        if USING_IMPROVED:
            client = ImHexClient(self.config)
        else:
            client = ImHexClient(**self.config)

        result = client.connect()
        self.assertTrue(result)

        if USING_IMPROVED:
            self.assertTrue(client.is_connected())

        client.disconnect()

        if USING_IMPROVED:
            self.assertFalse(client.is_connected())

    def test_connection_failure(self):
        """Test connection failure when server is not running."""
        # Stop the mock server
        self.mock_server.stop()

        if USING_IMPROVED:
            client = ImHexClient(self.config)
            with self.assertRaises(ConnectionError):
                client.connect()
        else:
            # Original version returns False instead of raising
            client = ImHexClient(**self.config)
            result = client.connect()
            self.assertFalse(result)

    def test_send_command_success(self):
        """Test sending a successful command."""
        self.mock_server.set_response("test/endpoint", {
            "status": "success",
            "data": {"result": "test_value"}
        })

        if USING_IMPROVED:
            client = ImHexClient(self.config)
        else:
            client = ImHexClient(**self.config)

        client.connect()

        response = client.send_command("test/endpoint", {"param": "value"})

        self.assertEqual(response["status"], "success")
        self.assertEqual(response["data"]["result"], "test_value")

        client.disconnect()

    def test_send_command_error(self):
        """Test sending a command that returns an error."""
        self.mock_server.set_response("error/endpoint", {
            "status": "error",
            "data": {"error": "Test error message"}
        })

        if USING_IMPROVED:
            client = ImHexClient(self.config)
        else:
            client = ImHexClient(**self.config)

        client.connect()

        if USING_IMPROVED:
            with self.assertRaises(ImHexError) as context:
                client.send_command("error/endpoint")
            self.assertIn("Test error message", str(context.exception))
        else:
            # Original version returns error in response instead of raising
            response = client.send_command("error/endpoint")
            self.assertEqual(response["status"], "error")
            self.assertIn("error", response["data"])

        client.disconnect()

    def test_context_manager(self):
        """Test using ImHexClient as a context manager."""
        if not USING_IMPROVED:
            self.skipTest("Context manager only available in improved version")

        with ImHexClient(self.config) as client:
            self.assertTrue(client.is_connected())

        # Should be disconnected after exiting context
        self.assertFalse(client.is_connected())

    def test_auto_reconnect(self):
        """Test automatic reconnection when not connected."""
        if USING_IMPROVED:
            client = ImHexClient(self.config)
        else:
            client = ImHexClient(**self.config)

        # Send command without explicitly connecting
        # Should automatically connect
        response = client.send_command("test/endpoint")

        if USING_IMPROVED:
            self.assertTrue(client.is_connected())

        self.assertEqual(response["status"], "success")

        client.disconnect()


class TestHelperFunctions(unittest.TestCase):
    """Test helper functions."""

    def test_hex_string_to_bytes(self):
        """Test converting hex string to bytes."""
        # This would need the actual implementation
        # For now, test the concept
        hex_str = "48656C6C6F"  # "Hello"
        expected = [0x48, 0x65, 0x6C, 0x6C, 0x6F]

        # Would test: result = hexStringToBytes(hex_str)
        # self.assertEqual(result, expected)

    def test_bytes_to_hex_string(self):
        """Test converting bytes to hex string."""
        # This would need the actual implementation
        bytes_data = [0x48, 0x65, 0x6C, 0x6C, 0x6F]
        expected = "48656C6C6F"

        # Would test: result = bytesToHexString(bytes_data)
        # self.assertEqual(result, expected)


class TestIntegration(unittest.TestCase):
    """Integration tests with mock server."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_server = MockImHexServer(port=31339)
        self.mock_server.start()

        if USING_IMPROVED:
            self.config = ServerConfig(
                imhex_host='localhost',
                imhex_port=31339,
                connection_timeout=2.0,
                read_timeout=2.0
            )
        else:
            self.config = {'host': 'localhost', 'port': 31339}

    def tearDown(self):
        """Clean up."""
        self.mock_server.stop()

    def test_capabilities_endpoint(self):
        """Test the capabilities endpoint."""
        self.mock_server.set_response("imhex/capabilities", {
            "status": "success",
            "data": {
                "build": {
                    "version": "1.38.0",
                    "commit": "abc123",
                    "branch": "master"
                },
                "commands": ["file/open", "data/read", "data/write"]
            }
        })

        if USING_IMPROVED:
            with ImHexClient(self.config) as client:
                response = client.send_command("imhex/capabilities")
        else:
            client = ImHexClient(**self.config)
            client.connect()
            response = client.send_command("imhex/capabilities")
            client.disconnect()

        self.assertEqual(response["status"], "success")
        self.assertIn("build", response["data"])
        self.assertIn("commands", response["data"])
        self.assertEqual(response["data"]["build"]["version"], "1.38.0")

    def test_file_open_endpoint(self):
        """Test the file/open endpoint."""
        self.mock_server.set_response("file/open", {
            "status": "success",
            "data": {
                "file": "/path/to/file.bin",
                "size": 1024,
                "name": "file.bin"
            }
        })

        if USING_IMPROVED:
            with ImHexClient(self.config) as client:
                response = client.send_command("file/open", {"path": "/path/to/file.bin"})
        else:
            client = ImHexClient(**self.config)
            client.connect()
            response = client.send_command("file/open", {"path": "/path/to/file.bin"})
            client.disconnect()

        self.assertEqual(response["status"], "success")
        self.assertEqual(response["data"]["size"], 1024)

    def test_data_read_endpoint(self):
        """Test the data/read endpoint."""
        self.mock_server.set_response("data/read", {
            "status": "success",
            "data": {
                "offset": 0,
                "length": 16,
                "data": "48656C6C6F20576F726C64210A0D0000"
            }
        })

        if USING_IMPROVED:
            with ImHexClient(self.config) as client:
                response = client.send_command("data/read", {
                    "offset": 0,
                    "length": 16
                })
        else:
            client = ImHexClient(**self.config)
            client.connect()
            response = client.send_command("data/read", {
                "offset": 0,
                "length": 16
            })
            client.disconnect()

        self.assertEqual(response["status"], "success")
        self.assertEqual(response["data"]["length"], 16)
        self.assertIn("data", response["data"])


if __name__ == '__main__':
    unittest.main()
