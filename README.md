# ImHex MCP Integration

**Model Context Protocol (MCP) server for ImHex - AI-powered binary analysis**

[![License](https://img.shields.io/badge/license-GPL--2.0-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![ImHex](https://img.shields.io/badge/ImHex-1.35%2B-orange.svg)](https://github.com/WerWolv/ImHex)

This project adds Model Context Protocol support to [ImHex](https://github.com/WerWolv/ImHex), enabling AI assistants like Claude to perform advanced binary file analysis.

## 🚀 Quick Start

### Prerequisites

- **ImHex** 1.35.0 or later
- **Python** 3.10+
- **Git**

### Installation

```bash
# 1. Clone this repository
git clone --recurse-submodules https://github.com/jmpnop/imhexMCP
cd imhexMCP

# 2. Build ImHex with MCP plugin
./scripts/build.sh

# 3. Install MCP server
cd mcp-server
./install.sh

# Done! Now configure Claude Desktop (see below)
```

## 📋 What's Included

This repository contains **only** the MCP integration components:

```
imhexMCP/
├── mcp-server/              # Python MCP server
│   ├── server.py           # MCP protocol implementation
│   ├── install.sh          # Installation script
│   └── tests/              # Unit tests
├── plugin/                  # ImHex C++ plugin
│   ├── CMakeLists.txt      # Build configuration
│   └── source/             # Plugin source code
├── scripts/                 # Build and setup scripts
│   ├── build.sh            # Build ImHex + plugin
│   └── setup.sh            # Complete setup
├── docs/                    # Documentation
│   ├── QUICKSTART.md
│   ├── BUILD.md
│   └── API.md
└── ImHex/                   # Git submodule → WerWolv/ImHex
```

**ImHex source code is NOT included** - it's referenced as a git submodule.

## ✨ Features

### MCP Server (Python)
- 11 MCP tools for binary analysis
- Enhanced error handling with retry logic
- CLI arguments for configuration
- Full type hints and tests

### ImHex Plugin (C++)
- 9 network endpoints
- File operations (open, read, write)
- Data inspection (24+ type interpretations)
- Hash calculation (MD5, SHA-1, SHA-256, SHA-384, SHA-512)
- Pattern search (10,000 matches)
- Data decoding (Base64, ASCII, binary, hex)
- Bookmark management

### AI Integration
- Works with Claude Code and Claude Desktop
- Pattern language generation
- Intelligent binary analysis
- Automated reverse engineering

## 🏗️ Architecture

```
┌─────────────┐
│   Claude    │  AI Assistant
└──────┬──────┘
       │ MCP Protocol (stdio)
┌──────▼──────┐
│ MCP Server  │  This project (Python)
└──────┬──────┘
       │ TCP (port 31337)
┌──────▼──────┐
│   ImHex     │  WerWolv/ImHex (git submodule)
│ + MCP Plugin│  + This project's plugin
└─────────────┘
```

## 📦 Installation Options

### Option 1: Automated (Recommended)

```bash
# Clone with submodules
git clone --recurse-submodules https://github.com/jmpnop/imhexMCP
cd imhexMCP

# Run setup script
./scripts/setup.sh
```

This will:
1. Initialize ImHex submodule
2. Build ImHex with MCP plugin
3. Install MCP server
4. Configure Claude Desktop

### Option 2: Manual

```bash
# Clone repository
git clone https://github.com/jmpnop/imhexMCP
cd imhexMCP

# Initialize ImHex submodule
git submodule update --init --recursive

# Build ImHex with plugin
cd ImHex
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
make -j$(nproc)
cd ../..

# Copy plugin to ImHex
cp -r plugin ImHex/plugins/mcp

# Rebuild with plugin
cd ImHex/build
make -j$(nproc)
cd ../..

# Install MCP server
cd mcp-server
pip install -r requirements.txt
./install.sh
```

### Option 3: Use Existing ImHex

If you already have ImHex installed:

```bash
# Clone this repository
git clone https://github.com/jmpnop/imhexMCP
cd imhexMCP

# Copy plugin to your ImHex installation
cp -r plugin /path/to/ImHex/plugins/mcp

# Rebuild ImHex
cd /path/to/ImHex/build
make mcp -j$(nproc)

# Install MCP server
cd /path/to/imhexMCP/mcp-server
./install.sh
```

## ⚙️ Configuration

### Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS):

```json
{
  "mcpServers": {
    "imhex": {
      "command": "python",
      "args": ["/full/path/to/imhexMCP/mcp-server/server.py"]
    }
  }
}
```

### ImHex

1. Launch ImHex
2. Go to: **Edit → Settings → General**
3. Enable: **Network Interface**
4. Restart ImHex

## 🎯 Usage Examples

### Example 1: Analyze Binary File

```
User: Open firmware.bin and analyze its structure

Claude will:
- Open the file in ImHex
- Read and inspect the header
- Calculate SHA256 hash
- Identify file type
- Report findings
```

### Example 2: Parse with Pattern Language

```
User: Parse this PE executable

Claude will:
- Write ImHex pattern language for PE format
- Execute the pattern
- Extract headers and sections
- Display parsed structure
```

### Example 3: Search and Bookmark

```
User: Find all PNG signatures and bookmark them

Claude will:
- Search for 89504E47 (PNG magic)
- Add bookmarks at each location
- Report offsets found
```

## 📖 Documentation

- **[QUICKSTART.md](docs/QUICKSTART.md)** - 5-minute setup guide
- **[BUILD.md](docs/BUILD.md)** - Detailed build instructions
- **[API.md](docs/API.md)** - MCP tools and endpoints reference
- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** - Technical architecture
- **[CONTRIBUTING.md](docs/CONTRIBUTING.md)** - How to contribute

## 🧪 Testing

```bash
# Run MCP server tests
cd mcp-server
pytest tests/ -v

# Test connection to ImHex
python test_connection.py
```

## 🛠️ Development

### Project Structure

```
imhexMCP/               # This repository
├── mcp-server/        # MCP server (Python)
├── plugin/            # ImHex plugin (C++)
├── scripts/           # Build/setup scripts
├── docs/              # Documentation
├── tests/             # Integration tests
└── ImHex/            # Git submodule → WerWolv/ImHex

ImHex/                 # External dependency (submodule)
└── [ImHex source]    # Not stored in this repo
```

### Building Plugin Only

```bash
# After ImHex is built
cd ImHex/build
make mcp -j$(nproc)
```

### Running Tests

```bash
# Unit tests
cd mcp-server
pytest tests/

# Integration tests
cd tests
./run_integration_tests.sh
```

## 🤝 Contributing

Contributions welcome! Please:

1. Fork this repository
2. Create a feature branch
3. Make changes (plugin or server)
4. Add tests
5. Submit pull request

See [CONTRIBUTING.md](docs/CONTRIBUTING.md) for details.

## 📊 Version Compatibility

| imhexMCP | ImHex | Python |
|----------|-------|--------|
| 0.2.x    | 1.35+ | 3.10+  |
| 0.1.x    | 1.35+ | 3.10+  |

## 🔗 Related Projects

- **[ImHex](https://github.com/WerWolv/ImHex)** - The amazing hex editor
- **[MCP Specification](https://modelcontextprotocol.io/)** - Protocol specification
- **[Claude](https://claude.ai/)** - AI assistant

## 📄 License

GPL-2.0 - Same as ImHex

This project is a plugin/extension for ImHex and follows its licensing.

## 🙏 Credits

- **[ImHex](https://github.com/WerWolv/ImHex)** by WerWolv - The hex editor
- **[Model Context Protocol](https://modelcontextprotocol.io/)** by Anthropic
- Contributors to this MCP integration

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/jmpnop/imhexMCP/issues)
- **Discussions**: [GitHub Discussions](https://github.com/jmpnop/imhexMCP/discussions)
- **ImHex Discord**: [Join](https://discord.gg/X63jZ36xBY)

## 🗺️ Roadmap

### v0.3.0 (Next)
- [ ] Regex search support
- [ ] Streaming for large files
- [ ] Full disassembly integration
- [ ] Compression support

### v1.0.0 (Future)
- [ ] Multi-file operations
- [ ] Real-time monitoring
- [ ] Visualization export
- [ ] Authentication support

---

**Version:** 0.2.0
**Status:** ✅ Production Ready
**Last Updated:** 2025-11-08

Made with ❤️ for the reverse engineering community
