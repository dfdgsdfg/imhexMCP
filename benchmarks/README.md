# ImHex MCP Benchmarks & Profiling

Performance testing and resource profiling tools for ImHex MCP.

## Tools

### 1. endpoint_benchmarks.py

Comprehensive benchmarking suite for all ImHex MCP endpoints.

**Features:**
- Latency measurements (min, max, mean, median, p95, p99)
- Throughput calculations (requests per second)
- Multiple file size scenarios
- JSON report generation
- Performance regression tracking

**Usage:**
```bash
# Basic benchmarking
python3 endpoint_benchmarks.py

# Save results to file
python3 endpoint_benchmarks.py --output results.json

# Custom iterations and warmup
python3 endpoint_benchmarks.py --iterations 200 --warmup 20

# Custom host/port
python3 endpoint_benchmarks.py --host 192.168.1.100 --port 31337
```

**Example Output:**
```
======================================================================
BENCHMARK SUMMARY
======================================================================

CORE:
  Operation                            Mean (ms)    P95 (ms)     RPS
  --------------------------------------------------------------------
  capabilities                         1.234        1.456        810.37
  file/list                            0.987        1.123        1013.17

DATA_READ:
  Operation                            Mean (ms)    P95 (ms)     RPS
  --------------------------------------------------------------------
  data/read (64 bytes)                 2.345        2.678        426.44
  data/read (1KB)                      3.456        3.890        289.35
  data/read (4KB)                      5.678        6.234        176.12

HASHING:
  Operation                            Mean (ms)    P95 (ms)     RPS
  --------------------------------------------------------------------
  data/hash (MD5, 1KB)                 4.567        5.123        219.03
  data/hash (SHA256, 1KB)              5.234        5.890        191.06
```

---

### 2. profile_imhex.py

Memory and CPU profiling tool for ImHex MCP operations.

**Features:**
- CPU usage monitoring
- Memory usage tracking (RSS, VMS)
- Thread count monitoring
- I/O statistics (platform-dependent)
- Memory leak detection
- Continuous monitoring mode

**Requirements:**
```bash
pip3 install psutil
```

**Usage:**

#### Profile Specific Operation:
```bash
python3 profile_imhex.py operation \
  --endpoint "data/hash" \
  --params '{"provider_id":0,"offset":0,"size":1024,"algorithm":"sha256"}' \
  --iterations 100
```

#### Continuous Monitoring:
```bash
# Monitor for 60 seconds with 1-second intervals
python3 profile_imhex.py monitor --duration 60 --interval 1.0
```

**Example Output:**

**Operation Profiling:**
```
======================================================================
Profiling Operation: data/hash
  Iterations: 100
  Sample Interval: 0.1s
======================================================================

Found ImHex process (PID: 12345)
  Baseline CPU: 2.5%
  Baseline Memory: 156.3 MB

Running 100 iterations...
  Progress: 10/100
  Progress: 20/100
  ...

Completed in 12.34s

======================================================================
PROFILING ANALYSIS
======================================================================

Operations:
  Total:      100
  Successful: 100
  Failed:     0

Operation Duration (seconds):
  Min:    0.003456s
  Max:    0.012345s
  Mean:   0.005678s
  Median: 0.005234s
  P95:    0.008901s
  P99:    0.011234s

CPU Delta (%):
  Min:    +0.12%
  Max:    +5.67%
  Mean:   +2.34%
  Median: +2.12%

Memory Delta (MB):
  Min:    +0.001 MB
  Max:    +0.234 MB
  Mean:   +0.012 MB
  Median: +0.010 MB

======================================================================
```

**Continuous Monitoring:**
```
======================================================================
Continuous Resource Monitoring
  Duration: 60s
  Interval: 1.0s
======================================================================

Monitoring ImHex (PID: 12345)

Time       CPU %      Memory MB    Threads
------------------------------------------
     0.0s    2.3%      156.2 MB        15
     1.0s    3.1%      157.1 MB        15
     2.0s    2.8%      157.3 MB        15
     3.0s    4.5%      158.2 MB        16
    ...

======================================================================
MONITORING SUMMARY
======================================================================
  Average CPU: 3.2%
  Average Memory: 157.8 MB
  Memory Range: 156.2 - 159.4 MB
  Samples Collected: 60
======================================================================
```

