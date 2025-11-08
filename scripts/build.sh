#!/bin/bash
# Build ImHex with MCP Plugin
set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
print_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }

print_info "Building ImHex with MCP Plugin"
echo "================================"

# Check if ImHex submodule exists
if [ ! -d "ImHex/.git" ]; then
    print_warn "ImHex submodule not initialized"
    print_info "Initializing submodule..."
    git submodule update --init --recursive
fi

# Copy plugin into ImHex
print_info "Copying MCP plugin into ImHex..."
rm -rf ImHex/plugins/mcp
cp -r plugin ImHex/plugins/mcp

# Create build directory
print_info "Creating build directory..."
mkdir -p ImHex/build
cd ImHex/build

# Configure CMake
print_info "Configuring CMake..."
cmake .. \
    -DCMAKE_BUILD_TYPE=Release \
    -DIMHEX_OFFLINE_BUILD=OFF

# Build
print_info "Building ImHex (this may take 10-30 minutes)..."
CORES=$(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 4)
print_info "Using $CORES cores..."

cmake --build . -j"$CORES"

cd ../..

print_info "Build complete!"
print_info "ImHex binary: ImHex/build/imhex"
print_info ""
print_info "Next steps:"
echo "  1. Run ImHex: ./ImHex/build/imhex"
echo "  2. Enable Network Interface (Settings → General)"
echo "  3. Install MCP server: cd mcp-server && ./install.sh"
