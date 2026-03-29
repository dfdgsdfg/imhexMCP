#!/usr/bin/env bash
set -e

echo "=================================="
echo "ImHex MCP Setup Script"
echo "=================================="

# Configuration
IMHEX_REPO="https://github.com/WerWolv/ImHex.git"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PATCHES_DIR="$SCRIPT_DIR/patches"
IMHEX_DIR="${1:-$SCRIPT_DIR/ImHex}"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo_success() { echo -e "${GREEN}✓${NC} $1"; }
echo_error() { echo -e "${RED}✗${NC} $1"; }
echo_info() { echo -e "${YELLOW}➜${NC} $1"; }

# Check if ImHex directory exists
if [ -d "$IMHEX_DIR" ]; then
    echo_info "ImHex directory already exists at: $IMHEX_DIR"
    read -p "Do you want to remove and re-clone? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo_info "Removing existing directory..."
        rm -rf "$IMHEX_DIR"
    else
        echo_info "Using existing directory"
    fi
fi

# Clone ImHex if needed
if [ ! -d "$IMHEX_DIR" ]; then
    echo_info "Cloning ImHex from $IMHEX_REPO..."
    git clone "$IMHEX_REPO" "$IMHEX_DIR"
    echo_success "Cloned ImHex"
fi

cd "$IMHEX_DIR"

# Show current commit
CURRENT_COMMIT=$(git rev-parse --short HEAD)
echo_info "Current ImHex commit: $CURRENT_COMMIT"

# Apply patches in order
echo ""
echo "=================================="
echo "Applying Patches"
echo "=================================="

# Array of patches in order
PATCHES=(
    "0007-fix-Replace-RequestOpenFile-event-based-approach-wit.patch"
    "0008-fix-Improve-disassembly-and-diff-error-handling.patch"
    "0009-fix-Implement-TaskManager-based-diff-analysis-ALL-v0.patch"
    "0010-feat-Add-batch-open_directory-endpoint-v1.0.0-Phase-.patch"
    "0011-Add-batch-search-endpoint-for-v1.0.0-Phase-2.patch"
    "0012-Add-batch-hash-endpoint-for-v1.0.0-Phase-2.patch"
    "0013-Fix-glob-pattern-matching-in-batch-open_directory.patch"
    "0014-Fix-glob-pattern-escaping-bug-in-batch-open_director.patch"
    "0001-feat-Implement-queue-based-file-opening-to-fix-netwo.patch"
    "0002-improvement-Add-detailed-error-logging-to-file-open-.patch"
)

APPLIED=0
FAILED=0

for patch in "${PATCHES[@]}"; do
    PATCH_PATH="$PATCHES_DIR/$patch"
    
    if [ ! -f "$PATCH_PATH" ]; then
        echo_error "Patch not found: $patch"
        FAILED=$((FAILED + 1))
        continue
    fi
    
    echo_info "Applying: $patch"
    if git apply --check "$PATCH_PATH" 2>/dev/null; then
        git apply "$PATCH_PATH"
        echo_success "Applied: $patch"
        APPLIED=$((APPLIED + 1))
    else
        echo_error "Failed to apply: $patch"
        echo "  Try manual application or check if ImHex version changed"
        FAILED=$((FAILED + 1))
    fi
done

echo ""
echo "=================================="
echo "Patch Application Summary"
echo "=================================="
echo_success "Applied: $APPLIED patches"
if [ $FAILED -gt 0 ]; then
    echo_error "Failed: $FAILED patches"
fi

# Set up MCP server Python environment with uv
echo ""
echo "=================================="
echo "Setting up MCP Server (uv)"
echo "=================================="

MCP_SERVER_DIR="$SCRIPT_DIR/mcp-server"

if ! command -v uv &>/dev/null; then
    echo_error "uv not found. Install it with: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

echo_info "Creating virtual environment..."
uv venv "$MCP_SERVER_DIR/.venv"
echo_info "Installing dependencies..."
uv pip install --python "$MCP_SERVER_DIR/.venv/bin/python" -r "$MCP_SERVER_DIR/requirements.txt"
echo_success "MCP server environment ready"

# Build instructions
echo ""
echo "=================================="
echo "Next Steps"
echo "=================================="
echo ""
echo "To build ImHex with MCP plugin:"
echo ""
echo "  cd $IMHEX_DIR"
echo "  mkdir -p build && cd build"
echo "  cmake .. -DCMAKE_BUILD_TYPE=Release"
echo "  cmake --build . -j\$(sysctl -n hw.ncpu)"
echo ""
echo "After building, the MCP plugin will be at:"
echo "  $IMHEX_DIR/build/plugins/mcp.hexplug"
echo ""
echo "To test the MCP plugin:"
echo "  1. Run ImHex: $IMHEX_DIR/build/imhex"
echo "  2. Enable Network Interface in Settings"
echo "  3. Run test: cd $MCP_SERVER_DIR && ./.venv/bin/python test_binary_analysis.py"
echo ""

if [ $FAILED -eq 0 ]; then
    echo_success "Setup complete! All patches applied successfully."
    exit 0
else
    echo_error "Setup completed with errors. Please review failed patches."
    exit 1
fi
