#!/bin/bash
# ImHex MCP Integration - Setup Verification Script
# Verifies that the system is correctly configured and working

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
IMHEX_DIR="$SCRIPT_DIR/ImHex"
MCP_SERVER_DIR="$SCRIPT_DIR/mcp-server"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}ImHex MCP Integration - Setup Verifier${NC}"
echo -e "${BLUE}========================================${NC}"
echo

# Track pass/fail counts
CHECKS_PASSED=0
CHECKS_FAILED=0
WARNINGS=0

# Function to check something
check() {
    local description="$1"
    local command="$2"

    echo -ne "Checking $description... "

    if eval "$command" > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC}"
        ((CHECKS_PASSED++))
        return 0
    else
        echo -e "${RED}✗${NC}"
        ((CHECKS_FAILED++))
        return 1
    fi
}

# Function to warn about something
warn() {
    local message="$1"
    echo -e "${YELLOW}⚠ Warning: $message${NC}"
    ((WARNINGS++))
}

echo -e "${BLUE}[1/5] Checking Repository Structure${NC}"
echo

check "ImHex directory exists" "[ -d '$IMHEX_DIR' ]"
check "MCP server directory exists" "[ -d '$MCP_SERVER_DIR' ]"
check "Patches directory exists" "[ -d '$SCRIPT_DIR/patches' ]"
check "Apply patches script exists" "[ -f '$SCRIPT_DIR/apply-patches.sh' ]"
check "Revert patches script exists" "[ -f '$SCRIPT_DIR/revert-patches.sh' ]"

echo
echo -e "${BLUE}[2/5] Checking ImHex Build${NC}"
echo

check "ImHex build directory exists" "[ -d '$IMHEX_DIR/build' ]"
check "ImHex binary exists" "[ -f '$IMHEX_DIR/build/imhex' ]"
check "Builtin library plugin exists" "[ -f '$IMHEX_DIR/build/plugins/builtin.hexpluglib' ]"
check "MCP plugin exists" "[ -f '$IMHEX_DIR/build/plugins/mcp.hexplug' ]"

# Check for old builtin.hexplug (should NOT exist)
if [ -f "$IMHEX_DIR/build/plugins/builtin.hexplug" ]; then
    warn "Old builtin.hexplug file exists - this may cause crashes!"
    echo "  Run: rm $IMHEX_DIR/build/plugins/builtin.hexplug"
fi

echo
echo -e "${BLUE}[3/5] Checking MCP Server${NC}"
echo

check "Python venv exists" "[ -d '$MCP_SERVER_DIR/venv' ]"
check "Python executable in venv" "[ -f '$MCP_SERVER_DIR/venv/bin/python' ]"
check "MCP server script exists" "[ -f '$MCP_SERVER_DIR/server.py' ]"
check "Test script exists" "[ -f '$MCP_SERVER_DIR/test_binary_analysis.py' ]"

echo
echo -e "${BLUE}[4/5] Checking ImHex Process${NC}"
echo

if pgrep -f "imhex" > /dev/null; then
    echo -e "${GREEN}✓${NC} ImHex is running"
    ((CHECKS_PASSED++))
else
    echo -e "${YELLOW}○${NC} ImHex is not running"
    warn "ImHex must be running with Network Interface enabled for testing"
fi

echo
echo -e "${BLUE}[5/5] Checking Network Interface${NC}"
echo

# Check if ImHex is listening on port 31337
if command -v lsof > /dev/null 2>&1; then
    if lsof -i :31337 | grep -q imhex; then
        echo -e "${GREEN}✓${NC} Network interface is listening on port 31337"
        ((CHECKS_PASSED++))
    else
        echo -e "${YELLOW}○${NC} Network Interface not detected on port 31337"
        warn "Enable Network Interface in ImHex: Extras → Settings → General"
    fi
else
    echo -e "${YELLOW}○${NC} lsof command not available, skipping network test"
fi

echo
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Verification Results${NC}"
echo -e "${BLUE}========================================${NC}"
echo

echo -e "Passed:   ${GREEN}${CHECKS_PASSED}${NC}"
echo -e "Failed:   ${RED}${CHECKS_FAILED}${NC}"
echo -e "Warnings: ${YELLOW}${WARNINGS}${NC}"

echo

if [ $CHECKS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ Setup verification passed!${NC}"
    echo
    echo -e "${YELLOW}Next steps:${NC}"
    echo "1. If ImHex is not running, start it:"
    echo "   cd $IMHEX_DIR/build"
    echo "   ./imhex"
    echo
    echo "2. Enable Network Interface (if not already enabled):"
    echo "   Extras → Settings → General → Network Interface → Enable"
    echo "   Restart ImHex after enabling"
    echo
    echo "3. Run comprehensive tests:"
    echo "   cd $MCP_SERVER_DIR"
    echo "   ./venv/bin/python test_binary_analysis.py"
    echo
    echo "4. Configure Claude Desktop (if not already done):"
    echo "   Edit: ~/Library/Application Support/Claude/claude_desktop_config.json"
    echo "   Add MCP server configuration (see README.md)"
    echo
    exit 0
else
    echo -e "${RED}✗ Setup verification failed!${NC}"
    echo
    echo "Please fix the issues above and try again."
    echo "See README.md and patches/README.md for detailed setup instructions."
    echo
    exit 1
fi
