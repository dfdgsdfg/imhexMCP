#!/usr/bin/env python3
"""
ImHex MCP Server Library Modules Demo

Demonstrates the use of the enhanced server library modules:
- Security (rate limiting, circuit breaker, input validation)
- Caching (LRU, TTL caching strategies)
- Metrics (request tracking, performance monitoring)
- Logging (structured logging with context)
- Configuration validation

This example shows how to build a robust MCP client using these modules.
"""

import sys
import time
from pathlib import Path

# Add lib to path so we can import modules
sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))

from security import (
    RateLimiter,
    CircuitBreaker,
    SecurityManager,
    SecurityConfig,
    validate_input,
)
from caching import CacheManager, CacheConfig, CacheStrategy
from metrics import MetricsCollector, MetricType
from logging_config import setup_logging, get_logger
from config_validator import ConfigValidator, validate_and_log


class EnhancedMCPClient:
    """MCP Client with security, caching, and monitoring."""

    def __init__(self, config: dict):
        """Initialize client with enhanced modules."""
        # Setup structured logging
        setup_logging(name="imhex_mcp", level="INFO", console=True)
        self.logger = get_logger("client", {"component": "enhanced_client"})

        # Validate configuration
        validator = ConfigValidator()
        is_valid, results = validator.validate_all(type("Config", (), config)())
        if not is_valid:
            self.logger.error("Configuration validation failed")
            for result in results:
                self.logger.error(
                    f"{result.level.value}: {result.field} - {result.message}"
                )
            raise ValueError("Invalid configuration")

        self.config = config
        self.logger.info("Configuration validated successfully")

        # Initialize security
        security_config = SecurityConfig(
            rate_limit_requests=config.get("rate_limit_requests", 100),
            rate_limit_window=config.get("rate_limit_window", 60),
            circuit_breaker_threshold=config.get("circuit_breaker_threshold", 5),
            circuit_breaker_timeout=config.get("circuit_breaker_timeout", 30),
        )
        self.security = SecurityManager(security_config)
        self.logger.info("Security manager initialized")

        # Initialize caching
        cache_config = CacheConfig(
            max_size=config.get("cache_max_size", 1000),
            ttl=config.get("cache_ttl", 300),
            strategy=CacheStrategy.LRU,
        )
        self.cache = CacheManager(cache_config)
        self.logger.info("Cache manager initialized")

        # Initialize metrics
        self.metrics = MetricsCollector()
        self.logger.info("Metrics collector initialized")

    def read_data(self, provider_id: int, offset: int, size: int) -> bytes:
        """
        Read data with security, caching, and metrics.

        Args:
            provider_id: File provider ID
            offset: Read offset
            size: Number of bytes to read

        Returns:
            Bytes read from file

        Raises:
            ValueError: If input validation fails
            RuntimeError: If rate limited or circuit breaker open
        """
        start_time = time.time()
        cache_key = f"data:{provider_id}:{offset}:{size}"

        try:
            # 1. Validate input
            validate_input("provider_id", provider_id, int, min_value=0)
            validate_input("offset", offset, int, min_value=0)
            validate_input("size", size, int, min_value=1, max_value=10 * 1024 * 1024)

            # 2. Check rate limit
            client_id = f"client_{provider_id}"
            if not self.security.rate_limiter.check_limit(client_id):
                self.logger.warning(
                    "Rate limit exceeded",
                    extra={"client_id": client_id, "endpoint": "data/read"},
                )
                self.metrics.record_event(MetricType.ERROR, "rate_limit_exceeded")
                raise RuntimeError("Rate limit exceeded. Please slow down requests.")

            # 3. Check cache
            cached_data = self.cache.get(cache_key)
            if cached_data is not None:
                self.logger.debug(
                    "Cache hit",
                    extra={"key": cache_key, "size": len(cached_data)},
                )
                self.metrics.record_event(MetricType.CACHE_HIT, cache_key)
                return cached_data

            self.metrics.record_event(MetricType.CACHE_MISS, cache_key)

            # 4. Execute with circuit breaker
            def read_operation():
                # Simulate network call
                import socket
                import json

                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                sock.connect(("localhost", 31337))

                request = (
                    json.dumps(
                        {
                            "endpoint": "data/read",
                            "data": {
                                "provider_id": provider_id,
                                "offset": offset,
                                "size": size,
                            },
                        }
                    )
                    + "\n"
                )
                sock.sendall(request.encode())

                response = b""
                while b"\n" not in response:
                    response += sock.recv(4096)

                sock.close()
                result = json.loads(response.decode().strip())

                if result["status"] != "success":
                    raise RuntimeError(result["data"].get("error", "Unknown error"))

                return bytes.fromhex(result["data"]["data"])

            data = self.security.circuit_breaker.call(read_operation)

            # 5. Update cache
            self.cache.put(cache_key, data)

            # 6. Record metrics
            duration_ms = (time.time() - start_time) * 1000
            self.metrics.record_request(duration_ms, "data/read", True)

            self.logger.info(
                "Data read successfully",
                extra={
                    "provider_id": provider_id,
                    "offset": offset,
                    "size": size,
                    "duration_ms": f"{duration_ms:.2f}",
                },
            )

            return data

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self.metrics.record_request(duration_ms, "data/read", False)
            self.metrics.record_event(MetricType.ERROR, str(e))

            self.logger.error(
                "Data read failed",
                extra={
                    "provider_id": provider_id,
                    "offset": offset,
                    "size": size,
                    "error": str(e),
                },
                exc_info=True,
            )
            raise

    def get_metrics_summary(self) -> dict:
        """Get metrics summary."""
        return self.metrics.get_summary()

    def get_cache_stats(self) -> dict:
        """Get cache statistics."""
        return {
            "size": len(self.cache.cache),
            "max_size": self.cache.config.max_size,
            "strategy": self.cache.config.strategy.value,
            "ttl": self.cache.config.ttl,
        }


