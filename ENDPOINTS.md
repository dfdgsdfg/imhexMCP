# ImHex MCP Plugin - Complete Endpoint Reference

**Total Endpoints**: 25
**Plugin Version**: 1.38.0 (ARM64 Native)
**Last Updated**: 2025-11-11

## 📋 Table of Contents

- [Core Operations](#core-operations) (8 endpoints)
- [Data Access](#data-access) (4 endpoints)
- [Search & Pattern Matching](#search--pattern-matching) (3 endpoints)
- [Hashing & Integrity](#hashing--integrity) (2 endpoints)
- [Bookmarks & Annotations](#bookmarks--annotations) (3 endpoints)
- [Batch Operations (Phase 4)](#batch-operations-phase-4) (4 endpoints)
- [Advanced Analysis (Phase 4)](#advanced-analysis-phase-4) (2 endpoints)

---

## Core Operations

### 1. `capabilities`
**Get ImHex build information and available commands**

```json
{
  "command": "capabilities"
}
```

**Returns**: Build version, commit, branch, endpoint list

---

### 2. `file/open`
**Open a file in ImHex (threading-safe async operation)**

```json
{
  "command": "file/open",
  "data": {"path": "/path/to/file.bin"}
}
```

**Returns**: Async status (poll `list/providers` for completion)

---

### 3. `file/close`
**Close an open file/provider**

```json
{
  "command": "file/close",
  "data": {"provider_id": 123}
}
```

---

### 4. `file/list`
**List all open files**

```json
{
  "command": "file/list"
}
```

**Returns**: Array of files with IDs, names, sizes, types

---

### 5. `list/providers`
**List all open providers (alias for file/list)**

```json
{
  "command": "list/providers"
}
```

**Returns**: `{"providers": [{id, name, size, type}]}`

---

### 6. `file/switch`
**Switch the active provider/file**

```json
{
  "command": "file/switch",
  "data": {"provider_id": 123}
}
```

---

### 7. `file/info`
**Get information about the currently active file**

```json
{
  "command": "file/info"
}
```

**Returns**: Name, size, path, provider type

---

### 8. `pattern/set`
**Set Pattern Language code for binary parsing**

```json
{
  "command": "pattern/set",
  "data": {"code": "u32 magic @ 0x00;"}
}
```

---

## Data Access

### 9. `data/read`
**Read hex data from the current file**

```json
{
  "command": "data/read",
  "data": {
    "offset": 0,
    "length": 256,
    "encoding": "hex"
  }
}
```

**Encodings**: `hex`, `base64`, `ascii`
**Max Length**: 1MB

---

### 10. `data/write`
**Write hex data to the current file**

```json
{
  "command": "data/write",
  "data": {
    "offset": 0,
    "data": "0A1B2C3D"
  }
}
```

---

### 11. `data/export`
**Export a region to a file**

```json
{
  "command": "data/export",
  "data": {
    "offset": 0,
    "length": 1024,
    "output_path": "/tmp/export.bin"
  }
}
```

---

### 12. `data/chunked_read`
**Read large files in chunks (pagination support)**

```json
{
  "command": "data/chunked_read",
  "data": {
    "offset": 0,
    "length": 10485760,
    "chunk_size": 1048576,
    "chunk_index": 0,
    "encoding": "hex"
  }
}
```

**Max Total**: 100MB
**Chunk Size**: Default 1MB
**Returns**: `{chunk_data, chunk_index, has_more, total_chunks}`

---

## Search & Pattern Matching

### 13. `data/search`
**Search for patterns in the current file**

```json
{
  "command": "data/search",
  "data": {
    "patterns": [
      {"pattern": "48656C6C6F", "type": "hex"},
      {"pattern": "World", "type": "text"}
    ],
    "limit": 10000,
    "offset": 0
  }
}
```

**Types**: `hex`, `text`, `regex`
**Pagination**: Use `offset` to skip results
**Returns**: Array of `{pattern, matches: [offsets]}`

---

### 14. `data/multi_search`
**Search for multiple patterns simultaneously**

```json
{
  "command": "data/multi_search",
  "data": {
    "patterns": [
      {"pattern": "CAFEBABE", "type": "hex"},
      {"pattern": "MZ", "type": "text"}
    ],
    "limit": 10000
  }
}
```

**Max Patterns**: 20
**Returns**: Results for each pattern

---

### 15. `data/replace`
**Replace pattern occurrences**

```json
{
  "command": "data/replace",
  "data": {
    "offset": 0,
    "old_data": "0A0B",
    "new_data": "FFFF"
  }
}
```

---

## Hashing & Integrity

### 16. `data/hash`
**Calculate hash of a region**

```json
{
  "command": "data/hash",
  "data": {
    "algorithm": "sha256",
    "offset": 0,
    "length": 1024
  }
}
```

**Algorithms**: `md5`, `sha1`, `sha224`, `sha256`, `sha384`, `sha512`
**Returns**: Hex-encoded hash string

---

### 17. `data/compare`
**Compare two files/providers**

```json
{
  "command": "data/compare",
  "data": {
    "provider_id_1": 123,
    "provider_id_2": 456
  }
}
```

**Max Size**: 1MB per file
**Returns**: Similarity percentage, matching bytes, sample differences

---

## Bookmarks & Annotations

### 18. `bookmark/add`
**Add a bookmark to a region**

```json
{
  "command": "bookmark/add",
  "data": {
    "offset": 0,
    "size": 16,
    "name": "Header",
    "comment": "File header structure",
    "color": "FF0000"
  }
}
```

---

### 19. `bookmark/list`
**List all bookmarks**

```json
{
  "command": "bookmark/list"
}
```

**Returns**: Array of bookmarks with offsets, sizes, names, colors

---

### 20. `bookmark/remove`
**Remove a bookmark**

```json
{
  "command": "bookmark/remove",
  "data": {"bookmark_id": 123}
}
```

---

## Batch Operations (Phase 4)

### 21. `batch/hash`
**✨ Hash multiple files simultaneously**

```json
{
  "command": "batch/hash",
  "data": {
    "provider_ids": "all",
    "algorithm": "sha256",
    "offset": 0,
    "size": 1048576
  }
}
```

**Provider IDs**: Array of integers or string `"all"`
**Max Size**: 100MB per file
**Returns**: `{hashes: [{provider_id, hash, status}], total}`

**Use Cases**:
- Verify file integrity across collections
- Find duplicate files
- Generate checksums for multiple files

---

### 22. `batch/search`
**✨ Search pattern across multiple files**

```json
{
  "command": "batch/search",
  "data": {
    "provider_ids": "all",
    "pattern": "48656C6C6F",
    "max_matches": 1000
  }
}
```

**Provider IDs**: Array or `"all"`
**Pattern**: Hex string
**Returns**: `{results: [{provider_id, file, matches: [offsets]}]}`

**Use Cases**:
- Find common signatures across files
- Locate specific data patterns
- Malware analysis across samples

---

### 23. `batch/diff`
**Compare reference file against multiple targets**

```json
{
  "command": "batch/diff",
  "data": {
    "reference_id": 123,
    "target_ids": "all",
    "algorithm": "myers",
    "max_diff_regions": 1000
  }
}
```

**Algorithms**: `myers` (more available in ImHex)
**Max File Size**: 100MB
**Returns**: Similarity percentages, diff regions, matching bytes

**Use Cases**:
- Compare file variants
- Find most similar files
- Analyze binary patches

---

## Advanced Analysis (Phase 4)

### 24. `data/entropy`
**✨ Calculate Shannon entropy for randomness detection**

```json
{
  "command": "data/entropy",
  "data": {
    "provider_id": 0,
    "offset": 0,
    "size": 1024
  }
}
```

**Max Size**: 10MB
**Returns**: `{entropy, percentage, interpretation}`

**Entropy Scale** (0-8 bits/byte):
- **0-1**: Very low (padding, zeros, repetitive)
- **1-3**: Low (text, structured data)
- **3-5**: Medium (mixed content)
- **5-7**: High (compressed/encrypted)
- **7-8**: Very high (encrypted, random)

**Use Cases**:
- Detect encrypted sections
- Identify compressed data
- Find padding or repetitive regions
- Analyze data randomness

---

### 25. `data/statistics`
**✨ Byte frequency and composition analysis**

```json
{
  "command": "data/statistics",
  "data": {
    "provider_id": 0,
    "offset": 0,
    "size": 1024,
    "include_distribution": false
  }
}
```

**Max Size**: 10MB
**Returns**:
- `unique_bytes`: Count of unique byte values (0-256)
- `most_common_byte`: Most frequent byte and count
- `null_bytes`: Count and percentage of null bytes
- `printable_chars`: ASCII printable character count/percentage
- `distribution`: Optional full 256-byte frequency map

**Use Cases**:
- Understand data composition
- Detect text vs binary data
- Find repetitive patterns
- Analyze byte distribution

---

## Performance Characteristics

### Threading Model
- **Main Thread**: All ImHex API calls via `TaskManager::doLater()`
- **Network Thread**: JSON RPC endpoint handlers
- **Async Operations**: `file/open`, `file/close` return immediately

### Size Limits
| Operation | Limit | Notes |
|-----------|-------|-------|
| Single Read | 1MB | Use chunked_read for larger |
| Chunked Read | 100MB total | 1MB chunks recommended |
| Hash | 100MB | Per file in batch operations |
| Diff | 100MB | Per file comparison |
| Entropy | 10MB | Statistical analysis |
| Statistics | 10MB | Byte frequency analysis |
| Search Results | 100,000 | Configurable per operation |

### Timeouts
- **Connection**: 5 seconds
- **Read**: 30 seconds
- **Batch Operations**: 30 seconds per file

---

## Error Handling

All endpoints return standard format:
```json
{
  "status": "success" | "error",
  "data": {...} | {"error": "message"}
}
```

### Common Errors
- `Provider not found`: Invalid provider_id
- `File too large`: Exceeds size limit
- `Terminating from non-main thread`: (Fixed in v1.38.0)
- `Endpoint not found`: Network interface not enabled

---

## Example Workflows

### 1. Multi-File Malware Analysis
```bash
# Open samples
file/open -> sample1.exe
file/open -> sample2.exe
file/open -> sample3.exe

# Find common signatures
batch/search -> pattern: "MZ"

# Calculate hashes
batch/hash -> algorithm: sha256

# Compare variants
batch/diff -> reference: sample1
```

### 2. Encrypted Data Detection
```bash
# Open file
file/open -> suspicious.dat

# Check entropy
data/entropy -> size: 4096
# High entropy (>7) = likely encrypted

# Analyze byte distribution
data/statistics -> size: 4096
# High unique_bytes = random/encrypted
```

### 3. File Integrity Verification
```bash
# Open multiple files
file/open -> file1, file2, file3

# Hash all
batch/hash -> all, sha256

# Compare hashes externally
```

---

## MCP Tool Names

When using via MCP (Model Context Protocol):
- `imhex_batch_hash` → `batch/hash`
- `imhex_batch_search` → `batch/search`
- `imhex_data_entropy` → `data/entropy`
- `imhex_data_statistics` → `data/statistics`
- `imhex_batch_diff` → `batch/diff`
- (All other tools follow `imhex_<category>_<operation>` pattern)

---

## Build Information

**Architecture**: ARM64 (Apple Silicon native)
**No Rosetta 2 Required**: ✅
**Plugin Size**: 530KB
**Dependencies**: All from `/opt/homebrew`

Build with: `./scripts/build-arm64.zsh`
