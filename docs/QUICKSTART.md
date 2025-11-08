# Quick Start Guide

Get ImHex MCP integration running in 5 minutes!

## Prerequisites

- Git
- Python 3.10+
- CMake 3.25+
- C++ compiler (GCC or Clang with C++23)

## Installation

### 1. Clone Repository

```bash
git clone --recurse-submodules https://github.com/jmpnop/imhexMCP
cd imhexMCP
```

**Note:** The `--recurse-submodules` flag is important! It downloads ImHex as a submodule.

### 2. Run Setup

```bash
./scripts/setup.sh
```

This will:
- Initialize ImHex submodule
- Build ImHex with MCP plugin
- Install MCP server
- Configure Claude Desktop

### 3. Enable Network Interface in ImHex

1. Launch ImHex: `./ImHex/build/imhex`
2. Go to: **Edit → Settings → General**
3. Enable: **Network Interface**
4. Restart ImHex

### 4. Restart Claude Desktop

Completely quit and restart Claude Desktop.

## Verify Setup

Ask Claude:

```
Can you check if ImHex is working? Use the capabilities tool.
```

Claude should respond with ImHex version and available commands!

## Next Steps

- See [README.md](../README.md) for features
- See [API.md](API.md) for tool reference
- See [BUILD.md](BUILD.md) for advanced build options

## Troubleshooting

### Submodule not initialized

```bash
git submodule update --init --recursive
```

### Build fails

See [BUILD.md](BUILD.md) for detailed build instructions and troubleshooting.

### Can't connect to ImHex

```bash
cd mcp-server
python test_connection.py
```

See error messages for specific issues.
