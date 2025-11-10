# ImHex MCP Integration - Context for Claude

## Overview
This MCP server exposes ImHex's hex editor capabilities to AI assistants via the Model Context Protocol.

## Key Achievement
✅ **Fully Automated File Opening** - The MCP plugin can now open files programmatically without manual GUI interaction!

## Architecture
- **ImHex Version**: 1.38.0.WIP
- **MCP Plugin**: `mcp.hexplug` (links against `builtin.hexpluglib`)
- **Network Interface**: Port 31337 (hardcoded)
- **Plugin Architecture**: Modified to allow cross-plugin symbol sharing

## Prerequisites
1. **ImHex must be running**:
   ```bash
   /Users/pasha/PycharmProjects/IMHexMCP/imhexMCP-standalone/ImHex/build/imhex
   ```

2. **Network Interface enabled**:
   - Go to: Extras → Settings → General
   - Enable: "Network Interface" checkbox
   - Port 31337 is used automatically

## Available MCP Tools

### File Operations
- **`file/open`** - Open files programmatically ✨ NEW: Fully automated!
  ```python
  {"path": "/path/to/file.bin"}
  ```

### Data Operations
- **`provider/info`** - Get info about currently open file
- **`data/read`** - Read hex data from file
  ```python
  {"offset": 0, "length": 64}
  ```
- **`data/write`** - Write hex data to file
  ```python
  {"offset": 0, "data": "DEADBEEF"}
  ```
- **`data/inspect`** - Inspect data types at offset
  ```python
  {"offset": 0, "length": 16}
  ```
- **`data/decode`** - Decode data (Base64, ASCII, etc.)
  ```python
  {"data": "48656C6C6F", "encoding": "ascii"}
  ```

### Analysis Operations
- **`hash/calculate`** - Calculate hashes (MD5, SHA-1, SHA-256, SHA-384, SHA-512)
  ```python
  {"offset": 0, "length": 1024, "algorithm": "sha256"}
  ```
- **`search/find`** - Search for hex/text patterns
  ```python
  {"pattern": "DEADBEEF", "type": "hex"}
  ```

### Annotation Operations
- **`bookmark/add`** - Add bookmarks to file regions
  ```python
  {"offset": 0, "size": 8, "name": "Header", "comment": "File magic"}
  ```
- **`pattern_editor/set_code`** - Set pattern language code

### System Operations
- **`imhex/capabilities`** - Get ImHex version and available commands

## Example Workflows

### 1. Analyze Unknown Binary
```
1. Open file: file/open → {"path": "/path/to/unknown.bin"}
2. Get info: provider/info
3. Read header: data/read → {"offset": 0, "length": 64}
4. Inspect types: data/inspect → {"offset": 0, "length": 16}
5. Calculate hash: hash/calculate → {"offset": 0, "length": 1024, "algorithm": "sha256"}
```

### 2. Search for Patterns
```
1. Open file: file/open → {"path": "/path/to/firmware.bin"}
2. Search: search/find → {"pattern": "CAFEBABE", "type": "hex"}
3. Add bookmark: bookmark/add → {"offset": <found_offset>, "size": 4, "name": "Magic"}
```

### 3. Data Extraction
```
1. Open file: file/open → {"path": "/path/to/data.bin"}
2. Read section: data/read → {"offset": 0x100, "length": 256}
3. Decode: data/decode → {"data": <hex_data>, "encoding": "ascii"}
```

## Technical Details

### Modified Files
- `plugins/builtin/CMakeLists.txt` - Added LIBRARY_PLUGIN export
- `plugins/builtin/include/content/providers/file_provider.hpp` - Made open(bool) public
- `plugins/mcp/CMakeLists.txt` - Links against builtin library
- `plugins/mcp/source/plugin_mcp.cpp` - Implemented automated file opening
- `plugins/builtin/source/content/providers/file_provider.cpp` - Graceful settings handling
- `lib/libimhex/source/providers/provider.cpp` - Base class settings handling

### Key Innovation
The plugin architecture was modified to allow the builtin plugin to export as a shared library (`builtin.hexpluglib`), enabling the MCP plugin to directly access FileProvider methods for automated file opening.

## Testing

Run the comprehensive test suite:
```bash
cd /Users/pasha/PycharmProjects/IMHexMCP/imhexMCP-standalone/mcp-server
./venv/bin/python test_binary_analysis.py
```

Expected result: **8/8 tests passed** ✅

## Troubleshooting

### "Connection refused"
- Ensure ImHex is running
- Check Network Interface is enabled (Extras → Settings → General)

### "No file is currently open"
- Use the `file/open` endpoint first
- Or manually open a file in ImHex GUI

### MCP server not appearing in Claude Desktop
- Check configuration in `~/Library/Application Support/Claude/claude_desktop_config.json`
- Restart Claude Desktop completely

## Support
- ImHex: https://github.com/WerWolv/ImHex
- MCP Protocol: https://modelcontextprotocol.io/
- Full Documentation: `/Users/pasha/PycharmProjects/IMHexMCP/imhexMCP-standalone/mcp-server/README_MCP_USAGE.md`
