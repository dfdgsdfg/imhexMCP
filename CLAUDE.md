# ImHex MCP - Project Context for Claude

**Project**: ImHex MCP Server - Model Context Protocol integration for ImHex hex editor
**Status**: Production-ready (17/17 improvements complete - 100%)
**Last Updated**: 2025-11-15

---

## Quick Overview

This project provides a **Model Context Protocol (MCP) server** that exposes ImHex's hex editor capabilities to AI assistants. It allows programmatic access to binary file analysis, hex editing, pattern matching, and data inspection through a Python-based MCP interface.

**Key Achievement**: ✅ Fully automated file opening, comprehensive async client library, 18% performance improvement through systematic optimization.

---

## Project Structure

```
ImHexMCP/
├── lib/                          # Core Python library (optimized, production-ready)
│   ├── async_client.py          # Main async client (18% faster)
│   ├── cache.py                 # Response caching (28% faster, LRU + orjson)
│   ├── data_compression.py      # Compression (adaptive levels, buffer reuse)
│   ├── connection_pool.py       # Connection pooling
│   ├── request_batching.py      # Batch operations
│   ├── error_handling.py        # Retry logic & error handling
│   ├── security.py              # Input validation & sanitization
│   ├── config.py                # Pydantic-based configuration
│   ├── metrics.py               # Prometheus metrics
│   └── test_*.py                # Test suite (255/255 passing ✅)
│
├── mcp-server/                  # MCP server implementation
│   ├── server.py                # Main MCP server (2381 lines)
│   ├── enhanced_client.py       # Enhanced client wrapper
│   ├── imhex_cli.py            # CLI interface
│   └── benchmark_*.py          # Performance benchmarks
│
├── ImHex/                       # ImHex submodule (1.38.0.WIP)
│   └── build/imhex             # ImHex binary
│
├── docs/                        # Comprehensive documentation
│   ├── LIBRARY-ARCHITECTURE.md # 15+ Mermaid diagrams
│   ├── SECURITY.md             # Security guidelines
│   └── ...
│
├── IMPROVEMENTS-SUMMARY.md      # All 17 improvements documented
└── CLAUDE.md                    # This file
```

---

## Key Components

### 1. **Async Client Library** (`lib/async_client.py`)
- **Features**: Connection pooling, caching, compression, retry logic, batch operations
- **Performance**: 18% faster than baseline, 28% faster cache operations
- **Status**: Production-ready, 255/255 tests passing
- **Usage**:
  ```python
  from async_client import AsyncImHexClient

  async with AsyncImHexClient(host="localhost", port=31337) as client:
      result = await client.send_request("file/open", {"path": "/path/to/file.bin"})
  ```

### 2. **MCP Server** (`mcp-server/server.py`)
- **Protocol**: Model Context Protocol (stdio transport)
- **Tools**: 40+ tools for file operations, data inspection, pattern matching
- **Network**: Connects to ImHex on port 31337
- **Features**: Batch operations, streaming, caching, compression

### 3. **Performance Optimizations** (2 rounds completed)
- **Round 1**: orjson (2-3x faster JSON), LRU caching, fast size estimation
- **Round 2**: Compression buffer reuse, adaptive levels, async lock optimization
- **Results**: 18% faster, 16% fewer function calls, 25% less lock overhead

---

## Recent Improvements (All 17 Complete)

### Critical Infrastructure
1. ✅ **Pytest Framework** - 255 tests, 100% pass rate
2. ✅ **CI/CD Pipeline** - GitHub Actions (tests, security, lint, benchmarks)
3. ✅ **Type Hints** - 100% mypy compliance
4. ✅ **Python 3.14 Compatibility** - All tests passing
5. ✅ **Test Suite Fixes** - 255/255 tests passing (was 86%)

### Performance & Optimization
6. ✅ **Performance Profiling** - cProfile analysis, bottleneck identification
7. ✅ **Performance Optimization Round 1** - 18% faster (orjson, LRU, fast size estimation)
8. ✅ **Performance Optimization Round 2** - 25% lock reduction (compression buffer reuse, adaptive levels)

### Security & Quality
9. ✅ **Security Hardening** - SQL/Command injection prevention, IP filtering
10. ✅ **Code Quality Tools** - Black, flake8, mypy
11. ✅ **Centralized Config** - Pydantic-based validation

### Documentation & Testing
12. ✅ **Sphinx API Documentation** - 100% module coverage (21 modules)
13. ✅ **Architecture Docs** - 15+ Mermaid diagrams
14. ✅ **Property-Based Testing** - Hypothesis tests for edge cases
15. ✅ **Prometheus Metrics** - Production monitoring

