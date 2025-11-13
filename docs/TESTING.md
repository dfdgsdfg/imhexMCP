# Testing Guide

This document describes the testing strategy and how to run tests for the ImHex MCP integration.

## Testing Strategy

The project uses two levels of testing:

1. **Unit Tests** - Fast tests using a mock ImHex server
2. **Integration Tests** - Real-world tests against an actual ImHex instance

## Unit Tests (Mock Server)

### Overview

Unit tests use a `MockImHexServer` to simulate ImHex responses without requiring a running ImHex instance. These tests are fast and can run in CI/CD pipelines.

### Location

`mcp-server/tests/test_imhex_client.py`

### What's Tested

- Connection and disconnection logic
- Command sending and response parsing
- Error handling
- Auto-reconnection
- Context manager usage
- Individual endpoint responses

### Running Unit Tests

```bash
cd mcp-server
python -m pytest tests/test_imhex_client.py -v
```

Or with unittest:

```bash
cd mcp-server
python tests/test_imhex_client.py
```

### Example Output

```
test_connection_success ... ok
test_connection_failure ... ok
test_send_command_success ... ok
test_send_command_error ... ok
test_context_manager ... ok
test_auto_reconnect ... ok

----------------------------------------------------------------------
Ran 6 tests in 0.245s

OK
```

## Integration Tests (Real ImHex)

### Overview

Integration tests connect to a real running ImHex instance and test all endpoints with actual data. These tests verify the complete integration works end-to-end.

### Location

`mcp-server/test_real_integration.py`

### Prerequisites

Before running integration tests:

1. **Build ImHex with MCP plugin**
   ```bash
   ./scripts/setup.sh
   ```

2. **Launch ImHex**
   ```bash
   ./ImHex/build/imhex
   ```

3. **Enable Network Interface**
   - Go to: **Edit → Settings → General**
   - Enable: **Network Interface**
   - Restart ImHex

4. **(Optional) Open a file**
   - Many tests work better with a file open
   - Open any binary file (e.g., an executable, image, PDF)

### Running Integration Tests

```bash
cd mcp-server
python test_real_integration.py
```

With custom host/port:

```bash
python test_real_integration.py --host localhost --port 31337
```

### What's Tested

The integration test suite tests all MCP endpoints:

1. **Connection** - Verifies ImHex is reachable
2. **Capabilities** - Gets ImHex version and available endpoints
3. **File Info** - Gets information about currently open file
4. **Data Read** - Reads bytes from the file
5. **Data Inspect** - Gets type interpretations of data
6. **Hash** - Calculates hashes (MD5, SHA-256, etc.)
7. **Search** - Searches for byte patterns
8. **Bookmarks** - Lists bookmarks
9. **Data Decode** - Decodes data (Base64, ASCII, etc.) [Improved version only]

### Example Output

```
======================================================================
ImHex MCP Server - Real Integration Tests
======================================================================

Testing against: localhost:31337
Using: Improved server implementation

Testing: Connection to ImHex
✓ Connected to ImHex at localhost:31337

Testing: Capabilities Endpoint
✓ ImHex version: 1.38.0
  Build commit: abc123def
  Build branch: master
  Available endpoints: 11
    - bookmarks/list
    - data/decode
    - data/hash
    - data/inspect
    - data/read
    - data/search
    - data/write
    - file/info
    - file/open
    - imhex/capabilities
    - pattern/execute

Testing: File Info Endpoint
✓ File is open in ImHex
  File: /path/to/firmware.bin
  Size: 1048576 bytes
  Name: firmware.bin

Testing: Data Read Endpoint
✓ Read 64 bytes from offset 0
  First 32 bytes: 7F454C4602010100000000000000000002003E0001000000

Testing: Data Inspect Endpoint
✓ Inspected 16 bytes at offset 0
  Data interpretations: 24
    uint8: 127
    int8: 127
    uint16_le: 17791
    uint16_be: 32581
    uint32_le: 1179403647
    uint32_be: 2135247942
    uint64_le: 72340172838076287
    uint64_be: 9187201950435737471
    float32_le: 1.234000
    double64_le: 3.141592
  ... and 14 more

Testing: Hash Endpoint
✓ SHA-256 hash calculated
  Algorithm: sha256
  Hash: a1b2c3d4e5f6...

Testing: Search Endpoint
✓ Search completed
  Pattern: 00
  Found 142 matches
  First few matches: [16, 17, 18, 32, 48]

Testing: Bookmarks List Endpoint
✓ Retrieved 3 bookmarks
  [0] Header: offset=0, size=64
  [1] Code Section: offset=4096, size=8192
  [2] Data Section: offset=12288, size=2048

Testing: Data Decode Endpoint
✓ Data decoded successfully
  Encoding: base64
  Decoded: f0VMRgIBAQAAAAAAAAAAAAIAPgABAAAA

======================================================================
Test Summary
======================================================================
Total tests run: 9
Passed: 9
Failed: 0

All tests passed!
```

