# ImHex MCP Integration

<div align="center">
<img width="2912" height="1632" alt="image" src="https://github.com/user-attachments/assets/27efbab1-de5a-42af-a6b8-3c429221e4c7" />


**🔧 AI-Powered Binary Analysis with ImHex**

[![License](https://img.shields.io/badge/license-GPL--2.0-green.svg)](LICENSE)
[![ImHex](https://img.shields.io/badge/ImHex-1.38.0-orange.svg)](https://github.com/WerWolv/ImHex)
[![Version](https://img.shields.io/badge/version-2.0.0-blue.svg)](https://github.com/jmpnop/imhexMCP)
[![Status](https://img.shields.io/badge/status-production%20ready-green.svg)](#)

[![CI](https://github.com/jmpnop/imhexMCP/actions/workflows/ci.yml/badge.svg)](https://github.com/jmpnop/imhexMCP/actions)
[![Tests](https://img.shields.io/badge/tests-255%2F255%20passing-success.svg)](#testing)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.14-blue.svg)](https://www.python.org/)
[![Performance](https://img.shields.io/badge/performance-18%25%20faster-brightgreen.svg)](#performance)

*Model Context Protocol server enabling AI assistants like Claude to analyze binary files programmatically*

**[⚡ Quick Start](#-quick-start)** • **[Features](#-features)** • **[Documentation](docs/)** • **[Testing](#-testing)** • **[Performance](#-performance)**

</div>

---

## 💡 Overview

ImHex MCP provides a **production-ready Python MCP server** that connects AI assistants to [ImHex](https://github.com/WerWolv/ImHex), the powerful hex editor. This enables autonomous binary analysis, malware inspection, firmware analysis, and reverse engineering workflows.

### What's Included

- **🔌 MCP Server** - 40+ tools for binary analysis (Python)
- **📦 ImHex Patches** - 10 patches adding network interface & queue-based file opening
- **⚡ Performance Optimizations** - 18% faster with caching, compression, async operations
- **🧪 Comprehensive Testing** - 255/255 tests passing (100% success rate)
- **📊 Production Features** - Prometheus metrics, circuit breakers, rate limiting
- **📖 Complete Documentation** - API docs, architecture diagrams, guides

---

## 🌟 Features

### Core Capabilities

**File Operations**
- Queue-based async file opening (no manual GUI interaction!)
- Multi-file management (list, switch, close)
- Binary data read/write with multiple encodings

**Analysis Tools**
- Pattern searching (hex, text, regex) with pagination
- Multi-architecture disassembly (x86, ARM, MIPS, etc.)
- Hash calculation (MD5, SHA-1, SHA-256, SHA-384, SHA-512)
- String extraction (ASCII, UTF-16)
- File type detection (30+ magic number signatures)
- Entropy analysis for encryption detection
- Binary diff with Myers algorithm

**Batch Operations**
- Multi-file pattern search
- Batch hashing
- Comparative analysis across files

**Advanced Features**
- Chunked reading for large files (100MB+)
- Data export (binary, hex, base64)
- Bookmark management
- Pattern Language integration

### Python Library Features

**Performance** (17 improvements, 100% complete)
- **18% faster overall** (0.217s → 0.178s)
- **98.9% bandwidth reduction** with zstd compression
- **28% faster cache operations** with orjson + LRU caching
- **25% lock reduction** with optimized critical sections
- **97% faster JSON** serialization

**Production Ready**
- Async/await support with connection pooling
- Response caching with LRU eviction
- Retry logic with exponential backoff
- Circuit breaker pattern
- Prometheus metrics export
- Rate limiting & input validation
- 100% type hints with mypy compliance

---

## 🚀 Quick Start

### Prerequisites

- macOS or Linux
- Python 3.10+ (tested on 3.10, 3.11, 3.12, 3.14)
- CMake 3.25+
- Git
- C++ compiler (GCC 11+ or Clang 14+)

### One-Command Setup

```bash
git clone --recurse-submodules https://github.com/jmpnop/imhexMCP.git
cd imhexMCP
./setup-imhex-mcp.sh
```

This script:
1. Clones ImHex repository
2. Applies all 10 patches automatically
3. Shows build instructions

### Build ImHex

```bash
cd ImHex
mkdir -p build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
cmake --build . -j$(sysctl -n hw.ncpu)  # macOS
# cmake --build . -j$(nproc)            # Linux
```

### Setup MCP Server

```bash
cd ../../mcp-server
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Start ImHex & Enable Network Interface

1. Run ImHex: `./ImHex/build/imhex`
2. Go to **Settings** → **General**
3. Enable **Network Interface**
4. Restart ImHex

Network interface listens on `localhost:31337`

### Configure Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "imhex": {
      "command": "/ABSOLUTE/PATH/TO/imhexMCP/mcp-server/venv/bin/python",
      "args": ["/ABSOLUTE/PATH/TO/imhexMCP/mcp-server/server.py"]
    }
  }
}
```

**Important**: Use absolute paths, not relative!

### Verify Setup

```bash
cd imhexMCP
./verify-setup.sh  # Should show 15/15 passed
```

### Test with Claude

In Claude, ask:
```
Can you check if ImHex is working? Use the imhex_get_capabilities tool.
```

---

## 📖 Key Endpoints

The ImHex MCP plugin provides 28 network endpoints. Here are the most important:

| Endpoint | Description | Example Usage |
|----------|-------------|---------------|
| `file/open` | Queue-based async file opening | Open firmware for analysis |
| `data/read` | Read hex data with encoding options | Extract file headers |
| `data/search` | Pattern search (hex/text/regex) | Find magic numbers |
| `data/hash` | Calculate file hashes | Verify file integrity |
| `data/strings` | Extract ASCII/UTF-16 strings | Find embedded URLs |
| `data/magic` | File type detection | Identify unknown files |
| `data/disassemble` | Multi-arch disassembly | Reverse engineer code |
| `batch/search` | Multi-file pattern search | Malware analysis |
| `batch/hash` | Batch hash calculation | Forensic analysis |
| `data/entropy` | Shannon entropy analysis | Detect encryption |

**Full reference**: See [ENDPOINTS.md](ENDPOINTS.md) for all 28 endpoints with detailed parameters.

---

## 🧪 Testing

### Test Suite

**255 tests, 100% passing** ✅

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=lib --cov=mcp-server --cov-report=term-missing

# Run specific test types
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests (requires ImHex)
pytest -m compression   # Compression tests
```

### Test Organization

Tests are organized with pytest markers:
- `@pytest.mark.unit` - Fast unit tests (no dependencies)
- `@pytest.mark.integration` - Requires running ImHex
- `@pytest.mark.slow` - Tests taking >1 second
- `@pytest.mark.compression` - Compression module tests

### Coverage

Current coverage by module:
- `error_handling.py`: 94%
- `advanced_features.py`: 96%
- `advanced_cache.py`: 92%
- `batching.py`: 90%
- `security.py`: 82%

**Target**: 80%+ coverage for all modules

---

## ⚡ Performance

### Overall Improvements

17/17 optimizations complete (100%)

| Metric | Baseline | Optimized | Improvement |
|--------|----------|-----------|-------------|
| **Total runtime** | 0.217s | 0.178s | **18% faster** |
| **Function calls** | 443,231 | 371,908 | **16% fewer** |
| **Cache operations** | 0.169s | ~0.127s | **28% faster** |
| **JSON serialization** | 0.072s | 0.002s | **97% faster** |
| **Lock overhead** | 24,044 calls | 18,024 | **25% reduction** |

### Key Optimizations

**Round 1**: orjson + LRU Caching + Fast Size Estimation
- orjson for 2-3x faster JSON (24x per call in practice)
- LRU-cached key generation with `@lru_cache(maxsize=1000)`
- Direct length calculations for size estimation

**Round 2**: Compression + Async Lock Optimization
- Compression buffer reuse with `zlib.compressobj()`
- Adaptive compression levels (based on data size)
- CacheEntry creation moved outside critical section
- 25% reduction in time.time() calls under lock

### Compression Performance

- **98.9% bandwidth reduction** with zstd
- **Net benefit**: 227ms saved per 100 requests (@ 100 Mbps)
- **Overhead**: <1ms compression time for most payloads
- **Cache speedup**: 21,670x faster for metadata

**Full details**: See [lib/PERFORMANCE_RESULTS.md](lib/PERFORMANCE_RESULTS.md) and [lib/OPTIMIZATION_RESULTS_ROUND2.md](lib/OPTIMIZATION_RESULTS_ROUND2.md)

---

## 📂 Project Structure

```
imhexMCP/
├── lib/                          # Core Python library (production-ready)
│   ├── async_client.py          # Main async client
│   ├── cache.py                 # Response caching (LRU + orjson)
│   ├── data_compression.py      # Adaptive compression
│   ├── connection_pool.py       # Connection pooling
│   ├── request_batching.py      # Batch operations
│   ├── error_handling.py        # Retry logic & circuit breaker
│   ├── security.py              # Input validation & sanitization
│   ├── metrics.py               # Prometheus metrics
│   └── test_*.py                # Test suite (255 tests)
│
├── mcp-server/                  # MCP server implementation
│   ├── server.py                # Main MCP server (2381 lines)
│   ├── enhanced_client.py       # Enhanced client wrapper
│   ├── imhex_cli.py            # CLI interface
│   └── benchmark_*.py          # Performance benchmarks
│
├── patches/                     # Git patches for ImHex
│   ├── PATCH_MANIFEST.md        # Patch documentation
│   ├── 0001-feat-*.patch        # Queue-based file opening
│   └── 0007-0014-*.patch        # Complete MCP plugin
│
├── ImHex/                       # ImHex submodule (1.38.0.WIP)
│   └── build/imhex             # ImHex binary
│
├── docs/                        # Comprehensive documentation
│   ├── LIBRARY-ARCHITECTURE.md # 15+ Mermaid diagrams
│   ├── API.md                  # API reference
│   └── ...
│
├── CLAUDE.md                    # AI assistant context
├── README.md                    # This file
└── setup-imhex-mcp.sh          # Automated setup script
```

---

## 🏗️ Architecture

```
┌─────────────────────┐
│   User / AI         │  Analyze binaries via Claude
└──────────┬──────────┘
           │ MCP Protocol (stdio)
┌──────────▼──────────┐
│   MCP Server        │  Python server (40+ tools)
│   - Request handling│  • Async operations
│   - Caching         │  • Connection pooling
│   - Compression     │  • Performance optimization
└──────────┬──────────┘
           │ JSON-RPC over TCP
┌──────────▼──────────┐
│   ImHex             │  Hex editor with network interface
│   Network Interface │  • Listens on localhost:31337
└──────────┬──────────┘
           │ Plugin API
┌──────────▼──────────┐
│   MCP Plugin        │  C++ plugin (patched)
│   - File operations │  • Queue-based file opening
│   - Data analysis   │  • 28 network endpoints
│   - Batch ops       │  • Enhanced error handling
└──────────┬──────────┘
           │ ImHex APIs
┌──────────▼──────────┐
│   ImHex Core        │
│   - FileProvider    │
│   - Pattern Engine  │
│   - Crypto Library  │
└─────────────────────┘
```

---

## 📊 Improvements Summary

**Status**: 17/17 complete (100%) 🎉

### Critical Improvements
1. ✅ **Pytest Framework** - Professional test suite (255 tests, 100% passing)
2. ✅ **CI/CD Pipeline** - GitHub Actions (tests, security, lint, benchmarks)
3. ✅ **Type Hints** - 100% mypy compliance
4. ✅ **Python 3.14 Compatibility** - All tests passing
5. ✅ **Test Suite Fixes** - From 86% to 100% pass rate

### Performance & Optimization
6. ✅ **Performance Profiling** - cProfile analysis, bottleneck identification
7. ✅ **Optimization Round 1** - orjson, LRU caching (18% faster)
8. ✅ **Optimization Round 2** - Compression, async locks (25% lock reduction)

### Security & Quality
9. ✅ **Security Hardening** - Rate limiting, input validation, SQL injection prevention
10. ✅ **Code Quality Tools** - Black, flake8, mypy
11. ✅ **Centralized Config** - Pydantic-based validation

### Documentation
12. ✅ **Sphinx API Documentation** - 100% module coverage (21 modules)
13. ✅ **Architecture Diagrams** - 15+ Mermaid diagrams
14. ✅ **Property-Based Testing** - Hypothesis integration
15. ✅ **Prometheus Metrics** - Production monitoring

**Full details**: See [IMPROVEMENTS-SUMMARY.md](IMPROVEMENTS-SUMMARY.md)

---

## 💻 Platform Support

### Tested Platforms
- ✅ **macOS ARM64** (Apple Silicon) - Native build
- ✅ **macOS x86_64** (Intel) - Full support

### Should Work (Untested)
- ⚠️ **Linux x86_64** - Standard ImHex build process
- ⚠️ **Windows** - Via MSYS2/MinGW64

---

## 🤝 Contributing

We welcome contributions!

### Areas for Help
- 🐛 Bug fixes and issue reports
- 📝 Documentation improvements
- 🧪 Testing on different platforms
- ✨ New features and endpoints

### Contribution Workflow

1. Fork this repository
2. Clone ImHex and apply patches
3. Make your changes
4. Run tests: `pytest`
5. Generate new patches: `git format-patch origin/master..HEAD`
6. Submit PR with updated patches

---

## 📄 Documentation

| Document | Description |
|----------|-------------|
| **[CLAUDE.md](CLAUDE.md)** | Complete project context for AI assistants |
| **[patches/PATCH_MANIFEST.md](patches/PATCH_MANIFEST.md)** | Patch documentation and application order |
| **[docs/LIBRARY-ARCHITECTURE.md](docs/LIBRARY-ARCHITECTURE.md)** | Architecture diagrams and design |
| **[lib/PERFORMANCE_RESULTS.md](lib/PERFORMANCE_RESULTS.md)** | Performance optimization results |
| **[TESTING.md](TESTING.md)** | Testing guide and best practices |
| **[docs/SECURITY.md](docs/SECURITY.md)** | Security guidelines |
| **[docs/API.md](docs/API.md)** | API reference |

---

## 🔗 Related Projects

- **[ImHex](https://github.com/WerWolv/ImHex)** - Feature-rich hex editor by WerWolv
- **[MCP Specification](https://modelcontextprotocol.io/)** - Model Context Protocol by Anthropic
- **[Claude](https://claude.ai/)** - AI assistant with MCP support

---

## 📞 Support

### Get Help
- 📖 **Documentation**: Start with [CLAUDE.md](CLAUDE.md)
- 🐛 **Issues**: [GitHub Issues](https://github.com/jmpnop/imhexMCP/issues)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/jmpnop/imhexMCP/discussions)

### Report Issues

Please include:
- ImHex commit hash
- Operating system and architecture
- Python version
- Error messages
- Steps to reproduce

---

## 📄 License

**GPL-2.0** - Same as ImHex

This project provides a Model Context Protocol server and patches for ImHex, following its licensing terms. See [LICENSE](LICENSE) for full text.

---

## 🙏 Credits

- **[ImHex](https://github.com/WerWolv/ImHex)** by [WerWolv](https://github.com/WerWolv) - The amazing hex editor
- **[Model Context Protocol](https://modelcontextprotocol.io/)** by [Anthropic](https://www.anthropic.com/) - Protocol specification
- The reverse engineering community for feedback and testing

---

<div align="center">

**⭐ Star this repository if you find it useful!**

**Made with ❤️ for the reverse engineering community**

[Report Bug](https://github.com/jmpnop/imhexMCP/issues) · [Request Feature](https://github.com/jmpnop/imhexMCP/issues) · [Documentation](docs/)

---

**Version 2.0.0** | **Last Updated: 2025-11-15** | **Status: ✅ Production Ready**

</div>
