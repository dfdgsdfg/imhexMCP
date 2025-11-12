# ImHex MCP Production Deployment Guide

## Overview

This guide covers deploying the ImHex MCP server with performance optimizations in production environments.

## Quick Start

### 1. Enable Performance Optimizations

```python
# mcp-server configuration
config = ServerConfig(
    imhex_host="localhost",
    imhex_port=31337,

    # Enable optimizations
    enable_performance_optimizations=True,
    enable_cache=True,
    cache_max_size=2000,  # Tune based on memory
    enable_profiling=False,  # Disable in production for max performance
    enable_lazy_loading=True,

    # Connection settings
    connection_timeout=5.0,
    read_timeout=30.0,
    max_retries=3
)
```

### 2. Test Configuration

```bash
# Run integration tests
cd mcp-server
python3 test_integration.py

# Run benchmarks
cd tests
python3 benchmark_performance.py
```

### 3. Monitor Performance

```python
# Enable monitoring
if config.enable_profiling:
    client.print_performance_report()

# Check cache stats
stats = client.get_cache_stats()
print(f"Cache hit rate: {stats['hit_rate']:.1f}%")
```

## Configuration Profiles

### Production (High Performance)

```python
ServerConfig(
    enable_performance_optimizations=True,
    enable_cache=True,
    cache_max_size=5000,  # Large cache
    enable_profiling=False,  # No overhead
    enable_lazy_loading=True,
    connection_timeout=5.0,
    read_timeout=60.0,  # Longer for large operations
    max_retries=3
)
```

**Best for**: Production workloads, high throughput

### Development (Debugging)

```python
ServerConfig(
    enable_performance_optimizations=True,
    enable_cache=False,  # Fresh data
    enable_profiling=True,  # Detailed metrics
    enable_lazy_loading=False,  # Immediate feedback
    log_level=LogLevel.DEBUG
)
```

**Best for**: Development, troubleshooting

### Staging (Testing)

```python
ServerConfig(
    enable_performance_optimizations=True,
    enable_cache=True,
    cache_max_size=1000,
    enable_profiling=True,  # Monitor performance
    enable_lazy_loading=True
)
```

**Best for**: Pre-production testing, performance validation

## Best Practices

### 1. Cache Configuration

**Guidelines**:
- Start with `cache_max_size=1000`
- Monitor hit rate (target >80%)
- Increase size if hit rate is low
- Decrease if memory constrained

**Tuning**:
```python
# Check hit rate
stats = client.get_cache_stats()
if stats['hit_rate'] < 80:
    # Increase cache size
    config.cache_max_size = 2000
```

### 2. Error Handling

**Always use try/except**:
```python
try:
    result = client.send_command("endpoint", data)
    if result.get("status") != "success":
        logger.error(f"Operation failed: {result.get('data', {}).get('error')}")
except ConnectionError as e:
    logger.error(f"Connection failed: {e}")
    # Implement retry logic
except Exception as e:
    logger.exception("Unexpected error")
```

### 3. Resource Cleanup

**Use context managers**:
```python
with create_client_from_config(config) as client:
    # Client automatically cleaned up
    result = client.send_command("capabilities")
# Resources freed here
```

### 4. Monitoring

**Key Metrics**:
- Cache hit rate (>80% is good)
- P95 latency (<50ms for cached, <200ms for network)
- Error rate (<1%)
- Memory usage

### 5. Logging

**Configuration**:
```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('imhex_mcp.log'),
        logging.StreamHandler()
    ]
)
```

## Troubleshooting

### Issue: Low Cache Hit Rate

**Symptoms**: Hit rate <50%, slow performance

**Solutions**:
1. Increase `cache_max_size`
2. Check if cache is being cleared too often
3. Verify TTL settings are appropriate
4. Monitor which endpoints have low hit rates

### Issue: High Memory Usage

**Symptoms**: Increasing memory consumption

**Solutions**:
1. Reduce `cache_max_size`
2. Check for memory leaks (use profiling)
3. Monitor cache size: `stats['size']`
4. Clear cache periodically if needed

