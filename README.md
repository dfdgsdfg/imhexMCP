# ImHex MCP Integration
<img width="2912" height="1632" alt="image" src="https://github.com/user-attachments/assets/76df84b3-b91e-4a6e-8971-96893213ea6c" />

<div align="center">

**🤖 AI-Powered Binary Analysis for ImHex**

[![License](https://img.shields.io/badge/license-GPL--2.0-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![ImHex](https://img.shields.io/badge/ImHex-1.35%2B-orange.svg)](https://github.com/WerWolv/ImHex)
[![MCP](https://img.shields.io/badge/MCP-1.0+-purple.svg)](https://modelcontextprotocol.io/)
[![Version](https://img.shields.io/badge/version-0.2.0-blue.svg)](CHANGELOG.md)

*Enable AI assistants like Claude to perform advanced binary file analysis through ImHex*

[Quick Start](#-quick-start) • [Features](#-features) • [Documentation](#-documentation) • [Examples](#-usage-examples) • [Contributing](#-contributing)

</div>

---

## 🌟 Highlights

- ✨ **11 MCP Tools** - Complete binary analysis toolkit for AI assistants
- 🚀 **Lightning Fast** - Enhanced connection management with retry logic
- 🔍 **Deep Inspection** - 24+ data type interpretations (int, float, ASCII, binary, etc.)
- 🔐 **Secure Hashing** - MD5, SHA-1, SHA-224, SHA-256, SHA-384, SHA-512
- 📝 **Smart Search** - Find up to 10,000 pattern matches instantly
- 🎨 **Visual Bookmarks** - AI-driven code annotation and highlighting
- 🧩 **Pattern Language** - AI generates ImHex patterns for binary parsing
- ⚡ **Data Decoding** - Base64, ASCII, binary, hex encoding support
- 🧪 **Fully Tested** - Comprehensive unit tests with mock server
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

Ask Claude:
```
Can you check if ImHex is working? Use the capabilities tool.
```

You should see ImHex version and available commands! 🎉

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
│   ├── server.py                     # Original server (470 lines)
│   ├── server_improved.py            # Enhanced server (850 lines)
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
│       ├── plugin_mcp.cpp            # Original (548 lines)
│       └── plugin_mcp_improved.cpp   # Enhanced (950 lines)
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
| [QUICKSTART.md](docs/QUICKSTART.md) | Get started in 5 minutes |
| [BUILD_MCP.md](docs/BUILD_MCP.md) | Detailed build instructions & troubleshooting |
| [IMPROVEMENTS.md](docs/IMPROVEMENTS.md) | What's new in v0.2.0 |
| [CHANGELOG.md](docs/CHANGELOG.md) | Complete version history |
| [ARCHITECTURE.md](mcp-server/ARCHITECTURE.md) | Technical deep dive |
| [API Reference](mcp-server/README.md) | MCP tools & endpoints |

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
python server_improved.py --debug --log-file debug.log
```

### Code Quality

```bash
# Install dev dependencies
pip install -r mcp-server/requirements-dev.txt

# Format Python code
black mcp-server/

# Type check
mypy mcp-server/server_improved.py

# Lint
pylint mcp-server/server_improved.py
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

| imhexMCP | ImHex | Python | MCP | Status |
|----------|-------|--------|-----|--------|
| **0.2.0** | 1.35+ | 3.10+ | 1.0+ | ✅ Current |
| 0.1.0 | 1.35+ | 3.10+ | 1.0+ | ⚠️ Legacy |

---

## 📈 Statistics

| Metric | Count | Notes |
|--------|-------|-------|
| **Repository Size** | 476 KB | 99.9% smaller than full ImHex |
| **Code Lines** | 6,353 | MCP integration only |
| **Documentation** | 3,500+ | Comprehensive guides |
| **Test Lines** | 400+ | Unit & integration tests |
| **MCP Tools** | 11 | For AI assistants |
| **Network Endpoints** | 9 | Plugin APIs |
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

### v0.3.0 (Next Release)

- [ ] **Regex Search** - Full regex pattern support
- [ ] **Streaming** - Handle files larger than 10MB
- [ ] **Disassembly** - Complete Capstone integration
- [ ] **Compression** - Support for compressed data
- [ ] **More Encodings** - URL, Base32, Punycode, etc.

### v0.4.0 (Future)

- [ ] **Pattern Templates** - Pre-built patterns for common formats
- [ ] **Diff Mode** - Compare two binary files
- [ ] **Scripting** - Python scripting API
- [ ] **Visualization** - Export charts and graphs

### v1.0.0 (Long-term)

- [ ] **Multi-file Operations** - Work with multiple files
- [ ] **Real-time Monitoring** - Watch file changes
- [ ] **Authentication** - Secure remote access
- [ ] **REST API** - Alternative to MCP
- [ ] **Web Interface** - Browser-based access

Vote on features in [GitHub Discussions](https://github.com/jmpnop/imhexMCP/discussions)!

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

**Version 0.2.0** | **Last Updated: 2025-11-08** | **Status: ✅ Production Ready**

</div>
