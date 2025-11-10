# ImHex MCP Integration - Patch Files

This directory contains patch files that modify ImHex source code to enable automated file opening via the MCP network interface.

## Why These Patches Are Needed

### The Problem
ImHex plugins are **isolated shared libraries** by design. Each plugin (`.hexplug`) cannot access symbols from other plugins. The `FileProvider` class that handles file opening lives in the `builtin` plugin, making it impossible for the `mcp` plugin to programmatically open files.

**Without patches**: Users must manually click "File → Open" in ImHex for every file analysis, completely breaking AI automation.

**With patches**: Claude AI can open files automatically via MCP, enabling true autonomous binary analysis.

### The Solution
The patches modify ImHex's plugin architecture to enable **controlled cross-plugin symbol sharing**, specifically allowing the MCP plugin to access `FileProvider` methods from the builtin plugin.

**Key Benefits**:
- ✅ **Zero manual interaction** - AI opens files automatically
- ✅ **Batch processing** - Analyze multiple files without human intervention
- ✅ **Faster workflow** - No context switching or waiting
- ✅ **True automation** - Compare, search, extract data autonomously
- ✅ **Scriptable pipelines** - Build automated binary analysis workflows

### How It Works
The patches accomplish cross-plugin symbol sharing through:
1. Exporting builtin plugin as a shared library (`.hexpluglib`)
2. Making FileProvider methods public for external access
3. Linking MCP plugin against builtin library
4. Gracefully handling missing settings for network interface usage
5. Implementing direct FileProvider construction and usage

## Patch Files

### 01-builtin-library-plugin.patch
**File**: `plugins/builtin/CMakeLists.txt`
**Purpose**: Export builtin plugin as a shared library instead of just a module
**Changes**: Adds `LIBRARY_PLUGIN` flag to `add_imhex_plugin()`
**Result**: Creates `builtin.hexpluglib` with exported symbols

### 02-fileprovider-public-open.patch
**File**: `plugins/builtin/include/content/providers/file_provider.hpp`
**Purpose**: Make `FileProvider::open(bool)` method accessible from external plugins
**Changes**: Moves `open(bool memoryMapped)` from private to public section
**Result**: External plugins can call `open(false)` or `open(true)` directly

### 03-fileprovider-graceful-settings.patch
**File**: `plugins/builtin/source/content/providers/file_provider.cpp`
**Purpose**: Handle missing settings gracefully during file opening
**Changes**:
- Wraps `ContentRegistry::Settings::read()` in try-catch in `open()` method
- Wraps entire `loadSettings()` method in try-catch
- Uses default values when settings unavailable
**Result**: File opening works before ImHex settings system fully initializes

### 04-provider-graceful-settings.patch
**File**: `lib/libimhex/source/providers/provider.cpp`
**Purpose**: Handle missing settings in base Provider class
**Changes**: Wraps `baseAddress` and `currPage` access in try-catch
**Result**: Provider can be created without complete settings JSON

### 05-mcp-plugin-link-builtin.patch
**File**: `plugins/mcp/CMakeLists.txt`
**Purpose**: Link MCP plugin against builtin library
**Changes**:
- Adds builtin plugin include directory
- Adds builtin to link libraries
**Result**: MCP plugin can access builtin plugin symbols

### 06-mcp-plugin-automated-file-open.patch
**File**: `plugins/mcp/source/plugin_mcp.cpp`
**Purpose**: Implement automated file opening in file/open endpoint
**Changes**:
- Adds `#include <content/providers/file_provider.hpp>`
- Replaces error-throwing stub with working implementation
- Creates FileProvider directly with `std::make_unique`
- Calls `setPath()` and `open(false)` methods
- Adds provider to ImHex with `Provider::add()`
**Result**: Files can be opened programmatically via network interface

## Applying Patches

### Automatic Application (Recommended)

Use the provided script:

