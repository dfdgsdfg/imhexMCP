# ImHex MCP Integration Tests

Comprehensive integration tests for all ImHex MCP endpoints.

## Prerequisites

1. **ImHex with MCP plugin installed**
2. **Network Interface enabled** in Settings → General
3. **Python 3.x** installed

## Running Tests

### Run all tests:
```bash
cd tests/integration
python3 test_all_endpoints.py
```

### Verbose mode:
```bash
python3 test_all_endpoints.py --verbose
```

### Custom host/port:
```bash
python3 test_all_endpoints.py --host 192.168.1.100 --port 31337
```

## Test Categories

The test suite covers 8 categories of endpoints:

1. **Core Endpoints** - capabilities, status
2. **File Operations** - file/open, file/list, file/close
3. **Data Operations** - data/read, data/write, data/size
4. **Hashing Operations** - MD5, SHA-1, SHA-256, SHA-384, SHA-512
5. **Search Operations** - Hex and string pattern search
6. **Analysis Operations** - entropy, statistics, strings, magic, disassemble
7. **Bookmark Operations** - bookmark/add, bookmark/list, bookmark/remove
8. **Batch Operations** - batch/hash, batch/search, batch/diff

## Test Output

### Success:
```
======================================================================
ImHex MCP Integration Tests
  Host: localhost:31337
======================================================================

[1/8] Testing Core Endpoints
----------------------------------------------------------------------
  ✓ capabilities
  ✓ status

[2/8] Testing File Operations
----------------------------------------------------------------------
  ✓ file/list (empty)
  ✓ file/open
  ✓ file/list (with files)
  ✓ file/current
  ✓ file/info

...

======================================================================
INTEGRATION TEST RESULTS
======================================================================
  Passed: 45
  Failed: 0
  Total:  45

  ✅ All tests PASSED!
======================================================================
```

### Failure:
```
[3/8] Testing Data Operations
----------------------------------------------------------------------
  ✓ data/read (64 bytes)
  ✗ data/read (1KB): Invalid provider ID
  ✓ data/size

======================================================================
INTEGRATION TEST RESULTS
======================================================================
  Passed: 43
  Failed: 2
  Total:  45

  ❌ 2 test(s) FAILED
======================================================================
```

## Exit Codes

- `0` - All tests passed
- `1` - One or more tests failed

## Continuous Integration

To use in CI/CD pipelines:

```bash
# Start ImHex in headless mode (if supported)
./imhex --headless &
IMHEX_PID=$!

# Wait for ImHex to start
sleep 5

# Run tests
python3 tests/integration/test_all_endpoints.py

# Save exit code
EXIT_CODE=$?

# Kill ImHex
kill $IMHEX_PID

# Exit with test result
exit $EXIT_CODE
```

## Troubleshooting

### Connection Refused

```
Error: Cannot connect to ImHex. Is it running?
```

**Solution:**
1. Start ImHex
2. Go to Settings → General
3. Enable "Network Interface"
4. Verify port 31337 is not in use

### Tests Timing Out

**Solution:**
- Increase timeout with `--timeout` flag
- Check system resources
- Ensure ImHex is responsive

### Provider Not Found

**Solution:**
- Ensure test files can be created in `/tmp`
- Check file permissions
- Verify ImHex can open files

## Adding New Tests

To add tests for a new endpoint:

1. Add method to `ImHexMCPTest` class:
```python
def test_new_category(self):
    """Test new endpoint category."""
    print("\n[X/8] Testing New Category")
    print("-" * 70)

    result = self.send_request("new/endpoint", {"param": "value"})
    self.assert_success(result, "new/endpoint")
```

2. Call method in `run_all_tests()`:
```python
def run_all_tests(self):
    # ... existing tests ...
    self.test_new_category()
```

## Contributing

Contributions welcome! Please ensure:
- All tests pass before submitting PR
- New endpoints have corresponding tests
- Tests are well-documented

## Support

- Documentation: [../../docs/](../../docs/)
- Issues: https://github.com/jmpnop/imhexMCP/issues
