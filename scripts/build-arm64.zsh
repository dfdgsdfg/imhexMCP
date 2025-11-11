#!/bin/zsh
#
# ARM64 Native Build Script for ImHex with MCP Plugin
#
# This script builds ImHex natively for Apple Silicon (ARM64) without Rosetta 2.
# It ensures all dependencies are ARM64 from /opt/homebrew.
#

set -e  # Exit on error

echo "🚀 Building ImHex for ARM64 (Apple Silicon)"
echo "==========================================="
echo ""

# Check if running on macOS
if [[ "$(uname)" != "Darwin" ]]; then
    echo "❌ Error: This script is for macOS only"
    exit 1
fi

# Check if running on Apple Silicon
ARCH=$(uname -m)
if [[ "$ARCH" != "arm64" ]]; then
    echo "⚠️  Warning: You appear to be running on $ARCH, not ARM64"
    echo "   This script builds for ARM64 architecture"
    read "?Continue anyway? (y/N) " response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Verify Homebrew ARM64 installation
if [[ ! -d "/opt/homebrew" ]]; then
    echo "❌ Error: ARM64 Homebrew not found at /opt/homebrew"
    echo "   Please install Homebrew for Apple Silicon:"
    echo "   /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
    exit 1
fi

echo "✓ ARM64 Homebrew found at /opt/homebrew"
echo ""

# Install ARM64 dependencies
echo "📦 Installing ARM64 dependencies..."
DEPS=(cmake ninja llvm capstone yara libmagic libssh2)

for dep in "${DEPS[@]}"; do
    if /opt/homebrew/bin/brew list --formula | grep -q "^${dep}\$"; then
        echo "  ✓ $dep (already installed)"
    else
        echo "  Installing $dep..."
        /opt/homebrew/bin/brew install "$dep"
    fi
done

echo ""
echo "📂 Preparing build directory..."

# Get script directory and repository root
SCRIPT_DIR="${0:a:h}"
REPO_ROOT="${SCRIPT_DIR:h}"
IMHEX_DIR="$REPO_ROOT/ImHex"
BUILD_DIR="$IMHEX_DIR/build"
PLUGIN_SRC="$REPO_ROOT/plugin/source/plugin_mcp.cpp"

# Verify ImHex submodule
if [[ ! -d "$IMHEX_DIR/.git" ]]; then
    echo "❌ Error: ImHex submodule not initialized"
    echo "   Run: git submodule update --init --recursive"
    exit 1
fi

# Clean and create build directory
if [[ -d "$BUILD_DIR" ]]; then
    echo "  Cleaning existing build directory..."
    rm -rf "$BUILD_DIR"
fi

mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"

echo ""
echo "⚙️  Configuring CMake for ARM64..."
echo "  Architecture: arm64"
echo "  Build type: Release"
echo "  Prefix path: /opt/homebrew"
echo ""

# Configure CMake with ARM64-specific flags
/opt/homebrew/bin/cmake -G Ninja \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_OSX_ARCHITECTURES=arm64 \
    -DCMAKE_PREFIX_PATH=/opt/homebrew \
    -DCMAKE_IGNORE_PATH=/usr/local \
    -DCMAKE_LIBRARY_PATH=/opt/homebrew/lib \
    -DLIBSSH2_LIBRARY=/opt/homebrew/lib/libssh2.dylib \
    -DLIBSSH2_INCLUDE_DIR=/opt/homebrew/include \
    ..

if [[ $? -ne 0 ]]; then
    echo "❌ CMake configuration failed"
    exit 1
fi

echo ""
echo "📋 Copying MCP plugin source..."

# Copy plugin source to build location
PLUGIN_DST="$IMHEX_DIR/plugins/mcp/source/plugin_mcp.cpp"
if [[ ! -f "$PLUGIN_SRC" ]]; then
    echo "❌ Error: Plugin source not found at $PLUGIN_SRC"
    exit 1
fi

cp "$PLUGIN_SRC" "$PLUGIN_DST"
echo "  ✓ Copied to $PLUGIN_DST"

echo ""
echo "🔨 Building ImHex (ARM64)..."
echo "  Using $(sysctl -n hw.ncpu) cores"
echo ""

# Build with all available cores
/opt/homebrew/bin/ninja -j$(sysctl -n hw.ncpu)

if [[ $? -ne 0 ]]; then
    echo ""
    echo "❌ Build failed"
    exit 1
fi

echo ""
echo "✅ Build successful!"
echo ""
echo "🔍 Verifying ARM64 architecture..."

# Verify architecture
IMHEX_BIN="$BUILD_DIR/imhex"
MCP_PLUGIN="$BUILD_DIR/plugins/mcp.hexplug"

if [[ ! -f "$IMHEX_BIN" ]]; then
    echo "❌ Error: ImHex binary not found at $IMHEX_BIN"
    exit 1
fi

IMHEX_ARCH=$(file "$IMHEX_BIN" | grep -o "arm64")
if [[ "$IMHEX_ARCH" == "arm64" ]]; then
    echo "  ✓ ImHex binary: ARM64"
else
    echo "  ❌ ImHex binary is NOT ARM64!"
    file "$IMHEX_BIN"
    exit 1
fi

if [[ -f "$MCP_PLUGIN" ]]; then
    PLUGIN_ARCH=$(file "$MCP_PLUGIN" | grep -o "arm64")
    if [[ "$PLUGIN_ARCH" == "arm64" ]]; then
        echo "  ✓ MCP plugin: ARM64"
    else
        echo "  ❌ MCP plugin is NOT ARM64!"
        file "$MCP_PLUGIN"
        exit 1
    fi
else
    echo "  ⚠️  Warning: MCP plugin not found at $MCP_PLUGIN"
fi

# Count ARM64 plugins
PLUGIN_COUNT=$(file "$BUILD_DIR/plugins/"*.hexplug 2>/dev/null | grep -c "arm64" || echo "0")
TOTAL_PLUGINS=$(ls "$BUILD_DIR/plugins/"*.hexplug 2>/dev/null | wc -l | tr -d ' ')

echo "  ✓ All plugins: $PLUGIN_COUNT/$TOTAL_PLUGINS are ARM64"

echo ""
echo "==========================================="
echo "✨ ARM64 Build Complete!"
echo "==========================================="
echo ""
echo "Binary location: $IMHEX_BIN"
echo "Architecture: ARM64 (native Apple Silicon)"
echo "No Rosetta 2 required!"
echo ""
echo "To run ImHex:"
echo "  cd $BUILD_DIR"
echo "  ./imhex"
echo ""
echo "Note: Enable Network Interface in ImHex settings"
echo "      (Extras → Settings → General → Network Interface)"
echo ""
