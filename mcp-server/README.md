# ImHex MCP Server

A Model Context Protocol (MCP) server that exposes ImHex hex editor functionality to AI assistants like Claude.

## Overview

This MCP server acts as a bridge between AI assistants and ImHex, allowing AI models to:
- Open and analyze binary files
- Execute pattern language scripts for data parsing
- Perform hex editing operations
- Calculate hashes and checksums
- Search for patterns in binary data
- Disassemble machine code
- Inspect data with various data type interpretations
- Add bookmarks and annotations
- Decode/encode data with various formats

## Architecture

The MCP server communicates with ImHex through its built-in TCP interface (port 31337):

```
AI Assistant (Claude) <--> MCP Server <--> ImHex TCP Server (port 31337)
```

## Prerequisites

1. **ImHex** must be running with the network interface enabled
   - Enable in ImHex: Settings → General → Network Interface
   - Default port: 31337

2. **Python 3.10+** for running the MCP server

## Installation

### 1. Install Python dependencies

```bash
cd ImHex/mcp_server
pip install -r requirements.txt
```

Or install the package:

```bash
pip install -e .
```

### 2. Configure MCP client

Add the server configuration to your MCP client settings (e.g., Claude Desktop):

**For Claude Desktop (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):**

```json
{
  "mcpServers": {
    "imhex": {
      "command": "python",
      "args": ["/path/to/ImHex/mcp_server/server.py"],
      "env": {
        "IMHEX_HOST": "localhost",
        "IMHEX_PORT": "31337"
      }
    }
  }
}
```

### 3. Start ImHex

1. Launch ImHex
2. Go to **Edit → Settings → General**
3. Enable **Network Interface**
4. Restart ImHex if prompted

## Available Tools

### File Operations

#### `imhex_open_file`
Open a file in ImHex for analysis.

**Parameters:**
- `path` (string): Path to the file to open

**Example:**
```json
{
  "path": "/path/to/binary/file.bin"
}
```

#### `imhex_read_hex`
Read hex data from the currently open file.

**Parameters:**
- `offset` (integer): Offset to start reading from (in bytes)
- `length` (integer): Number of bytes to read

**Example:**
```json
{
  "offset": 0,
  "length": 256
}
```

#### `imhex_write_hex`
Write hex data to the currently open file.

**Parameters:**
- `offset` (integer): Offset to start writing to (in bytes)
- `data` (string): Hex data to write (e.g., '0A1B2C3D')

**Example:**
```json
{
  "offset": 100,
  "data": "0A1B2C3D"
}
```

### Analysis Tools

#### `imhex_inspect_data`
Inspect data at a specific offset with various data type interpretations.

**Parameters:**
- `offset` (integer): Offset to inspect
- `types` (array, optional): Data types to display (int8, int16, int32, int64, float, double, ascii, etc.)

**Example:**
```json
{
  "offset": 0,
  "types": ["int32", "float", "ascii"]
}
```

#### `imhex_hash`
Calculate hash of data in the currently open file.

**Parameters:**
- `algorithm` (string): Hash algorithm (md5, sha1, sha256, sha512, etc.)
- `offset` (integer, optional): Offset to start hashing from (default: 0)
- `length` (integer, optional): Number of bytes to hash (default: entire file)

**Example:**
```json
{
  "algorithm": "sha256",
  "offset": 0,
  "length": 1024
}
```

#### `imhex_disassemble`
Disassemble binary code at a specific offset.

**Parameters:**
- `offset` (integer): Offset to start disassembly
- `length` (integer): Number of bytes to disassemble
- `architecture` (string): Architecture (x86, x64, arm, arm64, mips, etc.)

**Example:**
```json
{
  "offset": 0,
  "length": 100,
  "architecture": "x64"
}
```

### Search and Pattern Tools

#### `imhex_search`
Search for a pattern in the currently open file.

**Parameters:**
- `pattern` (string): Pattern to search for (hex string or text)
- `type` (string): Type of search to perform (hex, text, regex)

