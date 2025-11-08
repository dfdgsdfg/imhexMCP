# ImHex MCP Server Architecture

## Overview

The ImHex MCP Server provides a bridge between AI assistants (like Claude) and the ImHex hex editor, enabling AI-powered binary analysis and manipulation.

## Architecture Diagram

```
┌─────────────────────┐
│   AI Assistant      │
│   (Claude Code)     │
└──────────┬──────────┘
           │ MCP Protocol (stdio)
           │ JSON-RPC
           ▼
┌─────────────────────┐
│   MCP Server        │
│   (Python)          │
│                     │
│  - Tool handlers    │
│  - JSON validation  │
│  - Error handling   │
└──────────┬──────────┘
           │ TCP (localhost:31337)
           │ JSON messages
           ▼
┌─────────────────────┐
│   ImHex             │
│   Network Interface │
│                     │
│  - Endpoint registry│
│  - Plugin system    │
│  - Core features    │
└─────────────────────┘
```

## Components

### 1. MCP Server (server.py)

**Technology:** Python 3.10+ with MCP SDK

**Responsibilities:**
- Implements Model Context Protocol server interface
- Exposes ImHex functionality as MCP tools
- Manages TCP connection to ImHex
- Handles request/response translation
- Provides error handling and logging

**Key Classes:**
- `ImHexClient`: Manages TCP communication with ImHex
  - Connection management (connect, disconnect, reconnect)
  - JSON message serialization/deserialization
  - Socket timeout handling
  - Error recovery

- `app` (MCP Server): Main server instance
  - Tool registration (`@app.list_tools()`)
  - Tool execution (`@app.call_tool()`)
  - stdio transport management

**Communication Flow:**
1. Claude sends MCP tool request via stdio
2. MCP server receives and validates request
3. Server translates to ImHex endpoint format
4. Sends JSON request over TCP to ImHex
5. Receives JSON response from ImHex
6. Translates response to MCP format
7. Returns result to Claude via stdio

### 2. ImHex Network Interface

**Technology:** C++23, TCP Server (port 31337)

**Location:** `plugins/builtin/source/content/background_services.cpp`

**Implementation Details:**
- Uses `wolv::net::SocketServer` from libwolv library
- JSON-based request/response protocol
- Runs as a background service in ImHex
- Enabled via Settings → General → Network Interface

**Endpoint Registry:**
- `ContentRegistry::CommunicationInterface::registerNetworkEndpoint(name, handler)`
- Plugins can register custom endpoints
- Handlers receive JSON data and return JSON responses

**Existing Endpoints:**
- `imhex/capabilities`: Returns build info and available commands
- `pattern_editor/set_code`: Sets pattern language code
- (Additional endpoints can be registered by plugins)

**Message Format:**
```json
Request:
{
  "endpoint": "endpoint_name",
  "data": { ...parameters... }
}

Response (Success):
{
  "status": "success",
  "data": { ...result... }
}

Response (Error):
{
  "status": "error",
  "data": { "error": "error message" }
}
```

### 3. ImHex Core Architecture

**Plugin System:**
- Core library: `libimhex` (LGPL-2.1)
- Plugin interface for extensibility
- Built-in plugin contains most features

**Key Systems:**
- **Provider System**: Abstract interface for data sources
  - File providers, memory providers, network providers
  - Undo/redo stack
  - Data caching

- **Event System**: Event-driven architecture
  - `EventProviderCreated`, `EventProviderOpened`, etc.
  - Plugins subscribe to events
  - Async event handling

- **Content Registry**: Central registration system
  - Providers, Views, Tools, Commands
  - Data processors, Pattern functions
  - Network endpoints

- **Pattern Language**: Custom DSL for binary parsing
  - C++-like syntax
  - Type system (u8, u16, u32, u64, s8, s16, etc.)
  - Structs, arrays, pointers
  - Functions and expressions

## Data Flow Examples

### Example 1: Opening a File

```
1. Claude: "Open file.bin in ImHex"
2. MCP Server receives tool call: imhex_open_file
3. MCP Server → ImHex TCP:
   {
     "endpoint": "file/open",
     "data": {"path": "/path/to/file.bin"}
   }
4. ImHex processes request:
   - Validates path
   - Creates file provider
   - Opens file in UI
5. ImHex → MCP Server:
   {
     "status": "success",
     "data": {"file": "file.bin", "size": 12345}
   }
6. MCP Server → Claude:
   "File opened: /path/to/file.bin"
```

### Example 2: Pattern Language Execution

```
1. Claude: "Parse this as a PE file"
2. Claude generates pattern language code
3. MCP Server receives: imhex_set_pattern_code
4. MCP Server → ImHex TCP:
   {
     "endpoint": "pattern_editor/set_code",
     "data": {"code": "struct DOSHeader {...}; ..."}
   }
5. ImHex processes:
   - Compiles pattern
   - Executes on current provider
   - Updates pattern view
6. ImHex → MCP Server:
   {
     "status": "success",
     "data": {"compiled": true}
   }
7. MCP Server → Claude:
   "Pattern code set successfully"
```

## Extension Points

### Adding New MCP Tools

To add a new tool to the MCP server:

1. **Define the tool** in `list_tools()`:
```python
Tool(
    name="imhex_new_feature",
    description="Description of the feature",
    inputSchema={
        "type": "object",
        "properties": {
            "param": {"type": "string", "description": "Parameter"}
        },
        "required": ["param"]
    }
)
```

2. **Implement the handler** in `call_tool()`:
```python
elif name == "imhex_new_feature":
    param = arguments.get("param")
    response = imhex_client.send_command("new/endpoint", {"param": param})
    # Process response...
```

### Adding New ImHex Endpoints

To expose new functionality from ImHex:

1. **Create a plugin** or modify existing one
2. **Register endpoint** in plugin setup:
```cpp
ContentRegistry::CommunicationInterface::registerNetworkEndpoint(
    "new/endpoint",
    [](const nlohmann::json &data) -> nlohmann::json {
        // Extract parameters
        auto param = data["param"].get<std::string>();

        // Perform operation
        // ...

        // Return result
        return {
            {"status", "success"},
            {"data", {
                {"result", value}
            }}
        };
    }
);
```

## Protocol Specifications

### MCP Protocol (MCP Server ↔ Claude)

- **Transport:** stdio (stdin/stdout)
- **Format:** JSON-RPC 2.0
- **Messages:**
  - `initialize`: Handshake
  - `tools/list`: List available tools
  - `tools/call`: Execute a tool
  - `resources/list`: List available resources (future)

### ImHex Protocol (MCP Server ↔ ImHex)

- **Transport:** TCP (localhost:31337)
- **Format:** Line-delimited JSON
- **Message Structure:**
  - Request: `{"endpoint": "...", "data": {...}}\n`
  - Response: `{"status": "...", "data": {...}}\n`

## Security Considerations

### Current Security Model

1. **Local-only communication:**
   - ImHex listens on localhost only
   - No remote access by default

2. **No authentication:**
   - Any local process can connect to ImHex
   - Suitable for single-user desktop environment

3. **File system access:**
   - ImHex has full file system access
   - MCP server inherits this access
   - Claude can open/read/write any file ImHex can access

### Recommendations

1. **For production use:**
   - Add authentication to ImHex network interface
   - Implement access control for sensitive operations
   - Sandbox file access

2. **For multi-user systems:**
   - Use firewall rules to restrict port 31337
   - Run ImHex with appropriate user permissions
   - Consider using Unix domain sockets instead of TCP

## Performance Considerations

### Bottlenecks

1. **TCP latency:** Local TCP has minimal latency (~1ms)
2. **JSON parsing:** Negligible for small messages
3. **File I/O:** Main bottleneck for large files
4. **Pattern compilation:** Can be slow for complex patterns

### Optimizations

1. **Connection pooling:** Reuse TCP connection across requests
2. **Caching:** MCP server could cache repeated queries
3. **Streaming:** For large data transfers, consider chunking
4. **Async operations:** Use async handlers for long operations

## Future Enhancements

### Planned Features

1. **Resource support:** Expose files/data as MCP resources
2. **Streaming data:** Support for large binary data transfers
3. **Visualization:** Return images/charts as ImageContent
4. **Real-time updates:** Push notifications for file changes
5. **Plugin integration:** Direct access to ImHex plugins

### ImHex Integration

1. **Native MCP support:** Implement MCP protocol in C++ plugin
2. **Enhanced endpoints:** Expose more ImHex features
3. **Bidirectional events:** ImHex can push updates to Claude
4. **Workspace sync:** Sync ImHex workspace with Claude context

## Testing

### Unit Tests

- Test ImHex connection handling
- Test JSON message parsing
- Test error handling and recovery
- Mock ImHex responses for testing

### Integration Tests

- Test with actual ImHex instance
- Test all MCP tools
- Test error scenarios
- Test concurrent requests

### Test Script

`test_server.py` provides basic connectivity testing:
- Verifies ImHex is running and accessible
- Tests capabilities endpoint
- Validates response format

## Deployment

### Development Setup

```bash
cd ImHex/mcp_server
pip install -r requirements.txt
python test_server.py
python server.py
```

### Production Deployment

1. **Package as Python module:**
   ```bash
   pip install -e .
   ```

2. **Configure Claude Desktop:**
   - Add to `claude_desktop_config.json`
   - Use absolute paths

3. **Run as service:**
   - Could be daemonized
   - Auto-start with ImHex

### Distribution

- Could be distributed as PyPI package
- Could be bundled with ImHex
- Could be installed via ImHex plugin manager (future)

## Troubleshooting

### Connection Issues

1. **Check ImHex is running:** `ps aux | grep imhex`
2. **Check port is listening:** `netstat -an | grep 31337`
3. **Check firewall:** Ensure localhost:31337 is accessible
4. **Check network interface setting:** Settings → General → Network Interface

### Protocol Issues

1. **Enable logging:** Set logging level to DEBUG
2. **Inspect messages:** Log all TCP messages
3. **Validate JSON:** Check message format
4. **Check ImHex logs:** Look for endpoint errors

## References

- [Model Context Protocol Specification](https://spec.modelcontextprotocol.io/)
- [ImHex Documentation](https://docs.werwolv.net/)
- [ImHex Source Code](https://github.com/WerWolv/ImHex)
- [ImHex Pattern Language](https://docs.werwolv.net/pattern-language/)