### Issue: Connection Errors

**Symptoms**: "Connection refused" errors

**Solutions**:
1. Verify ImHex is running
2. Check port 31337 is accessible
3. Verify Network Interface is enabled in ImHex
4. Check firewall settings
5. Increase `connection_timeout`

### Issue: Slow Performance

**Symptoms**: High latency, timeouts

**Solutions**:
1. Enable profiling temporarily to identify bottlenecks
2. Check cache hit rate
3. Verify network latency to ImHex
4. Increase `read_timeout` for large operations
5. Use streaming for large data transfers

## Security Considerations

### 1. Network Security

- ImHex listens on localhost by default (secure)
- If exposing remotely, use firewall rules
- Consider VPN/SSH tunnel for remote access

### 2. Data Validation

- Validate all input parameters
- Check response status before processing
- Implement rate limiting if needed

### 3. Error Messages

- Don't expose internal paths in errors
- Log detailed errors, return generic messages to users
- Sanitize error messages

## Performance Tuning

### Step 1: Baseline

```bash
# Run benchmark
python3 tests/benchmark_performance.py

# Save results
mv benchmark_results_*.json baseline_results.json
```

### Step 2: Tune Configuration

Try different cache sizes:
```python
# Test various sizes
for size in [500, 1000, 2000, 5000]:
    config.cache_max_size = size
    # Run benchmark
    # Compare results
```

### Step 3: Validate

```bash
# Compare against baseline
python3 tests/compare_benchmarks.py --baseline baseline_results.json \
    --current new_results.json
```

### Step 4: Monitor

```python
# In production
if config.enable_profiling:
    stats = client.get_performance_stats()
    # Log to monitoring system
    metrics.gauge('cache_hit_rate', cache_stats['hit_rate'])
    metrics.gauge('p95_latency', perf_stats['p95_time_ms'])
```

## Scaling Considerations

### Vertical Scaling

- Increase `cache_max_size` with more RAM
- Use faster storage for ImHex files
- Optimize ImHex configuration

### Horizontal Scaling

- Run multiple ImHex instances
- Load balance across instances
- Use connection pooling
- Consider async client for high concurrency

## Deployment Checklist

**Pre-Deployment**:
- [ ] All tests passing
- [ ] Benchmarks run and acceptable
- [ ] Configuration tuned for environment
- [ ] Logging configured
- [ ] Monitoring in place
- [ ] Error handling tested

**Deployment**:
- [ ] ImHex installed and configured
- [ ] Network Interface enabled
- [ ] MCP server deployed
- [ ] Configuration applied
- [ ] Health checks passing

**Post-Deployment**:
- [ ] Monitor cache hit rate
- [ ] Monitor error rate
- [ ] Monitor latency metrics
- [ ] Verify logging working
- [ ] Test failover scenarios

## Maintenance

### Regular Tasks

**Daily**:
- Check error logs
- Monitor cache hit rate
- Review performance metrics

**Weekly**:
- Run regression benchmarks
- Review and archive logs
- Check for updates

**Monthly**:
- Performance review
- Capacity planning
- Configuration tuning

### Backup Strategy

**Configuration**:
- Version control for config files
- Document configuration changes
- Test restore procedures

**Monitoring Data**:
- Archive performance metrics
- Keep benchmark history
- Track trends over time

## Support

### Getting Help

1. Check documentation: `docs/` directory
2. Review examples: `examples/` directory
3. Run tests: `tests/` directory
4. Check GitHub issues

### Reporting Issues

Include:
- Configuration used
- Error messages/stack traces
- Steps to reproduce
- ImHex version
- Python version
- OS/environment details

## Conclusion

Following this guide ensures optimal performance and reliability for ImHex MCP server deployments. Monitor key metrics, tune configuration based on workload, and maintain regular maintenance schedules for best results.

---

**Version**: 1.0
**Last Updated**: 2025-01-12
**Status**: Production Ready