---

## Use Cases

### Performance Regression Testing

Track performance over time by saving benchmark results:

```bash
# Run benchmarks and save to timestamped file
DATE=$(date +%Y%m%d_%H%M%S)
python3 endpoint_benchmarks.py --output results_$DATE.json

# Compare with baseline
diff results_baseline.json results_$DATE.json
```

### Memory Leak Detection

Profile operations to detect memory leaks:

```bash
# Profile file/open with many iterations
python3 profile_imhex.py operation \
  --endpoint "file/open" \
  --params '{"path":"/tmp/test.bin"}' \
  --iterations 1000

# Check for increasing memory delta
# If mean > 1.0 MB, investigate further
```

### Load Testing

Benchmark under sustained load:

```bash
# Monitor system while running benchmarks
python3 profile_imhex.py monitor --duration 120 &
MONITOR_PID=$!

python3 endpoint_benchmarks.py --iterations 1000

kill $MONITOR_PID
```

### CI/CD Integration

Add to CI pipeline to catch regressions:

```yaml
# Example GitHub Actions workflow
- name: Run Performance Tests
  run: |
    python3 benchmarks/endpoint_benchmarks.py --output perf_results.json

- name: Check for Regressions
  run: |
    python3 scripts/check_perf_regression.py \
      --baseline baseline_perf.json \
      --current perf_results.json \
      --threshold 10  # 10% regression threshold
```

---

## Performance Targets

Based on typical hardware (2020+ laptop/desktop):

| Category | Operation | Target Mean | Target P95 |
|----------|-----------|-------------|------------|
| Core | capabilities | < 2ms | < 3ms |
| Core | file/list | < 1ms | < 2ms |
| Data | read (64B) | < 3ms | < 5ms |
| Data | read (1KB) | < 5ms | < 8ms |
| Data | read (4KB) | < 10ms | < 15ms |
| Hash | MD5 (1KB) | < 5ms | < 8ms |
| Hash | SHA256 (1KB) | < 6ms | < 10ms |
| Search | hex pattern (1MB) | < 50ms | < 100ms |
| Analysis | entropy (1KB) | < 10ms | < 20ms |
| Analysis | statistics (1KB) | < 15ms | < 30ms |

---

## Interpreting Results

### Latency Metrics

- **Min/Max**: Range of observed latencies
- **Mean**: Average latency across all iterations
- **Median**: Middle value, less affected by outliers
- **P95**: 95th percentile - 95% of requests complete within this time
- **P99**: 99th percentile - 99% of requests complete within this time

### Throughput

- **RPS** (Requests Per Second): How many operations can be performed per second
- Higher is better
- Limited by both network and processing overhead

### CPU & Memory

- **CPU Delta**: Change in CPU usage during operation
  - Negative values: Operation ran during idle time
  - Positive values: Operation increased CPU load
- **Memory Delta**: Change in memory usage
  - Small increases (< 0.1 MB) are normal
  - Large or growing increases may indicate leaks

---

## Troubleshooting

### ImHex Not Found

```
Error: ImHex process not found
```

**Solution:**
- Ensure ImHex is running
- Verify process name contains "imhex"
- Check with: `ps aux | grep imhex`

### Connection Refused

```
Error: Cannot connect to ImHex
```

**Solution:**
- Enable Network Interface in Settings → General
- Verify port 31337 is not blocked
- Check firewall settings

### High Variance

If P95/P99 are significantly higher than mean:

**Possible Causes:**
- System load from other processes
- Garbage collection
- Disk I/O wait
- Network congestion

**Solution:**
- Run on idle system
- Increase warmup iterations
- Close unnecessary applications

---

## Contributing

To add new benchmarks:

1. Add benchmark case to `endpoint_benchmarks.py`
2. Document expected performance
3. Update this README with new metrics

## Support

- Documentation: [../docs/](../docs/)
- Issues: https://github.com/jmpnop/imhexMCP/issues