**Example:**
```json
{
  "pattern": "48656C6C6F",
  "type": "hex"
}
```

#### `imhex_set_pattern_code`
Set pattern language code in ImHex for binary data parsing.

**Parameters:**
- `code` (string): Pattern language code to execute

**Example:**
```json
{
  "code": "struct Header { u32 magic; u32 version; }; Header header @ 0x00;"
}
```

### Annotation Tools

#### `imhex_bookmark_add`
Add a bookmark to a specific location in the file.

**Parameters:**
- `offset` (integer): Offset of the bookmark
- `size` (integer): Size of the bookmarked region
- `name` (string): Name/comment for the bookmark
- `color` (string, optional): Color of the bookmark (hex RGB, e.g., 'FF0000')

**Example:**
```json
{
  "offset": 0,
  "size": 4,
  "name": "File Magic",
  "color": "00FF00"
}
```

### Utility Tools

#### `imhex_decode`
Decode data using various encoding schemes.

**Parameters:**
- `data` (string): Data to decode (hex string)
- `encoding` (string): Encoding type (base64, ascii85, url, etc.)

**Example:**
```json
{
  "data": "48656C6C6F",
  "encoding": "hex"
}
```

#### `imhex_get_capabilities`
Get ImHex build version, commit, branch, and available commands.

**Parameters:** None

## Usage Examples

### Example 1: Analyze a Binary File

```
User: Analyze the file /path/to/firmware.bin

Claude will:
1. Use imhex_open_file to open the file
2. Use imhex_read_hex to read the header
3. Use imhex_inspect_data to interpret the header data
4. Use imhex_hash to calculate checksums
5. Report findings
```

### Example 2: Parse Binary Structure with Pattern Language

```
User: Parse the PE header of this executable

Claude will:
1. Open the file with imhex_open_file
2. Write a pattern language script for PE header parsing
3. Use imhex_set_pattern_code to execute the pattern
4. Report the parsed structure
```

### Example 3: Search and Patch

```
User: Find all occurrences of the string "DEBUG" and replace with "RELEAS"

Claude will:
1. Use imhex_search to find all occurrences
2. Use imhex_write_hex to patch each occurrence
3. Report results
```

## Pattern Language

ImHex includes a powerful pattern language for binary data parsing. The MCP server allows Claude to write and execute pattern scripts. Here's a basic example:

```cpp
// Simple PE header pattern
struct DOSHeader {
    char magic[2];
    u16 lastsize;
    u16 nblocks;
    // ... more fields
};

struct PEHeader {
    char signature[4];
    u16 machine;
    u16 numberOfSections;
    // ... more fields
};

DOSHeader dosHeader @ 0x00;
PEHeader peHeader @ dosHeader.e_lfanew;
```

## Troubleshooting

### ImHex not responding

1. Ensure ImHex is running
2. Check that Network Interface is enabled in Settings
3. Verify ImHex is listening on port 31337:
   ```bash
   netstat -an | grep 31337
   ```

### Connection refused

1. Check firewall settings
2. Ensure IMHEX_HOST and IMHEX_PORT environment variables are correct
3. Try restarting ImHex

### MCP server not appearing in Claude

1. Check Claude Desktop configuration file syntax
2. Verify the path to server.py is correct
3. Restart Claude Desktop
4. Check Claude Desktop logs

## Development

### Running the server standalone

```bash
python server.py
```

The server communicates via stdin/stdout using the MCP protocol.

### Testing connections

You can test the ImHex TCP connection directly:

```bash
echo '{"endpoint":"imhex/capabilities","data":{}}' | nc localhost 31337
```

## License

This MCP server follows ImHex's GPL-2.0 license.

## Contributing

Contributions are welcome! Areas for improvement:
- Add more ImHex endpoints
- Improve error handling
- Add data visualization support
- Extend pattern language integration
- Add resource support for reading files

## References

- [ImHex GitHub](https://github.com/WerWolv/ImHex)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [ImHex Pattern Language Documentation](https://docs.werwolv.net/pattern-language/)
