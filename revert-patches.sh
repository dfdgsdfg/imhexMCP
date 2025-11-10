#!/bin/bash
# ImHex MCP Integration - Patch Reversion Script
# Reverts all patches from ImHex source code

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
echo -e "${BLUE}ImHex MCP Integration - Patch Reverter${NC}"
echo -e "${BLUE}========================================${NC}"
echo

# Check if ImHex directory exists
if [ ! -d "$IMHEX_DIR" ]; then
    echo -e "${RED}Error: ImHex directory not found at: $IMHEX_DIR${NC}"
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

# List of patches in REVERSE order for reverting
PATCHES=(
    "06-mcp-plugin-automated-file-open.patch"
    "05-mcp-plugin-link-builtin.patch"
    "04-provider-graceful-settings.patch"
    "03-fileprovider-graceful-settings.patch"
    "02-fileprovider-public-open.patch"
    "01-builtin-library-plugin.patch"
)

# Check which patches are applied
PATCHES_APPLIED=0
PATCHES_NOT_APPLIED=0

for patch_file in "${PATCHES[@]}"; do
    patch_path="$PATCHES_DIR/$patch_file"

    if [ ! -f "$patch_path" ]; then
        echo -e "${RED}Error: Patch file not found: $patch_file${NC}"
        exit 1
    fi

    # Check if patch is applied (can be reversed)
    if patch -R -p1 --dry-run -s < "$patch_path" > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} $patch_file - Applied (can revert)"
        ((PATCHES_APPLIED++))
    else
        echo -e "${YELLOW}○${NC} $patch_file - Not applied"
        ((PATCHES_NOT_APPLIED++))
    fi
done

echo
echo -e "Status: ${GREEN}${PATCHES_APPLIED} applied${NC}, ${YELLOW}${PATCHES_NOT_APPLIED} not applied${NC}"
echo

# If no patches applied
if [ $PATCHES_APPLIED -eq 0 ]; then
    echo -e "${GREEN}No patches to revert!${NC}"
    exit 0
fi

# Ask for confirmation
echo -e "${YELLOW}Ready to revert $PATCHES_APPLIED patch(es) from ImHex source.${NC}"
echo -e "${RED}Warning: This will restore the original ImHex code.${NC}"
read -p "Continue? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi

echo
echo -e "${BLUE}Reverting patches...${NC}"
echo

# Revert each patch
REVERTED_COUNT=0
SKIPPED_COUNT=0
FAILED_COUNT=0

for patch_file in "${PATCHES[@]}"; do
    patch_path="$PATCHES_DIR/$patch_file"

    # Check if patch is applied
    if ! patch -R -p1 --dry-run -s < "$patch_path" > /dev/null 2>&1; then
        echo -e "${YELLOW}⊘ ${patch_file} - Skipped (not applied)${NC}"
        ((SKIPPED_COUNT++))
        continue
    fi

    # Try to revert patch
    if patch -R -p1 < "$patch_path"; then
        echo -e "${GREEN}✓ ${patch_file} - Reverted successfully${NC}"
        ((REVERTED_COUNT++))
    else
        echo -e "${RED}✗ ${patch_file} - Failed to revert${NC}"
        ((FAILED_COUNT++))
        echo
        echo -e "${RED}Error reverting patch!${NC}"
        echo "Manual intervention may be required."
        exit 1
    fi
done

echo
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Patch Reversion Complete${NC}"
echo -e "${BLUE}========================================${NC}"
echo
echo -e "Reverted: ${GREEN}${REVERTED_COUNT}${NC}"
echo -e "Skipped:  ${YELLOW}${SKIPPED_COUNT}${NC}"
echo -e "Failed:   ${RED}${FAILED_COUNT}${NC}"
echo

if [ $FAILED_COUNT -eq 0 ]; then
    echo -e "${GREEN}✓ All patches reverted successfully!${NC}"
    echo
    echo -e "${YELLOW}Next steps:${NC}"
    echo "1. Rebuild ImHex to use original code:"
    echo "   cd ImHex/build"
    echo "   ninja -j\$(sysctl -n hw.ncpu)"
    echo
    echo "2. Note: Automated file opening will NOT work without patches"
    echo "   Files must be opened manually in ImHex GUI"
    echo
else
    echo -e "${RED}✗ Some patches failed to revert.${NC}"
    echo "Please resolve the issues manually."
    exit 1
fi
