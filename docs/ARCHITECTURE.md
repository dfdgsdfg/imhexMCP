# ImHex MCP Architecture

**Version**: 1.38.0
**Last Updated**: 2025-11-11

## Table of Contents

- [System Overview](#system-overview)
- [High-Level Architecture](#high-level-architecture)
- [Component Breakdown](#component-breakdown)
- [Threading Model](#threading-model)
- [Data Flow](#data-flow)
- [Network Protocol](#network-protocol)
- [Integration Points](#integration-points)
- [Deployment Models](#deployment-models)
- [Security Considerations](#security-considerations)

---

## System Overview

ImHex MCP is a network interface plugin for ImHex that exposes binary analysis capabilities through a JSON-RPC over TCP protocol. It enables programmatic access to ImHex's powerful binary analysis features, including file operations, data manipulation, pattern matching, hashing, and advanced analysis operations.

### Key Characteristics

- **Platform**: Cross-platform (macOS, Linux, Windows)
- **Protocol**: JSON-RPC over TCP
- **Port**: 31337 (localhost only)
- **Architecture**: ARM64-native on Apple Silicon, x86_64 on Intel
- **Threading**: Thread-safe with TaskManager integration
- **Language**: C++17 with ImHex plugin API

### Design Goals

1. **Thread Safety**: All ImHex API calls routed through main thread
2. **Performance**: Efficient batch operations for multiple files
3. **Extensibility**: Easy to add new endpoints
4. **Reliability**: Comprehensive error handling
5. **Integration**: MCP server for AI/automation workflows

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Client Layer                          │
├──────────┬──────────┬──────────┬──────────┬─────────────────┤
│  Python  │   Node   │    Go    │   Rust   │  MCP Server     │
│  Client  │  Client  │  Client  │  Client  │  (Claude AI)    │
└──────────┴──────────┴──────────┴──────────┴─────────────────┘
           │          │          │          │          │
           └──────────┴──────────┴──────────┴──────────┘
                              │
                     [TCP Socket: 31337]
                              │
┌─────────────────────────────┴─────────────────────────────┐
│                     Network Layer                          │
│  ┌──────────────────────────────────────────────────────┐ │
│  │        ImHex MCP Plugin Network Interface            │ │
│  │  ┌────────────┐  ┌────────────┐  ┌──────────────┐  │ │
│  │  │  Listener  │  │   Router   │  │   Handler    │  │ │
│  │  │  (Async)   │→ │  (Parser)  │→ │  (Executor)  │  │ │
│  │  └────────────┘  └────────────┘  └──────────────┘  │ │
│  └──────────────────────────────────────────────────────┘ │
└────────────────────────────┬──────────────────────────────┘
                             │
                    [TaskManager::doLater()]
                             │
┌────────────────────────────┴──────────────────────────────┐
│                    ImHex Main Thread                       │
│  ┌──────────────────────────────────────────────────────┐ │
│  │               ImHex Core APIs                        │ │
│  │  ┌────────────┬──────────┬──────────┬──────────────┐│ │
│  │  │  Provider  │  Pattern │  Search  │  Hashing     ││ │
│  │  │  Manager   │  Engine  │  Engine  │  Engine      ││ │
│  │  └────────────┴──────────┴──────────┴──────────────┘│ │
│  │  ┌────────────┬──────────┬──────────┬──────────────┐│ │
│  │  │  Bookmark  │  Magic   │  Strings │  Disassembly ││ │
│  │  │  Manager   │  Detect  │  Extract │  Engine      ││ │
│  │  └────────────┴──────────┴──────────┴──────────────┘│ │
│  └──────────────────────────────────────────────────────┘ │
└────────────────────────────┬──────────────────────────────┘
                             │
┌────────────────────────────┴──────────────────────────────┐
│                    File System Layer                       │
│  ┌──────────────────────────────────────────────────────┐ │
│  │         Binary Files & Data Providers                │ │
│  │  ┌───────────┐  ┌──────────┐  ┌──────────────────┐  │ │
│  │  │   File    │  │  Memory  │  │    Network       │  │ │
│  │  │  Provider │  │ Provider │  │    Provider      │  │ │
│  │  └───────────┘  └──────────┘  └──────────────────┘  │ │
│  └──────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────┘
```

---

## Component Breakdown

### 1. Network Interface Layer

#### TCP Listener
- **File**: `plugins/builtin/source/content/background_services.cpp`
- **Purpose**: Accept incoming TCP connections on port 31337
- **Threading**: Runs in background thread pool
- **State**: Managed by background service

**Key Code Location**:
```cpp
// ImHex/plugins/builtin/source/content/background_services.cpp:109-111
ContentRegistry::Settings::onChange("hex.builtin.setting.general",
    "hex.builtin.setting.general.network_interface", [](const ContentRegistry::Settings::SettingsValue &value) {
    s_networkInterfaceServiceEnabled = value.get<bool>(false);
});
```

#### JSON-RPC Router
- **Purpose**: Parse incoming JSON requests and route to handlers
- **Validation**: Schema validation, parameter checking
- **Error Handling**: Catches exceptions and returns error responses

#### Endpoint Handlers
- **Count**: 28 endpoints across 6 categories
- **Pattern**: Each handler validates input → calls ImHex API → formats response
- **Threading**: All handlers use `TaskManager::doLater()` for main thread execution

### 2. Core API Integration

#### Provider Management
- **Operations**: `file/open`, `file/close`, `file/list`, `file/switch`
- **Provider Types**: File, Memory, Network, Diff
- **State**: Tracked via Provider Registry

**Key Concepts**:
- **Provider ID**: Unique integer identifier for each open file
- **Active Provider**: Currently selected provider for operations
- **Provider Lifecycle**: Open → Use → Close

#### Data Access
- **Operations**: `data/read`, `data/write`, `data/export`, `data/chunked_read`
- **Limits**: 1MB single read, 100MB chunked read
- **Encoding**: Hex, Base64, ASCII

#### Pattern Matching & Search
- **Operations**: `data/search`, `data/multi_search`, `batch/search`
- **Algorithms**: Boyer-Moore, regex support
- **Performance**: Optimized for large files

#### Hashing & Integrity
- **Operations**: `data/hash`, `batch/hash`, `data/compare`
- **Algorithms**: MD5, SHA-1, SHA-224, SHA-256, SHA-384, SHA-512
- **Optimization**: Entire file hashing uses optimized path

#### Advanced Analysis
- **Strings**: ASCII and UTF-16LE extraction
- **Magic**: File type detection (30+ formats)
- **Disassembly**: Multi-architecture support (x86, ARM, MIPS, etc.)
- **Entropy**: Shannon entropy for encryption detection
- **Statistics**: Byte frequency analysis

### 3. MCP Server Layer

**File**: `mcp-server/server.py`

```
┌───────────────────────────────────────────────────────┐
│               MCP Server (Python)                      │
│  ┌─────────────────────────────────────────────────┐  │
│  │         Claude Code / AI Integration            │  │
│  └─────────────────────────────────────────────────┘  │
│  ┌─────────────────────────────────────────────────┐  │
│  │         Tool Registry (28 tools)                │  │
│  │  ┌──────────┬──────────┬────────────────────┐   │  │
│  │  │ imhex_   │ imhex_   │   imhex_batch_     │   │  │
│  │  │ file_*   │ data_*   │   operations       │   │  │
│  │  └──────────┴──────────┴────────────────────┘   │  │
│  └─────────────────────────────────────────────────┘  │
│  ┌─────────────────────────────────────────────────┐  │
│  │    TCP Client (connects to ImHex:31337)        │  │
│  └─────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────┘
```

**Purpose**:
- Expose ImHex capabilities to AI assistants (Claude, GPT, etc.)
- Automatic schema generation from ImHex endpoints
- Error handling and retry logic
- State management for multi-step operations

---

## Threading Model

### Overview

ImHex MCP uses a hybrid threading model to ensure thread safety:

```
┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│   Network    │         │   Router     │         │   ImHex      │
│   Thread     │────────>│   Thread     │────────>│   Main       │
│   (Accept)   │         │   (Parse)    │         │   Thread     │
└──────────────┘         └──────────────┘         └──────────────┘
      │                        │                         │
      │ TCP Accept             │ Parse JSON              │ Execute API
      │ Non-blocking           │ Validate                │ Return result
      v                        v                         v
  [Connection]            [Request]                 [Response]
```

### Thread Responsibilities

#### Network Thread Pool
- **Count**: 1-4 threads (configurable)
- **Purpose**: Accept connections, read requests
- **Blocking**: I/O bound, can block on socket operations
- **Lifetime**: Entire ImHex session

#### Request Processing
- **Count**: 1 per request
- **Purpose**: Parse JSON, validate, route to handler
- **Blocking**: CPU bound, minimal blocking
- **Lifetime**: Duration of single request

#### ImHex Main Thread
- **Count**: 1 (singleton)
- **Purpose**: Execute all ImHex API calls
- **Blocking**: Can block on file I/O, large operations
- **Access**: Via `TaskManager::doLater()`

### TaskManager Integration

**Critical Pattern**:
```cpp
// ALL ImHex API calls MUST use this pattern
TaskManager::doLater([provider_id]() {
    auto provider = ImHexApi::Provider::get(provider_id);
    if (provider == nullptr) {
        return error_response("Provider not found");
    }

    // Safe to use ImHex APIs here
    auto result = provider->read(offset, size);
    return success_response(result);
});
```

**Why This Matters**:
- ImHex UI runs on main thread
- Many APIs are not thread-safe
- File operations require main thread context
- Provider state is main-thread owned

### Async Operations

**file/open** and **file/close** are truly asynchronous:

```
Client Request          Network Thread          Main Thread
      │                      │                       │
      │──file/open──────────>│                       │
      │                      │──TaskManager::────────>│
      │<─────"queued"────────│    doLater()          │
      │                      │                       │ [open file]
      │                      │                       │
      │──file/list───────────>│                       │
      │<─────providers───────│<──────────────────────│
```

**Benefit**: Client doesn't block waiting for file open

---

## Data Flow

### Example: Reading Binary Data

```
┌─────────────────────────────────────────────────────────────┐
│ Step 1: Client sends request                                │
└─────────────────────────────────────────────────────────────┘
                         │
          {"endpoint": "data/read",
           "data": {"provider_id": 0, "offset": 0, "size": 256}}
                         │
                         v
┌─────────────────────────────────────────────────────────────┐
│ Step 2: Network layer receives and parses                   │
│  - Validate JSON syntax                                      │
│  - Extract endpoint and data                                 │
└─────────────────────────────────────────────────────────────┘
                         │
                         v
┌─────────────────────────────────────────────────────────────┐
│ Step 3: Route to data/read handler                          │
│  - Validate parameters (provider_id, offset, size)           │
│  - Check size limit (max 1MB)                               │
└─────────────────────────────────────────────────────────────┘
                         │
                         v
┌─────────────────────────────────────────────────────────────┐
│ Step 4: Queue task on main thread                           │
│  TaskManager::doLater([provider_id, offset, size]() { ... })│
└─────────────────────────────────────────────────────────────┘
                         │
                         v
┌─────────────────────────────────────────────────────────────┐
│ Step 5: Execute on main thread                              │
│  - Get provider by ID                                        │
│  - Call provider->read(offset, size)                         │
│  - Convert bytes to hex string                               │
└─────────────────────────────────────────────────────────────┘
                         │
                         v
┌─────────────────────────────────────────────────────────────┐
│ Step 6: Format response                                      │
│  {"status": "success",                                       │
│   "data": {"data": "4d5a9000...", "offset": 0, "size": 256}}│
└─────────────────────────────────────────────────────────────┘
                         │
                         v
┌─────────────────────────────────────────────────────────────┐
│ Step 7: Send response to client                             │
│  - JSON encode                                               │
│  - Append newline                                            │
│  - Write to socket                                           │
│  - Close socket                                              │
└─────────────────────────────────────────────────────────────┘
```

### Batch Operation Data Flow

Batch operations process multiple files concurrently:

```
batch/hash with 3 providers
         │
         v
┌────────────────────────────────────────┐
│  Create 3 tasks, one per provider      │
│  TaskManager::doLater() x 3            │
└────────────────────────────────────────┘
         │
    ┌────┴────┐
    │    │    │
    v    v    v
┌───────┬───────┬───────┐
│ Hash  │ Hash  │ Hash  │
│ Prov0 │ Prov1 │ Prov2 │
└───────┴───────┴───────┘
    │    │    │
    └────┬────┘
         │
         v
┌────────────────────────────────────────┐
│  Collect results                       │
│  {"hashes": [{...}, {...}, {...}]}     │
└────────────────────────────────────────┘
```

---

## Network Protocol

### Connection Lifecycle

```
Client                          Server
  │                               │
  │──── TCP Connect ─────────────>│
  │                               │ [Accept]
  │                               │
  │──── JSON Request + \n ───────>│
  │                               │ [Parse]
  │                               │ [Execute]
  │                               │
  │<──── JSON Response + \n ──────│
  │                               │
  │──── TCP Close ───────────────>│
  │                               │ [Cleanup]
```

### Request Format

```json
{
  "endpoint": "category/operation",
  "data": {
    "param1": "value1",
    "param2": 123
  }
}\n
```

**Important**: Newline (`\n`) is the message delimiter.

### Response Format

**Success**:
```json
{
  "status": "success",
  "data": {
    "result1": "value1",
    "result2": [1, 2, 3]
  }
}\n
```

**Error**:
```json
{
  "status": "error",
  "data": {
    "error": "Provider with ID 99 not found"
  }
}\n
```

### Connection Handling

- **One request per connection**: Client must open new socket for each request
- **No keep-alive**: Connections closed after response sent
- **Timeout**: Server enforces read timeout (30 seconds)
- **Backlog**: Server accepts up to 10 pending connections

---

## Integration Points

### 1. ImHex Plugin System

**Registration** (Content Registry):
```cpp
ContentRegistry::Settings::add("hex.builtin.setting.general",
                               "hex.builtin.setting.general.network_interface",
                               false);

ContentRegistry::Settings::onChange("hex.builtin.setting.general",
    "hex.builtin.setting.general.network_interface",
    [](const ContentRegistry::Settings::SettingsValue &value) {
        s_networkInterfaceServiceEnabled = value.get<bool>(false);
});
```

**Hooks**:
- Settings change callbacks
- Provider creation/destruction events
- Task manager integration

### 2. MCP Protocol Integration

**Tool Registration**:
```python
@server.list_tools()
async def list_tools():
    return [
        types.Tool(
            name="imhex_file_open",
            description="Open a binary file in ImHex",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path"}
                },
                "required": ["path"]
            }
        ),
        # ... 27 more tools
    ]
```

**Tool Execution**:
```python
@server.call_tool()
async def call_tool(name: str, arguments: dict):
    endpoint = name.replace("imhex_", "").replace("_", "/")
    result = await send_request_to_imhex(endpoint, arguments)
    return [types.TextContent(type="text", text=json.dumps(result))]
```

### 3. AI Assistant Integration

**Claude Code** accesses ImHex via MCP:
```
Claude Code
     │
     │ [MCP Protocol]
     v
MCP Server (Python)
     │
     │ [JSON-RPC over TCP]
     v
ImHex Plugin (C++)
     │
     │ [ImHex API]
     v
Binary File Analysis
```

**Example Flow**:
1. User asks Claude: "Analyze this firmware for hardcoded passwords"
2. Claude calls `imhex_file_open` tool
3. MCP server sends `file/open` request to ImHex
4. Claude calls `imhex_data_strings` tool
5. MCP server sends `data/strings` request
6. Claude analyzes string results for suspicious patterns
7. Claude presents findings to user

---

## Deployment Models

### 1. Local Development

```
┌─────────────────────────────────────┐
│  Developer Workstation               │
│                                      │
│  ┌──────────────┐  ┌──────────────┐ │
│  │    ImHex     │  │  Python      │ │
│  │  (running)   │←─│  Script      │ │
│  └──────────────┘  └──────────────┘ │
│        :31337                        │
└─────────────────────────────────────┘
```

**Use Case**: Interactive development, testing

### 2. CI/CD Pipeline

```
┌─────────────────────────────────────┐
│  GitHub Actions Runner               │
│                                      │
│  ┌──────────────┐                   │
│  │  Build        │                   │
│  │  ImHex        │                   │
│  └──────┬────────┘                   │
│         │                            │
│  ┌──────v────────┐  ┌──────────────┐│
│  │  Start        │  │  Run         ││
│  │  ImHex        │←─│  Tests       ││
│  │  Headless     │  │              ││
│  └───────────────┘  └──────────────┘│
└─────────────────────────────────────┘
```

**Use Case**: Automated testing, binary validation

### 3. AI-Assisted Analysis

```
┌──────────────┐         ┌──────────────┐
│   Claude     │         │    ImHex     │
│   Code       │         │   (local)    │
│              │         │              │
│ ┌──────────┐ │         │              │
│ │   MCP    │ │  TCP    │              │
│ │  Server  │←┼─────────┤              │
│ └──────────┘ │ :31337  │              │
└──────────────┘         └──────────────┘
```

**Use Case**: Interactive binary analysis with AI assistance

### 4. Batch Processing

```
┌─────────────────────────────────────┐
│  Analysis Server                     │
│                                      │
│  ┌──────────────┐                   │
│  │    ImHex     │                   │
│  │  (headless)  │                   │
│  └──────┬────────┘                   │
│         │                            │
│  ┌──────v────────┐                   │
│  │  Python       │                   │
│  │  Pipeline     │                   │
│  │  - Open files │                   │
│  │  - Extract    │                   │
│  │  - Analyze    │                   │
│  │  - Report     │                   │
│  └───────────────┘                   │
└─────────────────────────────────────┘
```

**Use Case**: Large-scale malware analysis, firmware auditing

---

## Security Considerations

### Current Security Model

**Localhost Only**:
- Network interface binds to `127.0.0.1` only
- No remote connections accepted
- Assumes trusted local environment

**No Authentication**:
- Any local process can connect
- No user verification
- No rate limiting

**File System Access**:
- Plugin has same permissions as ImHex process
- Can read any file accessible to user
- Can write to any file with write permissions

### Threat Model

**In Scope** (Current):
- Malicious local processes
- Accidental misuse
- File system traversal

**Out of Scope** (Current):
- Network attackers (no remote access)
- Privilege escalation (same user as ImHex)
- DoS attacks (local only)

### Security Enhancements (Roadmap)

1. **Authentication**:
   - API key/token-based auth
   - Per-tool permissions
   - Session management

2. **Authorization**:
   - File path whitelisting
   - Read-only mode
   - Operation restrictions

3. **Encryption**:
   - TLS/SSL for remote connections
   - Certificate-based auth

4. **Rate Limiting**:
   - Request throttling
   - Connection limits
   - Resource quotas

5. **Auditing**:
   - Request logging
   - Access tracking
   - Security event notifications

---

## Performance Characteristics

### Throughput

| Operation | Throughput | Notes |
|-----------|-----------|-------|
| Small reads (<1KB) | ~10,000 req/s | Limited by JSON parsing |
| Large reads (1MB) | ~100 req/s | Limited by file I/O |
| Hashing (SHA-256) | ~200 MB/s | Single file, SSD |
| Batch hash (10 files) | ~150 MB/s aggregate | Parallel processing |
| String extraction | ~50 MB/s | Regex scanning overhead |

### Latency

| Operation | Latency (p50) | Latency (p99) | Notes |
|-----------|--------------|---------------|-------|
| file/open | 2-5ms | 50ms | Async, returns immediately |
| file/list | <1ms | 2ms | In-memory operation |
| data/read (1KB) | 1-2ms | 5ms | Small buffer |
| data/read (1MB) | 10-20ms | 100ms | Disk I/O |
| data/hash (1MB) | 5-10ms | 25ms | CPU-bound |
| data/strings (1MB) | 20-40ms | 100ms | Regex overhead |

### Resource Usage

**Memory**:
- Base plugin: ~1MB
- Per file open: ~10-50MB (depending on file size)
- Request processing: ~1-10MB per request
- MCP server: ~50MB Python runtime

**CPU**:
- Idle: <1%
- Active request: 5-25% (one core)
- Batch operations: 50-100% (multi-core)

---

## Future Architecture

### Planned Enhancements

1. **WebSocket Support**:
   - Persistent connections
   - Server-push notifications
   - Streaming responses

2. **Plugin Architecture**:
   - Third-party endpoints
   - Custom analyzers
   - Extension marketplace

3. **Distributed Processing**:
   - Remote ImHex workers
   - Load balancing
   - Horizontal scaling

4. **Advanced Caching**:
   - Result caching
   - Provider state caching
   - Computed value memoization

---

## References

- [API Reference](API.md)
- [Endpoint Reference](../ENDPOINTS.md)
- [Quickstart Guide](QUICKSTART.md)
- [Testing Guide](TESTING.md)
