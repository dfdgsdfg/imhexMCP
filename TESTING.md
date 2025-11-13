# Testing Guide

## Overview

This project uses **pytest** as the primary testing framework, providing comprehensive test coverage for all modules including compression, caching, connection pooling, and more.

## Quick Start

### Installation

```bash
# Install testing dependencies
cd mcp-server
./venv/bin/pip install -r dev-requirements.txt
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=lib --cov=mcp-server --cov-report=term-missing

# Run specific test file
pytest mcp-server/test_compression_pytest.py

# Run tests matching a pattern
pytest -k "compression"

# Run unit tests only (fast)
pytest -m unit

# Run integration tests (requires ImHex running)
pytest -m integration

# Verbose output
pytest -v

# Stop on first failure
pytest -x

# Run tests in parallel (faster)
pytest -n auto  # requires pytest-xdist
```

## Test Organization

### Test Markers

Tests are organized using pytest markers:

- `@pytest.mark.unit` - Unit tests that don't require external dependencies
- `@pytest.mark.integration` - Integration tests that require ImHex running
- `@pytest.mark.slow` - Tests that take more than 1 second
- `@pytest.mark.compression` - Compression-related tests
- `@pytest.mark.async` - Asynchronous tests
- `@pytest.mark.network` - Tests requiring network access
- `@pytest.mark.benchmark` - Performance benchmark tests

### Running Specific Test Types

```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Exclude slow tests
pytest -m "not slow"

# Run compression tests only
pytest -m compression
```

## Test Structure

### Example Test File

```python
import pytest
from your_module import YourClass

# Fixtures for setup/teardown
@pytest.fixture
def sample_data():
    """Fixture providing test data."""
    return {"key": "value"}

# Test class organization
class TestYourFeature:
    """Test suite for YourFeature."""

    @pytest.mark.unit
    def test_basic_functionality(self, sample_data):
        """Test basic functionality."""
        result = YourClass.process(sample_data)
        assert result is not None

    @pytest.mark.unit
    @pytest.mark.parametrize("input,expected", [
        (1, 2),
        (2, 4),
        (3, 6),
    ])
    def test_multiple_inputs(self, input, expected):
        """Test with multiple parameter sets."""
        assert YourClass.double(input) == expected
```

## Coverage Reports

### Generating Coverage

```bash
# Terminal report
pytest --cov=lib --cov=mcp-server --cov-report=term-missing

# HTML report (opens in browser)
pytest --cov=lib --cov=mcp-server --cov-report=html
open htmlcov/index.html

# XML report (for CI/CD)
pytest --cov=lib --cov=mcp-server --cov-report=xml
```

### Coverage Goals

- **Minimum coverage**: 80%
- **Target coverage**: 90%+
- **Critical modules** (compression, caching): 95%+

## Test Examples

### Current Test Files

1. **test_compression_pytest.py** - Comprehensive compression module tests
   - 20 tests covering all compression functionality
   - Fixtures for common test data
   - Parametrized tests for algorithms
   - Performance benchmarks

2. **test_compression.py** (legacy) - Original test format
   - Being converted to pytest format
   - Will be deprecated once conversion is complete

3. **test_client_compression.py** - AsyncImHexClient compression integration
   - Tests client-level compression features

## Best Practices

### Writing Tests

1. **Use descriptive test names**: `test_compress_decompress_cycle`
2. **One assertion per test** (when possible)
3. **Use fixtures** for common setup
4. **Use parametrize** for testing multiple inputs
5. **Add docstrings** explaining what is tested
6. **Mark tests appropriately** (unit, integration, slow, etc.)

### Test Organization

```
mcp-server/
├── test_compression_pytest.py    # Pytest-style tests
├── test_connection_pool.py        # Connection pooling tests
├── test_caching.py                # Caching tests
└── tests/                         # Additional test subdirectory
    └── test_imhex_client.py      # Client integration tests
```

## Continuous Integration

Tests are automatically run on:
- Every push to main branch
- Every pull request
- Nightly builds (full test suite)

See `.github/workflows/tests.yml` for CI configuration.

## Troubleshooting

### Common Issues

**Import errors:**
```bash
# Ensure lib is in Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)/lib"
```

**Coverage warnings:**
```bash
# Install coverage extras
pip install coverage[toml]
```

**Async test failures:**
```bash
# Ensure pytest-asyncio is installed
pip install pytest-asyncio
```

### Debugging Tests

```bash
# Run with Python debugger
pytest --pdb

# Print output (even on success)
pytest -s

# Show local variables on failure
pytest -l

# Increase verbosity
pytest -vv
```

## Performance Testing

### Running Benchmarks

```bash
# Run all benchmarks
pytest -m benchmark

# Run benchmark with statistics
pytest -m benchmark --benchmark-only

# Save benchmark results
pytest -m benchmark --benchmark-save=results
```

### Benchmark Files

- `benchmark_optimizations.py` - Compression benchmarks
- `benchmark_caching.py` - Cache performance
- `benchmark_batching.py` - Request batching
- `benchmark_connection_pool.py` - Connection pooling

## Migration Guide

### Converting Old Tests to Pytest

1. **Replace custom assertions** with pytest assertions:
   ```python
   # Old
   if result != expected:
       print("✗ Test failed")
       return False

   # New
   assert result == expected, "Test failed"
   ```

2. **Use fixtures** instead of setup functions:
   ```python
   # Old
   def test_something():
       data = setup_data()
       # test code

   # New
   @pytest.fixture
   def data():
       return setup_data()

   def test_something(data):
       # test code uses fixture
   ```

3. **Add markers** for organization:
   ```python
   @pytest.mark.unit
   @pytest.mark.compression
   def test_feature():
       pass
   ```

4. **Use parametrize** for multiple test cases:
   ```python
   @pytest.mark.parametrize("algo", ["zstd", "gzip", "zlib"])
   def test_algorithms(algo):
       # test runs 3 times, once per algorithm
       pass
   ```

## Resources

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-cov Documentation](https://pytest-cov.readthedocs.io/)
- [pytest-asyncio Documentation](https://pytest-asyncio.readthedocs.io/)

## Summary

- **Framework**: pytest 9.0+
- **Coverage**: pytest-cov with 80%+ target
- **Async support**: pytest-asyncio
- **Markers**: unit, integration, slow, compression, etc.
- **CI/CD**: GitHub Actions (automated on every push)

Run `pytest --help` for more options.