## Connection Test

A simple connection test is also available:

### Location

`mcp-server/test_server.py`

### Running

```bash
cd mcp-server
python test_server.py
```

This quickly verifies:
- ImHex is running
- Network interface is enabled
- Basic communication works

### Example Output

```
ImHex MCP Server - Connection Test
==================================================
Testing connection to ImHex at localhost:31337...
✓ Connected to ImHex successfully

Sending capabilities request...

Response:
{
  "status": "success",
  "data": {
    "build": {
      "version": "1.38.0",
      "commit": "abc123",
      "branch": "master"
    }
  }
}

✓ ImHex is responding correctly

ImHex capabilities:
  build: {'version': '1.38.0', 'commit': 'abc123', 'branch': 'master'}

==================================================
✓ All tests passed!

You can now use the MCP server with Claude.
```

## Troubleshooting

### Connection Refused

**Problem**: Tests fail with "Connection refused"

**Solution**:
1. Make sure ImHex is running
2. Enable Network Interface in **Settings → General**
3. Restart ImHex after enabling

### Tests Skip File Operations

**Problem**: Tests show "Skipping - no file open"

**Solution**: Open a file in ImHex before running tests. Any binary file will work.

### Import Errors

**Problem**: `ModuleNotFoundError: No module named 'server'`

**Solution**: Make sure you're running from the `mcp-server` directory:
```bash
cd mcp-server
python test_real_integration.py
```

### Port Already in Use

**Problem**: Mock server tests fail with "Address already in use"

**Solution**:
1. Make sure no other tests are running
2. Wait a few seconds for ports to be released
3. Try again

## Continuous Integration

### Unit Tests in CI

Unit tests can run in CI/CD pipelines without ImHex:

```yaml
# Example GitHub Actions workflow
- name: Run unit tests
  run: |
    cd mcp-server
    python -m pytest tests/test_imhex_client.py
```

### Integration Tests in CI

Integration tests require ImHex to be built and running. This is more complex for CI but possible:

```yaml
# Example - would need ImHex build step first
- name: Build ImHex
  run: ./scripts/build.sh

- name: Start ImHex
  run: |
    ./ImHex/build/imhex --headless &
    sleep 5

- name: Run integration tests
  run: |
    cd mcp-server
    python test_real_integration.py
```

## Test Coverage

### Current Coverage

- **Unit Tests**: Core client functionality, error handling, connection management
- **Integration Tests**: All 9 MCP endpoints
- **Connection Tests**: Basic connectivity and capabilities

### What's Not Covered

- File write operations (to avoid modifying test files)
- Pattern execution (requires ImHex pattern language knowledge)
- Bookmark creation/deletion (to avoid modifying ImHex state)
- Edge cases with very large files
- Concurrent connections

### Future Improvements

