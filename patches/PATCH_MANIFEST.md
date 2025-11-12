# ImHex MCP Plugin Patches

This directory contains all patches needed to modify [WerWolv/ImHex](https://github.com/WerWolv/ImHex) to support the MCP (Model Context Protocol) plugin.

## Patch Application Order

Apply patches in numerical order:

### Core ImHex Modifications (01-06)

These patches modify ImHex core to enable the MCP plugin:

1. **01-builtin-library-plugin.patch** (214 bytes)
   - Enables builtin plugin library support

2. **02-fileprovider-public-open.patch** (640 bytes)
   - Makes FileProvider::open() method public

3. **03-fileprovider-graceful-settings.patch** (2.1 KB)
   - Adds graceful settings handling to FileProvider

4. **04-provider-graceful-settings.patch** (891 bytes)
   - Adds graceful settings handling to Provider base class

5. **05-mcp-plugin-link-builtin.patch** (272 bytes)
   - Links MCP plugin with builtin libraries

6. **06-mcp-plugin-automated-file-open.patch** (3.4 KB)
   - Enables automated file opening in MCP plugin

### MCP Plugin Evolution (0001-0014)

These patches implement the complete MCP plugin with all features:

#### Foundation & File Operations (0001-0002, 0007)

**0007-fix-Replace-RequestOpenFile-event-based-approach-wit.patch** (61 KB)
- Replaces event-based file opening with direct FileProvider approach
- Initial implementation of MCP network interface
- **Files modified:**
  - `cmake/build_helpers.cmake` - Build system support
  - `lib/libimhex/source/providers/provider.cpp` - Provider modifications
  - `plugins/builtin/CMakeLists.txt` - Builtin plugin integration
  - `plugins/builtin/include/content/providers/file_provider.hpp` - FileProvider header
  - `plugins/builtin/source/content/providers/file_provider.cpp` - FileProvider implementation
  - `plugins/mcp/CMakeLists.txt` - MCP plugin build configuration
  - `plugins/mcp/source/plugin_mcp.cpp` - **CREATES FULL MCP PLUGIN** (~2500 lines)

**0008-fix-Improve-disassembly-and-diff-error-handling.patch** (6.8 KB)
- Enhanced error handling for disassembly operations
- Improved diff analysis error reporting

**0009-fix-Implement-TaskManager-based-diff-analysis-ALL-v0.patch** (5.6 KB)
- Implements TaskManager for asynchronous diff operations
- ALL v0.4.0 TESTS PASSING milestone

#### Batch Operations (0010-0014)

**0010-feat-Add-batch-open_directory-endpoint-v1.0.0-Phase-.patch** (11 KB)
- Adds `batch/open_directory` endpoint
- v1.0.0 Phase 1 milestone

**0011-Add-batch-search-endpoint-for-v1.0.0-Phase-2.patch** (8.4 KB)
- Adds `batch/search` endpoint for pattern searching

**0012-Add-batch-hash-endpoint-for-v1.0.0-Phase-2.patch** (7.1 KB)
- Adds `batch/hash` endpoint for computing hashes

**0013-Fix-glob-pattern-matching-in-batch-open_directory.patch** (2.1 KB)
- Fixes glob pattern matching issues

**0014-Fix-glob-pattern-escaping-bug-in-batch-open_director.patch** (2.9 KB)
- Fixes glob pattern escaping bug

#### Queue-Based File Opening (0001-0002)

**0001-feat-Implement-queue-based-file-opening-to-fix-netwo.patch** (91 KB)
- Implements event-based request queue for file opening
- Fixes "Connection reset by peer" errors
- Adds `file/open` and `file/open/status` endpoints
- Uses EventFrameEnd for main-thread queue processing

**0002-improvement-Add-detailed-error-logging-to-file-open-.patch** (9.5 KB)
- Captures FileProvider::getErrorMessage() for detailed diagnostics
- Improves error reporting for file open failures

## Application Instructions

### Fresh ImHex Clone

```bash
# Clone ImHex
git clone https://github.com/WerWolv/ImHex.git
cd ImHex

# Apply core modifications
git apply /path/to/patches/01-builtin-library-plugin.patch
git apply /path/to/patches/02-fileprovider-public-open.patch
git apply /path/to/patches/03-fileprovider-graceful-settings.patch
git apply /path/to/patches/04-provider-graceful-settings.patch
git apply /path/to/patches/05-mcp-plugin-link-builtin.patch
git apply /path/to/patches/06-mcp-plugin-automated-file-open.patch

# Apply MCP plugin implementation
git apply /path/to/patches/0007-fix-Replace-RequestOpenFile-event-based-approach-wit.patch
git apply /path/to/patches/0008-fix-Improve-disassembly-and-diff-error-handling.patch
git apply /path/to/patches/0009-fix-Implement-TaskManager-based-diff-analysis-ALL-v0.patch
git apply /path/to/patches/0010-feat-Add-batch-open_directory-endpoint-v1.0.0-Phase-.patch
git apply /path/to/patches/0011-Add-batch-search-endpoint-for-v1.0.0-Phase-2.patch
git apply /path/to/patches/0012-Add-batch-hash-endpoint-for-v1.0.0-Phase-2.patch
git apply /path/to/patches/0013-Fix-glob-pattern-matching-in-batch-open_directory.patch
git apply /path/to/patches/0014-Fix-glob-pattern-escaping-bug-in-batch-open_director.patch
git apply /path/to/patches/0001-feat-Implement-queue-based-file-opening-to-fix-netwo.patch
git apply /path/to/patches/0002-improvement-Add-detailed-error-logging-to-file-open-.patch

# Build
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
cmake --build .
```

## Complete Feature Set

After applying all patches, ImHex will have:

### Network Interface Endpoints

#### File Operations
- `file/open` - Queue-based file opening (async)
- `file/open/status` - Check file open progress
- `file/list` - List open files
- `file/close` - Close file by provider ID

#### Data Operations  
- `data/read` - Read bytes from file
- `data/write` - Write bytes to file
- `data/strings` - Extract strings from file
- `data/magic` - File type identification
- `data/disassemble` - Disassemble binary code
- `data/hash` - Compute hashes

#### Batch Operations
- `batch/open_directory` - Open multiple files by glob pattern
- `batch/search` - Search patterns across files
- `batch/hash` - Compute hashes for multiple files
- `batch/diff` - Compare files

#### Analysis Operations
- `analysis/entropy` - Calculate entropy
- `analysis/diff` - Compare two providers
- `capabilities` - List available endpoints

## Tested Against

- **ImHex Version:** Nightly build (commit b1e218596)
- **Date:** November 11, 2025
- **Platform:** macOS (Darwin 25.0.0)
- **Architecture:** ARM64 (Apple Silicon)

## Known Working Status

All endpoints tested and working:
- Connection reset issue: **RESOLVED**
- Queue-based file opening: **WORKING**
- Batch operations: **WORKING**
- Diff analysis: **WORKING**
- All v1.0.0 tests: **PASSING**

## Maintenance

These patches are maintained as part of the imhexMCP project:
- **Project:** https://github.com/jmpnop/imhexMCP
- **Approach:** Patch-based (do not push modified ImHex)
- **Updates:** Regenerate patches after upstream ImHex changes

## Notes

1. The patches modify ImHex core minimally - most changes are in the MCP plugin itself
2. Patch 0007 creates the complete MCP plugin from scratch (~2500 lines)
3. Apply patches in order - later patches depend on earlier ones
4. Test after each major patch group (01-06, then 0007-0014, then 0001-0002)
