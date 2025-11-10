#!/bin/bash
# ImHex MCP Integration - Patch Application Script
# Applies all patches to ImHex source code to enable automated file opening

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PATCHES_DIR="$SCRIPT_DIR/patches"
IMHEX_DIR="$SCRIPT_DIR/ImHex"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}ImHex MCP Integration - Patch Applicator${NC}"
echo -e "${BLUE}========================================${NC}"
echo

# Check if ImHex directory exists
if [ ! -d "$IMHEX_DIR" ]; then
    echo -e "${RED}Error: ImHex directory not found at: $IMHEX_DIR${NC}"
    echo "Please ensure ImHex source is cloned in the project root."
    exit 1
fi

# Check if patches directory exists
if [ ! -d "$PATCHES_DIR" ]; then
    echo -e "${RED}Error: Patches directory not found at: $PATCHES_DIR${NC}"
    exit 1
fi

# Change to ImHex directory
cd "$IMHEX_DIR"

echo -e "${YELLOW}Checking patch status...${NC}"
echo

# List of patches in order
PATCHES=(
    "01-builtin-library-plugin.patch"
    "02-fileprovider-public-open.patch"
    "03-fileprovider-graceful-settings.patch"
    "04-provider-graceful-settings.patch"
    "05-mcp-plugin-link-builtin.patch"
    "06-mcp-plugin-automated-file-open.patch"
)

# Check if patches are already applied
PATCHES_APPLIED=0
PATCHES_NOT_APPLIED=0

for patch_file in "${PATCHES[@]}"; do
    patch_path="$PATCHES_DIR/$patch_file"

    if [ ! -f "$patch_path" ]; then
        echo -e "${RED}Error: Patch file not found: $patch_file${NC}"
        exit 1
    fi

    # Check if patch is already applied (dry-run in reverse)
    if patch -R -p1 --dry-run -s < "$patch_path" > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} $patch_file - Already applied"
        ((PATCHES_APPLIED++))
    else
        echo -e "${YELLOW}○${NC} $patch_file - Not applied"
        ((PATCHES_NOT_APPLIED++))
    fi
done

echo
echo -e "Status: ${GREEN}${PATCHES_APPLIED} applied${NC}, ${YELLOW}${PATCHES_NOT_APPLIED} pending${NC}"
echo

# If all patches already applied
if [ $PATCHES_NOT_APPLIED -eq 0 ]; then
    echo -e "${GREEN}All patches are already applied!${NC}"
    echo
    echo "To revert patches, run: ./revert-patches.sh"
    exit 0
fi

# Ask for confirmation
echo -e "${YELLOW}Ready to apply $PATCHES_NOT_APPLIED patch(es) to ImHex source.${NC}"
read -p "Continue? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi

echo
echo -e "${BLUE}Applying patches...${NC}"
echo

# Apply each patch
APPLIED_COUNT=0
SKIPPED_COUNT=0
FAILED_COUNT=0

for patch_file in "${PATCHES[@]}"; do
    patch_path="$PATCHES_DIR/$patch_file"

    # Check if already applied
    if patch -R -p1 --dry-run -s < "$patch_path" > /dev/null 2>&1; then
        echo -e "${GREEN}⊘ ${patch_file} - Skipped (already applied)${NC}"
        ((SKIPPED_COUNT++))
        continue
    fi

    # Try to apply patch
    if patch -p1 < "$patch_path"; then
        echo -e "${GREEN}✓ ${patch_file} - Applied successfully${NC}"
        ((APPLIED_COUNT++))
    else
        echo -e "${RED}✗ ${patch_file} - Failed to apply${NC}"
        ((FAILED_COUNT++))
        echo
        echo -e "${RED}Error applying patch!${NC}"
        echo "This may be due to:"
        echo "  - ImHex source has changed (different git commit)"
        echo "  - Patches were partially applied"
        echo "  - Files were manually modified"
        echo
        echo "To revert changes, run: ./revert-patches.sh"
        exit 1
    fi
done

echo
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Patch Application Complete${NC}"
echo -e "${BLUE}========================================${NC}"
echo
echo -e "Applied: ${GREEN}${APPLIED_COUNT}${NC}"
echo -e "Skipped: ${YELLOW}${SKIPPED_COUNT}${NC}"
echo -e "Failed:  ${RED}${FAILED_COUNT}${NC}"
echo

if [ $FAILED_COUNT -eq 0 ]; then
    echo -e "${GREEN}✓ All patches applied successfully!${NC}"
    echo
    echo -e "${YELLOW}Next steps:${NC}"
    echo "1. Clean old build artifacts:"
    echo "   cd ImHex/build"
    echo "   rm -f plugins/builtin.hexplug"
    echo
    echo "2. Rebuild ImHex:"
    echo "   ninja -j\$(sysctl -n hw.ncpu)"
    echo
    echo "3. Start ImHex and enable Network Interface:"
    echo "   ./imhex"
    echo "   Extras → Settings → General → Enable 'Network Interface'"
    echo
    echo "4. Test automated file opening:"
    echo "   cd ../mcp-server"
    echo "   ./venv/bin/python test_binary_analysis.py"
    echo
else
    echo -e "${RED}✗ Some patches failed to apply.${NC}"
    echo "Please resolve the issues and try again."
    exit 1
fi
