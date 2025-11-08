# ImHex MCP Server Tests

Unit and integration tests for the ImHex MCP Server.

## Running Tests

### All Tests

```bash
cd mcp_server
python -m pytest tests/
```

### Specific Test File

```bash
python -m pytest tests/test_imhex_client.py
```

### With Coverage

```bash
python -m pytest --cov=server_improved --cov-report=html tests/
```

### Verbose Output

```bash
python -m pytest -v tests/
```

## Test Structure

- `test_imhex_client.py` - Tests for ImHexClient and connection management
- `test_server.py` - Tests for MCP server functionality (to be added)
- `test_tools.py` - Tests for individual MCP tools (to be added)

## Mock Server

The tests include a `MockImHexServer` that simulates ImHex's TCP interface for testing without requiring a running ImHex instance.

## Adding Tests

To add new tests:

1. Create a new test file following the pattern `test_*.py`
2. Import necessary modules and the mock server
3. Write test cases using unittest or pytest
4. Run tests to verify

## Dependencies

Install test dependencies:

```bash
pip install pytest pytest-cov pytest-asyncio
```
