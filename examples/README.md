# ImHex MCP Examples

This directory contains practical examples demonstrating how to use the ImHex MCP network interface for various binary analysis tasks.

## Prerequisites

1. **ImHex with MCP plugin running:**
```bash
cd /path/to/ImHex/build
./imhex
# Enable Network Interface in Settings → General
```

2. **Python 3.x** installed

3. **Network interface enabled** on `localhost:31337`

## Examples Overview

| Example | Description | Use Case | Status |
|---------|-------------|----------|--------|
| [01-basic-file-analysis.py](01-basic-file-analysis.py) | Basic file operations | Learning the API | ✅ |
| [02-malware-scanning.py](02-malware-scanning.py) | Batch malware scanning | Security analysis | ✅ |
| [03-firmware-analysis.py](03-firmware-analysis.py) | Firmware reverse engineering | IoT/Embedded | ✅ |
| [04-diff-comparison.py](04-diff-comparison.py) | Binary diff comparison | Patch analysis | ✅ |
| [05-automated-pipeline.py](05-automated-pipeline.py) | Full analysis workflow | Automation | ✅ |
| [08-lib-modules-demo.py](08-lib-modules-demo.py) | Enhanced server modules | Production client | ✅ |
| [09-config-validation.py](09-config-validation.py) | Configuration management | Server setup | ✅ |

## Running Examples

```bash
cd examples

# Basic file analysis
python3 01-basic-file-analysis.py /path/to/binary

# Malware scanning
python3 02-malware-scanning.py /path/to/malware/samples/

# Firmware analysis
python3 03-firmware-analysis.py firmware.bin

# Binary diff
python3 04-diff-comparison.py original.bin patched.bin

# Full pipeline
python3 05-automated-pipeline.py /path/to/files/ --output report.json --workers 4
```

## Common Patterns

### Connecting to ImHex
```python
import socket
import json

def send_request(endpoint, data=None):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(10)
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
```

### Opening a File
```python
# Open file
result = send_request("file/open", {"path": "/path/to/binary.bin"})
provider_id = result["data"]["provider_id"]
```

### Reading Data
```python
# Read 1024 bytes from offset 0
result = send_request("data/read", {
    "provider_id": provider_id,
    "offset": 0,
    "size": 1024
})
data = bytes.fromhex(result["data"]["data"])
```

### Extracting Strings
```python
result = send_request("data/strings", {
    "provider_id": provider_id,
    "offset": 0,
    "size": 10000,
    "min_length": 4,
    "type": "ascii"
})
strings = result["data"]["strings"]
```

### Computing Hashes
```python
result = send_request("data/hash", {
    "provider_id": provider_id,
    "offset": 0,
    "size": -1,  # Entire file
    "algorithm": "sha256"
})
hash_value = result["data"]["hash"]
```

### Batch Operations
```python
# Scan entire directory
result = send_request("batch/open_directory", {
    "path": "/path/to/directory",
    "pattern": "*.exe"
})
```

## Error Handling

Always check the response status:

```python
result = send_request("file/open", {"path": "/nonexistent.bin"})
if result["status"] == "error":
    print(f"Error: {result['data']['error']}")
else:
    print(f"Success! Provider ID: {result['data']['provider_id']}")
```

## Tips

1. **Close files when done:**
```python
send_request("file/close", {"provider_id": provider_id})
```

2. **Check capabilities:**
```python
result = send_request("capabilities")
endpoints = result["data"]["endpoints"]
```

3. **Handle large files:**
```python
# Read in chunks
chunk_size = 1024 * 1024  # 1MB
for offset in range(0, file_size, chunk_size):
    result = send_request("data/read", {
        "provider_id": provider_id,
        "offset": offset,
        "size": min(chunk_size, file_size - offset)
    })
    process_chunk(result["data"]["data"])
```

## Contributing

Have a useful example? Submit a PR with:
- Clear, commented code
- Usage instructions in the script
- Example output

## Support

- Documentation: See `../docs/`
- Endpoint Reference: `../ENDPOINTS.md`
- Issues: https://github.com/jmpnop/imhexMCP/issues
