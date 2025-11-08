#!/usr/bin/env python3
"""
ImHex MCP Server
A Model Context Protocol server that exposes ImHex functionality to AI assistants.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
    INVALID_PARAMS,
    INTERNAL_ERROR,
)
from pydantic import AnyUrl
import socket

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("imhex-mcp-server")

# ImHex TCP server configuration
IMHEX_HOST = "localhost"
IMHEX_PORT = 31337

class ImHexClient:
    """Client for communicating with ImHex's TCP interface."""

    def __init__(self, host: str = IMHEX_HOST, port: int = IMHEX_PORT):
        self.host = host
        self.port = port
        self.socket: Optional[socket.socket] = None

    def connect(self) -> bool:
        """Connect to ImHex TCP server."""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5.0)
            self.socket.connect((self.host, self.port))
            logger.info(f"Connected to ImHex at {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to ImHex: {e}")
            self.socket = None
            return False

    def disconnect(self):
        """Disconnect from ImHex TCP server."""
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None

    def send_command(self, endpoint: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Send a command to ImHex and return the response."""
        if not self.socket:
            if not self.connect():
                return {"status": "error", "data": {"error": "Not connected to ImHex"}}

        try:
            # Prepare request
            request = {
                "endpoint": endpoint,
                "data": data or {}
            }

            # Send request
            request_json = json.dumps(request) + "\n"
            self.socket.sendall(request_json.encode('utf-8'))

            # Receive response
            response_data = b""
            while True:
                chunk = self.socket.recv(4096)
                if not chunk:
                    break
                response_data += chunk
                if b"\n" in response_data:
                    break

            # Parse response
            response_str = response_data.decode('utf-8').strip()
            response = json.loads(response_str)
            return response

        except Exception as e:
            logger.error(f"Error sending command to ImHex: {e}")
            self.disconnect()
            return {"status": "error", "data": {"error": str(e)}}


# Initialize ImHex client
imhex_client = ImHexClient()

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
                        "description": "Offset to start reading from (in bytes)"
                    },
                    "length": {
                        "type": "integer",
                        "description": "Number of bytes to read"
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
                        "description": "Offset to start writing to (in bytes)"
                    },
                    "data": {
                        "type": "string",
                        "description": "Hex data to write (e.g., '0A1B2C3D')"
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
                        "enum": ["hex", "text", "regex"],
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
                        "description": "Hash algorithm (md5, sha1, sha256, sha512, etc.)"
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Offset to start hashing from"
                    },
                    "length": {
                        "type": "integer",
                        "description": "Number of bytes to hash"
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
                        "description": "Offset of the bookmark"
                    },
                    "size": {
                        "type": "integer",
                        "description": "Size of the bookmarked region"
                    },
                    "name": {
                        "type": "string",
                        "description": "Name/comment for the bookmark"
                    },
                    "color": {
                        "type": "string",
                        "description": "Color of the bookmark (hex RGB, e.g., 'FF0000')"
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
                        "description": "Offset to inspect"
                    },
                    "types": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Data types to display (int8, int16, int32, int64, float, double, ascii, etc.)"
                    }
                },
                "required": ["offset"]
            }
        ),
        Tool(
            name="imhex_decode",
            description="Decode data using various encoding schemes",
            inputSchema={
                "type": "object",
                "properties": {
                    "data": {
                        "type": "string",
                        "description": "Data to decode (hex string)"
                    },
                    "encoding": {
                        "type": "string",
                        "description": "Encoding type (base64, ascii85, url, etc.)"
                    }
                },
                "required": ["data", "encoding"]
            }
        ),
        Tool(
            name="imhex_disassemble",
            description="Disassemble binary code at a specific offset",
            inputSchema={
                "type": "object",
                "properties": {
                    "offset": {
                        "type": "integer",
                        "description": "Offset to start disassembly"
                    },
                    "length": {
                        "type": "integer",
                        "description": "Number of bytes to disassemble"
                    },
                    "architecture": {
                        "type": "string",
                        "description": "Architecture (x86, x64, arm, arm64, mips, etc.)"
                    }
                },
                "required": ["offset", "length", "architecture"]
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> List[TextContent | ImageContent | EmbeddedResource]:
    """Handle tool calls."""

    try:
        # Get capabilities
        if name == "imhex_get_capabilities":
            response = imhex_client.send_command("imhex/capabilities")
            if response.get("status") == "success":
                return [TextContent(
                    type="text",
                    text=json.dumps(response.get("data", {}), indent=2)
                )]
            else:
                error_msg = response.get("data", {}).get("error", "Unknown error")
                return [TextContent(type="text", text=f"Error: {error_msg}")]

        # Set pattern code
        elif name == "imhex_set_pattern_code":
            code = arguments.get("code")
            response = imhex_client.send_command("pattern_editor/set_code", {"code": code})
            if response.get("status") == "success":
                return [TextContent(type="text", text="Pattern code set successfully")]
            else:
                error_msg = response.get("data", {}).get("error", "Unknown error")
                return [TextContent(type="text", text=f"Error: {error_msg}")]

        # Open file
        elif name == "imhex_open_file":
            path = arguments.get("path")
            response = imhex_client.send_command("file/open", {"path": path})
            if response.get("status") == "success":
                return [TextContent(type="text", text=f"File opened: {path}")]
            else:
                error_msg = response.get("data", {}).get("error", "Unknown error")
                return [TextContent(type="text", text=f"Error: {error_msg}")]

        # Read hex data
        elif name == "imhex_read_hex":
            offset = arguments.get("offset")
            length = arguments.get("length")
            response = imhex_client.send_command("data/read", {
                "offset": offset,
                "length": length
            })
            if response.get("status") == "success":
                data = response.get("data", {})
                return [TextContent(type="text", text=json.dumps(data, indent=2))]
            else:
                error_msg = response.get("data", {}).get("error", "Unknown error")
                return [TextContent(type="text", text=f"Error: {error_msg}")]

        # Write hex data
        elif name == "imhex_write_hex":
            offset = arguments.get("offset")
            data = arguments.get("data")
            response = imhex_client.send_command("data/write", {
                "offset": offset,
                "data": data
            })
            if response.get("status") == "success":
                return [TextContent(type="text", text="Data written successfully")]
            else:
                error_msg = response.get("data", {}).get("error", "Unknown error")
                return [TextContent(type="text", text=f"Error: {error_msg}")]

        # Search
        elif name == "imhex_search":
            pattern = arguments.get("pattern")
            search_type = arguments.get("type")
            response = imhex_client.send_command("search/find", {
                "pattern": pattern,
                "type": search_type
            })
            if response.get("status") == "success":
                results = response.get("data", {})
                return [TextContent(type="text", text=json.dumps(results, indent=2))]
            else:
                error_msg = response.get("data", {}).get("error", "Unknown error")
                return [TextContent(type="text", text=f"Error: {error_msg}")]

        # Hash calculation
        elif name == "imhex_hash":
            algorithm = arguments.get("algorithm")
            offset = arguments.get("offset", 0)
            length = arguments.get("length")
            response = imhex_client.send_command("hash/calculate", {
                "algorithm": algorithm,
                "offset": offset,
                "length": length
            })
            if response.get("status") == "success":
                hash_result = response.get("data", {})
                return [TextContent(type="text", text=json.dumps(hash_result, indent=2))]
            else:
                error_msg = response.get("data", {}).get("error", "Unknown error")
                return [TextContent(type="text", text=f"Error: {error_msg}")]

        # Add bookmark
        elif name == "imhex_bookmark_add":
            offset = arguments.get("offset")
            size = arguments.get("size")
            name = arguments.get("name")
            color = arguments.get("color", "FF0000")
            response = imhex_client.send_command("bookmark/add", {
                "offset": offset,
                "size": size,
                "name": name,
                "color": color
            })
            if response.get("status") == "success":
                return [TextContent(type="text", text="Bookmark added successfully")]
            else:
                error_msg = response.get("data", {}).get("error", "Unknown error")
                return [TextContent(type="text", text=f"Error: {error_msg}")]

        # Inspect data
        elif name == "imhex_inspect_data":
            offset = arguments.get("offset")
            types = arguments.get("types", ["int8", "int16", "int32", "float", "ascii"])
            response = imhex_client.send_command("data/inspect", {
                "offset": offset,
                "types": types
            })
            if response.get("status") == "success":
                inspection = response.get("data", {})
                return [TextContent(type="text", text=json.dumps(inspection, indent=2))]
            else:
                error_msg = response.get("data", {}).get("error", "Unknown error")
                return [TextContent(type="text", text=f"Error: {error_msg}")]

        # Decode data
        elif name == "imhex_decode":
            data = arguments.get("data")
            encoding = arguments.get("encoding")
            response = imhex_client.send_command("data/decode", {
                "data": data,
                "encoding": encoding
            })
            if response.get("status") == "success":
                decoded = response.get("data", {})
                return [TextContent(type="text", text=json.dumps(decoded, indent=2))]
            else:
                error_msg = response.get("data", {}).get("error", "Unknown error")
                return [TextContent(type="text", text=f"Error: {error_msg}")]

        # Disassemble
        elif name == "imhex_disassemble":
            offset = arguments.get("offset")
            length = arguments.get("length")
            architecture = arguments.get("architecture")
            response = imhex_client.send_command("disassemble/code", {
                "offset": offset,
                "length": length,
                "architecture": architecture
            })
            if response.get("status") == "success":
                disassembly = response.get("data", {})
                return [TextContent(type="text", text=json.dumps(disassembly, indent=2))]
            else:
                error_msg = response.get("data", {}).get("error", "Unknown error")
                return [TextContent(type="text", text=f"Error: {error_msg}")]

        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

    except Exception as e:
        logger.error(f"Error executing tool {name}: {e}")
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def main():
    """Run the MCP server."""
    logger.info("Starting ImHex MCP Server...")

    # Run the server using stdin/stdout
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