def main():
    """Demo the enhanced MCP client."""
    print("=" * 70)
    print("ImHex MCP Enhanced Client Demo")
    print("=" * 70)

    # Configuration
    config = {
        "imhex_host": "localhost",
        "imhex_port": 31337,
        "connection_timeout": 5.0,
        "read_timeout": 30.0,
        "max_retries": 3,
        "retry_delay": 1.0,
        "rate_limit_requests": 10,
        "rate_limit_window": 60,
        "circuit_breaker_threshold": 3,
        "circuit_breaker_timeout": 10,
        "cache_max_size": 100,
        "cache_ttl": 300,
        "enable_cache": True,
        "enable_profiling": False,
        "enable_performance_optimizations": True,
        "enable_lazy_loading": True,
    }

    # Initialize client
    print("\n[1/4] Initializing enhanced client...")
    try:
        client = EnhancedMCPClient(config)
        print("  ✓ Client initialized with security, caching, and metrics")
    except Exception as e:
        print(f"  ✗ Initialization failed: {e}")
        return 1

    # Test 1: Normal operations
    print("\n[2/4] Testing normal operations...")
    try:
        # First read - cache miss
        data = client.read_data(provider_id=0, offset=0, size=1024)
        print(f"  ✓ Read {len(data)} bytes (cache miss)")

        # Second read - cache hit
        data = client.read_data(provider_id=0, offset=0, size=1024)
        print(f"  ✓ Read {len(data)} bytes (cache hit)")

        # Different offset - cache miss
        data = client.read_data(provider_id=0, offset=1024, size=1024)
        print(f"  ✓ Read {len(data)} bytes (cache miss)")
    except Exception as e:
        print(f"  ✗ Operation failed: {e}")

    # Test 2: Rate limiting
    print("\n[3/4] Testing rate limiting...")
    rate_limit_hit = False
    for i in range(15):
        try:
            client.read_data(provider_id=0, offset=i * 1024, size=1024)
        except RuntimeError as e:
            if "Rate limit exceeded" in str(e):
                print(f"  ✓ Rate limiter triggered after {i} requests")
                rate_limit_hit = True
                break
    if not rate_limit_hit:
        print("  ⚠ Rate limiter not triggered (may need more requests)")

    # Test 3: Metrics summary
    print("\n[4/4] Metrics Summary:")
    metrics = client.get_metrics_summary()
    print(f"  Total requests: {metrics['total_requests']}")
    print(f"  Successful: {metrics['successful_requests']}")
    print(f"  Failed: {metrics['failed_requests']}")
    print(f"  Success rate: {metrics['success_rate']*100:.1f}%")
    print(f"  Avg response time: {metrics['avg_response_time']:.2f}ms")

    cache_stats = client.get_cache_stats()
    print(f"\nCache Statistics:")
    print(f"  Current size: {cache_stats['size']}/{cache_stats['max_size']}")
    print(f"  Strategy: {cache_stats['strategy']}")
    print(f"  TTL: {cache_stats['ttl']}s")

    print("\n" + "=" * 70)
    print("Demo completed successfully!")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
