# ImHex MCP Integration - Quick Start Guide

Get up and running with AI-powered binary analysis in 5 minutes!

## Prerequisites

Before starting, ensure you have:
- ✅ macOS or Linux
- ✅ Python 3.10+
- ✅ CMake 3.25+
- ✅ Git
- ✅ C++ compiler (GCC 11+ or Clang 14+)
- ✅ Claude Desktop installed

## Step 1: Clone Repository (30 seconds)

```bash
git clone --recurse-submodules https://github.com/jmpnop/imhexMCP.git
cd imhexMCP
```

**Note**: The `--recurse-submodules` flag automatically downloads ImHex source code.

## Step 2: Apply Patches (1 minute)

Apply the 6 patches to enable automated file opening:

```bash
./apply-patches.sh
```

You'll see:
```
========================================
ImHex MCP Integration - Patch Applicator
========================================

Checking patch status...

✓ 01-builtin-library-plugin.patch - Not applied
✓ 02-fileprovider-public-open.patch - Not applied
...

Ready to apply 6 patch(es) to ImHex source.
Continue? (y/N) y

Applying patches...

✓ 01-builtin-library-plugin.patch - Applied successfully
✓ 02-fileprovider-public-open.patch - Applied successfully
...

🎉 All patches applied successfully!
```

## Step 3: Build ImHex (2-3 minutes)

```bash
cd ImHex
mkdir -p build && cd build

# Configure
cmake -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DIMHEX_OFFLINE_BUILD=ON \
  ..

# Build (uses all CPU cores)
ninja -j$(sysctl -n hw.ncpu)  # macOS
# ninja -j$(nproc)              # Linux
```

**Important**: After building, verify the correct files exist:
```bash
ls -lh plugins/ | grep -E "(builtin|mcp)"

# Should show:
# builtin.hexpluglib  (23MB)  ✅
# mcp.hexplug         (296KB) ✅
#
# Should NOT show:
# builtin.hexplug     ❌ (if exists, delete it!)
```

If `builtin.hexplug` exists, remove it:
```bash
rm plugins/builtin.hexplug
```

## Step 4: Setup MCP Server (30 seconds)

```bash
cd ../../mcp-server

# Create virtual environment
python3 -m venv venv

# Activate venv
source venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt
```

## Step 5: Start ImHex (10 seconds)

```bash
cd ../ImHex/build
./imhex
```

## Step 6: Enable Network Interface (20 seconds)

In ImHex:
1. Click **Extras** menu
2. Select **Settings**
3. Go to **General** tab
4. Find **Network Interface** section
5. Check **Enable** checkbox
6. Click **Save**
7. **Restart ImHex**

The Network Interface will now listen on `localhost:31337`.

## Step 7: Verify Setup (10 seconds)

```bash
cd ../../
./verify-setup.sh
```

You should see:
```
========================================
Verification Results
========================================

Passed:   15
Failed:   0
Warnings: 0

✓ Setup verification passed!
```

## Step 8: Run Tests (15 seconds)

```bash
cd mcp-server
./venv/bin/python test_binary_analysis.py
```

Expected output:
```
======================================================================
Test Summary
======================================================================
Total tests run: 8
✓ Passed: 8
✗ Failed: 0

🎉 All binary analysis tests passed!
```

## Step 9: Configure Claude Desktop (1 minute)

Edit Claude Desktop config:
```bash
# macOS
code ~/Library/Application\ Support/Claude/claude_desktop_config.json

# Or manually edit the file
```

Add this configuration (replace paths with your actual paths):
```json
{
  "mcpServers": {
    "imhex": {
      "command": "/FULL/PATH/TO/imhexMCP/mcp-server/venv/bin/python",
      "args": [
        "/FULL/PATH/TO/imhexMCP/mcp-server/server.py"
      ]
    }
  }
}
```

**Important**: Use absolute paths, not `~` or relative paths!

Example:
```json
{
  "mcpServers": {
    "imhex": {
      "command": "/Users/pasha/Projects/imhexMCP/mcp-server/venv/bin/python",
      "args": [
        "/Users/pasha/Projects/imhexMCP/mcp-server/server.py"
      ]
    }
  }
}
```

## Step 10: Restart Claude Desktop (5 seconds)

1. Quit Claude Desktop completely
2. Start Claude Desktop again
3. Wait for it to fully load

## Step 11: Test with Claude! (30 seconds)

In Claude, ask:
```
Can you check if ImHex is working? Use the imhex_get_capabilities tool.
```

Claude should respond with ImHex version and available tools!

## Your First Binary Analysis