### Analysis
16. ✅ **Module Consolidation Analysis** - Kept both sync/async for compatibility
17. ✅ **Test Coverage Expansion** - 217 tests across all components

---

## Working with This Codebase

### Running Tests
```bash
# All tests (255 tests)
pytest

# With coverage
pytest --cov=lib --cov=mcp-server --cov-report=term-missing

# Specific test files
pytest lib/test_async_client.py -v
pytest lib/test_connection_pool.py -v

# Markers
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests
pytest -m compression   # Compression tests
```

### Performance Profiling
```bash
cd lib
python3 profile_performance.py
```

### Code Quality
```bash
# Type checking
mypy lib/async_client.py lib/cache.py

# Formatting
black lib/ --line-length 79

# Linting
flake8 lib/ --max-line-length 79
```

### Running the MCP Server
```bash
# 1. Start ImHex (required)
./ImHex/build/imhex

# 2. Enable Network Interface (port 31337)
# Extras → Settings → General → Network Interface

# 3. Run MCP server
cd mcp-server
python3 server.py
```

---

## Important Files to Know

### Core Library Files
- **`lib/async_client.py`** (304 lines) - Main async client with all features
- **`lib/cache.py`** (794 lines) - Response caching with LRU eviction
- **`lib/data_compression.py`** (287 lines) - Adaptive compression
- **`lib/connection_pool.py`** (223 lines) - Connection pooling
- **`lib/error_handling.py`** (231 lines) - Retry logic & circuit breaker

### Configuration Files
- **`pytest.ini`** - Pytest configuration
- **`pyproject.toml`** - Tool configurations (black, mypy, etc.)
- **`lib/config.yaml.example`** - Example configuration
- **`mcp-server/requirements.txt`** - Production dependencies

### Documentation Files
- **`IMPROVEMENTS-SUMMARY.md`** - All 17 improvements documented
- **`lib/PERFORMANCE_RESULTS.md`** - Round 1 optimization results
- **`lib/OPTIMIZATION_RESULTS_ROUND2.md`** - Round 2 optimization results
- **`lib/PERFORMANCE_OPTIMIZATION.md`** - Original profiling analysis
- **`docs/LIBRARY-ARCHITECTURE.md`** - Architecture diagrams

---

## Performance Characteristics

### Baseline vs Optimized
| Metric | Baseline | Optimized | Improvement |
|--------|----------|-----------|-------------|
| Total runtime | 0.217s | 0.178s | **18% faster** |
| Function calls | 443,231 | 371,908 | **16% fewer** |
| Cache operations | 0.169s | ~0.127s | **28% faster** |
| JSON serialization | 0.072s | 0.002s | **97% faster** |
| Lock overhead | 24,044 calls | 18,024 calls | **25% fewer** |

### Real-World Performance
- **Cache hit rate**: 50-90% (typical workloads)
- **Compression ratio**: 99.1% (excellent)
- **Connection pool**: Reuse rate >80%
- **Batch operations**: 3-5x faster for multiple requests

---

## Key Design Decisions

### Why Async?
- ImHex MCP operations can be I/O-bound (network calls)
- Async allows concurrent operations (batch requests, streaming)
- Connection pooling maximizes efficiency

### Why orjson?
- 2-3x faster than stdlib json
- Graceful fallback to stdlib if not available
- 24x faster per call in practice (0.0036ms → 0.00015ms)

### Why LRU Caching?
- Cache key generation was 38% of execution time
- LRU cache with maxsize=1000 saves redundant hash calculations
- 26% faster cache key generation

### Why Adaptive Compression?
- Large files: Lower compression for speed
- Small files: Higher compression for better ratio
- Optimizes for real-world mixed workloads (5-15% improvement)

### Why Lock Optimization?
- time.time() calls under lock were wasteful
- Moving CacheEntry creation outside lock reduced contention
- 25% reduction in lock-held operations

---

## Testing Philosophy

### Coverage
- **255 tests total** (100% pass rate)
- **Unit tests**: Individual components
- **Integration tests**: Cross-component functionality
- **Property-based tests**: Hypothesis for edge cases
- **Compression tests**: Round-trip verification

### Test Files
- `test_async_client.py` - 35 tests (async client functionality)
- `test_connection_pool.py` - 34 tests (connection pooling)
- `test_property_based.py` - 11 tests (Hypothesis)
- `test_advanced_features.py` - Advanced caching & batching
- `test_security.py` - Security validation

---

## Common Tasks

### Adding a New Feature
1. Write tests first (TDD approach)
2. Implement feature in relevant module
3. Run tests: `pytest -v`
4. Type check: `mypy lib/your_module.py`
5. Format code: `black lib/your_module.py`
6. Update documentation

