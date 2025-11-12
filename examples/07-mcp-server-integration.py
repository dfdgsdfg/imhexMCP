#!/usr/bin/env python3
"""
MCP Server Integration Example

This example demonstrates how to integrate the EnhancedImHexClient
into an MCP server or similar production application.
"""

import sys
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Dict, Any
from enum import Enum

# Add paths
sys.path.insert(0, str(Path(__file__).parent.parent / "mcp-server"))
sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))

from enhanced_client import create_enhanced_client, EnhancedImHexClient


class LogLevel(Enum):
    """Log level enumeration."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class ServerConfig:
    """Example server configuration with performance optimization settings."""

    # Basic ImHex connection settings
    imhex_host: str = "localhost"
    imhex_port: int = 31337
    connection_timeout: float = 5.0
    read_timeout: float = 30.0

    # Performance optimization settings
    enable_performance_optimizations: bool = False  # Master switch
    enable_cache: bool = True  # Enable response caching
    cache_max_size: int = 1000  # Maximum cache entries
    enable_profiling: bool = False  # Enable performance profiling
    enable_lazy_loading: bool = True  # Enable lazy loading

    # Logging
    log_level: LogLevel = LogLevel.INFO


class EnhancedImHexClientAdapter:
    """
    Adapter that wraps EnhancedImHexClient to match your existing client interface.

    This allows the enhanced client to be used as a drop-in replacement
    throughout your application.
    """

    def __init__(self, config: ServerConfig):
        """Initialize adapter with enhanced client."""
        self.config = config

        # Create enhanced client with configuration
        self.enhanced_client = create_enhanced_client(
            host=config.imhex_host,
            port=config.imhex_port,
            config={
                'timeout': int(config.read_timeout),
                'enable_cache': config.enable_cache,
                'cache_max_size': config.cache_max_size,
                'enable_profiling': config.enable_profiling,
                'enable_lazy': config.enable_lazy_loading
            }
        )

        print(f"Enhanced client adapter initialized with optimizations:")
        print(f"  - Cache: {config.enable_cache} (max size: {config.cache_max_size})")
        print(f"  - Profiling: {config.enable_profiling}")
        print(f"  - Lazy loading: {config.enable_lazy_loading}")

    def connect(self) -> bool:
        """Connect to ImHex (no-op for enhanced client, it auto-connects)."""
        print("Enhanced client connects automatically")
        return True

    def disconnect(self):
        """Disconnect from ImHex (no-op for enhanced client)."""
        print("Enhanced client disconnects automatically")

    def is_connected(self) -> bool:
        """Check if connected (always True for enhanced client)."""
        return True

    def send_command(self, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Send a command using the enhanced client."""
        # Use enhanced client's send_request method
        response = self.enhanced_client.send_request(endpoint, data)

        # Check for errors
        if response.get("status") == "error":
            error_msg = response.get("data", {}).get("error", "Unknown error")
            raise Exception(f"ImHex error: {error_msg}")

        return response

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - print performance report if profiling enabled."""
        if self.config.enable_profiling:
            print("\n=== Performance Report ===")
            self.enhanced_client.print_performance_report()
        self.disconnect()


def create_client_from_config(config: ServerConfig):
    """
    Factory function that creates the appropriate client based on configuration.

    This is the recommended integration pattern - use a factory function
    that returns either the enhanced client or a standard client based on
    configuration.
    """
    if config.enable_performance_optimizations:
        print("Creating enhanced client with performance optimizations enabled")
        return EnhancedImHexClientAdapter(config)
    else:
        print("Creating standard client (performance optimizations disabled)")
        # Return your standard client here
        # return StandardImHexClient(config)
        # For this example, we'll return the enhanced client with minimal config
        minimal_config = ServerConfig(
            imhex_host=config.imhex_host,
            imhex_port=config.imhex_port,
            enable_performance_optimizations=False,
            enable_cache=False,
            enable_profiling=False,
            enable_lazy_loading=False
        )
        return EnhancedImHexClientAdapter(minimal_config)


def example_1_basic_integration():
    """Example 1: Basic integration with default optimizations."""
    print("\n" + "=" * 70)
    print("Example 1: Basic Integration")
    print("=" * 70)

    # Create configuration
    config = ServerConfig(
        imhex_host="localhost",
        imhex_port=31337,
        enable_performance_optimizations=True,
        enable_cache=True,
        cache_max_size=1000,
        enable_profiling=False,
        enable_lazy_loading=True
    )

    # Create client using factory
    client = create_client_from_config(config)

    try:
        # Use client like normal
        print("\n[1/2] Getting capabilities...")
        caps = client.send_command("capabilities")
        print(f"  Status: {caps.get('status')}")
        print(f"  Endpoints: {len(caps.get('data', {}).get('endpoints', []))}")

        print("\n[2/2] Listing files...")
        files = client.send_command("file/list")
        print(f"  Status: {files.get('status')}")
        print(f"  Files: {files.get('data', {}).get('count', 0)}")

        print("\nIntegration successful!")

    except Exception as e:
        print(f"Error: {e}")


def example_2_context_manager():
    """Example 2: Using context manager for automatic cleanup."""
    print("\n" + "=" * 70)
    print("Example 2: Context Manager Usage")
    print("=" * 70)

    config = ServerConfig(
        enable_performance_optimizations=True,
        enable_profiling=True  # Will print report on exit
    )

    try:
        # Use context manager for automatic cleanup and reporting
        with create_client_from_config(config) as client:
            print("\n[1/3] Inside context manager...")

            # Make some requests
            caps = client.send_command("capabilities")
            print(f"  Capabilities: {caps.get('status')}")

            files = client.send_command("file/list")
            print(f"  Files: {files.get('status')}")

            # Make more requests to generate profiling data
            for i in range(5):
                client.send_command("capabilities")

            print("\n[2/3] Exiting context manager...")

        print("\n[3/3] Context manager exited, resources cleaned up!")

    except Exception as e:
        print(f"Error: {e}")


def example_3_different_profiles():
    """Example 3: Using different configuration profiles."""
    print("\n" + "=" * 70)
    print("Example 3: Configuration Profiles")
    print("=" * 70)

    # Production profile (high performance, no profiling)
    production_config = ServerConfig(
        enable_performance_optimizations=True,
        enable_cache=True,
        cache_max_size=5000,  # Large cache
        enable_profiling=False,  # No overhead
        enable_lazy_loading=True
    )

    # Development profile (profiling enabled, smaller cache)
    development_config = ServerConfig(
        enable_performance_optimizations=True,
        enable_cache=True,
        cache_max_size=100,  # Small cache for testing
        enable_profiling=True,  # Profile everything
        enable_lazy_loading=False  # Immediate feedback
    )

    # Use production config
    print("\n[Production Profile]")
    prod_client = create_client_from_config(production_config)

    # Use development config
    print("\n[Development Profile]")
    dev_client = create_client_from_config(development_config)

    print("\nChoose appropriate profile based on environment!")


def example_4_error_handling():
    """Example 4: Robust error handling with retries."""
    print("\n" + "=" * 70)
    print("Example 4: Error Handling and Retries")
    print("=" * 70)

    config = ServerConfig(
        enable_performance_optimizations=True
    )

    client = create_client_from_config(config)

    def safe_request(endpoint: str, data: Optional[Dict] = None, retries: int = 3) -> Optional[Dict]:
        """Make request with retry logic."""
        for attempt in range(retries):
            try:
                return client.send_command(endpoint, data)
            except ConnectionError as e:
                print(f"  Connection error (attempt {attempt + 1}/{retries}): {e}")
                if attempt == retries - 1:
                    raise
                import time
                time.sleep(1 * (attempt + 1))  # Exponential backoff
            except Exception as e:
                print(f"  Error: {e}")
                if attempt == retries - 1:
                    raise
        return None

    try:
        print("\n[1/2] Making request with retry logic...")
        result = safe_request("capabilities")
        if result:
            print(f"  Success: {result.get('status')}")

        print("\n[2/2] Making request to non-existent endpoint (will fail)...")
        try:
            result = safe_request("nonexistent/endpoint")
        except Exception as e:
            print(f"  Failed after retries (expected): {e}")

    except Exception as e:
        print(f"Unexpected error: {e}")


def example_5_monitoring():
    """Example 5: Monitoring cache and performance metrics."""
    print("\n" + "=" * 70)
    print("Example 5: Monitoring and Metrics")
    print("=" * 70)

    config = ServerConfig(
        enable_performance_optimizations=True,
        enable_cache=True,
        cache_max_size=1000,
        enable_profiling=True
    )

    adapter = create_client_from_config(config)
    client = adapter.enhanced_client  # Access underlying enhanced client

    try:
        # Make some requests
        print("\n[1/3] Making requests to generate metrics...")
        for i in range(10):
            client.get_capabilities()

        for i in range(5):
            client.list_files()

        # Check cache statistics
        print("\n[2/3] Cache Statistics:")
        cache_stats = client.get_cache_stats()
        if cache_stats.get('enabled'):
            print(f"  Hit rate: {cache_stats.get('hit_rate', 0):.1f}%")
            print(f"  Hits: {cache_stats.get('hits', 0)}")
            print(f"  Misses: {cache_stats.get('misses', 0)}")
            print(f"  Size: {cache_stats.get('size', 0)}/{cache_stats.get('max_size', 0)}")

        # Check performance statistics
        print("\n[3/3] Performance Statistics:")
        perf_stats = client.get_performance_stats()
        if perf_stats.get('enabled'):
            for op_name, stats in perf_stats.get('operations', {}).items():
                print(f"  {op_name}:")
                print(f"    Calls: {stats['call_count']}")
                print(f"    Avg: {stats['avg_time_ms']:.2f}ms")
                print(f"    P95: {stats['p95_time_ms']:.2f}ms")

    except Exception as e:
        print(f"Error: {e}")


def main():
    """Run all integration examples."""
    print("\n" + "=" * 70)
    print("MCP Server Integration Examples")
    print("=" * 70)
    print("\nDemonstrating integration patterns for production applications")

    try:
        example_1_basic_integration()
        example_2_context_manager()
        example_3_different_profiles()
        example_4_error_handling()
        example_5_monitoring()

        print("\n" + "=" * 70)
        print("Integration Examples Complete!")
        print("=" * 70)
        print("\nKey Takeaways:")
        print("  1. Use factory function to create appropriate client")
        print("  2. Use context manager for automatic cleanup")
        print("  3. Choose configuration profile based on environment")
        print("  4. Implement retry logic for robustness")
        print("  5. Monitor cache and performance metrics")
        print("\nSee docs/INTEGRATION_GUIDE.md for more details")

    except KeyboardInterrupt:
        print("\n\nExamples interrupted by user.")


if __name__ == "__main__":
    main()
