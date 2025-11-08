# Building ImHex with MCP Support

This guide explains how to build ImHex with the MCP plugin and set up the complete MCP integration.

## Prerequisites

### System Requirements

**All Platforms:**
- GCC or LLVM Clang with C++23 support (MSVC and AppleClang are NOT supported)
- CMake 3.25 or higher
- Python 3.10+ (for MCP server)
- Git

**Platform-Specific:**

**Linux:**
```bash
# Ubuntu/Debian
sudo apt install build-essential cmake git python3 python3-pip \
    libglfw3-dev libmbedtls-dev libfreetype-dev libmagic-dev

# Fedora
sudo dnf install gcc gcc-c++ cmake git python3 python3-pip \
    glfw-devel mbedtls-devel freetype-devel file-devel
```

**macOS:**
```bash
# Install Homebrew if not already installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install dependencies
brew install cmake llvm python3 glfw mbedtls freetype libmagic
```

**Windows:**
- Install MSYS2 from https://www.msys2.org/
- Use MSYS2 MinGW64 terminal:
```bash
pacman -S mingw-w64-x86_64-gcc mingw-w64-x86_64-cmake \
    mingw-w64-x86_64-glfw mingw-w64-x86_64-mbedtls \
    mingw-w64-x86_64-freetype git python3
```

## Building ImHex with MCP Plugin

### Step 1: Clone and Initialize

```bash
cd /path/to/your/projects
git clone --recurse-submodules https://github.com/WerWolv/ImHex
cd ImHex

# If you already cloned without --recurse-submodules:
git submodule update --init --recursive
```

### Step 2: Copy MCP Plugin

If you have the MCP plugin files separately:

```bash
# From your ImHex directory
cp -r /path/to/plugins/mcp ./plugins/
```

Or if following this repository structure, the plugin should already be in `plugins/mcp/`.

### Step 3: Configure Build

```bash
mkdir build
cd build

# Configure with CMake
cmake .. \
    -DCMAKE_BUILD_TYPE=Release \
    -DIMHEX_OFFLINE_BUILD=OFF \
    -DIMHEX_ENABLE_UNIT_TESTS=OFF

# On macOS with Homebrew LLVM:
cmake .. \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_C_COMPILER=/usr/local/opt/llvm/bin/clang \
    -DCMAKE_CXX_COMPILER=/usr/local/opt/llvm/bin/clang++ \
    -DIMHEX_OFFLINE_BUILD=OFF
```

### Step 4: Build

```bash
# Build ImHex and all plugins
cmake --build . -j$(nproc)

# Or use make directly
make -j$(nproc)
```

Build time varies:
- First build: 10-30 minutes depending on CPU
- Subsequent builds: 1-5 minutes

### Step 5: Install (Optional)

```bash
# Install to system directories (requires sudo/admin)
sudo cmake --install .

# Or install to custom location
cmake --install . --prefix=/path/to/install
```

## Verifying the Build

### Check Plugin Built Successfully

```bash
# From build directory
ls -la plugins/

# You should see libmcp.so (Linux), libmcp.dylib (macOS), or mcp.dll (Windows)
```

### Run ImHex

```bash
# From build directory
./imhex

# Or if installed:
imhex
```

### Verify MCP Plugin Loaded

1. Launch ImHex
2. Check console output for: `MCP plugin loaded - registered 8 network endpoints`
3. Go to Edit → Settings → General
4. Enable "Network Interface"
5. Restart ImHex
6. Plugin endpoints should now be active on port 31337

### Test Network Interface

```bash
# Test capabilities endpoint
echo '{"endpoint":"imhex/capabilities","data":{}}' | nc localhost 31337

# You should see output including MCP endpoints like:
# - file/open
# - data/read
# - data/write
# - data/inspect
# - bookmark/add
# - hash/calculate
# - search/find
# - provider/info
```

## Setting Up the MCP Server

### Step 1: Install Python Dependencies

```bash
cd mcp_server
pip install -r requirements.txt
```

Or install as a package:

```bash
cd mcp_server
pip install -e .
```

### Step 2: Test MCP Server Connection

```bash
# Make sure ImHex is running with Network Interface enabled
python test_server.py
```

Expected output:
```
Testing connection to ImHex at localhost:31337...
✓ Connected to ImHex successfully
✓ ImHex is responding correctly
✓ All tests passed!
```

### Step 3: Configure Claude Code

Edit your Claude Code MCP configuration:

**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`

**Linux:** `~/.config/Claude/claude_desktop_config.json`

**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

Add:

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

**Important:** Use absolute paths!

### Step 4: Restart Claude Code

Completely quit and restart Claude Code/Claude Desktop.

## Troubleshooting Build Issues

### CMake Configuration Fails

**Problem:** CMake can't find dependencies

**Solution:**
```bash
# Clear CMake cache
rm -rf build
mkdir build
cd build