### Optimizing Performance
1. Profile: `python3 lib/profile_performance.py`
2. Identify bottlenecks (top functions by cumtime)
3. Implement optimization
4. Benchmark: Re-run profiler
5. Verify: All tests still pass
6. Document: Update PERFORMANCE_*.md

### Fixing a Bug
1. Write failing test that reproduces bug
2. Fix bug in source code
3. Verify test now passes
4. Check for regressions: `pytest`
5. Commit with descriptive message

---

## Git Workflow

### Branches
- **main** - Production-ready code (all tests passing)
- Feature branches as needed

### Commit Messages
Follow this format:
```
<type>: <short description>

<detailed description>

<metrics/results if applicable>

```

Types: feat, fix, perf, docs, test, refactor, chore

---

## Dependencies

### Production (`mcp-server/requirements.txt`)
- `mcp>=1.3.0` - Model Context Protocol
- `pydantic>=2.10.0` - Data validation
- `orjson>=3.9.0` - Fast JSON serialization
- `prometheus-client>=0.21.0` - Metrics

### Development (`mcp-server/dev-requirements.txt`)
- `pytest>=9.0.0` - Testing framework
- `pytest-asyncio>=0.24.0` - Async test support
- `pytest-cov>=6.0.0` - Coverage
- `mypy>=1.15.0` - Type checking
- `black>=25.0.0` - Code formatting
- `hypothesis>=6.120.0` - Property-based testing

---

## Security Considerations

### Input Validation
- All user inputs validated with Pydantic
- Path traversal prevention
- SQL injection prevention
- Command injection prevention

### Network Security
- IP allowlist/blocklist support
- Rate limiting (TODO)
- TLS/SSL support (TODO)

### Code Security
- No eval() or exec() usage
- Parameterized queries
- Secure file operations
- Input sanitization

See `docs/SECURITY.md` for full details.

---

## Troubleshooting

### Tests Failing?
```bash
# Run specific test with verbose output
pytest lib/test_async_client.py::TestClass::test_method -vv

# Check for import errors
python3 -c "import sys; sys.path.insert(0, 'lib'); from async_client import AsyncImHexClient"

# Clear pytest cache
rm -rf .pytest_cache
```

### Type Errors?
```bash
# Check specific file
mypy lib/async_client.py --show-error-codes

# Ignore specific error
# type: ignore[error-code]
```

### Performance Regression?
```bash
# Profile before and after
python3 lib/profile_performance.py > before.txt
# ... make changes ...
python3 lib/profile_performance.py > after.txt
diff before.txt after.txt
```

---

## Future Optimization Opportunities

If further optimization is desired (see `lib/OPTIMIZATION_RESULTS_ROUND2.md`):

1. **Lock-free data structures** (15-20ms potential)
   - Atomic operations for stats counters
   - Reader-writer locks for cache access

2. **Memory pooling** (5-10ms potential)
   - Pre-allocate CacheEntry objects
   - Buffer pooling for compression

3. **Batch operations** (10-15ms potential)
   - Batch cache insertions
   - Amortize lock overhead

**Combined potential**: Additional 20-30% improvement

---

## Contact & Resources

- **Repository**: https://github.com/jmpnop/imhexMCP.git
- **ImHex**: https://github.com/WerWolv/ImHex
- **MCP Specification**: https://modelcontextprotocol.io/

---

## Notes for AI Assistants

### When Making Changes
1. **Always run tests** before committing: `pytest`
2. **Check types** if modifying typed code: `mypy lib/module.py`
3. **Update documentation** if adding features
4. **Profile if optimizing** performance: `lib/profile_performance.py`

### Code Style
- **Line length**: 79 characters (black --line-length 79)
- **Type hints**: Required for public APIs
- **Docstrings**: Google style
- **Imports**: Sorted, grouped (stdlib, third-party, local)

### Performance-Critical Paths
- `cache.py:_generate_key()` - Already optimized with orjson + LRU
- `cache.py:set()` - Lock minimized, entry created outside lock
- `data_compression.py:compress_data()` - Adaptive compression, buffer reuse
- Avoid adding `time.time()` calls inside locks

### Testing Requirements
- **New features**: Write tests first (TDD)
- **Bug fixes**: Write failing test, then fix
- **Performance**: Before/after profiling required
- **Coverage**: Aim for >80% coverage on new code

---

**Last Updated**: 2025-11-15
**Project Status**: Production-ready (17/17 improvements complete)
**Test Status**: ✅ 255/255 passing
**Performance**: ✅ 18% faster than baseline