- [ ] Add file write tests with temporary files
- [ ] Add pattern execution tests with sample patterns
- [ ] Add bookmark manipulation tests
- [ ] Add stress tests with large files
- [ ] Add concurrent connection tests
- [ ] Add performance benchmarks

## Best Practices

### When Writing Tests

1. **Use mock tests for logic** - Fast feedback, no dependencies
2. **Use integration tests for behavior** - Real-world verification
3. **Make tests independent** - Each test should be self-contained
4. **Clean up resources** - Use context managers, tearDown methods
5. **Test error cases** - Not just happy paths

### When Running Tests

1. **Run unit tests frequently** - During development
2. **Run integration tests before commits** - Verify everything works
3. **Run connection test after setup** - Quick sanity check
4. **Keep ImHex clean** - Close files between test runs for consistent results

## Summary

- **Quick check**: `python test_server.py`
- **Development**: `python tests/test_imhex_client.py`
- **Before commit**: `python test_real_integration.py`
- **CI/CD**: Unit tests only (mock server)

All tests are designed to be informative, showing exactly what's being tested and what the results are.

## Advanced Testing

### Property-Based Testing

Property-based testing uses randomly generated inputs to verify that code properties hold true across a wide range of scenarios.

#### Location

`lib/test_property_based.py`

#### What is Property-Based Testing?

Instead of writing specific test cases like "cache.put('key1', 'value1') should return 'value1'", you write general properties like "getting a key after putting it should always return the value, regardless of the key/value used".

#### Running Property-Based Tests

```bash
cd mcp-server
./venv/bin/pytest ../lib/test_property_based.py -v

# Show statistics
./venv/bin/pytest ../lib/test_property_based.py -v --hypothesis-show-statistics

# Increase test examples for more thoroughness
./venv/bin/pytest ../lib/test_property_based.py -v --hypothesis-seed=random
```

#### What's Tested

- **Cache Properties**: Get after put, overwrite behavior, multiple keys, operation sequences
- **Pattern Detection**: Sequential, strided, and random access patterns
- **Priority Queue**: Priority ordering, queue size invariants
- **Circuit Breaker**: Stays closed on success, opens on failures
- **Stateful Testing**: Random sequences of cache operations

#### Benefits

1. **Broader Coverage**: Tests thousands of cases automatically (default: 100 examples per property)
2. **Edge Case Discovery**: Finds corner cases developers didn't think of
3. **Reproducible**: Failed cases are shrunk to minimal examples
4. **Regression Prevention**: Generated cases can be added to test suite

#### Example Output

```
test_property_based.py::TestCacheProperties::test_cache_get_after_put PASSED
test_property_based.py::TestCacheProperties::test_cache_overwrite PASSED
test_property_based.py::TestPatternDetectorProperties::test_sequential_pattern_detection PASSED
test_property_based.py::TestPriorityQueueProperties::test_priority_ordering PASSED
test_property_based.py::TestCircuitBreakerProperties::test_circuit_stays_closed_on_success PASSED
test_property_based.py::TestCircuitBreakerProperties::test_circuit_opens_on_failures PASSED

Hypothesis Statistics:
  - test_cache_get_after_put: 100 examples, 0 failures
  - test_cache_overwrite: 100 examples, 0 failures
  - test_sequential_pattern_detection: 50 examples, 0 failures
  - test_priority_ordering: 50 examples, 0 failures
```

### Mutation Testing

Mutation testing evaluates test suite quality by introducing small bugs (mutations) into source code and checking if tests catch them.

#### What is Mutation Testing?

Mutation testing:
1. Introduces small bugs (mutations) into source code
2. Runs tests against mutated code
3. Checks if tests fail (catch the bug)

If tests pass despite mutations, the tests are insufficient.

#### Running Mutation Testing

```bash
# Install dependencies
cd mcp-server
./venv/bin/pip install mutmut

# Run mutation testing
cd ..
./mcp-server/venv/bin/mutmut run

# Show results
./mcp-server/venv/bin/mutmut results

# Show specific mutant
./mcp-server/venv/bin/mutmut show <mutant-id>

# Apply a mutant to investigate
./mcp-server/venv/bin/mutmut apply <mutant-id>
```

