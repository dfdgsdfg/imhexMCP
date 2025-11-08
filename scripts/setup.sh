#!/bin/bash
# Complete setup script for ImHex MCP Integration
set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
print_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }

echo "======================================"
echo "ImHex MCP Integration - Complete Setup"
echo "======================================"
echo

# Step 1: Build ImHex with plugin
print_info "Step 1: Building ImHex with MCP plugin"
./scripts/build.sh

# Step 2: Install MCP server
print_info ""
print_info "Step 2: Installing MCP server"
cd mcp-server
./install.sh
cd ..

echo
echo "======================================"
print_info "Setup complete!"
echo "======================================"
echo
print_info "Next steps:"
echo "  1. Run ImHex: ./ImHex/build/imhex"
echo "  2. Enable Network Interface in ImHex"
echo "  3. Restart Claude Desktop"
echo "  4. Test by asking Claude about ImHex capabilities"
echo