# Try with verbose output
cmake .. -DCMAKE_VERBOSE_MAKEFILE=ON
```

### Compiler Not Supported

**Problem:** "MSVC is not supported" or "AppleClang is not supported"

**Solution:**
- **macOS:** Install and use LLVM Clang via Homebrew
  ```bash
  brew install llvm
  export CC=/usr/local/opt/llvm/bin/clang
  export CXX=/usr/local/opt/llvm/bin/clang++
  ```

- **Windows:** Use MSYS2 MinGW64 GCC (not Visual Studio)

### Build Errors in MCP Plugin

**Problem:** Compilation errors in `plugin_mcp.cpp`

**Solutions:**

1. **Missing headers:** Ensure you're using the latest ImHex source
   ```bash
   git pull
   git submodule update --init --recursive
   ```

2. **API changes:** If using a different ImHex version, the API might have changed. Check ImHex version compatibility:
   ```bash
   git log --oneline -1
   # Plugin developed for ImHex v1.38.0.WIP
   ```

3. **Check build log:** Look for specific missing functions/types and check ImHex API documentation

### Plugin Not Loading

**Problem:** ImHex starts but MCP plugin not listed

**Solution:**

1. Check plugin was built:
   ```bash
   ls build/plugins/ | grep mcp
   ```

2. Check ImHex log for plugin load errors:
   ```bash
   # Launch from terminal to see output
   ./build/imhex
   # Look for "MCP plugin loaded" message
   ```

3. Verify plugin installation location:
   ```bash
   # Find where ImHex looks for plugins
   ./build/imhex --version
   ```

### Network Interface Not Working

**Problem:** Can't connect to port 31337

**Solutions:**

1. **Enable in Settings:**
   - Edit → Settings → General → Network Interface
   - Enable checkbox
   - Restart ImHex

2. **Check port is listening:**
   ```bash
   # Linux/macOS
   netstat -an | grep 31337
   lsof -i :31337

   # Windows (in PowerShell)
   netstat -an | findstr 31337
   ```

3. **Firewall blocking:**
   - Add firewall exception for ImHex
   - Or temporarily disable firewall for testing

4. **Port already in use:**
   ```bash
   # Find what's using the port
   lsof -i :31337  # Linux/macOS
   ```

## Development Build (Debug)

For development and debugging:

```bash
mkdir build-debug
cd build-debug

cmake .. \
    -DCMAKE_BUILD_TYPE=Debug \
    -DIMHEX_ENABLE_UNIT_TESTS=ON

make -j$(nproc)
```

Debug build includes:
- Debug symbols
- Assertions enabled
- More verbose logging
- Slower but easier to debug

## Advanced Build Options

### Static Linking

```bash
cmake .. \
    -DCMAKE_BUILD_TYPE=Release \
    -DIMHEX_STATIC_LINK_PLUGINS=ON
```

### Custom Plugin Directory

```bash
cmake .. \
    -DIMHEX_PLUGINS_IN_SHARE=OFF \
    -DIMHEX_PLUGINS_IN_APPLICATION_DIR=ON
```

### Unity Build (Faster Compilation)

```bash
cmake .. \
    -DCMAKE_BUILD_TYPE=Release \
    -DIMHEX_USE_UNITY_BUILD=ON
```

### Cross-Compilation

See ImHex's main documentation for cross-compilation instructions.

## Keeping Up to Date

### Update ImHex

```bash
cd ImHex
git pull
git submodule update --init --recursive

cd build
cmake ..
make -j$(nproc)
```

### Update MCP Plugin

If you update the plugin code:

```bash
cd build
make -j$(nproc)

# Just rebuild the plugin (faster)
make mcp -j$(nproc)
```

## Performance Optimization

### Build with LTO (Link-Time Optimization)

```bash
cmake .. \
    -DCMAKE_BUILD_TYPE=Release \
    -DIMHEX_ENABLE_LTO=ON

make -j$(nproc)
```

### Native CPU Optimization

```bash
cmake .. \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_CXX_FLAGS="-march=native"

make -j$(nproc)
```

## Next Steps

After successful build:

1. **Test the integration:** Follow the [QUICKSTART.md](mcp_server/QUICKSTART.md)
2. **Read the documentation:** See [mcp_server/README.md](mcp_server/README.md)
3. **Try example patterns:** Check [mcp_server/examples/](mcp_server/examples/)
4. **Explore the architecture:** Read [mcp_server/ARCHITECTURE.md](mcp_server/ARCHITECTURE.md)

## Getting Help

- **ImHex Issues:** https://github.com/WerWolv/ImHex/issues
- **ImHex Discord:** https://discord.gg/X63jZ36xBY
- **Build Problems:** Check ImHex's documentation at https://docs.werwolv.net/

## References

- [ImHex GitHub](https://github.com/WerWolv/ImHex)
- [ImHex Documentation](https://docs.werwolv.net/)
- [CMake Documentation](https://cmake.org/documentation/)