#### Configuration

Mutation testing is configured in `.mutmut_config.py`:
- **Paths to mutate**: `lib/` directory
- **Test command**: `python -m pytest lib/test_*.py -x --tb=short`
- **Workers**: 4 parallel workers
- **Filtering**: Skips documentation, logging, imports, and type hints

#### Mutation Operators

Common mutations applied:
1. **Arithmetic**: `+` → `-`, `*` → `/`
2. **Comparison**: `<` → `<=`, `==` → `!=`
3. **Boolean**: `and` → `or`, `True` → `False`
4. **Return**: `return x` → `return None`
5. **Constants**: `1` → `2`, `"foo"` → `"XXfooXX"`

#### Interpreting Results

```bash
# Mutation score calculation
Mutation Score = (Killed Mutants / Total Mutants) * 100%

# Goals:
# - 80%+: Good test coverage
# - 90%+: Excellent test coverage
# - 95%+: Outstanding test coverage
```

#### Example Output

```
⠧ 45/100  🎉 45  ⏰ 0  🤔 0  🙁 0  🔇 0

Legend:
🎉 Killed mutants (tests caught the bug)
⏰ Timeout (infinite loop)
🤔 Suspicious (tests passed despite mutation)
🙁 Survived (tests didn't catch the bug)
🔇 Skipped (filtered out)

Results:
  Mutation Score: 90.0% (45 killed / 50 total)
  Status: EXCELLENT
```

#### Workflow

```bash
# 1. Run mutation testing
./mcp-server/venv/bin/mutmut run

# 2. Check results
./mcp-server/venv/bin/mutmut results

# 3. Investigate survivors (mutants not caught)
./mcp-server/venv/bin/mutmut show 42

# 4. Add test to catch the survivor
# 5. Re-run mutation testing
./mcp-server/venv/bin/mutmut run
```

### Installing Dependencies

```bash
cd mcp-server
./venv/bin/pip install hypothesis mutmut
```

### Best Practices

#### Property-Based Testing

1. **Start Simple**: Begin with basic properties like "get after put returns the value"
2. **Use Strategies**: Leverage Hypothesis strategies to generate realistic inputs
3. **Add Assumptions**: Use `assume()` to filter out invalid input combinations
4. **Check Invariants**: Test properties that should always hold
5. **Set Reasonable Limits**: Don't generate gigabytes of data

Example:
```python
from hypothesis import given, strategies as st, assume

@given(
    key=st.text(min_size=1, max_size=100),
    value=st.text(min_size=0, max_size=1000)
)
async def test_cache_property(key, value):
    # Test with thousands of random key/value pairs
    cache = CacheTier("test", config)
    await cache.put(key, value, len(value))
    result = await cache.get(key)
    assert result == value
```

#### Mutation Testing

1. **Run Incrementally**: Test one module at a time
2. **Investigate Survivors**: Add tests for uncaught mutants
3. **Skip Non-Critical Code**: Focus on business logic
4. **Use in CI**: Run on pull requests to maintain quality
5. **Set Thresholds**: Require minimum mutation score (e.g., 80%)

### Test Coverage Summary

| Test Type | Coverage | Speed | When to Run |
|-----------|----------|-------|-------------|
| Unit Tests | Core logic | Fast | During development |
| Integration Tests | Full system | Medium | Before commits |
| Property-Based | Edge cases | Medium | Before releases |
| Mutation Testing | Test quality | Slow | Weekly/monthly |

### Resources

- [Hypothesis Documentation](https://hypothesis.readthedocs.io/)
- [Mutmut Documentation](https://mutmut.readthedocs.io/)
- [Property-Based Testing Guide](https://hypothesis.works/articles/what-is-property-based-testing/)
- [Mutation Testing Best Practices](https://pitest.org/quickstart/basic_concepts/)
