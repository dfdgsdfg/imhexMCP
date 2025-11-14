# Getting Started with ImHex MCP

This guide will help you get started with ImHex MCP, from installation to writing your first binary analysis client.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Understanding the Architecture](#understanding-the-architecture)
- [Your First Client](#your-first-client)
- [Using Enhanced Modules](#using-enhanced-modules)
- [Best Practices](#best-practices)
- [Next Steps](#next-steps)

## Prerequisites

Before you begin, ensure you have:

1. **ImHex** hex editor installed
2. **Python 3.9+** (Python 3.14 recommended for full type support)
3. **Basic knowledge** of:
   - Python programming
   - Binary file formats
   - Network sockets

The codebase includes:
- Full type hints (PEP 561 compliant)
- Comprehensive test coverage
- Production-ready security and logging modules

## Installation

### 1. Build ImHex with MCP Plugin

```bash
# Clone the repository
git clone --recurse-submodules https://github.com/jmpnop/imhexMCP.git
cd imhexMCP

# Build ImHex with the MCP plugin
./scripts/build.sh

# Launch ImHex
./ImHex/build/imhex
```

### 2. Enable Network Interface

1. Open ImHex
2. Go to **Settings → General**
3. Enable **Network Interface**
4. Verify it's listening on `localhost:31337`

### 3. Set Up Python Environment

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
cd mcp-server
pip install -r requirements.txt
```

## Quick Start

### Test the Connection

Create a simple test script `test_connection.py`:

```python
#!/usr/bin/env python3
import socket
import json

def send_request(endpoint, data=None):
    """Send a request to ImHex MCP."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    sock.connect(("localhost", 31337))

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

# Test capabilities
result = send_request("capabilities")
print(f"✓ Connected to ImHex MCP")
print(f"✓ Available endpoints: {len(result['data']['endpoints'])}")
```

Run it:

```bash
python3 test_connection.py
```

Expected output:
```
✓ Connected to ImHex MCP
✓ Available endpoints: 15
```

## Understanding the Architecture

ImHex MCP has three main components:

```
┌─────────────────┐
│  Your Client    │  ← Python code you write
│   (Python)      │
└────────┬────────┘
         │ JSON over TCP
         ↓
┌─────────────────┐
│  MCP Server     │  ← Request router & security
│  (lib modules)  │
└────────┬────────┘
         │ Native API
         ↓
┌─────────────────┐
│    ImHex        │  ← Hex editor with MCP plugin
│   (C++ Plugin)  │
└─────────────────┘
```

### Key Concepts

- **Provider**: An open file in ImHex (identified by `provider_id`)
- **Endpoint**: An API function (e.g., `file/open`, `data/read`)
- **Request/Response**: JSON messages sent over TCP
- **Modules**: Server-side enhancements (security, caching, metrics)

## Your First Client

Let's build a simple binary analyzer that reads a file and extracts strings.

### Step 1: Open a File

```python
#!/usr/bin/env python3
import socket
import json

def send_request(endpoint, data=None):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    sock.connect(("localhost", 31337))

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

# Open a binary file
result = send_request("file/open", {
    "path": "/bin/ls"  # Change to any binary file
})

if result["status"] == "success":
    provider_id = result["data"]["provider_id"]
    size = result["data"]["size"]
    print(f"✓ File opened: provider_id={provider_id}, size={size} bytes")
else:
    print(f"✗ Error: {result['data']['error']}")
    exit(1)
```

### Step 2: Read File Metadata

```python
# Get file info
result = send_request("file/info", {
    "provider_id": provider_id
})

print(f"File: {result['data']['name']}")
print(f"Size: {result['data']['size']} bytes")
print(f"Format: {result['data']['format']}")
```

### Step 3: Extract Strings

```python
# Find ASCII strings (min length 4)
result = send_request("data/strings", {
    "provider_id": provider_id,
    "offset": 0,
    "size": 10000,  # Search first 10KB
    "min_length": 4,
    "type": "ascii"
})

strings = result["data"]["strings"]
print(f"\n✓ Found {len(strings)} strings:")
for s in strings[:10]:  # Show first 10
    print(f"  0x{s['offset']:04x}: {s['value']}")
```

### Step 4: Compute Hash

```python
# Compute SHA256 hash
result = send_request("data/hash", {
    "provider_id": provider_id,
    "offset": 0,
    "size": -1,  # Entire file
    "algorithm": "sha256"
})

print(f"\n✓ SHA256: {result['data']['hash']}")
```

### Step 5: Clean Up

```python
# Close the file
send_request("file/close", {
    "provider_id": provider_id
})
print("\n✓ File closed")
```

### Complete Example

Save this as `first_analyzer.py`:

```python
#!/usr/bin/env python3
"""Simple binary file analyzer using ImHex MCP."""

import socket
import json
import sys

def send_request(endpoint, data=None):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    sock.connect(("localhost", 31337))

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

def analyze_file(file_path):
    """Analyze a binary file."""
    print(f"Analyzing: {file_path}")
    print("=" * 60)

    # Open file
    result = send_request("file/open", {"path": file_path})
    if result["status"] != "success":
        print(f"✗ Error: {result['data']['error']}")
        return

    provider_id = result["data"]["provider_id"]
    print(f"✓ File opened (provider_id={provider_id})")

    try:
        # Get file info
        result = send_request("file/info", {"provider_id": provider_id})
        info = result["data"]
        print(f"\nFile Information:")
        print(f"  Name: {info['name']}")
        print(f"  Size: {info['size']:,} bytes")

        # Extract strings
        result = send_request("data/strings", {
            "provider_id": provider_id,
            "offset": 0,
            "size": min(info['size'], 100000),  # First 100KB
            "min_length": 4,
            "type": "ascii"
        })
        strings = result["data"]["strings"]
        print(f"\nStrings (first 10 of {len(strings)}):")
        for s in strings[:10]:
            print(f"  0x{s['offset']:04x}: {s['value'][:50]}")

        # Compute hash
        result = send_request("data/hash", {
            "provider_id": provider_id,
            "offset": 0,
            "size": -1,
            "algorithm": "sha256"
        })
        print(f"\nSHA256: {result['data']['hash']}")

    finally:
        # Always close the file
        send_request("file/close", {"provider_id": provider_id})
        print("\n✓ Analysis complete")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 first_analyzer.py <binary_file>")
        sys.exit(1)

    analyze_file(sys.argv[1])
```

Run it:

```bash
python3 first_analyzer.py /bin/ls
```

## Using Enhanced Modules

The MCP server includes enhanced modules for production use:

### Security Module

Protect your server with rate limiting and circuit breakers:

```python
from security import SecurityManager, SecurityConfig

config = SecurityConfig(
    rate_limit_requests=100,  # 100 requests
    rate_limit_window=60,      # per 60 seconds
    circuit_breaker_threshold=5,  # Open after 5 failures
    circuit_breaker_timeout=30,   # Reset after 30 seconds
)

security = SecurityManager(config)

# Check rate limit before request
if not security.rate_limiter.check_limit(client_id):
    print("Rate limit exceeded!")
```

### Caching Module

Cache frequently accessed data:

```python
from caching import CacheManager, CacheConfig, CacheStrategy

config = CacheConfig(
    max_size=1000,
    ttl=300,  # 5 minutes
    strategy=CacheStrategy.LRU
)

cache = CacheManager(config)

# Check cache before request
key = f"data:{provider_id}:{offset}:{size}"
cached = cache.get(key)
if cached:
    return cached

# ... make request ...
cache.put(key, data)
```

### Metrics Module

Track performance and usage:

```python
from metrics import MetricsCollector, MetricType

metrics = MetricsCollector()

# Record request
start = time.time()
# ... perform operation ...
duration_ms = (time.time() - start) * 1000

metrics.record_request(duration_ms, "data/read", success=True)

# Get summary
summary = metrics.get_summary()
print(f"Avg response time: {summary['avg_response_time']:.2f}ms")
print(f"Success rate: {summary['success_rate']*100:.1f}%")
```

### Logging Module

Structured logging with context:

```python
from logging_config import setup_logging, get_logger

# Setup logging
setup_logging(
    name="imhex_mcp",
    level="INFO",
    console=True,
    json_output=False  # Human-readable for development
)

# Get logger with context
logger = get_logger("analyzer", {
    "component": "binary_analyzer",
    "session_id": "abc123"
})

logger.info("Starting analysis", extra={"file": file_path})
logger.error("Analysis failed", extra={"error": str(e)}, exc_info=True)
```

For a complete example using all modules, see [`examples/08-lib-modules-demo.py`](../examples/08-lib-modules-demo.py).

## Best Practices

### 1. Always Close Files

```python
try:
    result = send_request("file/open", {"path": file_path})
    provider_id = result["data"]["provider_id"]
    # ... work with file ...
finally:
    send_request("file/close", {"provider_id": provider_id})
```

### 2. Handle Errors Gracefully

```python
result = send_request("file/open", {"path": file_path})
if result["status"] != "success":
    error = result["data"]["error"]
    print(f"Error: {error}")
    return
```

### 3. Use Timeouts

```python
sock.settimeout(10)  # 10-second timeout
```

### 4. Read Large Files in Chunks

```python
chunk_size = 1024 * 1024  # 1MB
for offset in range(0, file_size, chunk_size):
    result = send_request("data/read", {
        "provider_id": provider_id,
        "offset": offset,
        "size": min(chunk_size, file_size - offset)
    })
    process_chunk(result["data"]["data"])
```

### 5. Validate Configuration

```python
from config_validator import validate_and_log

config = {
    "imhex_host": "localhost",
    "imhex_port": 31337,
    # ... other settings ...
}

if not validate_and_log(config):
    print("Invalid configuration!")
    sys.exit(1)
```

## Next Steps

Now that you've built your first client, explore these resources:

### Documentation

- **[API Reference](API.md)** - Complete endpoint documentation
- **[Architecture Overview](ARCHITECTURE.md)** - System design and components
- **[Performance Guide](PERFORMANCE_OPTIMIZATIONS.md)** - Optimization techniques
- **[Testing Guide](TESTING.md)** - Writing tests for your client
- **[Integration Guide](INTEGRATION_GUIDE.md)** - Integrating with other tools

### Examples

The [`examples/`](../examples/) directory contains practical examples:

1. **Basic file analysis** - File operations and metadata
2. **Malware scanning** - Batch scanning with pattern detection
3. **Firmware analysis** - IoT/embedded binary analysis
4. **Binary diffing** - Comparing file versions
5. **Automated pipeline** - Full analysis workflow
6. **Enhanced client quickstart** - Production-ready client
7. **MCP server integration** - Full server setup
8. **Configuration validation** - Config management
9. **Lib modules demo** - Using security, caching, metrics

### Advanced Topics

- **Batch Operations** - Process multiple files efficiently
- **Compression** - Reduce network bandwidth
- **Custom Endpoints** - Extend the MCP plugin
- **Deployment** - Production server setup

## Getting Help

- **Issues**: [GitHub Issues](https://github.com/jmpnop/imhexMCP/issues)
- **Documentation**: Check the `docs/` directory
- **Examples**: Study the `examples/` directory
- **Source Code**: Read lib modules for implementation details

## Summary

You've learned:

- ✓ How to install and set up ImHex MCP
- ✓ The basic architecture and concepts
- ✓ How to write your first binary analyzer
- ✓ How to use enhanced server modules
- ✓ Best practices for production clients

Start exploring the examples and building your own binary analysis tools!
