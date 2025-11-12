#!/usr/bin/env python3
"""
Configuration Validation Example

Demonstrates how to use the configuration validation module to catch
configuration issues early.
"""

import sys
from pathlib import Path

# Add lib to path
sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))
sys.path.insert(0, str(Path(__file__).parent.parent / "mcp-server"))

from dataclasses import dataclass
from enum import Enum
import logging
from config_validator import validate_config, validate_and_log, print_validation_report


# Import ServerConfig types
class LogLevel(Enum):
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR


@dataclass
class ServerConfig:
    """Server configuration (simplified)."""
    imhex_host: str = "localhost"
    imhex_port: int = 31337
    connection_timeout: float = 5.0
    read_timeout: float = 30.0
    max_retries: int = 3
    retry_delay: float = 1.0
    log_level: LogLevel = LogLevel.INFO
    enable_performance_optimizations: bool = False
    enable_cache: bool = True
    cache_max_size: int = 1000
    enable_profiling: bool = False
    enable_lazy_loading: bool = True


def main():
    """Run configuration validation examples."""

    print("=" * 70)
    print("Configuration Validation Examples")
    print("=" * 70)

    # Example 1: Valid configuration
    print("\n[Example 1] Valid Configuration")
    print("-" * 70)
    config = ServerConfig()
    is_valid, results = validate_config(config)
    print_validation_report(results)

    # Example 2: Configuration with warnings
    print("\n[Example 2] Configuration with Warnings")
    print("-" * 70)
    config = ServerConfig(
        connection_timeout=0.5,  # Very short
        cache_max_size=50,  # Small cache
        enable_profiling=True,  # In production
        enable_performance_optimizations=True
    )
    is_valid, results = validate_config(config)
    print_validation_report(results)

    # Example 3: Invalid configuration
    print("\n[Example 3] Invalid Configuration (Errors)")
    print("-" * 70)
    config = ServerConfig(
        imhex_host="",  # Empty host
        imhex_port=70000,  # Invalid port
        connection_timeout=-1,  # Negative timeout
        max_retries=-5,  # Negative retries
        cache_max_size=-100  # Negative cache size
    )
    is_valid, results = validate_config(config)
    print_validation_report(results)
    print(f"Can start server: {is_valid}")

    # Example 4: Using validate_and_log
    print("\n[Example 4] Using validate_and_log (logs to logger)")
    print("-" * 70)
    logging.basicConfig(level=logging.INFO,
                       format='%(levelname)s: %(message)s')
    config = ServerConfig(
        imhex_port=80,  # Privileged port
        connection_timeout=50,  # Very long
        max_retries=15  # Too many
    )
    is_valid = validate_and_log(config)
    print(f"\nConfiguration valid: {is_valid}")

    # Example 5: Suboptimal cache settings
    print("\n[Example 5] Suboptimal Cache Settings")
    print("-" * 70)
    config = ServerConfig(
        enable_cache=True,
        enable_performance_optimizations=False  # Cache enabled but not used
    )
    is_valid, results = validate_config(config)
    print_validation_report(results)

    # Example 6: Inconsistent timeout settings
    print("\n[Example 6] Inconsistent Timeout Settings")
    print("-" * 70)
    config = ServerConfig(
        connection_timeout=10.0,
        read_timeout=5.0,  # Read timeout < connection timeout
        max_retries=10,  # High retries
        retry_delay=20.0  # Long delay
    )
    is_valid, results = validate_config(config)
    print_validation_report(results)

    # Example 7: Remote host warning
    print("\n[Example 7] Remote Host Configuration")
    print("-" * 70)
    config = ServerConfig(
        imhex_host="example.com",  # Remote host
        imhex_port=8080  # Non-standard port
    )
    is_valid, results = validate_config(config)
    print_validation_report(results)

    # Example 8: Optimal production configuration
    print("\n[Example 8] Optimal Production Configuration")
    print("-" * 70)
    config = ServerConfig(
        imhex_host="localhost",
        imhex_port=31337,
        connection_timeout=5.0,
        read_timeout=30.0,
        max_retries=3,
        retry_delay=1.0,
        enable_performance_optimizations=True,
        enable_cache=True,
        cache_max_size=2000,
        enable_profiling=False,  # Disabled for production
        enable_lazy_loading=True
    )
    is_valid, results = validate_config(config)
    print_validation_report(results)

    print("\n" + "=" * 70)
    print("Validation Examples Complete")
    print("=" * 70)
    print("\nKey Takeaways:")
    print("  1. Run validation at startup to catch configuration errors early")
    print("  2. Pay attention to warnings - they indicate suboptimal settings")
    print("  3. Use validate_and_log() to integrate with your logging setup")
    print("  4. Print validation reports for user-facing tools")
    print("  5. Fix ERROR level issues before starting the server")


if __name__ == "__main__":
    main()
