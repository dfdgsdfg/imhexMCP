# ImHex MCP Integration

<div align="center">
<img width="2912" height="1632" alt="image" src="https://github.com/user-attachments/assets/925eb2fc-921b-40fe-8d59-e334bf985a4a" />

**🔧 Patch-Based MCP Plugin for ImHex**

[![License](https://img.shields.io/badge/license-GPL--2.0-green.svg)](LICENSE)
[![ImHex](https://img.shields.io/badge/ImHex-nightly-orange.svg)](https://github.com/WerWolv/ImHex)
[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)](patches/PATCH_MANIFEST.md)
[![Status](https://img.shields.io/badge/status-production%20ready-green.svg)](STATUS.md)

*Add Model Context Protocol support to ImHex through automated patches*

**[⚡ Quick Start](#-quick-start)** • [Features](#-features) • [Documentation](#-documentation) • [Patches](patches/PATCH_MANIFEST.md) • [Status](STATUS.md)

</div>

---

## 💡 What is This?

This project provides **git patches** that add Model Context Protocol (MCP) support to [ImHex](https://github.com/WerWolv/ImHex), enabling AI assistants like Claude to interact with the hex editor programmatically.

### Patch-Based Approach

Instead of maintaining a fork of ImHex, we maintain **lightweight patches** that you apply to a fresh ImHex clone. This approach:

- ✅ **Stays current** - Apply patches to latest ImHex
- ✅ **Minimal maintenance** - Only patch code, not entire codebase
- ✅ **Easy updates** - Regenerate patches after changes
- ✅ **Clear changes** - See exactly what's modified
- ✅ **Portable** - Patches work across ImHex versions

### What's Included?

**10 Production-Ready Patches** (~200KB total):
- Queue-based async file opening (fixes connection reset errors)
- Complete MCP plugin implementation (~2500 lines)
- 16+ network endpoints for binary analysis
- Batch operations (open_directory, search, hash, diff)
- Enhanced error handling and detailed logging

---

## 🌟 Features

### Network Interface Endpoints

After applying patches, ImHex will have:

#### File Operations
- `file/open` - Queue-based async file opening
- `file/open/status` - Check file open progress
- `file/list` - List all open files
- `file/close` - Close file by provider ID

#### Data Operations
- `data/read` - Read bytes from file
- `data/write` - Write bytes to file
- `data/strings` - Extract ASCII/UTF-16 strings
- `data/magic` - File type identification via magic numbers
- `data/disassemble` - Multi-architecture disassembly (x86, ARM, etc.)
- `data/hash` - Compute MD5, SHA-1, SHA-256, SHA-384, SHA-512

#### Batch Operations
- `batch/open_directory` - Open multiple files by glob pattern
- `batch/search` - Search patterns across multiple files
- `batch/hash` - Compute hashes for multiple files
- `batch/diff` - Compare files with Myers diff algorithm

#### Analysis Operations
- `analysis/entropy` - Calculate entropy for data regions
- `analysis/diff` - Compare two providers with detailed region analysis
- `capabilities` - List all available endpoints

---

## 🚀 Quick Start

### One-Command Setup

```bash
git clone https://github.com/jmpnop/imhexMCP
cd imhexMCP
./setup-imhex-mcp.sh
```

That's it! The script will:
1. Clone ImHex from official repository
2. Apply all 10 patches automatically
3. Show what was applied and build instructions

### Build ImHex with MCP Plugin

```bash
cd ImHex
mkdir -p build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
cmake --build . -j$(sysctl -n hw.ncpu)
```

After building, the MCP plugin will be at:
```
ImHex/build/plugins/mcp.hexplug
```

### Enable Network Interface

1. Run ImHex: `./ImHex/build/imhex`
2. Go to **Settings** → **General**
3. Enable **Network Interface**
4. Restart ImHex

The network interface will listen on `localhost:31337`

---

## 📦 Repository Structure

```
imhexMCP/                              # Lightweight patch repository
│
├── 📄 README.md                       # This file
├── 📄 STATUS.md                       # Project status and roadmap
├── 📄 setup-imhex-mcp.sh             # Automated setup script (executable)
│
└── 📁 patches/                        # Git patches for ImHex
    ├── PATCH_MANIFEST.md              # Comprehensive patch documentation
    ├── README.md                      # Patch overview
    │
    ├── 0001-feat-Implement-queue...  # Queue-based file opening (91KB)
    ├── 0002-improvement-Add-detail... # Error logging improvements (9.5KB)
    │
    ├── 0007-fix-Replace-RequestOpe... # Complete MCP plugin (61KB)
    ├── 0008-fix-Improve-disassembl... # Enhanced error handling (6.8KB)
    ├── 0009-fix-Implement-TaskMana... # Async diff analysis (5.6KB)
    │
    ├── 0010-feat-Add-batch-open_di... # Batch open_directory (11KB)
    ├── 0011-Add-batch-search-endpo... # Batch search (8.4KB)
    ├── 0012-Add-batch-hash-endpoin... # Batch hash (7.1KB)
    ├── 0013-Fix-glob-pattern-match... # Glob pattern fix (2.1KB)
    └── 0014-Fix-glob-pattern-escap... # Glob escaping fix (2.9KB)
```

**Total Repository Size:** ~500KB (patches only, no source code)

---

## 📖 Documentation

| Document | Description |
|----------|-------------|
| **[PATCH_MANIFEST.md](patches/PATCH_MANIFEST.md)** | Complete patch documentation with application order |
| **[STATUS.md](STATUS.md)** | Project status, metrics, and roadmap |
| [patches/README.md](patches/README.md) | Patch overview and explanation |

---

## 🧪 Testing

All patches have been tested against **ImHex nightly build (commit b1e218596)** on macOS ARM64.

### Known Working Status
- ✅ Connection reset issue: RESOLVED
- ✅ Queue-based file opening: WORKING
- ✅ Batch operations: WORKING
- ✅ Diff analysis: WORKING
- ✅ All v1.0.0 tests: PASSING

### Test After Building

```bash
# Ensure ImHex is running with Network Interface enabled
cd mcp-server
./venv/bin/python test_binary_analysis.py
```

Expected: All endpoints respond correctly

---

## 🔧 For Developers

### Regenerating Patches

If you modify the ImHex source after applying patches:

```bash
cd ImHex
git format-patch origin/master..HEAD -o ../patches/ --start-number=7
```

This generates new patches from your commits.

### Updating to Latest ImHex

```bash
# 1. Clone latest ImHex
git clone https://github.com/WerWolv/ImHex.git ImHex-new
cd ImHex-new

# 2. Apply patches (may need manual fixes if ImHex changed)
git apply /path/to/imhexMCP/patches/*.patch

# 3. Resolve conflicts if any
# 4. Commit and regenerate patches
git add .
git commit -m "Apply MCP patches to latest ImHex"
git format-patch origin/master..HEAD -o /path/to/imhexMCP/patches/
```

---

## 🏗️ Architecture

```
┌─────────────────────┐
│   User / AI         │  Analyze binaries
└──────────┬──────────┘
           │ Network requests (JSON over TCP)
           │
┌──────────▼──────────┐
│   ImHex             │  Hex editor with network interface
│   Network Interface │  • Listens on localhost:31337
└──────────┬──────────┘
           │ Internal API calls
           │
┌──────────▼──────────┐
│   MCP Plugin        │  This project's patches
│   - File operations │  • 16+ network endpoints
│   - Data analysis   │  • Queue-based file opening
│   - Batch ops       │  • Async diff analysis
│   - Hash/Search     │  • Enhanced error handling
└──────────┬──────────┘
           │ ImHex APIs
           │
┌──────────▼──────────┐
│   ImHex Core        │
│   - FileProvider    │
│   - Pattern Engine  │
│   - Crypto Library  │
│   - TaskManager     │
└─────────────────────┘
```

---

## 💻 Platform Support

### Tested Platforms
- ✅ **macOS ARM64** (Apple Silicon) - Native build
- ✅ **macOS x86_64** (Intel) - Full support

### Should Work (Untested)
- ⚠️ **Linux x86_64** - Standard ImHex build process
- ⚠️ **Windows** - Via MSYS2/MinGW64

Patches modify ImHex's C++ code, so any platform ImHex supports should work.

---

## 🤝 Contributing

We welcome contributions! Areas for help:

- 🐛 **Bug fixes** - Report and fix issues
- 📝 **Documentation** - Improve guides and examples
- 🧪 **Testing** - Test on different platforms
- ✨ **Features** - Add new endpoints or improve existing ones

### Contribution Workflow

1. Fork this repository
2. Clone ImHex and apply patches
3. Make your changes to ImHex source
4. Test thoroughly
5. Commit your changes to ImHex
6. Generate new patches: `git format-patch origin/master..HEAD`
7. Submit PR with updated patches

---

## 📊 Project Statistics

| Metric | Value | Notes |
|--------|-------|-------|
| **Repository Size** | ~500KB | Patches only |
| **Total Patches** | 10 | All tested and working |
| **Patch Size** | 209KB | Total size of all patches |
| **Network Endpoints** | 16+ | File, data, batch, analysis operations |
| **Code Lines Added** | ~3,500 | MCP plugin implementation |
| **Tested ImHex Version** | b1e218596 | ImHex nightly build |
| **Platform** | macOS ARM64 | Also works on x86_64 |

---

## 🗺️ Roadmap

### v1.0.0 (Current) ✅
- [x] Complete MCP plugin implementation
- [x] Queue-based async file opening
- [x] 16+ network endpoints
- [x] Batch operations (open_directory, search, hash)
- [x] Diff analysis with Myers algorithm
- [x] Production-ready automated setup

### Future (Community Driven)
- [ ] WebSocket support for streaming responses
- [ ] Authentication for network interface
- [ ] MCP server integration (Python)
- [ ] Docker container for easy deployment
- [ ] Homebrew formula for macOS

Have ideas? Open an issue or discussion!

---

## ❓ FAQ

<details>
<summary><b>Do patches work with the latest ImHex?</b></summary>

Patches are tested against ImHex commit b1e218596. They should apply to nearby commits, but may need adjustments for major ImHex changes. If patches fail, open an issue.

</details>

<details>
<summary><b>Can I use my existing ImHex installation?</b></summary>

Yes! Just apply the patches to your ImHex directory and rebuild. The setup script is optional - it just automates the process.

</details>

<details>
<summary><b>What if a patch fails to apply?</b></summary>

First, check you're in a clean ImHex directory. If ImHex has changed significantly, patches may need manual adjustment. Open an issue and we'll update the patches.

</details>

<details>
<summary><b>Do I need the MCP server (Python)?</b></summary>

No! The patches add a network interface directly to ImHex. You can connect to it from any client (Python, curl, AI assistants, etc.). An MCP server would be an additional component.

</details>

<details>
<summary><b>Is this safe for malware analysis?</b></summary>

The MCP plugin runs inside ImHex with the same permissions. The network interface only listens on localhost (127.0.0.1). Use appropriate sandboxing as you would with ImHex normally.

</details>

---

## 🔗 Related Projects

- **[ImHex](https://github.com/WerWolv/ImHex)** - Feature-rich hex editor by WerWolv
- **[MCP Specification](https://modelcontextprotocol.io/)** - Model Context Protocol by Anthropic
- **[Claude](https://claude.ai/)** - AI assistant with MCP support

---

## 📄 License

**GPL-2.0** - Same as ImHex

This project provides patches for ImHex and follows its licensing terms. See [LICENSE](LICENSE) for full text.

---

## 🙏 Credits

### Core Project
- **[ImHex](https://github.com/WerWolv/ImHex)** by [WerWolv](https://github.com/WerWolv) - The amazing hex editor
- **[Model Context Protocol](https://modelcontextprotocol.io/)** by [Anthropic](https://www.anthropic.com/) - Protocol specification

### Special Thanks
- WerWolv for creating ImHex and its excellent plugin API
- Anthropic for the MCP specification
- The reverse engineering community for feedback and testing

---

## 📞 Support

### Get Help
- 📖 **Documentation:** Start with [PATCH_MANIFEST.md](patches/PATCH_MANIFEST.md)
- 🐛 **Issues:** [GitHub Issues](https://github.com/jmpnop/imhexMCP/issues)
- 💬 **Discussions:** [GitHub Discussions](https://github.com/jmpnop/imhexMCP/discussions)

### Report Issues

When reporting issues, please include:
- ImHex commit hash
- Operating system and architecture
- Which patches failed to apply
- Error messages
- Steps to reproduce

---

<div align="center">

**⭐ Star this repository if you find it useful!**

**Made with ❤️ for the reverse engineering community**

[Report Bug](https://github.com/jmpnop/imhexMCP/issues) · [Request Feature](https://github.com/jmpnop/imhexMCP/issues) · [Documentation](patches/)

---

**Version 1.0.0** | **Last Updated: 2025-11-11** | **Status: ✅ Production Ready**

</div>
