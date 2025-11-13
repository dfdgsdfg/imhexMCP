# ImHex MCP CLI Tool

A command-line interface for interacting with the ImHex MCP server.

## Installation

The CLI tool requires Python 3.10+ and the `click` library:

```bash
cd mcp-server
source venv/bin/activate
pip install click
```

## Usage

### Basic Commands

```bash
# Check server status
./imhex_cli.py status

# Show server metrics
./imhex_cli.py metrics
```

### File Operations

```bash
# List all open files
./imhex_cli.py files list

# Open a file
./imhex_cli.py files open /path/to/file.bin

# Read data from file (provider_id, offset, size)
./imhex_cli.py files read 0 0x100 256

# Read with hex dump display
./imhex_cli.py files read 0 0 256 --hex

# Search for a hex pattern
./imhex_cli.py files search 0 "504B0304"
```

### Data Analysis

```bash
# Extract strings from binary data
./imhex_cli.py data strings 0

# With options
./imhex_cli.py data strings 0 --offset 0 --size 2048 --min-length 8 --type utf8

# Detect file type using magic signatures
./imhex_cli.py data magic 0
```

### Interactive Mode

Enter interactive mode for a command prompt:

```bash
./imhex_cli.py interactive
```

Available commands in interactive mode:
- `status` - Check server status
- `list` - List open files
- `metrics` - Show metrics
- `help` - Show help
- `exit` or `quit` - Exit interactive mode

### Connection Options

Connect to a custom host/port:

```bash
./imhex_cli.py --host 192.168.1.100 --port 31337 --timeout 30 status
```

## Command Reference

### Status Commands

- `status` - Check server status and list available endpoints
- `metrics` - Show server performance metrics and health status

### File Commands

- `files list` - List all currently open files with details
- `files open FILE` - Open a file in ImHex
- `files read ID OFFSET SIZE` - Read data from a file provider
  - `--hex` - Display as hex dump
  - `--ascii` - Display ASCII representation
- `files search ID PATTERN` - Search for hex pattern
  - `--max-results N` - Limit results (default: 10)

### Data Analysis Commands

- `data strings ID` - Extract strings from binary data
  - `--offset N` - Start offset (default: 0)
  - `--size N` - Data size to analyze (default: 1024)
  - `--min-length N` - Minimum string length (default: 4)
  - `--type TYPE` - String type: ascii, utf8, utf16 (default: ascii)
  - `--max-results N` - Maximum results to display (default: 20)
- `data magic ID` - Detect file type using magic signatures

### Interactive Mode

- `interactive` - Enter interactive command prompt

## Examples

### Basic Workflow

```bash
# 1. Check if server is running
./imhex_cli.py status

# 2. Open a binary file
./imhex_cli.py files open /tmp/firmware.bin

# 3. List open files to get provider ID
./imhex_cli.py files list

# 4. Read first 256 bytes
./imhex_cli.py files read 0 0 256 --hex

# 5. Extract strings
./imhex_cli.py data strings 0 --min-length 8

# 6. Detect file type
./imhex_cli.py data magic 0
```

### Searching for Patterns

```bash
# Search for ZIP signature
./imhex_cli.py files search 0 "504B0304"

# Search for ELF magic
./imhex_cli.py files search 0 "7F454C46"

# Search for PE signature
./imhex_cli.py files search 0 "4D5A"
```

### String Extraction

```bash
# Extract ASCII strings (min length 10)
./imhex_cli.py data strings 0 --min-length 10 --max-results 50

# Extract UTF-8 strings from specific region
./imhex_cli.py data strings 0 --offset 0x1000 --size 4096 --type utf8

# Extract UTF-16 strings
./imhex_cli.py data strings 0 --type utf16
```

## Output Examples

### Status Command

```
Checking ImHex MCP server status...

✓ Server is running

Available Endpoints:
  • capabilities
  • health
  • file/list
  • file/open
  • file/read
  • file/search
  • data/strings
  • data/magic

Version: 1.0.0
```

### Files List

```
Open Files (2):

  [0] /tmp/firmware.bin
      Size: 2.05 MB
      Flags: readable

  [1] /path/to/data.bin
      Size: 512.00 KB
      Flags: readable, writable
```

### Hex Dump

```
Data from provider 0 at offset 0x00000000:

  00000000  50 4b 03 04 14 00 00 00  08 00 21 8b 65 57 9e 3f  PK........!.eW.?
  00000010  d6 c5 8c 00 00 00 ac 00  00 00 08 00 1c 00 74 65  ..............te
  00000020  73 74 2e 74 78 74 55 54  09 00 03 6f b0 9a 64 6f  st.txtUT...o..do
  00000030  b0 9a 64 75 78 0b 00 01  04 e8 03 00 00 04 e8 03  ..dux...........
```

## Error Handling

The CLI provides clear error messages:

- Connection errors: "Connection refused - is ImHex running?"
- Timeout errors: "Request timeout"
- Invalid input: "Error: Invalid hex data"

Exit codes:
- `0` - Success
- `1` - Error occurred

## Tips

1. Use `--help` on any command to see detailed options:
   ```bash
   ./imhex_cli.py files read --help
   ```

2. Provider IDs start at 0 and increment for each opened file

3. Hex patterns should be provided without spaces or `0x` prefix:
   ```bash
   # Correct
   ./imhex_cli.py files search 0 "504B0304"

   # Also works (spaces and 0x are removed)
   ./imhex_cli.py files search 0 "50 4B 03 04"
   ```

4. Use interactive mode for exploratory analysis:
   ```bash
   ./imhex_cli.py interactive
   imhex> status
   imhex> list
   imhex> exit
   ```

## Troubleshooting

**"Connection refused"**
- Ensure ImHex is running with MCP network interface enabled
- Check the server is listening on the correct port (default: 31337)

**"Request timeout"**
- Increase timeout: `--timeout 60`
- Check network connectivity

**"No files currently open"**
- Use `files open` to open a file first
- Or open files through the ImHex GUI

## Integration

The CLI can be used in scripts:

```bash
#!/bin/bash

# Open file and extract strings to file
./imhex_cli.py files open firmware.bin
./imhex_cli.py data strings 0 --min-length 10 > strings.txt

# Search for specific patterns
./imhex_cli.py files search 0 "504B0304" | grep "Offset"
```

## Future Enhancements

Planned features:
- JSON output format for scripting
- Configuration file support
- Batch operations
- Data export/import
- Pattern library management
