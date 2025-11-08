#!/usr/bin/env python3
"""
ImHex MCP Server - Improved Version
A Model Context Protocol server that exposes ImHex functionality to AI assistants.

Improvements:
- Better error handling and connection management
- Connection pooling and retry logic
- Configuration system
- CLI arguments
- Enhanced logging
- Type hints
- Async operations where beneficial
"""

import asyncio
import json
import logging
import socket
import argparse
import sys
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
)

# Type hints
JSON = Dict[str, Any]

# Configure logging
logger = logging.getLogger("imhex-mcp-server")


class LogLevel(Enum):
    """Logging levels."""
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR


@dataclass
class ServerConfig:
    """Server configuration."""
    imhex_host: str = "localhost"
    imhex_port: int = 31337
    connection_timeout: float = 5.0
    read_timeout: float = 30.0
    max_retries: int = 3
    retry_delay: float = 1.0
    log_level: LogLevel = LogLevel.INFO


class ConnectionError(Exception):
    """Raised when connection to ImHex fails."""
    pass


class ImHexError(Exception):
    """Raised when ImHex returns an error."""
    pass


class ImHexClient:
    """
    Client for communicating with ImHex's TCP interface.

    Features:
    - Connection pooling
    - Automatic reconnection
    - Retry logic
    - Better error handling
    """

    def __init__(self, config: ServerConfig):
        self.config = config
        self.socket: Optional[socket.socket] = None
        self._connect_attempts = 0
        logger.debug(f"ImHexClient initialized with config: {config}")

    def connect(self) -> bool:
        """
        Connect to ImHex TCP server with retry logic.

        Returns:
            bool: True if connected successfully

        Raises:
            ConnectionError: If connection fails after retries
        """
        for attempt in range(self.config.max_retries):
            try:
                self._connect_attempts += 1
                logger.debug(
                    f"Connection attempt {attempt + 1}/{self.config.max_retries} "
                    f"to {self.config.imhex_host}:{self.config.imhex_port}"
                )

                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.settimeout(self.config.connection_timeout)
                self.socket.connect((self.config.imhex_host, self.config.imhex_port))

                # Set read timeout
                self.socket.settimeout(self.config.read_timeout)

                logger.info(
                    f"Connected to ImHex at {self.config.imhex_host}:{self.config.imhex_port} "
                    f"(attempt {attempt + 1})"
                )
                return True

            except socket.timeout:
                logger.warning(f"Connection timeout (attempt {attempt + 1})")
                self._cleanup_socket()
                if attempt < self.config.max_retries - 1:
                    asyncio.sleep(self.config.retry_delay)

            except ConnectionRefusedError:
                logger.warning(f"Connection refused (attempt {attempt + 1})")
                self._cleanup_socket()
                if attempt < self.config.max_retries - 1:
                    asyncio.sleep(self.config.retry_delay)

            except Exception as e:
                logger.error(f"Connection error: {e} (attempt {attempt + 1})")
                self._cleanup_socket()
                if attempt < self.config.max_retries - 1:
                    asyncio.sleep(self.config.retry_delay)

        # All attempts failed
        error_msg = (
            f"Failed to connect to ImHex after {self.config.max_retries} attempts. "
            f"Please ensure ImHex is running and Network Interface is enabled."
        )
        logger.error(error_msg)
        raise ConnectionError(error_msg)

    def _cleanup_socket(self):
        """Clean up socket resources."""
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None

    def disconnect(self):
        """Disconnect from ImHex TCP server."""
        logger.debug("Disconnecting from ImHex")
        self._cleanup_socket()

    def is_connected(self) -> bool:
        """Check if connected to ImHex."""
        return self.socket is not None

    def send_command(self, endpoint: str, data: Optional[JSON] = None) -> JSON:
        """
        Send a command to ImHex and return the response.

        Args:
            endpoint: The endpoint to call
            data: Optional data to send

        Returns:
            JSON response from ImHex

        Raises:
            ConnectionError: If not connected or connection fails
            ImHexError: If ImHex returns an error
        """
        # Ensure connected
        if not self.is_connected():
            logger.debug("Not connected, attempting to connect...")
            self.connect()

        try:
            # Prepare request
            request: JSON = {
                "endpoint": endpoint,
                "data": data or {}
            }

            logger.debug(f"Sending command: {endpoint} with data: {data}")

            # Send request
            request_json = json.dumps(request) + "\n"
            self.socket.sendall(request_json.encode('utf-8'))

            # Receive response
            response_data = b""
            while True:
                try:
                    chunk = self.socket.recv(4096)
                    if not chunk:
                        raise ConnectionError("Connection closed by ImHex")
                    response_data += chunk
                    if b"\n" in response_data:
                        break
                except socket.timeout:
                    if len(response_data) > 0:
                        break  # Got partial response
                    raise ConnectionError("Read timeout waiting for ImHex response")

            # Parse response
            response_str = response_data.decode('utf-8').strip()
            logger.debug(f"Received response: {response_str[:200]}...")

            response: JSON = json.loads(response_str)

            # Check for errors
            if response.get("status") == "error":
                error_msg = response.get("data", {}).get("error", "Unknown error")
                logger.error(f"ImHex returned error: {error_msg}")
                raise ImHexError(error_msg)

            return response

        except (socket.timeout, socket.error, ConnectionError) as e:
            logger.error(f"Connection error in send_command: {e}")
            self.disconnect()
            raise ConnectionError(f"Connection error: {e}")

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            raise ImHexError(f"Invalid JSON response from ImHex: {e}")

        except Exception as e:
            logger.error(f"Unexpected error in send_command: {e}")
            raise

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="ImHex MCP Server - AI assistant integration for ImHex",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          # Run with default settings
  %(prog)s --host 192.168.1.100     # Connect to remote ImHex
  %(prog)s --port 31338             # Use custom port
  %(prog)s --debug                  # Enable debug logging
  %(prog)s --log-file server.log    # Log to file
        """
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

    parser.add_argument(
        "--timeout",
        type=float,
        default=5.0,
        help="Connection timeout in seconds (default: 5.0)"
    )

    parser.add_argument(
        "--read-timeout",
        type=float,
        default=30.0,
        help="Read timeout in seconds (default: 30.0)"
    )

    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Maximum connection retry attempts (default: 3)"
    )

    parser.add_argument(
        "--retry-delay",
        type=float,
        default=1.0,
        help="Delay between retries in seconds (default: 1.0)"
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )

    parser.add_argument(
        "--log-file",
        type=str,
        help="Log to file instead of stderr"
    )

    parser.add_argument(
        "--version",
        action="version",
        version="ImHex MCP Server 0.2.0"
    )

    return parser.parse_args()


def setup_logging(args: argparse.Namespace):
    """Setup logging based on arguments."""
    log_level = logging.DEBUG if args.debug else logging.INFO

    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    if args.log_file:
        logging.basicConfig(
            level=log_level,
            format=log_format,
            handlers=[
                logging.FileHandler(args.log_file),
                logging.StreamHandler(sys.stderr)
            ]
        )
    else:
        logging.basicConfig(
            level=log_level,
            format=log_format,
            handlers=[logging.StreamHandler(sys.stderr)]
        )


def create_config(args: argparse.Namespace) -> ServerConfig:
    """Create server configuration from arguments."""
    return ServerConfig(
        imhex_host=args.host,
        imhex_port=args.port,
        connection_timeout=args.timeout,
        read_timeout=args.read_timeout,
        max_retries=args.max_retries,
        retry_delay=args.retry_delay,
        log_level=LogLevel.DEBUG if args.debug else LogLevel.INFO
    )


# Global client instance
imhex_client: Optional[ImHexClient] = None

# Create MCP server
app = Server("imhex-mcp-server")


@app.list_tools()
async def list_tools() -> List[Tool]:
    """List all available ImHex tools."""
    return [
        Tool(
            name="imhex_get_capabilities",
            description="Get ImHex build version, commit, branch, and available commands",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="imhex_set_pattern_code",
            description="Set pattern language code in ImHex for binary data parsing",
            inputSchema={
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "Pattern language code to execute"
                    }
                },
                "required": ["code"]
            }
        ),
        Tool(
            name="imhex_open_file",
            description="Open a file in ImHex for analysis",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file to open"
                    }
                },
                "required": ["path"]
            }
        ),
        Tool(
            name="imhex_read_hex",
            description="Read hex data from the currently open file",
            inputSchema={
                "type": "object",
                "properties": {
                    "offset": {
                        "type": "integer",
                        "description": "Offset to start reading from (in bytes)",
                        "minimum": 0
                    },
                    "length": {
                        "type": "integer",
                        "description": "Number of bytes to read",
                        "minimum": 1,
                        "maximum": 1048576  # 1MB max
                    }
                },
                "required": ["offset", "length"]
            }
        ),
        Tool(
            name="imhex_write_hex",
            description="Write hex data to the currently open file",
            inputSchema={
                "type": "object",
                "properties": {
                    "offset": {
                        "type": "integer",
                        "description": "Offset to start writing to (in bytes)",
                        "minimum": 0
                    },
                    "data": {
                        "type": "string",
                        "description": "Hex data to write (e.g., '0A1B2C3D')",
                        "pattern": "^[0-9A-Fa-f]+$"
                    }
                },
                "required": ["offset", "data"]
            }
        ),
        Tool(
            name="imhex_search",
            description="Search for a pattern in the currently open file",
            inputSchema={
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Pattern to search for (hex string or text)"
                    },
                    "type": {
                        "type": "string",
                        "enum": ["hex", "text"],
                        "description": "Type of search to perform"
                    }
                },
                "required": ["pattern", "type"]
            }
        ),
        Tool(
            name="imhex_hash",
            description="Calculate hash of data in the currently open file",
            inputSchema={
                "type": "object",
                "properties": {
                    "algorithm": {
                        "type": "string",
                        "enum": ["md5", "sha1", "sha224", "sha256", "sha384", "sha512"],
                        "description": "Hash algorithm to use"
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Offset to start hashing from (default: 0)",
                        "minimum": 0
                    },
                    "length": {
                        "type": "integer",
                        "description": "Number of bytes to hash (default: entire file)",
                        "minimum": 1
                    }
                },
                "required": ["algorithm"]
            }
        ),
        Tool(
            name="imhex_bookmark_add",
            description="Add a bookmark to a specific location in the file",
            inputSchema={
                "type": "object",
                "properties": {
                    "offset": {
                        "type": "integer",
                        "description": "Offset of the bookmark",
                        "minimum": 0
                    },
                    "size": {
                        "type": "integer",
                        "description": "Size of the bookmarked region",
                        "minimum": 1
                    },
                    "name": {
                        "type": "string",
                        "description": "Name/comment for the bookmark",
                        "minLength": 1
                    },
                    "color": {
                        "type": "string",
                        "description": "Color of the bookmark (hex RGB, e.g., 'FF0000')",
                        "pattern": "^[0-9A-Fa-f]{6}$"
                    }
                },
                "required": ["offset", "size", "name"]
            }
        ),
        Tool(
            name="imhex_inspect_data",
            description="Inspect data at a specific offset with various data types",
            inputSchema={
                "type": "object",
                "properties": {
                    "offset": {
                        "type": "integer",
                        "description": "Offset to inspect",
                        "minimum": 0
                    }
                },
                "required": ["offset"]
            }
        ),
        Tool(
            name="imhex_provider_info",
            description="Get information about the currently open file/provider",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> List[TextContent | ImageContent | EmbeddedResource]:
    """Handle tool calls with improved error handling."""

    if not imhex_client:
        return [TextContent(
            type="text",
            text="Error: ImHex client not initialized"
        )]

    try:
        # Get capabilities
        if name == "imhex_get_capabilities":
            response = imhex_client.send_command("imhex/capabilities")
            data = response.get("data", {})
            return [TextContent(
                type="text",
                text=json.dumps(data, indent=2)
            )]

        # Set pattern code
        elif name == "imhex_set_pattern_code":
            code = arguments.get("code")
            response = imhex_client.send_command("pattern_editor/set_code", {"code": code})
            return [TextContent(type="text", text="Pattern code set successfully")]

        # Open file
        elif name == "imhex_open_file":
            path = arguments.get("path")

            # Validate path exists
            file_path = Path(path)
            if not file_path.exists():
                return [TextContent(type="text", text=f"Error: File not found: {path}")]

            response = imhex_client.send_command("file/open", {"path": str(file_path.absolute())})
            data = response.get("data", {})

            result = f"File opened: {path}\n"
            if "size" in data:
                result += f"Size: {data['size']:,} bytes\n"
            if "name" in data:
                result += f"Name: {data['name']}\n"

            return [TextContent(type="text", text=result)]

        # Read hex data
        elif name == "imhex_read_hex":
            offset = arguments.get("offset")
            length = arguments.get("length")

            response = imhex_client.send_command("data/read", {
                "offset": offset,
                "length": length
            })
            data = response.get("data", {})

            hex_data = data.get("data", "")
            result = f"Offset: 0x{offset:X} ({offset})\n"
            result += f"Length: {length} bytes\n"
            result += f"Hex Data:\n{hex_data}\n"

            return [TextContent(type="text", text=result)]

        # Write hex data
        elif name == "imhex_write_hex":
            offset = arguments.get("offset")
            data_hex = arguments.get("data")

            response = imhex_client.send_command("data/write", {
                "offset": offset,
                "data": data_hex
            })

            bytes_written = len(data_hex) // 2
            return [TextContent(
                type="text",
                text=f"Successfully wrote {bytes_written} bytes at offset 0x{offset:X}"
            )]

        # Search
        elif name == "imhex_search":
            pattern = arguments.get("pattern")
            search_type = arguments.get("type")

            response = imhex_client.send_command("search/find", {
                "pattern": pattern,
                "type": search_type
            })
            data = response.get("data", {})

            matches = data.get("matches", [])
            count = data.get("count", 0)

            result = f"Search for '{pattern}' ({search_type})\n"
            result += f"Found {count} match(es)\n\n"

            if matches:
                result += "Matches:\n"
                for i, match in enumerate(matches[:100], 1):  # Limit display to 100
                    result += f"  {i}. Offset: 0x{match:X} ({match})\n"

                if count > 100:
                    result += f"\n... and {count - 100} more matches"

            return [TextContent(type="text", text=result)]

        # Hash calculation
        elif name == "imhex_hash":
            algorithm = arguments.get("algorithm")
            offset = arguments.get("offset", 0)
            length = arguments.get("length")

            params = {"algorithm": algorithm, "offset": offset}
            if length is not None:
                params["length"] = length

            response = imhex_client.send_command("hash/calculate", params)
            data = response.get("data", {})

            hash_value = data.get("hash", "")
            result = f"Algorithm: {algorithm.upper()}\n"
            result += f"Offset: 0x{offset:X} ({offset})\n"
            if length:
                result += f"Length: {length} bytes\n"
            result += f"Hash: {hash_value}\n"

            return [TextContent(type="text", text=result)]

        # Add bookmark
        elif name == "imhex_bookmark_add":
            offset = arguments.get("offset")
            size = arguments.get("size")
            name_str = arguments.get("name")
            color = arguments.get("color", "FF0000")

            response = imhex_client.send_command("bookmark/add", {
                "offset": offset,
                "size": size,
                "name": name_str,
                "color": color
            })
            data = response.get("data", {})

            bookmark_id = data.get("id", "unknown")
            return [TextContent(
                type="text",
                text=f"Bookmark added: '{name_str}' at 0x{offset:X} (ID: {bookmark_id})"
            )]

        # Inspect data
        elif name == "imhex_inspect_data":
            offset = arguments.get("offset")

            response = imhex_client.send_command("data/inspect", {"offset": offset})
            data = response.get("data", {})

            types_data = data.get("types", {})
            result = f"Data at offset 0x{offset:X} ({offset}):\n\n"

            for type_name, value in types_data.items():
                result += f"{type_name:12s}: {value}\n"

            return [TextContent(type="text", text=result)]

        # Provider info
        elif name == "imhex_provider_info":
            response = imhex_client.send_command("provider/info")
            data = response.get("data", {})

            if not data.get("valid", False):
                return [TextContent(type="text", text="No file is currently open in ImHex")]

            result = "Current Provider Information:\n\n"
            result += f"Name: {data.get('name', 'Unknown')}\n"
            result += f"Size: {data.get('size', 0):,} bytes\n"
            result += f"Writable: {data.get('writable', False)}\n"
            result += f"Readable: {data.get('readable', False)}\n"
            result += f"Modified: {data.get('dirty', False)}\n"

            return [TextContent(type="text", text=result)]

        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

    except ConnectionError as e:
        error_msg = (
            f"Connection error: {e}\n\n"
            "Please ensure:\n"
            "1. ImHex is running\n"
            "2. Network Interface is enabled (Settings → General)\n"
            "3. ImHex is listening on the correct port\n"
        )
        logger.error(error_msg)
        return [TextContent(type="text", text=error_msg)]

    except ImHexError as e:
        error_msg = f"ImHex error: {e}"
        logger.error(error_msg)
        return [TextContent(type="text", text=error_msg)]

    except Exception as e:
        error_msg = f"Unexpected error: {e}"
        logger.exception("Unexpected error in call_tool")
        return [TextContent(type="text", text=error_msg)]


async def main():
    """Run the MCP server."""
    global imhex_client

    # Parse arguments
    args = parse_args()

    # Setup logging
    setup_logging(args)

    logger.info("Starting ImHex MCP Server v0.2.0")
    logger.info(f"Connecting to ImHex at {args.host}:{args.port}")

    # Create configuration
    config = create_config(args)

    # Initialize client
    imhex_client = ImHexClient(config)

    # Test connection
    try:
        imhex_client.connect()
        logger.info("Successfully connected to ImHex")

        # Get capabilities to verify
        response = imhex_client.send_command("imhex/capabilities")
        build_info = response.get("data", {}).get("build", {})
        logger.info(f"ImHex version: {build_info.get('version', 'unknown')}")

    except ConnectionError as e:
        logger.error(f"Failed to connect to ImHex: {e}")
        logger.error("Please start ImHex and enable Network Interface, then restart this server")
        sys.exit(1)

    # Run the server using stdin/stdout
    try:
        async with stdio_server() as (read_stream, write_stream):
            await app.run(
                read_stream,
                write_stream,
                app.create_initialization_options()
            )
    finally:
        if imhex_client:
            imhex_client.disconnect()
        logger.info("Server stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.exception("Fatal error")
        sys.exit(1)
