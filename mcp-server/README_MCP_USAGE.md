# ImHex MCP Integration - Usage Guide

## Overview
This MCP server exposes ImHex's hex editor capabilities to AI assistants via the Model Context Protocol.

## Prerequisites
1. **ImHex must be running** with Network Interface enabled
2. **Files must be opened manually** in ImHex GUI before using MCP endpoints

## Configuration

### ImHex Setup
1. Start ImHex
2. Go to: **Extras → Settings → Interface**
3. Enable **"Network Interface"**
4. Set port to **31337** (default)
5. Click **"Restart Interface"** if needed

### Claude Desktop Configuration
Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "imhex": {
      "command": "/path/to/mcp-server/venv/bin/python",
      "args": ["/path/to/mcp-server/server.py"]
    }
  }
}
```

## Available Endpoints

### ✅ Fully Functional Endpoints

1. **imhex/capabilities** - Get ImHex version and available commands
2. **provider/info** - Get information about currently open file
3. **data/read** - Read hex data from file
4. **data/inspect** - Inspect data types at offset
5. **data/write** - Write hex data to file
6. **hash/calculate** - Calculate hashes (MD5, SHA-1, SHA-256, SHA-384, SHA-512)
7. **search/find** - Search for hex/text patterns
8. **bookmark/add** - Add bookmarks to file regions
9. **pattern_editor/set_code** - Set pattern language code
10. **data/decode** - Decode data (Base64, ASCII, etc.)

### ⚠️ Limited Endpoint

**file/open** - Has architectural limitations due to ImHex plugin system
- **Workaround**: Open files manually in ImHex GUI
- **Reason**: Plugins are isolated shared libraries; FileProvider methods aren't accessible from external plugins

## Usage Workflow

1. **Start ImHex** with Network Interface enabled
2. **Open a file** in ImHex GUI (File → Open File)
3. **Use MCP endpoints** to analyze the open file

## Testing

### Basic Connectivity Test
```bash
./venv/bin/python test_server.py
```

### Integration Tests
```bash
./venv/bin/python test_real_integration.py
```

### Endpoint Tests (with file open)
```bash
# Open any file in ImHex first, then run:
./venv/bin/python test_endpoints_only.py
```

## Example Use Cases

### 1. Hash Calculation
```python
response = client.send_command("hash/calculate", {
    "offset": 0,
    "length": 1024,
    "algorithm": "sha256"
})
```

### 2. Pattern Search
```python
response = client.send_command("search/find", {
    "pattern": "DEADBEEF",
    "type": "hex"
})
```

### 3. Data Inspection
```python
response = client.send_command("data/inspect", {
    "offset": 0,
    "length": 16
})
```

### 4. Add Bookmark
```python
response = client.send_command("bookmark/add", {
    "offset": 0,
    "size": 8,
    "name": "File Header",
    "comment": "Magic bytes and version"
})
```

## Troubleshooting

### "Connection refused"
- Ensure ImHex is running
- Check Network Interface is enabled (Extras → Settings → Interface)
- Verify port 31337 is not blocked

### "No file is currently open"
- Open a file in ImHex GUI (File → Open File)
- The file/open endpoint has limitations - use manual opening

### "Read timeout"
- Operation may be taking too long
- Check ImHex isn't frozen or showing a dialog
- Restart ImHex if needed

## Architecture Notes

The MCP plugin is implemented as a native ImHex plugin that:
- Runs in ImHex's process space
- Listens on TCP port 31337
- Handles JSON-RPC style requests
- Returns results in JSON format

Due to ImHex's plugin isolation:
- Plugins can't directly access other plugins' classes
- FileProvider methods (like `setPath`) aren't accessible from MCP plugin
- Workaround: Use ImHex GUI for file operations, MCP for analysis

## Build Information

- **ImHex Version**: 1.38.0.WIP
- **MCP Plugin**: mcp.hexplug (282KB)
- **Compiler**: AppleClang 17.0.0
- **Build Date**: 2025-11-09

## Support

For issues or questions:
- ImHex: https://github.com/WerWolv/ImHex
- MCP: This is a custom integration