```bash
cd /path/to/imhexMCP-standalone
./apply-patches.sh
```

### Manual Application

Apply patches in order from the ImHex root directory:

```bash
cd ImHex

# Apply each patch
patch -p1 < ../patches/01-builtin-library-plugin.patch
patch -p1 < ../patches/02-fileprovider-public-open.patch
patch -p1 < ../patches/03-fileprovider-graceful-settings.patch
patch -p1 < ../patches/04-provider-graceful-settings.patch
patch -p1 < ../patches/05-mcp-plugin-link-builtin.patch
patch -p1 < ../patches/06-mcp-plugin-automated-file-open.patch
```

### Verifying Patches

After applying, verify with:

```bash
cd ImHex

# Check builtin CMakeLists has LIBRARY_PLUGIN
grep -A2 "LIBRARY_PLUGIN" plugins/builtin/CMakeLists.txt

# Check FileProvider has public open(bool)
grep "bool open(bool" plugins/builtin/include/content/providers/file_provider.hpp

# Check MCP plugin links builtin
grep "builtin" plugins/mcp/CMakeLists.txt
```

## Building After Patching

1. **Clean old build artifacts** (important!):
   ```bash
   cd ImHex/build
   rm -f plugins/builtin.hexplug  # Remove old module file
   ```

2. **Rebuild**:
   ```bash
   ninja -j$(sysctl -n hw.ncpu)
   ```

3. **Verify output**:
   ```bash
   ls -la plugins/builtin.hexpluglib  # Should exist
   ls -la plugins/mcp.hexplug          # Should exist
   ```

## Reverting Patches

To revert all patches:

```bash
cd ImHex

# Revert in reverse order
patch -R -p1 < ../patches/06-mcp-plugin-automated-file-open.patch
patch -R -p1 < ../patches/05-mcp-plugin-link-builtin.patch
patch -R -p1 < ../patches/04-provider-graceful-settings.patch
patch -R -p1 < ../patches/03-fileprovider-graceful-settings.patch
patch -R -p1 < ../patches/02-fileprovider-public-open.patch
patch -R -p1 < ../patches/01-builtin-library-plugin.patch
```

## Testing

After building with patches applied:

1. Start ImHex
2. Enable Network Interface (Extras → Settings → General)
3. Run test suite:
   ```bash
   cd mcp-server
   ./venv/bin/python test_binary_analysis.py
   ```

Expected result: **8/8 tests passed** ✅

## Compatibility

- **ImHex Version**: 1.38.0.WIP (master branch)
- **Git Commit**: b1e2185 (as of patch creation)
- **Platform**: macOS, Linux (patches are platform-independent)
- **Compiler**: AppleClang 17.0.0, GCC 11+, Clang 14+

## Notes

- These patches are **non-invasive** and don't break existing functionality
- The builtin plugin can be used both as a library and as a plugin
- Other plugins are unaffected by these changes
- The patches follow ImHex coding standards
- All changes include appropriate error handling and logging

## Troubleshooting

### Patch fails to apply

**Cause**: ImHex source has diverged from patch base
**Solution**:
1. Check ImHex git commit hash
2. If different, patches may need adjustment
3. See `IMPLEMENTATION_SUCCESS.md` for manual modification instructions

### Build fails after patching

**Cause**: Old `builtin.hexplug` file exists
**Solution**: `rm ImHex/build/plugins/builtin.hexplug`

### ImHex crashes on startup

**Cause**: Both `builtin.hexplug` and `builtin.hexpluglib` are loaded
**Solution**: Only `builtin.hexpluglib` should exist in plugins directory

## Support

For issues or questions about these patches:
1. Review `IMPLEMENTATION_SUCCESS.md` for detailed implementation notes
2. Check `mcp-server/README_MCP_USAGE.md` for usage documentation
3. Verify ImHex version compatibility

## License

These patches modify ImHex source code and are subject to ImHex's GPL-2.0 license.
