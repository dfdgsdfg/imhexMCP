#!/usr/bin/env python3
"""
ImHex MCP CLI Tool

A command-line interface for interacting with the ImHex MCP server.

Usage:
    imhex-cli status                    # Check server status
    imhex-cli files list                # List open files
    imhex-cli files open FILE           # Open a file
    imhex-cli files read ID OFFSET SIZE # Read data from file
    imhex-cli files search ID PATTERN   # Search for pattern
    imhex-cli data strings ID           # Extract strings
    imhex-cli data magic ID             # Detect file type
    imhex-cli metrics                   # Show metrics
    imhex-cli interactive               # Interactive mode
"""

import sys
import json
import socket
import click
from typing import Dict, Any, Optional
from pathlib import Path
import time


class ImHexClient:
    """Client for ImHex MCP server."""

    def __init__(self, host: str = "localhost", port: int = 31337, timeout: int = 10):
        """Initialize client."""
        self.host = host
        self.port = port
        self.timeout = timeout

    def send_request(self, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Send request to server."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            sock.connect((self.host, self.port))

            request = {"endpoint": endpoint, "data": data or {}}
            request_json = json.dumps(request) + "\n"
            sock.sendall(request_json.encode())

            response = b""
            while b"\n" not in response:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                response += chunk

            sock.close()

            return json.loads(response.decode().strip())

        except socket.timeout:
            return {"status": "error", "data": {"error": "Request timeout"}}
        except ConnectionRefusedError:
            return {"status": "error", "data": {"error": "Connection refused - is ImHex running?"}}
        except Exception as e:
            return {"status": "error", "data": {"error": str(e)}}


# Global client instance
client = ImHexClient()


def format_size(size: int) -> str:
    """Format size in human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} TB"


def print_success(message: str):
    """Print success message."""
    click.secho(f"✓ {message}", fg="green")


def print_error(message: str):
    """Print error message."""
    click.secho(f"✗ {message}", fg="red", err=True)


def print_info(message: str):
    """Print info message."""
    click.secho(f"ℹ {message}", fg="blue")


def print_warning(message: str):
    """Print warning message."""
    click.secho(f"⚠ {message}", fg="yellow")


def handle_response(response: Dict[str, Any], success_msg: Optional[str] = None):
    """Handle server response."""
    if response.get("status") == "success":
        if success_msg:
            print_success(success_msg)
        return response.get("data", {})
    else:
        error = response.get("data", {}).get("error", "Unknown error")
        print_error(f"Error: {error}")
        sys.exit(1)


@click.group()
@click.option('--host', default='localhost', help='Server host')
@click.option('--port', default=31337, help='Server port')
@click.option('--timeout', default=10, help='Request timeout in seconds')
def cli(host, port, timeout):
    """ImHex MCP CLI - Command-line interface for ImHex MCP server."""
    global client
    client = ImHexClient(host, port, timeout)


# ============================================================================
# Status Commands
# ============================================================================

@cli.command()
def status():
    """Check server status and capabilities."""
    click.echo("Checking ImHex MCP server status...")
    click.echo()

    # Test connection
    response = client.send_request("capabilities")

    if response.get("status") == "error":
        print_error(f"Server unavailable: {response['data']['error']}")
        sys.exit(1)

    data = response.get("data", {})

    print_success("Server is running")
    click.echo()

    # Show capabilities
    click.secho("Available Endpoints:", bold=True)
    endpoints = data.get("endpoints", [])
    for endpoint in endpoints:
        click.echo(f"  • {endpoint}")

    click.echo()

    # Show version info
    version = data.get("version", "Unknown")
    click.secho(f"Version: {version}", bold=True)


@cli.command()
def metrics():
    """Show server metrics."""
    click.echo("Fetching server metrics...")
    click.echo()

    response = client.send_request("health")
    data = handle_response(response)

    # Display health status
    click.secho("Health Status:", bold=True)
    click.echo(f"  Status: {data.get('status', 'unknown')}")
    click.echo(f"  Uptime: {data.get('uptime', 0):.2f}s")
    click.echo()

    # Show metrics if available
    if "metrics" in data:
        metrics = data["metrics"]
        click.secho("Performance Metrics:", bold=True)
        click.echo(f"  Requests: {metrics.get('requests', 0)}")
        click.echo(f"  Errors: {metrics.get('errors', 0)}")
        click.echo(f"  Avg Latency: {metrics.get('avg_latency', 0):.2f}ms")


# ============================================================================
# File Commands
# ============================================================================

@cli.group()
def files():
    """File operations."""
    pass


@files.command('list')
def files_list():
    """List all open files."""
    response = client.send_request("file/list")
    data = handle_response(response)

    count = data.get("count", 0)
    providers = data.get("providers", [])

    if count == 0:
        print_info("No files currently open")
        return

    click.secho(f"\nOpen Files ({count}):", bold=True)
    click.echo()

    for provider in providers:
        provider_id = provider.get("id", "?")
        name = provider.get("name", "Unknown")
        size = provider.get("size", 0)
        readable = provider.get("readable", False)
        writable = provider.get("writable", False)

        click.echo(f"  [{provider_id}] {name}")
        click.echo(f"      Size: {format_size(size)}")
        flags = []
        if readable:
            flags.append("readable")
        if writable:
            flags.append("writable")
        click.echo(f"      Flags: {', '.join(flags) if flags else 'none'}")
        click.echo()


@files.command('open')
@click.argument('file_path', type=click.Path(exists=True))
def files_open(file_path):
    """Open a file in ImHex."""
    abs_path = str(Path(file_path).absolute())

    click.echo(f"Opening file: {abs_path}")

    response = client.send_request("file/open", {"path": abs_path})
    data = handle_response(response, "File opened successfully")

    click.echo()
    if "message" in data:
        print_info(data["message"])


@files.command('read')
@click.argument('provider_id', type=int)
@click.argument('offset', type=int)
@click.argument('size', type=int)
@click.option('--hex', is_flag=True, help='Display as hex dump')
@click.option('--ascii', is_flag=True, help='Display ASCII representation')
def files_read(provider_id, offset, size, hex, ascii):
    """Read data from a file."""
    response = client.send_request("file/read", {
        "provider_id": provider_id,
        "offset": offset,
        "size": size
    })
    data = handle_response(response)

    hex_data = data.get("data", "")

    if not hex_data:
        print_warning("No data returned")
        return

    click.echo()
    click.secho(f"Data from provider {provider_id} at offset 0x{offset:08x}:", bold=True)
    click.echo()

    # Convert hex string to bytes
    try:
        bytes_data = bytes.fromhex(hex_data)
    except ValueError:
        print_error("Invalid hex data received")
        return

    if hex or not ascii:
        # Hex dump format
        for i in range(0, len(bytes_data), 16):
            chunk = bytes_data[i:i+16]
            hex_str = ' '.join(f'{b:02x}' for b in chunk)
            ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
            click.echo(f"  {offset+i:08x}  {hex_str:<48}  {ascii_str}")

    if ascii:
        click.echo()
        # ASCII representation
        ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in bytes_data)
        click.echo(f"  ASCII: {ascii_str}")


@files.command('search')
@click.argument('provider_id', type=int)
@click.argument('pattern')
@click.option('--max-results', default=10, help='Maximum number of results')
def files_search(provider_id, pattern, max_results):
    """Search for a hex pattern in a file."""
    # Remove spaces and 0x prefix if present
    pattern = pattern.replace(" ", "").replace("0x", "").upper()

    click.echo(f"Searching for pattern: {pattern}")
    click.echo()

    response = client.send_request("file/search", {
        "provider_id": provider_id,
        "pattern": pattern
    })
    data = handle_response(response)

    results = data.get("results", [])

    if not results:
        print_info("No matches found")
        return

    click.secho(f"Found {len(results)} match(es):", bold=True)
    click.echo()

    for i, offset in enumerate(results[:max_results], 1):
        click.echo(f"  [{i}] Offset: 0x{offset:08x} ({offset})")

    if len(results) > max_results:
        click.echo()
        print_info(f"Showing first {max_results} of {len(results)} results")


# ============================================================================
# Data Analysis Commands
# ============================================================================

@cli.group()
def data():
    """Data analysis operations."""
    pass


@data.command('strings')
@click.argument('provider_id', type=int)
@click.option('--offset', default=0, help='Start offset')
@click.option('--size', default=1024, help='Data size to analyze')
@click.option('--min-length', default=4, help='Minimum string length')
@click.option('--type', default='ascii', type=click.Choice(['ascii', 'utf8', 'utf16']), help='String type')
@click.option('--max-results', default=20, help='Maximum results to display')
def data_strings(provider_id, offset, size, min_length, type, max_results):
    """Extract strings from binary data."""
    click.echo(f"Extracting {type} strings (min length: {min_length})...")
    click.echo()

    response = client.send_request("data/strings", {
        "provider_id": provider_id,
        "offset": offset,
        "size": size,
        "min_length": min_length,
        "type": type
    })
    data = handle_response(response)

    strings = data.get("strings", [])

    if not strings:
        print_info("No strings found")
        return

    click.secho(f"Found {len(strings)} string(s):", bold=True)
    click.echo()

    for i, s in enumerate(strings[:max_results], 1):
        str_offset = s.get("offset", 0)
        value = s.get("value", "")
        str_type = s.get("type", "unknown")

        click.echo(f"  [{i}] 0x{str_offset:08x} ({str_type}): \"{value}\"")

    if len(strings) > max_results:
        click.echo()
        print_info(f"Showing first {max_results} of {len(strings)} results")


@data.command('magic')
@click.argument('provider_id', type=int)
def data_magic(provider_id):
    """Detect file type using magic signatures."""
    click.echo("Detecting file type...")
    click.echo()

    response = client.send_request("data/magic", {
        "provider_id": provider_id
    })
    data = handle_response(response)

    matches = data.get("matches", [])

    if not matches:
        print_info("No file type signatures matched")
        return

    click.secho(f"File Type Detection ({len(matches)} match(es)):", bold=True)
    click.echo()

    for i, match in enumerate(matches, 1):
        match_type = match.get("type", "unknown")
        description = match.get("description", "No description")
        confidence = match.get("confidence", 0)

        click.echo(f"  [{i}] {match_type}")
        click.echo(f"      {description}")
        click.echo(f"      Confidence: {confidence}%")
        click.echo()


# ============================================================================
# Interactive Mode
# ============================================================================

@cli.command()
def interactive():
    """Enter interactive mode."""
    click.secho("\nImHex MCP Interactive Mode", bold=True, fg="cyan")
    click.echo("Type 'help' for available commands, 'exit' to quit")
    click.echo()

    while True:
        try:
            command = click.prompt(click.style("imhex>", fg="green"), type=str)
            command = command.strip()

            if not command:
                continue

            if command in ['exit', 'quit']:
                click.echo("Goodbye!")
                break

            if command == 'help':
                click.echo("Available commands:")
                click.echo("  status       - Check server status")
                click.echo("  list         - List open files")
                click.echo("  metrics      - Show metrics")
                click.echo("  exit/quit    - Exit interactive mode")
                click.echo()
                continue

            if command == 'status':
                ctx = click.Context(status)
                ctx.invoke(status)
                continue

            if command == 'list':
                ctx = click.Context(files_list)
                ctx.invoke(files_list)
                continue

            if command == 'metrics':
                ctx = click.Context(metrics)
                ctx.invoke(metrics)
                continue

            print_error(f"Unknown command: {command}")
            click.echo("Type 'help' for available commands")

        except KeyboardInterrupt:
            click.echo("\nUse 'exit' or 'quit' to exit")
        except EOFError:
            click.echo("\nGoodbye!")
            break
        except Exception as e:
            print_error(f"Error: {e}")


if __name__ == '__main__':
    cli()
