# Quick Start Guide

Get up and running with ImHex MCP Server in 5 minutes!

## Step 1: Setup ImHex

1. **Download and install ImHex** from [https://github.com/WerWolv/ImHex/releases](https://github.com/WerWolv/ImHex/releases)

2. **Launch ImHex**

3. **Enable Network Interface:**
   - Open ImHex
   - Go to **Edit → Settings → General** (or **Preferences** on macOS)
   - Scroll down to find **Network Interface**
   - Check the box to enable it
   - Click **Save**
   - **Restart ImHex** for changes to take effect

4. **Verify ImHex is listening:**
   ```bash
   # On Linux/macOS:
   netstat -an | grep 31337

   # On Windows:
   netstat -an | findstr 31337
   ```

   You should see ImHex listening on port 31337.

## Step 2: Install MCP Server

1. **Navigate to the mcp_server directory:**
   ```bash
   cd ImHex/mcp_server
   ```

2. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Test the connection to ImHex:**
   ```bash
   python test_server.py
   ```

   You should see:
   ```
   ✓ Connected to ImHex successfully
   ✓ ImHex is responding correctly
   ✓ All tests passed!
   ```

## Step 3: Configure Claude Desktop

1. **Find your Claude Desktop config file:**
   - **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - **Windows**: `%APPDATA%/Claude/claude_desktop_config.json`
   - **Linux**: `~/.config/Claude/claude_desktop_config.json`

2. **Edit the config file** and add the ImHex MCP server:
   ```json
   {
     "mcpServers": {
       "imhex": {
         "command": "python",
         "args": ["/FULL/PATH/TO/ImHex/mcp_server/server.py"]
       }
     }
   }
   ```

   **Important**: Replace `/FULL/PATH/TO/` with the actual path to your ImHex directory!

3. **Restart Claude Desktop**

## Step 4: Test with Claude

1. **Open Claude Desktop**

2. **Check if ImHex MCP server is connected:**
   - Look for the hammer icon in Claude's interface
   - The ImHex tools should appear in the tools list

3. **Try a simple command:**
   ```
   Can you check if ImHex is working? Use the capabilities tool.
   ```

   Claude should use the `imhex_get_capabilities` tool and show you ImHex's version and capabilities.

## Step 5: Analyze Your First File

1. **Create a test binary file:**
   ```bash
   echo "Hello, ImHex!" > test.txt
   ```

2. **Ask Claude to analyze it:**
   ```
   Open the file test.txt in ImHex and show me its contents in hex format.
   Read the first 32 bytes.
   ```

3. **Claude will:**
   - Use `imhex_open_file` to open the file
   - Use `imhex_read_hex` to read the data
   - Show you the hex dump

## Common Commands

### Analyze a binary file
```
Open /path/to/file.bin in ImHex and analyze its structure.
What's in the first 256 bytes?
```

### Calculate a hash
```
Calculate the SHA256 hash of the entire file.
```

### Search for a pattern
```
Search for the hex pattern "504B0304" (ZIP signature) in the file.
```

### Parse with Pattern Language
```
Parse this file as a PE executable using the pattern language.
Show me the DOS header and PE header.
```

### Disassemble code
```
Disassemble 100 bytes at offset 0x1000 as x64 assembly.
```

## Troubleshooting

### ImHex not responding

**Problem:** `✗ Connection refused` when running test_server.py

**Solutions:**
1. Make sure ImHex is actually running
2. Check that Network Interface is enabled in Settings
3. Restart ImHex after enabling the network interface
4. Check firewall settings

### MCP server not appearing in Claude

**Problem:** ImHex tools don't show up in Claude Desktop

**Solutions:**
1. Check the config file path is correct
2. Make sure the path to server.py is absolute (full path)
3. Restart Claude Desktop completely
4. Check Claude Desktop logs for errors
5. Verify Python is in your PATH

### Tools fail with "Not connected to ImHex"

**Problem:** Tools return "Not connected to ImHex" error

**Solutions:**
1. Make sure ImHex is running BEFORE starting Claude
2. Enable Network Interface in ImHex settings
3. Check port 31337 is not blocked by firewall
4. Try restarting both ImHex and Claude Desktop

### "endpoint not found" errors

**Problem:** Tools return errors about endpoints not being found

**Note:** The current implementation provides a bridge to ImHex's network interface. Some endpoints in the MCP server may need to be implemented on the ImHex side as custom network endpoints. The basic endpoints that should work are:
- `imhex/capabilities`
- `pattern_editor/set_code`

For full functionality, you may need to:
1. Create a custom ImHex plugin to register additional endpoints
2. Or use ImHex's existing UI through other means

## Next Steps

1. Read the full [README.md](README.md) for detailed documentation
2. Explore [example_patterns.hexpat](examples/example_patterns.hexpat) for pattern language examples
3. Try analyzing different file formats (PE, ELF, ZIP, PNG, etc.)
4. Experiment with the pattern language for custom binary formats

## Need Help?

- ImHex Documentation: [https://docs.werwolv.net/](https://docs.werwolv.net/)
- ImHex GitHub: [https://github.com/WerWolv/ImHex](https://github.com/WerWolv/ImHex)
- MCP Documentation: [https://modelcontextprotocol.io/](https://modelcontextprotocol.io/)

Happy hex editing!
