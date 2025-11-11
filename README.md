# ImHex MCP Integration
<img width="2912" height="1632" alt="image" src="https://github.com/user-attachments/assets/76df84b3-b91e-4a6e-8971-96893213ea6c" />

<div align="center">

**🤖 AI-Powered Binary Analysis for ImHex**

[![License](https://img.shields.io/badge/license-GPL--2.0-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![ImHex](https://img.shields.io/badge/ImHex-1.35%2B-orange.svg)](https://github.com/WerWolv/ImHex)
[![MCP](https://img.shields.io/badge/MCP-1.0+-purple.svg)](https://modelcontextprotocol.io/)
[![Version](https://img.shields.io/badge/version-0.4.0-blue.svg)](CHANGELOG.md)

*Enable AI assistants like Claude to perform advanced binary file analysis through ImHex*

**[⚡ Quickstart Guide](QUICKSTART.md)** • [Features](#-features) • [Documentation](#-documentation) • [Testing](#-testing) • [Roadmap](#️-roadmap) • [Contributing](#-contributing)

</div>

---

## 🌟 Highlights

- ✨ **20 MCP Tools** - Complete binary analysis toolkit for AI assistants
- 🤖 **Automated File Opening** - Fully implemented programmatic file access (no manual GUI!)
- 🚀 **Lightning Fast** - Enhanced connection management with retry logic
- 🔍 **Deep Inspection** - 24+ data type interpretations (int, float, ASCII, binary, etc.)
- 🔐 **Secure Hashing** - MD5, SHA-1, SHA-224, SHA-256, SHA-384, SHA-512
- 📝 **Smart Search** - Find up to 10,000 pattern matches instantly
- 🎨 **Visual Bookmarks** - AI-driven code annotation and highlighting
- 🧩 **Pattern Language** - AI generates ImHex patterns for binary parsing
- ⚡ **Data Decoding** - Base64, ASCII, binary, hex encoding support
- 🔧 **Clean Patch System** - 6 automated patches for ImHex source modification
- 🧪 **Fully Tested** - 8/8 binary analysis tests passing
- 📦 **Lightweight** - Only 476 KB (ImHex via git submodule)

---

## 💡 What is This?

This project adds **Model Context Protocol (MCP)** support to [ImHex](https://github.com/WerWolv/ImHex), enabling AI assistants to interact with the hex editor programmatically. Think of it as giving Claude "eyes" for binary files.

### What Can AI Do With This?

🔬 **Analyze** - Identify file formats, extract headers, find signatures
📊 **Parse** - Generate and execute pattern language for complex formats
🔎 **Search** - Find patterns, strings, magic numbers across files
✏️ **Annotate** - Add intelligent bookmarks and comments
🔐 **Verify** - Calculate and compare hashes automatically
🎯 **Extract** - Pull data from specific offsets with type awareness

### Why Use MCP?

- **Automate** repetitive reverse engineering tasks
- **Leverage** AI for pattern recognition in binaries
- **Accelerate** firmware and malware analysis workflows
- **Document** findings with AI-generated annotations
- **Learn** binary formats through AI explanations

---

## 🚀 Quick Start

### One-Command Setup

```bash
git clone --recurse-submodules https://github.com/jmpnop/imhexMCP
cd imhexMCP
./scripts/setup.sh
```

That's it! The script will:
1. ✅ Initialize ImHex submodule
2. ✅ Build ImHex with MCP plugin
3. ✅ Install Python MCP server
4. ✅ Configure Claude Desktop

### Manual Installation

<details>
<summary>Click to expand manual steps</summary>

```bash
# 1. Clone with submodules
git clone --recurse-submodules https://github.com/jmpnop/imhexMCP
cd imhexMCP

# 2. Build ImHex with plugin
./scripts/build.sh

# 3. Install MCP server
cd mcp-server
pip install -r requirements.txt
./install.sh

# 4. Configure Claude Desktop
# Edit: ~/Library/Application Support/Claude/claude_desktop_config.json
{
  "mcpServers": {
    "imhex": {
      "command": "python",
      "args": ["/full/path/to/imhexMCP/mcp-server/server.py"]
    }
  }
}

# 5. Enable Network Interface in ImHex
# Settings → General → Network Interface → Enable → Restart
```

</details>

### Verify Installation

**Option 1: Automated Verification Script**
```bash
./verify-setup.sh
```

This will check:
- ✅ Repository structure (ImHex, patches, scripts)
- ✅ Build artifacts (plugins, binaries)
- ✅ MCP server setup
- ✅ ImHex process running
- ✅ Network interface listening on port 31337

**Option 2: Ask Claude**
```
Can you check if ImHex is working? Use the capabilities tool.
```

You should see ImHex version and available commands! 🎉

---

## 🎯 Automated File Opening - Now Fully Working!

**Big Update**: Automated file opening is now fully implemented! Files can be opened programmatically via MCP without any manual GUI interaction.

### Why ImHex Needed Patching

**The Problem**: ImHex plugins are **isolated shared libraries** by design. Each plugin (`.hexplug`) is loaded independently and cannot access symbols from other plugins. The `FileProvider` class that handles file opening lives in the `builtin` plugin, making it inaccessible to the `mcp` plugin.

**Original Limitation**: Without these patches, the MCP workflow required:
1. 🖱️ **Manual GUI interaction** - User must click "File → Open" in ImHex
2. 🔄 **Context switching** - Switch between Claude and ImHex windows
3. ⏱️ **Slower analysis** - Wait for manual file loading before AI can proceed
4. 🚫 **No automation** - Cannot batch process multiple files
5. 💬 **Verbose communication** - "Please open file X in ImHex, then I'll analyze it..."

This broke the AI workflow entirely - Claude couldn't autonomously analyze binary files.

### How The Patches Solve It

We modified ImHex's plugin architecture to enable **controlled cross-plugin symbol sharing**:

1. **Builtin Plugin as Library** - Export `builtin` plugin as shared library (`.hexpluglib`)
   - Exposes FileProvider symbols for linking
   - Still works as a plugin (dual-purpose)

2. **Public FileProvider API** - Made `FileProvider::open(bool)` public
   - External plugins can call file opening methods
   - Maintains encapsulation of internal methods

3. **Graceful Settings Handling** - Handle missing settings with defaults
   - Works when ImHex settings system isn't initialized
   - Network interface doesn't require full GUI startup

4. **MCP Plugin Linking** - Link MCP plugin against builtin library
   - Resolves FileProvider symbols at build time
   - Clean dependency management

5. **Direct FileProvider Usage** - Create and open files directly
   - Bypasses event system that caused deadlocks
   - Immediate file loading without GUI interaction

### Workflow Benefits

**Before Patches** (Manual Workflow):
```
User: "Analyze firmware.bin"
Claude: "Please open firmware.bin in ImHex first"
User: [Switches to ImHex, clicks File → Open, selects file]
User: "OK, it's open"
Claude: [Now can read and analyze the file]
```

**After Patches** (Automated Workflow):
```
User: "Analyze firmware.bin"
Claude: [Opens file automatically]
Claude: [Reads file automatically]
Claude: [Analyzes and reports results]
Done! ✨
```

**Key Benefits**:
- ✅ **Zero manual interaction** - AI handles everything
- ✅ **Batch processing** - Analyze multiple files automatically
- ✅ **Faster workflow** - No context switching or waiting
- ✅ **True automation** - Compare files, hunt patterns, extract data autonomously
- ✅ **Better UX** - Just ask Claude, it handles the rest
- ✅ **Scriptable** - Build automated binary analysis pipelines

### Apply Patches

The implementation requires 6 patches to ImHex source code. Apply them automatically:

```bash
cd /path/to/imhexMCP-standalone
./apply-patches.sh
```

The script will:
- ✅ Check which patches are already applied
- ✅ Dry-run verify before applying
- ✅ Apply patches in correct order
- ✅ Provide next steps for building

After applying patches, rebuild ImHex:

```bash
cd ImHex/build
rm -f plugins/builtin.hexplug  # Remove old module
ninja -j$(sysctl -n hw.ncpu)   # Rebuild
```

### Test Results

All 8 comprehensive binary analysis tests pass with 100% success rate:

```
======================================================================
Test Summary
======================================================================
Total tests run: 8
✓ Passed: 8
✗ Failed: 0

Tests Executed:
✓ File Opening - Programmatic file opening via MCP
✓ Header Reading - Read and verified magic bytes
✓ Data Inspection - Type interpretation at offsets
✓ SHA-256 Hashing - Hash calculation and verification
✓ Pattern Search - Found hex patterns in binary data
✓ ASCII Text Reading - Text extraction from binary
✓ Bookmark Creation - Added annotations to file regions
✓ Multi-Hash - MD5, SHA-1, SHA-256 generation

🎉 All binary analysis tests passed!
======================================================================
```

Run the test suite yourself:
```bash
# Ensure ImHex is running with Network Interface enabled
cd mcp-server
./venv/bin/python test_binary_analysis.py
```

### Troubleshooting

**Issue: "Connection refused" when running tests**
- Solution: Start ImHex and enable Network Interface
- Location: Extras → Settings → **General** → Enable "Network Interface"
- Port: 31337 (hardcoded, localhost only)
- Restart ImHex after enabling

**Issue: ImHex crashes on startup with "Failed to add shortcut"**
- Cause: Duplicate builtin plugin files (both `.hexplug` and `.hexpluglib`)
- Solution: Remove old module file:
  ```bash
  rm ImHex/build/plugins/builtin.hexplug
  ```
- Only `builtin.hexpluglib` should exist

**Issue: "Settings not available" messages in ImHex logs**
- Status: Normal - these are debug messages showing graceful fallback to defaults
- Impact: None - functionality works correctly
- Reason: Network interface doesn't require full GUI initialization

**Issue: Patches fail to apply**
- Cause: ImHex source has diverged from patch base (commit b1e2185)
- Solution: See `patches/README.md` for manual modification instructions
- Check current commit: `cd ImHex && git rev-parse HEAD`

**Issue: Tests fail after rebuild**
- Solution: Ensure old `builtin.hexplug` file is removed
- Verify: `ls ImHex/build/plugins/` should show `builtin.hexpluglib` not `builtin.hexplug`
- Restart ImHex after rebuilding

### Documentation

- **[patches/README.md](patches/README.md)** - Patch documentation and application guide
- **[CLAUDE_CONTEXT.md](mcp-server/CLAUDE_CONTEXT.md)** - Context for other Claude sessions
- **[apply-patches.sh](apply-patches.sh)** - Automated patch application script
- **[revert-patches.sh](revert-patches.sh)** - Patch reversion script

---

## ✨ Features

### 🐍 MCP Server (Python)

The Python server implements the Model Context Protocol and provides:

| Feature | Description |
|---------|-------------|
| **11 MCP Tools** | Complete binary analysis toolkit |
| **Enhanced Error Handling** | Automatic retry with exponential backoff |
| **CLI Arguments** | `--host`, `--port`, `--debug`, `--timeout`, etc. |
| **Connection Pooling** | Efficient socket reuse |
| **Type Safety** | Full type hints throughout |
| **Comprehensive Logging** | DEBUG, INFO, WARN, ERROR levels |
| **Unit Tested** | Mock server for testing without ImHex |

**Commands:**
```bash
# Run with debug logging
python server.py --debug

# Custom host/port
python server.py --host 192.168.1.100 --port 31338

# Log to file
python server.py --log-file mcp.log --debug
```

### 🔌 ImHex Plugin (C++)

The C++ plugin extends ImHex with network endpoints:

| Feature | Description |
|---------|-------------|
| **9 Network Endpoints** | File I/O, search, hash, inspect, etc. |
| **24+ Data Types** | int8/16/32/64, float, double, ASCII, binary |
| **Big & Little Endian** | Both byte orders supported |
| **Hash Algorithms** | MD5, SHA-1/224/256/384/512 |
| **10K Search Matches** | 10x more than v0.1.0 |
| **Data Decoding** | Base64, ASCII, binary, hex |
| **Bounds Checking** | Prevent crashes and memory issues |
| **Size Limits** | Max 10MB reads for safety |

### 🤖 MCP Tools for AI

| Tool | Purpose | Parameters |
|------|---------|------------|
| `imhex_get_capabilities` | Get ImHex version & features | - |
| `imhex_open_file` | Open binary file | `path` |
| `imhex_read_hex` | Read hex data | `offset`, `length` |
| `imhex_write_hex` | Write hex data | `offset`, `data` |
| `imhex_inspect_data` | Multi-type inspection | `offset` |
| `imhex_search` | Find patterns | `pattern`, `type` |
| `imhex_hash` | Calculate hash | `algorithm`, `offset`, `length` |
| `imhex_bookmark_add` | Add bookmark | `offset`, `size`, `name`, `color` |
| `imhex_set_pattern_code` | Execute pattern | `code` |
| `imhex_decode` | Decode data | `data`, `encoding` |
| `imhex_provider_info` | Get file info | - |

---

## 🏗️ Architecture

```
┌─────────────────────┐
│   Claude / User     │  Ask questions about binaries
└──────────┬──────────┘
           │ Natural Language
           │
┌──────────▼──────────┐
│   Claude Code       │  AI Assistant
└──────────┬──────────┘
           │ MCP Protocol (JSON-RPC via stdio)
           │
┌──────────▼──────────┐
│   MCP Server        │  This Project (Python)
│   - Tool handlers   │  • Connection management
│   - Error handling  │  • Protocol translation
│   - Validation      │  • Retry logic
└──────────┬──────────┘
           │ TCP Socket (localhost:31337)
           │ Line-delimited JSON
           │
┌──────────▼──────────┐
│   ImHex             │  WerWolv/ImHex (Submodule)
│   Network Interface │  • Built-in TCP server
└──────────┬──────────┘
           │ Internal API
           │
┌──────────▼──────────┐
│   MCP Plugin        │  This Project (C++)
│   - File I/O        │  • 9 network endpoints
│   - Data inspection │  • Hash calculation
│   - Search & hash   │  • Pattern execution
│   - Bookmarks       │  • Data decoding
└──────────┬──────────┘
           │ ImHex APIs
           │
┌──────────▼──────────┐
│   ImHex Core        │
│   - Providers       │
│   - Pattern Engine  │
│   - Crypto Library  │
└─────────────────────┘
```

---

## 🎯 Usage Examples

### Example 1: Firmware Analysis

**User:**
```
I have firmware.bin. Can you analyze it and tell me what you find?
```

**Claude will:**
1. Open `firmware.bin` in ImHex
2. Read the first 512 bytes (header)
3. Inspect as various data types
4. Search for magic numbers (ELF, PE, etc.)
5. Calculate SHA256 hash
6. Identify file format
7. Report findings with offsets

### Example 2: PE Executable Parsing

**User:**
```
Parse this PE executable and show me the headers.
```

**Claude will:**
1. Generate ImHex pattern language for PE format:
```cpp
struct DOSHeader {
    char magic[2];      // "MZ"
    u16 lastsize;
    // ... more fields
    u32 e_lfanew;      // PE header offset
};

struct PEHeader {
    char signature[4];  // "PE\0\0"
    u16 machine;
    u16 numberOfSections;
    // ... more fields
};

DOSHeader dosHeader @ 0x00;
PEHeader peHeader @ dosHeader.e_lfanew;
```
2. Execute the pattern with `imhex_set_pattern_code`
3. Extract and display parsed structure

### Example 3: Malware Signature Hunting

**User:**
```
Find all suspicious patterns in this malware sample:
- Check for PE signature
- Look for "http://" and "https://" strings
- Find XOR keys (sequences of 0x00-0xFF)
- Calculate hashes
```

**Claude will:**
1. Search for `4D5A` (MZ signature)
2. Search for `687474703A2F2F` (http://)
3. Search for `68747470733A2F2F` (https://)
4. Search for XOR key patterns
5. Calculate MD5, SHA-1, SHA-256
6. Bookmark all findings with colors
7. Generate comprehensive report

### Example 4: Data Extraction

**User:**
```
At offset 0x1000, there's a structure. Can you tell me what it contains?
```

**Claude will:**
1. Use `imhex_inspect_data` at 0x1000
2. Show interpretations:
   - `uint8`: 72
   - `uint16_le`: 25928
   - `uint32_le`: 1819043144
   - `float_le`: 11.96875
   - `ascii`: "Hello..."
   - `hex`: "48656C6C6F"
3. Determine most likely data type
4. Explain findings

### Example 5: Firmware Diff Analysis (v0.4.0)

**User:**
```
Compare firmware_v1.bin and firmware_v2.bin to identify what changed between versions.
```

**Claude will:**
1. Open both firmware files
2. Use `diff/analyze` with Myers algorithm
3. Report diff regions:
   - **Matches**: Unchanged code/data regions
   - **Mismatches**: Modified bytes (patches, updates)
   - **Insertions**: New code added in v2
   - **Deletions**: Code removed from v1
4. Highlight critical changes:
   - Security patches at specific offsets
   - Modified function implementations
   - Updated configuration data
5. Calculate similarity percentage
6. Export changed regions for detailed analysis

**Real Output:**
```
Found 3 diff regions:
- 0x8-0x9: Mismatch (2 bytes) - Immediate value changed
- 0x78-0x3FF: Match (904 bytes) - Identical padding
- 0x400-0x72F: Mismatch (816 bytes) - Data pattern shift
Similarity: 92.3%
```

### Example 6: Shellcode Disassembly (v0.4.0)

**User:**
```
I found suspicious code at offset 0x2000 in this binary. Disassemble it to see what it does.
```

**Claude will:**
1. Use `disasm/disassemble` with appropriate architecture (x86/ARM/etc.)
2. Show instruction details:
   ```
   0x2000: mov     eax, 1        [B8 01 00 00 00]
   0x2005: mov     ebx, 2        [BB 02 00 00 00]
   0x200A: add     eax, ebx      [01 D8]
   0x200C: ret                   [C3]
   ```
3. Analyze instruction flow:
   - Identify function prologues/epilogues
   - Detect system calls
   - Find suspicious API calls
   - Track control flow (jumps, calls)
4. Explain what the code does
5. Flag potential malicious behavior

**Supported Architectures:**
- x86, x86-64 (Intel/AMD)
- ARM, ARM64 (AArch64)
- MIPS, PowerPC, SPARC
- And 10+ more via Capstone

### Example 7: Large File Analysis (v0.4.0)

**User:**
```
Analyze this 4GB memory dump for suspicious patterns, but my system has limited RAM.
```

**Claude will:**
1. Use `data/read_chunked` with 1MB chunks
2. Process memory dump incrementally:
   - **Chunk 0**: Scan 0x000000-0x0FFFFF (1MB)
   - **Chunk 1**: Scan 0x100000-0x1FFFFF (1MB)
   - Continue through entire dump...
3. Search each chunk for patterns:
   - PE/ELF headers (injected code)
   - Suspicious strings (URLs, IPs)
   - Shellcode signatures
4. Track progress: "Processing chunk 42/4096 (1.0%)"
5. Report findings with offsets
6. No memory constraints - handles multi-GB files

**Benefits:**
- **Memory Efficient**: Only 1MB in memory at a time
- **Progress Tracking**: See chunk index and remaining bytes
- **Flexible Encoding**: Hex or Base64 output
- **Unlimited Size**: Handle disk images, memory dumps, large binaries

---

## 📦 Repository Structure

This repository contains **only** the MCP integration (476 KB):

```
imhexMCP/                              # Your lightweight repo
│
├── 📄 README.md                       # This file
├── 📄 LICENSE                         # GPL-2.0
├── 📄 .gitmodules                     # Submodule config
│
├── 🐍 mcp-server/                     # Python MCP server
│   ├── server.py                     # MCP server (850 lines)
│   ├── install.sh                    # Auto-installer
│   ├── test_server.py                # Connection test
│   ├── requirements.txt              # Dependencies
│   ├── pyproject.toml                # Package config
│   └── tests/                        # Unit tests
│       ├── test_imhex_client.py      # Client tests
│       └── README.md                 # Test docs
│
├── 🔌 plugin/                         # ImHex C++ plugin
│   ├── CMakeLists.txt                # Build config
│   └── source/
│       └── plugin_mcp.cpp            # MCP plugin (950 lines)
│
├── 🔧 scripts/                        # Automation scripts
│   ├── build.sh                      # Build ImHex + plugin
│   └── setup.sh                      # Complete setup
│
├── 📚 docs/                           # Documentation
│   ├── QUICKSTART.md                 # 5-min guide
│   ├── BUILD_MCP.md                  # Build instructions
│   ├── IMPROVEMENTS.md               # v0.2.0 changes
│   ├── CHANGELOG.md                  # Version history
│   └── ARCHITECTURE.md               # Technical details
│
└── 📦 ImHex/                          # Git submodule (not stored)
    └── [WerWolv/ImHex source]        # Downloaded on init
```

**Why lightweight?**
- ✅ **99.9% smaller** - 476 KB vs 500 MB
- ✅ **Faster clones** - Seconds instead of minutes
- ✅ **Clear focus** - Only MCP integration code
- ✅ **Easy updates** - Pull latest ImHex separately
- ✅ **Better PRs** - See only relevant changes

---

## 📖 Documentation

| Document | Description |
|----------|-------------|
| **[QUICKSTART.md](QUICKSTART.md)** | ⚡ **Get started in 5 minutes!** |
| **[CHANGELOG.md](CHANGELOG.md)** | 📝 **Version history & upgrade guide** |
| [patches/README.md](patches/README.md) | Patch documentation & application guide |
| [CLAUDE_CONTEXT.md](mcp-server/CLAUDE_CONTEXT.md) | Context for other Claude sessions |
| [verify-setup.sh](verify-setup.sh) | Automated setup verification script |
| [apply-patches.sh](apply-patches.sh) | Automated patch application |
| [revert-patches.sh](revert-patches.sh) | Automated patch reversion |

---

## 🧪 Testing

### Run Unit Tests

```bash
cd mcp-server
pytest tests/ -v
```

### Test Connection to ImHex

```bash
cd mcp-server
python test_server.py
```

Expected output:
```
✓ Connected to ImHex successfully
✓ ImHex is responding correctly
✓ All tests passed!
```

### Integration Tests

```bash
cd tests
./run_integration_tests.sh
```

---

## 🛠️ Development

### Prerequisites

- **ImHex:** 1.35.0+
- **Python:** 3.10+
- **CMake:** 3.25+
- **C++ Compiler:** GCC or Clang with C++23 support

### Build Plugin Only

```bash
cd ImHex/build
make mcp -j$(nproc)
```

### Run Server in Debug Mode

```bash
cd mcp-server
python server.py --debug --log-file debug.log
```

### Code Quality

```bash
# Install dev dependencies
pip install -r mcp-server/requirements-dev.txt

# Format Python code
black mcp-server/

# Type check
mypy mcp-server/server.py

# Lint
pylint mcp-server/server.py
```

---

## 🤝 Contributing

We welcome contributions! Here's how:

1. **Fork** this repository
2. **Clone** your fork with submodules
3. **Create** a feature branch
4. **Make** changes (plugin or server)
5. **Add** tests for new features
6. **Test** thoroughly
7. **Commit** with clear messages
8. **Push** and create a Pull Request

### Areas for Contribution

- 🐛 **Bug fixes** - Report and fix issues
- ✨ **New features** - Regex search, streaming, etc.
- 📝 **Documentation** - Improve guides and examples
- 🧪 **Tests** - Increase coverage
- 🎨 **Examples** - Add usage examples
- 🌐 **Translations** - Help translate docs

See [CONTRIBUTING.md](docs/CONTRIBUTING.md) for detailed guidelines.

---

## 📊 Version Compatibility

| imhexMCP | ImHex | Python | MCP | Status | Key Features |
|----------|-------|--------|-----|--------|--------------|
| **0.4.0** | 1.38+ | 3.10+ | 1.0+ | ✅ Current | Binary diffing, disassembly, chunked read |
| 0.3.0 | 1.38+ | 3.10+ | 1.0+ | ✅ Stable | Multi-file support, regex search, data export |
| 0.2.5 | 1.38+ | 3.10+ | 1.0+ | ⚠️ Legacy | Automated file opening, patch system |
| 0.2.0 | 1.35+ | 3.10+ | 1.0+ | 🗄️ Archived | Manual file opening only |
| 0.1.0 | 1.35+ | 3.10+ | 1.0+ | 🗄️ Archived | Initial release |

---

## 📈 Statistics

| Metric | Count | Notes |
|--------|-------|-------|
| **Repository Size** | 476 KB | 99.9% smaller than full ImHex |
| **Code Lines** | 6,353 | MCP integration only |
| **Documentation** | 3,500+ | Comprehensive guides |
| **Test Lines** | 400+ | Unit & integration tests |
| **MCP Tools** | 20 | For AI assistants |
| **Network Endpoints** | 20 | Plugin APIs |
| **Data Types** | 24+ | Inspection modes |
| **Hash Algorithms** | 6 | MD5, SHA family |
| **Search Limit** | 10,000 | Pattern matches |

---

## ❓ FAQ

<details>
<summary><b>Do I need to download ImHex separately?</b></summary>

No! The `--recurse-submodules` flag downloads ImHex automatically. The setup script handles everything.

</details>

<details>
<summary><b>Can I use my existing ImHex installation?</b></summary>

Yes! Just copy the `plugin/` directory to your ImHex plugins folder and rebuild. See [Option 3](#option-3-use-existing-imhex).

</details>

<details>
<summary><b>Does this work on Windows?</b></summary>

Yes! Use MSYS2 MinGW64 environment. See [BUILD_MCP.md](docs/BUILD_MCP.md) for Windows instructions.

</details>

<details>
<summary><b>Can I use this without Claude?</b></summary>

Yes! The MCP server works with any MCP-compatible client. You can also use the ImHex plugin standalone via its TCP interface.

</details>

<details>
<summary><b>Is this safe for malware analysis?</b></summary>

The MCP server runs on localhost only with no authentication. Use appropriate sandboxing for malware analysis as you would with ImHex normally.

</details>

<details>
<summary><b>How do I update to a newer ImHex version?</b></summary>

```bash
cd ImHex
git pull origin master
git submodule update --recursive
cd ../build
cmake .. && make -j$(nproc)
```

</details>

---

## 🔗 Related Projects

- **[ImHex](https://github.com/WerWolv/ImHex)** - Feature-rich hex editor by WerWolv
- **[MCP Specification](https://modelcontextprotocol.io/)** - Model Context Protocol by Anthropic
- **[Claude](https://claude.ai/)** - AI assistant with MCP support
- **[Python MCP SDK](https://github.com/modelcontextprotocol/python-sdk)** - Official Python MCP library

---

## 📄 License

**GPL-2.0** - Same as ImHex

This project is a plugin/extension for ImHex and follows its licensing terms. See [LICENSE](LICENSE) for full text.

---

## 🙏 Credits

### Core Projects

- **[ImHex](https://github.com/WerWolv/ImHex)** by [WerWolv](https://github.com/WerWolv) - The amazing hex editor that makes this possible
- **[Model Context Protocol](https://modelcontextprotocol.io/)** by [Anthropic](https://www.anthropic.com/) - The protocol that connects AI to tools
- **[Claude](https://claude.ai/)** by [Anthropic](https://www.anthropic.com/) - AI assistant that uses this integration

### Contributors

- **MCP Integration Team** - This project's implementation
- **Open Source Community** - Bug reports, suggestions, and contributions

### Special Thanks

- WerWolv for creating ImHex and its excellent plugin API
- Anthropic for the MCP specification and Claude
- The reverse engineering community for feedback

---

## 📞 Support & Community

### Get Help

- 📖 **Documentation:** Start with [QUICKSTART.md](docs/QUICKSTART.md)
- 🐛 **Issues:** [GitHub Issues](https://github.com/jmpnop/imhexMCP/issues)
- 💬 **Discussions:** [GitHub Discussions](https://github.com/jmpnop/imhexMCP/discussions)
- 🗨️ **ImHex Discord:** [Join Server](https://discord.gg/X63jZ36xBY)

### Report Issues

When reporting issues, please include:
- ImHex version
- imhexMCP version
- Operating system
- Python version
- Error messages/logs
- Steps to reproduce

---

## 🗺️ Roadmap

### v0.2.5 (Current - Just Completed! 🎉)

- [x] **Automated File Opening** - Fully implemented via plugin architecture patches
- [x] **Cross-Plugin Symbol Sharing** - Builtin plugin exported as shared library
- [x] **Graceful Settings Handling** - Network interface works without full GUI
- [x] **Comprehensive Testing** - 8/8 binary analysis tests passing
- [x] **Clean Patch System** - 6 automated patches with scripts

### v0.3.0 (Completed! 🎉)

**Focus: Enhanced Binary Analysis Capabilities**

- [x] **Multiple File Support** - Open and compare multiple files simultaneously
  - [x] List all open files with metadata (ID, name, size, permissions, active status)
  - [x] Switch between open files/providers
  - [x] Close specific files
  - [x] Compare two files (similarity analysis up to 1MB)

- [x] **Advanced Search** - Pattern and string searching improvements
  - [x] Regex pattern support (via C++ std::regex)
  - [x] Multi-pattern search in single request (up to 20 patterns)
  - [x] Search result pagination with offset/limit (>10,000 matches)
  - [x] Total match count and has_more metadata

- [x] **Data Export** - Extract and export binary data
  - [x] Export regions to files (binary/hex/base64 formats)
  - [x] Export embedded data (up to 100MB)
  - [x] Save search results to CSV/JSON with context bytes

- [x] **Enhanced Bookmarks** - Improve annotation capabilities
  - [x] Programmatic bookmark removal by ID
  - Note: Bookmark listing requires GUI interaction (ImHex API limitation)

### v0.4.0 - Completed! 🎉

**Focus: Advanced Analysis & Automation**

- [x] **Binary Diffing** - Enhanced diff with detailed region analysis
  - [x] `diff/analyze` endpoint with Simple and Myers algorithms
  - [x] Returns up to 10,000 diff regions (match/mismatch/insertion/deletion)
  - [x] Perfect for firmware diff and patch analysis
  - ✅ **Tested and working**

- [x] **Disassembly Integration** - Multi-architecture disassembly via Capstone
  - [x] `disasm/disassemble` endpoint with full instruction details
  - [x] Supports x86, x86-64, ARM, ARM64, MIPS, PowerPC, SPARC, and more
  - [x] Returns mnemonic, operands, bytes, addresses (up to 64KB/1000 instructions)
  - ✅ **Tested and working** (31 instructions disassembled from x86 code)

- [x] **Streaming Large Files** - Chunked reading for files >128MB
  - [x] `data/read_chunked` endpoint with configurable chunk size (default 1MB)
  - [x] Hex and Base64 encoding support
  - [x] Progress tracking (chunk index, total chunks, bytes remaining)
  - ✅ **Tested and working** (50-byte chunks with hex encoding verified)

**Plugin Statistics**
- Total Endpoints: **20** (up from 17 in v0.3.0)
- New in v0.4.0: **3 advanced analysis endpoints**

### v1.0.0 (Long-term - 2025)

**Focus: Production Features & Ecosystem**

- [ ] **Batch Operations** - Automate repetitive tasks
  - Process directory of files
  - Batch pattern extraction
  - Report generation

- [ ] **Enhanced Security** - Production-ready security
  - Optional authentication for network interface
  - Configurable port binding
  - Access control and logging

- [ ] **Integration Improvements** - Better MCP ecosystem integration
  - Support for MCP sampling/resources
  - Cached pattern compilation
  - Background task support

- [ ] **Documentation** - Complete documentation suite
  - Video tutorials
  - Common use case examples
  - Best practices guide
  - API reference improvements

### Community Driven

Have ideas? We'd love to hear them!

- 💡 **Request features** in [GitHub Issues](https://github.com/jmpnop/imhexMCP/issues)
- 💬 **Discuss ideas** in [GitHub Discussions](https://github.com/jmpnop/imhexMCP/discussions)
- 🤝 **Contribute** - See [Contributing](#-contributing) section above
- ⭐ **Star & Watch** to follow development progress

---

## 🎖️ Project Status

- ✅ **Production Ready** - Stable and tested
- 🔄 **Actively Maintained** - Regular updates
- 📈 **Growing** - New features in development
- 🤝 **Community Driven** - Open to contributions

---

<div align="center">

**⭐ Star this repository if you find it useful!**

**Made with ❤️ for the reverse engineering community**

[Report Bug](https://github.com/jmpnop/imhexMCP/issues) · [Request Feature](https://github.com/jmpnop/imhexMCP/issues) · [Documentation](docs/)

---

**Version 0.4.0** | **Last Updated: 2025-11-11** | **Status: ✅ Production Ready**

</div>
