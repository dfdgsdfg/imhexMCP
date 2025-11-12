# ImHex MCP API Reference

**Version**: 1.38.0
**Protocol**: JSON over TCP
**Port**: 31337 (localhost)
**Last Updated**: 2025-11-11

## Table of Contents

- [Quick Start](#quick-start)
- [Protocol Specification](#protocol-specification)
- [Authentication](#authentication)
- [Endpoint Categories](#endpoint-categories)
- [Complete Endpoint Reference](#complete-endpoint-reference)
- [Error Handling](#error-handling)
- [Best Practices](#best-practices)
- [Code Examples](#code-examples)
- [Performance & Limits](#performance--limits)

---

## Quick Start

### 1. Enable Network Interface

**Option A: Via UI**
1. Launch ImHex
2. Go to `Settings → General`
3. Enable `Network Interface`
4. Restart ImHex

**Option B: Via Configuration File** (Automated)

```bash
# macOS
echo '{"hex.builtin.setting.general.network_interface": true}' > \
  ~/Library/Application\ Support/imhex/config/settings.json

# Linux
echo '{"hex.builtin.setting.general.network_interface": true}' > \
  ~/.config/imhex/config/settings.json

# Windows
echo '{"hex.builtin.setting.general.network_interface": true}' > \
  %APPDATA%\imhex\config\settings.json
```

### 2. Test Connection

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

# Test capabilities
result = send_request("capabilities")
print(f"ImHex version: {result['data']['version']}")
print(f"Available endpoints: {len(result['data']['endpoints'])}")
```

---

## Protocol Specification

### Request Format

```json
{
  "endpoint": "<category>/<operation>",
  "data": {
    "param1": "value1",
    "param2": "value2"
  }
}
```

**Required**:
- `endpoint` (string): The API endpoint to call
- Must end with newline character (`\n`)

**Optional**:
- `data` (object): Parameters for the endpoint (defaults to `{}`)

### Response Format

```json
{
  "status": "success",
  "data": {
    "result1": "value1",
    "result2": "value2"
  }
}
```

**Success Response**:
```json
{
  "status": "success",
  "data": { ... }
}
```

**Error Response**:
```json
{
  "status": "error",
  "data": {
    "error": "Error message description"
  }
}
```

### Connection Lifecycle

1. **Open TCP socket** to `localhost:31337`
2. **Send request** (JSON + `\n`)
3. **Receive response** (JSON + `\n`)
4. **Close socket**

Each request requires a new connection. The server does not maintain persistent connections.

---

## Authentication

**Current Version**: No authentication required

Network interface only accepts connections from `localhost` (127.0.0.1).

**Future Versions** (Roadmap):
- API key authentication
- Token-based auth
- SSL/TLS encryption
- Remote connections with authentication

---

## Endpoint Categories

| Category | Endpoints | Description |
|----------|-----------|-------------|
| **Core** | 8 | File operations, capabilities, provider management |
| **Data** | 10 | Read, write, search, hash, analyze binary data |
| **Batch** | 4 | Multi-file operations (hash, search, diff) |
| **Bookmarks** | 3 | Add, list, remove annotations |
| **Advanced** | 3 | Strings extraction, file type detection, disassembly |

**Total**: 28 endpoints

---

## Complete Endpoint Reference

### Core Operations

#### `capabilities`

Get ImHex version information and available endpoints.

**Request**:
```json
{
  "endpoint": "capabilities"
}
```

**Response**:
```json
{
  "status": "success",
  "data": {
    "version": "1.38.0",
    "commit": "abc123",
    "branch": "master",
    "endpoints": ["capabilities", "file/open", "file/list", ...]
  }
}
```

**Use Cases**:
- Verify ImHex is running
- Check available features
- Version compatibility check

---

#### `file/open`

Open a binary file for analysis (asynchronous operation).

**Request**:
```json
{
  "endpoint": "file/open",
  "data": {
    "path": "/path/to/file.bin"
  }
}
```

**Response** (Immediate):
```json
{
  "status": "success",
  "data": {
    "message": "File open request queued",
    "path": "/path/to/file.bin"
  }
}
```

**Notes**:
- Operation completes asynchronously via ImHex TaskManager
- Poll `file/list` to check when file is opened
- Absolute path required
- File must exist and be readable

**Example**:
```python
# Request file open
result = send_request("file/open", {"path": "/tmp/binary.bin"})
print(result["data"]["message"])

# Wait for file to open
import time
time.sleep(2)

# Verify file is open
result = send_request("file/list")
files = result["data"]["providers"]
print(f"Files open: {len(files)}")
```

---

#### `file/close`

Close an open file/provider.

**Request**:
```json
{
  "endpoint": "file/close",
  "data": {
    "provider_id": 0
  }
}
```

**Response**:
```json
{
  "status": "success",
  "data": {
    "message": "Provider closed"
  }
}
```

**Error Cases**:
- `provider_id` does not exist
- Provider is already closed

---

#### `file/list`

List all currently open files/providers.

**Request**:
```json
{
  "endpoint": "file/list"
}
```

**Response**:
```json
{
  "status": "success",
  "data": {
    "count": 2,
    "providers": [
      {
        "id": 0,
        "name": "file.bin",
        "size": 1048576,
        "type": "FileProvider"
      },
      {
        "id": 1,
        "name": "image.exe",
        "size": 524288,
        "type": "FileProvider"
      }
    ]
  }
}
```

---

#### `file/switch`

Switch the active provider (used for subsequent operations).

**Request**:
```json
{
  "endpoint": "file/switch",
  "data": {
    "provider_id": 1
  }
}
```

**Response**:
```json
{
  "status": "success",
  "data": {
    "message": "Switched to provider 1"
  }
}
```

---

#### `file/info`

Get information about the currently active file.

**Request**:
```json
{
  "endpoint": "file/info"
}
```

**Response**:
```json
{
  "status": "success",
  "data": {
    "name": "binary.bin",
    "size": 1048576,
    "path": "/tmp/binary.bin",
    "type": "FileProvider"
  }
}
```

---

### Data Operations

#### `data/read`

Read binary data from the active file.

**Request**:
```json
{
  "endpoint": "data/read",
  "data": {
    "provider_id": 0,
    "offset": 0,
    "size": 256
  }
}
```

**Response**:
```json
{
  "status": "success",
  "data": {
    "data": "4d5a9000030000000400000000000000...",
    "offset": 0,
    "size": 256
  }
}
```

**Parameters**:
- `provider_id` (int, optional): Provider to read from (default: active)
- `offset` (int): Starting byte offset
- `size` (int): Number of bytes to read (max: 1MB)

**Limits**:
- Maximum read size: 1MB per request
- Use `data/chunked_read` for larger reads

---

#### `data/write`

Write binary data to the active file.

**Request**:
```json
{
  "endpoint": "data/write",
  "data": {
    "provider_id": 0,
    "offset": 0,
    "data": "48656c6c6f"
  }
}
```

**Response**:
```json
{
  "status": "success",
  "data": {
    "bytes_written": 5
  }
}
```

**Notes**:
- Data must be hex-encoded
- Modifies file in-place
- Changes are immediately visible in ImHex

---

#### `data/hash`

Calculate cryptographic hash of a data region.

**Request**:
```json
{
  "endpoint": "data/hash",
  "data": {
    "provider_id": 0,
    "offset": 0,
    "size": -1,
    "algorithm": "sha256"
  }
}
```

**Response**:
```json
{
  "status": "success",
  "data": {
    "hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "algorithm": "sha256"
  }
}
```

**Supported Algorithms**:
- `md5`
- `sha1`
- `sha224`
- `sha256`
- `sha384`
- `sha512`

**Special Values**:
- `size: -1` = hash entire file

**Limits**:
- Max size: 100MB per hash operation

---

#### `data/search`

Search for patterns in binary data.

**Request**:
```json
{
  "endpoint": "data/search",
  "data": {
    "provider_id": 0,
    "pattern": "4d5a",
    "type": "hex",
    "max_matches": 100
  }
}
```

**Response**:
```json
{
  "status": "success",
  "data": {
    "matches": [0, 1024, 2048],
    "count": 3,
    "truncated": false
  }
}
```

**Pattern Types**:
- `hex`: Hex string (e.g., "4d5a90")
- `text`: ASCII text (e.g., "Hello")
- `regex`: Regular expression (not yet implemented)

**Limits**:
- Max matches: 100,000 (configurable)
- Max scan size: entire file

---

#### `data/entropy`

Calculate Shannon entropy for detecting encryption/compression.

**Request**:
```json
{
  "endpoint": "data/entropy",
  "data": {
    "provider_id": 0,
    "offset": 0,
    "size": 4096
  }
}
```

**Response**:
```json
{
  "status": "success",
  "data": {
    "entropy": 7.84,
    "percentage": 98.0,
    "interpretation": "Very high entropy - likely encrypted or random data"
  }
}
```

**Entropy Scale** (0-8 bits/byte):
| Range | Interpretation | Examples |
|-------|----------------|----------|
| 0-1 | Very low | Padding, zeros, repetitive data |
| 1-3 | Low | Text files, structured data |
| 3-5 | Medium | Mixed content, binaries |
| 5-7 | High | Compressed data |
| 7-8 | Very high | Encrypted, random data |

**Limits**:
- Max size: 10MB

---

#### `data/statistics`

Analyze byte frequency and distribution.

**Request**:
```json
{
  "endpoint": "data/statistics",
  "data": {
    "provider_id": 0,
    "offset": 0,
    "size": 1024,
    "include_distribution": true
  }
}
```

**Response**:
```json
{
  "status": "success",
  "data": {
    "unique_bytes": 256,
    "most_common_byte": {
      "value": 0,
      "count": 342,
      "percentage": 33.4
    },
    "null_bytes": {
      "count": 342,
      "percentage": 33.4
    },
    "printable_chars": {
      "count": 128,
      "percentage": 12.5
    },
    "distribution": {
      "0": 342,
      "1": 12,
      ...
    }
  }
}
```

**Parameters**:
- `include_distribution` (bool, default: false): Include full 256-byte frequency map

**Limits**:
- Max size: 10MB

---

#### `data/chunked_read`

Read large files in manageable chunks with pagination.

**Request**:
```json
{
  "endpoint": "data/chunked_read",
  "data": {
    "provider_id": 0,
    "offset": 0,
    "length": 10485760,
    "chunk_size": 1048576,
    "chunk_index": 0
  }
}
```

**Response**:
```json
{
  "status": "success",
  "data": {
    "chunk_data": "4d5a900003000000...",
    "chunk_index": 0,
    "chunk_size": 1048576,
    "has_more": true,
    "total_chunks": 10
  }
}
```

**Limits**:
- Max total read: 100MB
- Default chunk size: 1MB
- Recommended chunk size: 1MB

**Example**:
```python
def read_large_file(provider_id, offset, total_size):
    chunk_size = 1048576  # 1MB
    chunk_index = 0
    data = b""

    while True:
        result = send_request("data/chunked_read", {
            "provider_id": provider_id,
            "offset": offset,
            "length": total_size,
            "chunk_size": chunk_size,
            "chunk_index": chunk_index
        })

        chunk = bytes.fromhex(result["data"]["chunk_data"])
        data += chunk

        if not result["data"]["has_more"]:
            break

        chunk_index += 1

    return data
```

---

### Advanced Analysis

#### `data/strings`

Extract ASCII and UTF-16 strings from binary data.

**Request**:
```json
{
  "endpoint": "data/strings",
  "data": {
    "provider_id": 0,
    "offset": 0,
    "size": 0,
    "min_length": 4,
    "type": "ascii",
    "max_strings": 1000
  }
}
```

**Response**:
```json
{
  "status": "success",
  "data": {
    "strings": [
      {
        "offset": 4096,
        "length": 24,
        "type": "ascii",
        "value": "C:\\Windows\\System32"
      },
      {
        "offset": 8192,
        "length": 15,
        "type": "utf16le",
        "value": "http://api.com"
      }
    ],
    "count": 247,
    "truncated": false
  }
}
```

**Parameters**:
- `offset` (int): Start offset
- `size` (int): Scan size (0 = entire file)
- `min_length` (int): Minimum string length (default: 4)
- `type` (string): `"ascii"`, `"utf16le"`, or `"all"`
- `max_strings` (int): Maximum strings to return (default: 1000)

**Limits**:
- Max scan size: 100MB
- Max strings: 10,000

**Use Cases**:
- Extract URLs, file paths, error messages
- Find API endpoints in executables
- Malware analysis (C2 servers, config strings)
- Firmware reverse engineering

---

#### `data/magic`

Detect file type using magic number signatures.

**Request**:
```json
{
  "endpoint": "data/magic",
  "data": {
    "provider_id": 0,
    "offset": 0,
    "size": 512
  }
}
```

**Response**:
```json
{
  "status": "success",
  "data": {
    "matches": [
      {
        "type": "PE",
        "description": "DOS/Windows executable (MZ)",
        "offset": 0,
        "confidence": "high"
      },
      {
        "type": "ZIP",
        "description": "ZIP archive",
        "offset": 1024,
        "confidence": "medium"
      }
    ],
    "match_count": 2
  }
}
```

**Supported Formats** (30+):
- **Executables**: PE (MZ), ELF, Mach-O, Java class
- **Archives**: ZIP, RAR, TAR, GZIP, BZIP2, 7z
- **Images**: JPEG, PNG, GIF, BMP, TIFF
- **Documents**: PDF, DOC, DOCX, RTF, XML
- **Media**: MP3, MP4, AVI, WAV, FLAC

**Use Cases**:
- Identify obfuscated files
- Detect file type mismatches
- Find embedded files
- Validate file headers

---

#### `data/disassemble`

Disassemble machine code into assembly instructions.

**Request**:
```json
{
  "endpoint": "data/disassemble",
  "data": {
    "provider_id": 0,
    "offset": 0,
    "size": 64,
    "architecture": "x86_64",
    "base_address": 4198400
  }
}
```

**Response**:
```json
{
  "status": "success",
  "data": {
    "instructions": [
      {
        "address": "0x401000",
        "offset": 0,
        "size": 3,
        "bytes": "4889e5",
        "mnemonic": "mov",
        "operands": "rbp, rsp"
      },
      {
        "address": "0x401003",
        "offset": 3,
        "size": 5,
        "bytes": "e800000000",
        "mnemonic": "call",
        "operands": "0x401008"
      }
    ],
    "count": 2,
    "architecture": "x86_64",
    "base_address": "0x401000"
  }
}
```

**Parameters**:
- `architecture` (string): Target architecture (e.g., "x86_64", "arm", "mips")
- `base_address` (int, optional): Virtual address for disassembly (default: 0)

**Limits**:
- Max size: 4KB
- Max instructions: 100

**Supported Architectures**:
Depends on ImHex disassembler registry. Common: `x86`, `x86_64`, `arm`, `aarch64`, `mips`, `mips64`, `powerpc`

**Use Cases**:
- Reverse engineering
- Entry point analysis
- Shellcode analysis
- Malware behavior analysis

---

### Batch Operations

#### `batch/hash`

Calculate hashes for multiple files simultaneously.

**Request**:
```json
{
  "endpoint": "batch/hash",
  "data": {
    "provider_ids": "all",
    "algorithm": "sha256",
    "offset": 0,
    "size": -1
  }
}
```

**Response**:
```json
{
  "status": "success",
  "data": {
    "hashes": [
      {
        "provider_id": 0,
        "file": "sample1.exe",
        "hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "status": "success"
      },
      {
        "provider_id": 1,
        "file": "sample2.exe",
        "hash": "6a8f...",
        "status": "success"
      }
    ],
    "total": 2,
    "successful": 2,
    "failed": 0
  }
}
```

**Parameters**:
- `provider_ids`: Array of IDs `[0, 1, 2]` or string `"all"`
- `algorithm`: Hash algorithm
- `offset`: Start offset (default: 0)
- `size`: Size to hash (-1 = entire file)

**Limits**:
- Max file size: 100MB per file

---

#### `batch/search`

Search for a pattern across multiple files.

**Request**:
```json
{
  "endpoint": "batch/search",
  "data": {
    "provider_ids": "all",
    "pattern": "4d5a",
    "max_matches": 1000
  }
}
```

**Response**:
```json
{
  "status": "success",
  "data": {
    "results": [
      {
        "provider_id": 0,
        "file": "file1.exe",
        "matches": [0, 1024],
        "count": 2
      },
      {
        "provider_id": 1,
        "file": "file2.exe",
        "matches": [0],
        "count": 1
      }
    ],
    "total_files": 2,
    "total_matches": 3
  }
}
```

---

#### `batch/diff`

Compare reference file against multiple targets.

**Request**:
```json
{
  "endpoint": "batch/diff",
  "data": {
    "reference_id": 0,
    "target_ids": "all",
    "algorithm": "myers",
    "max_diff_regions": 1000
  }
}
```

**Response**:
```json
{
  "status": "success",
  "data": {
    "comparisons": [
      {
        "target_id": 1,
        "target_name": "patched.exe",
        "similarity": 98.5,
        "matching_bytes": 1028096,
        "total_bytes": 1048576,
        "diff_regions": [
          {"offset": 4096, "size": 128},
          {"offset": 8192, "size": 64}
        ]
      }
    ],
    "reference_name": "original.exe",
    "total_comparisons": 1
  }
}
```

**Use Cases**:
- Patch analysis
- Find file variants
- Identify binary modifications

---

### Bookmarks

#### `bookmark/add`

Add a bookmark annotation to a region.

**Request**:
```json
{
  "endpoint": "bookmark/add",
  "data": {
    "offset": 0,
    "size": 16,
    "name": "File Header",
    "comment": "DOS header structure",
    "color": "FF0000"
  }
}
```

**Response**:
```json
{
  "status": "success",
  "data": {
    "bookmark_id": 0
  }
}
```

---

#### `bookmark/list`

List all bookmarks for the active file.

**Request**:
```json
{
  "endpoint": "bookmark/list"
}
```

**Response**:
```json
{
  "status": "success",
  "data": {
    "bookmarks": [
      {
        "id": 0,
        "offset": 0,
        "size": 16,
        "name": "File Header",
        "comment": "DOS header structure",
        "color": "FF0000"
      }
    ],
    "count": 1
  }
}
```

---

#### `bookmark/remove`

Remove a bookmark by ID.

**Request**:
```json
{
  "endpoint": "bookmark/remove",
  "data": {
    "bookmark_id": 0
  }
}
```

---

## Error Handling

### Common Error Codes

| Error Message | Cause | Solution |
|---------------|-------|----------|
| `Connection refused` | ImHex not running or network interface disabled | Enable network interface |
| `Provider not found` | Invalid `provider_id` | Check `file/list` for valid IDs |
| `File too large` | Exceeds size limit | Use chunked operations |
| `File not found` | Invalid path in `file/open` | Verify file path exists |
| `Endpoint not found` | Invalid endpoint name | Check `capabilities` |
| `Invalid parameter` | Missing or malformed parameter | Verify request format |

### Error Response Example

```json
{
  "status": "error",
  "data": {
    "error": "Provider with ID 99 not found"
  }
}
```

### Handling Errors in Code

```python
def safe_request(endpoint, data=None):
    try:
        result = send_request(endpoint, data)
        if result["status"] == "error":
            raise Exception(f"API Error: {result['data']['error']}")
        return result["data"]
    except ConnectionRefusedError:
        raise Exception("ImHex is not running or network interface is disabled")
    except socket.timeout:
        raise Exception(f"Request to {endpoint} timed out")
    except json.JSONDecodeError:
        raise Exception("Invalid JSON response from ImHex")
```

---

## Best Practices

### 1. Connection Management

**DO**:
- Create new socket for each request
- Close socket after receiving response
- Set reasonable timeouts (10-30s)

**DON'T**:
- Reuse sockets across requests
- Leave sockets open indefinitely

### 2. File Operations

**Opening Files**:
```python
# Open file
result = send_request("file/open", {"path": "/tmp/file.bin"})

# Wait for async operation to complete
time.sleep(2)

# Verify file is open
result = send_request("file/list")
provider_id = result["data"]["providers"][0]["id"]
```

**Closing Files**:
```python
# Always close files when done
send_request("file/close", {"provider_id": provider_id})
```

### 3. Large File Handling

```python
# For files > 1MB, use chunked reads
def read_large_file(provider_id, total_size):
    chunk_size = 1048576  # 1MB chunks
    data = b""

    for chunk_index in range((total_size + chunk_size - 1) // chunk_size):
        result = send_request("data/chunked_read", {
            "provider_id": provider_id,
            "offset": 0,
            "length": total_size,
            "chunk_size": chunk_size,
            "chunk_index": chunk_index
        })

        data += bytes.fromhex(result["data"]["chunk_data"])

        if not result["data"]["has_more"]:
            break

    return data
```

### 4. Batch Operations

```python
# Process multiple files efficiently
result = send_request("batch/hash", {
    "provider_ids": "all",
    "algorithm": "sha256"
})

for file_hash in result["data"]["hashes"]:
    print(f"{file_hash['file']}: {file_hash['hash']}")
```

### 5. Error Handling

```python
def robust_request(endpoint, data=None, retries=3):
    for attempt in range(retries):
        try:
            result = send_request(endpoint, data)
            if result["status"] == "success":
                return result["data"]
            else:
                print(f"Error: {result['data']['error']}")
                return None
        except Exception as e:
            if attempt == retries - 1:
                raise
            time.sleep(1)
```

---

## Code Examples

### Python

See [examples/](../examples/) directory for complete examples:
- `01-basic-file-analysis.py`: Basic file operations
- `02-malware-scanning.py`: Batch malware scanning
- `03-firmware-analysis.py`: Firmware reverse engineering
- `04-diff-comparison.py`: Binary diff analysis
- `05-automated-pipeline.py`: Complete automation workflow

### JavaScript/Node.js

```javascript
const net = require('net');

function sendRequest(endpoint, data = {}) {
    return new Promise((resolve, reject) => {
        const client = new net.Socket();
        client.setTimeout(10000);

        client.connect(31337, 'localhost', () => {
            const request = JSON.stringify({
                endpoint: endpoint,
                data: data
            }) + '\n';

            client.write(request);
        });

        let response = '';
        client.on('data', (data) => {
            response += data.toString();
            if (response.includes('\n')) {
                client.destroy();
                resolve(JSON.parse(response.trim()));
            }
        });

        client.on('error', reject);
        client.on('timeout', () => reject(new Error('Timeout')));
    });
}

// Usage
async function main() {
    const result = await sendRequest('capabilities');
    console.log(`ImHex version: ${result.data.version}`);
}
```

### Go

```go
package main

import (
    "bufio"
    "encoding/json"
    "fmt"
    "net"
    "time"
)

type Request struct {
    Endpoint string                 `json:"endpoint"`
    Data     map[string]interface{} `json:"data"`
}

type Response struct {
    Status string                 `json:"status"`
    Data   map[string]interface{} `json:"data"`
}

func sendRequest(endpoint string, data map[string]interface{}) (*Response, error) {
    conn, err := net.DialTimeout("tcp", "localhost:31337", 10*time.Second)
    if err != nil {
        return nil, err
    }
    defer conn.Close()

    req := Request{
        Endpoint: endpoint,
        Data:     data,
    }

    reqBytes, err := json.Marshal(req)
    if err != nil {
        return nil, err
    }

    _, err = conn.Write(append(reqBytes, '\n'))
    if err != nil {
        return nil, err
    }

    reader := bufio.NewReader(conn)
    respBytes, err := reader.ReadBytes('\n')
    if err != nil {
        return nil, err
    }

    var resp Response
    err = json.Unmarshal(respBytes, &resp)
    return &resp, err
}

func main() {
    resp, err := sendRequest("capabilities", nil)
    if err != nil {
        panic(err)
    }

    fmt.Printf("ImHex version: %v\n", resp.Data["version"])
}
```

---

## Performance & Limits

### Size Limits

| Operation | Limit | Notes |
|-----------|-------|-------|
| Single read | 1MB | Use `chunked_read` for larger |
| Chunked read | 100MB total | 1MB chunks recommended |
| Hash | 100MB | Per file in batch operations |
| Search | Unlimited | Memory-constrained |
| Strings | 100MB scan | 10,000 strings max |
| Disassemble | 4KB | 100 instructions max |
| Entropy/Stats | 10MB | Statistical analysis |

### Timeouts

| Operation | Recommended Timeout |
|-----------|---------------------|
| Connection | 5 seconds |
| Simple operations | 10 seconds |
| File operations | 30 seconds |
| Batch operations | 30s per file |

### Threading Model

- **Network Thread**: Handles incoming requests
- **Main Thread**: All ImHex API calls executed via `TaskManager::doLater()`
- **Async Operations**: `file/open`, `file/close` return immediately

### Performance Tips

1. **Use batch operations** for multiple files instead of individual requests
2. **Read in chunks** for large files (1MB chunk size recommended)
3. **Set reasonable timeouts** to avoid hanging connections
4. **Close files** when done to free resources
5. **Use `size: -1`** for full-file hashes (optimized path)

---

## Roadmap

See [ROADMAP.md](ROADMAP.md) for planned features:
- WebSocket support for streaming
- Authentication and remote access
- Additional analysis endpoints
- VSCode extension
- Web UI dashboard

---

## Support

- **Documentation**: [docs/](.)
- **Examples**: [examples/](../examples/)
- **Issues**: https://github.com/jmpnop/imhexMCP/issues
- **Main Endpoint Reference**: [ENDPOINTS.md](../ENDPOINTS.md)