Now try analyzing a binary file:

```
I have a binary file at /path/to/firmware.bin. Can you:
1. Open it
2. Read the first 64 bytes
3. Calculate the SHA-256 hash
4. Search for any ASCII strings
```

Claude will:
- ✅ Open the file automatically (no manual GUI interaction!)
- ✅ Read the header
- ✅ Calculate the hash
- ✅ Search for ASCII text
- ✅ Report all findings

## Common Issues & Solutions

### Issue: "Connection refused"
**Solution**: Make sure ImHex is running with Network Interface enabled.

### Issue: ImHex crashes on startup
**Solution**: Delete old `builtin.hexplug` file:
```bash
rm ImHex/build/plugins/builtin.hexplug
```

### Issue: Patches won't apply
**Solution**: Your ImHex version may have diverged. See `patches/README.md` for manual application.

### Issue: Claude can't find imhex tools
**Solution**:
1. Check Claude Desktop config has correct absolute paths
2. Restart Claude Desktop completely
3. Check ImHex is running with Network Interface enabled

### Issue: Tests fail
**Solution**:
1. Verify ImHex is running: `ps aux | grep imhex`
2. Verify Network Interface: `lsof -i :31337`
3. Run verification: `./verify-setup.sh`

## What's Next?

Check out these guides:
- **[README.md](README.md)** - Complete project documentation
- **[patches/README.md](patches/README.md)** - Patch system details
- **[CHANGELOG.md](CHANGELOG.md)** - Version history
- **[CLAUDE_CONTEXT.md](mcp-server/CLAUDE_CONTEXT.md)** - Context for Claude sessions

## Example Workflows

### Malware Analysis
```
I have a suspicious executable at /path/to/malware.exe. Can you:
1. Calculate its hashes (MD5, SHA-1, SHA-256)
2. Search for URLs (http:// and https://)
3. Look for suspicious patterns (XOR keys, shellcode markers)
4. Extract any embedded strings
```

### Firmware Analysis
```
Analyze this firmware file: /path/to/firmware.bin
- Identify the file format
- Find the bootloader
- Extract the version string
- Calculate checksums
```

### Binary Comparison
```
I have two firmware versions:
- /path/to/firmware_v1.bin
- /path/to/firmware_v2.bin

Can you compare them and tell me what changed?
```

### Data Extraction
```
At offset 0x1000 in /path/to/data.bin, there's a structure.
Can you:
1. Read 256 bytes from that offset
2. Interpret it as various data types
3. Search for any patterns in that region
4. Create a bookmark for this section
```

## Tips for Best Results

1. **Be Specific**: Provide exact file paths and offsets
2. **Use Hex Notation**: Offsets like `0x1000` instead of `4096`
3. **Request Multiple Operations**: Claude can chain operations automatically
4. **Ask for Explanations**: "What does this data mean?" helps Claude provide context
5. **Bookmark Important Findings**: Ask Claude to create bookmarks for reference

## Troubleshooting Commands

Quick diagnostics:
```bash
# Check ImHex is running
ps aux | grep imhex

# Check Network Interface
lsof -i :31337

# Verify setup
./verify-setup.sh

# Run tests
cd mcp-server && ./venv/bin/python test_binary_analysis.py

# Check patch status
cd ImHex && git diff --name-only
```

## Performance Tips

- Files under 128MB load into memory (fast)
- Files over 128MB use direct access (slower but works)
- Pattern searches return up to 10,000 matches
- Hashing is fast (native ImHex performance)

## Getting Help

- 📖 Read the [README.md](README.md)
- 🐛 Check [GitHub Issues](https://github.com/jmpnop/imhexMCP/issues)
- 💬 Join [GitHub Discussions](https://github.com/jmpnop/imhexMCP/discussions)
- 📧 Report bugs with logs and steps to reproduce

## Success Indicators

You'll know everything is working when:
- ✅ `./verify-setup.sh` shows 15/15 passed
- ✅ `test_binary_analysis.py` shows 8/8 tests passed
- ✅ Claude can list imhex tools via `imhex_get_capabilities`
- ✅ Claude can open files automatically without asking you to open them manually
- ✅ You can analyze multiple files in one conversation

## Total Time: ~5-6 minutes

- Clone repository: 30s
- Apply patches: 1m
- Build ImHex: 2-3m
- Setup MCP server: 30s
- Start ImHex + enable Network Interface: 30s
- Verify + test: 25s
- Configure Claude Desktop: 1m
- Restart Claude Desktop: 5s

**Congratulations! You're ready to analyze binaries with AI! 🎉**
