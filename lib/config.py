"""
Centralized Configuration Module

Provides pydantic-based configuration loading with validation
and environment variable overrides.
"""

import os
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field, field_validator


class ConnectionConfig(BaseModel):
    """Connection configuration."""

    host: str = "localhost"
    port: int = 31337
    timeout: float = 30.0
    max_retries: int = 3
    retry_delay: float = 1.0

    @field_validator("port")
    @classmethod
    def validate_port(cls, v: int) -> int:
        """Validate port number."""
        if not 1 <= v <= 65535:
            raise ValueError(f"Port must be between 1 and 65535, got {v}")
        return v


class PerformanceConfig(BaseModel):
    """Performance configuration."""

    enable_compression: bool = True
    compression_threshold: int = 1024
    max_workers: int = 4
    request_timeout: float = 60.0

    @field_validator("max_workers")
    @classmethod
    def validate_workers(cls, v: int) -> int:
        """Validate worker count."""
        if v < 1:
            raise ValueError(f"max_workers must be >= 1, got {v}")
        return v


class CacheConfig(BaseModel):
    """Cache configuration."""

    enabled: bool = True
    max_size: int = 1000
    ttl: int = 300
    enable_l2_cache: bool = True
    l2_max_size: int = 10000

    @field_validator("max_size", "l2_max_size")
    @classmethod
    def validate_cache_size(cls, v: int) -> int:
        """Validate cache size."""
        if v < 1:
            raise ValueError(f"Cache size must be >= 1, got {v}")
        return v


class SecurityConfig(BaseModel):
    """Security configuration."""

    enable_rate_limiting: bool = True
    requests_per_second: int = 100
    max_payload_size: int = 10485760  # 10 MB
    enable_input_validation: bool = True

    @field_validator("max_payload_size")
    @classmethod
    def validate_payload_size(cls, v: int) -> int:
        """Validate payload size."""
        if v < 1:
            raise ValueError(f"max_payload_size must be >= 1, got {v}")
        return v


class MonitoringConfig(BaseModel):
    """Monitoring configuration."""

    enable_metrics: bool = True
    metrics_port: int = 8000
    enable_prometheus: bool = False
    log_level: str = "INFO"

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"log_level must be one of {valid_levels}")
        return v_upper


class CircuitBreakerConfig(BaseModel):
    """Circuit breaker configuration."""

    enabled: bool = True
    failure_threshold: int = 5
    timeout: float = 60.0
    half_open_timeout: float = 30.0

    @field_validator("failure_threshold")
    @classmethod
    def validate_threshold(cls, v: int) -> int:
        """Validate failure threshold."""
        if v < 1:
            raise ValueError(f"failure_threshold must be >= 1, got {v}")
        return v


class PriorityConfig(BaseModel):
    """Priority queue configuration."""

    enable_aging: bool = True
    aging_interval: float = 1.0
    max_queue_size: int = 1000

    @field_validator("max_queue_size")
    @classmethod
    def validate_queue_size(cls, v: int) -> int:
        """Validate queue size."""
        if v < 1:
            raise ValueError(f"max_queue_size must be >= 1, got {v}")
        return v


class LoggingConfig(BaseModel):
    """Logging configuration."""

    format: str = "json"
    file: Optional[str] = None
    level: str = "INFO"
    enable_colors: bool = True

    @field_validator("format")
    @classmethod
    def validate_format(cls, v: str) -> str:
        """Validate log format."""
        if v not in {"json", "console"}:
            raise ValueError(f"format must be 'json' or 'console', got '{v}'")
        return v


class Config(BaseModel):
    """Root configuration."""

    connection: ConnectionConfig = Field(default_factory=ConnectionConfig)
    performance: PerformanceConfig = Field(
        default_factory=PerformanceConfig
    )
    cache: CacheConfig = Field(default_factory=CacheConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)
    circuit_breaker: CircuitBreakerConfig = Field(
        default_factory=CircuitBreakerConfig
    )
    priority: PriorityConfig = Field(default_factory=PriorityConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)


def load_config(config_path: Optional[str] = None) -> Config:
    """
    Load configuration from YAML file with environment variable overrides.

    Args:
        config_path: Path to config file (defaults to ./config.yaml)

    Returns:
        Validated Config object

    Environment variables can override config values using the pattern:
        IMHEX_MCP_<SECTION>_<KEY>

    Examples:
        IMHEX_MCP_CONNECTION_HOST=192.168.1.100
        IMHEX_MCP_PERFORMANCE_MAX_WORKERS=8
    """
    # Determine config path
    if config_path is None:
        config_path = os.environ.get(
            "IMHEX_MCP_CONFIG", "config.yaml"
        )

    # Load base configuration
    config_dict: dict = {}
    if Path(config_path).exists():
        with open(config_path, "r", encoding="utf-8") as f:
            config_dict = yaml.safe_load(f) or {}

    # Apply environment variable overrides
    config_dict = _apply_env_overrides(config_dict)

    # Validate and return
    return Config(**config_dict)


def _apply_env_overrides(config_dict: dict) -> dict:
    """Apply environment variable overrides to config dict."""
    prefix = "IMHEX_MCP_"

    for key, value in os.environ.items():
        if not key.startswith(prefix):
            continue

        # Parse environment variable name
        parts = key[len(prefix):].lower().split("_", 1)
        if len(parts) != 2:
            continue

        section, setting = parts

        # Initialize section if needed
        if section not in config_dict:
            config_dict[section] = {}

        # Convert value to appropriate type
        config_dict[section][setting] = _parse_env_value(value)

    return config_dict


def _parse_env_value(value: str):
    """Parse environment variable value to appropriate Python type."""
    # Boolean
    if value.lower() in {"true", "yes", "1", "on"}:
        return True
    if value.lower() in {"false", "no", "0", "off"}:
        return False

    # Integer
    try:
        return int(value)
    except ValueError:
        pass

    # Float
    try:
        return float(value)
    except ValueError:
        pass

    # String (null handling)
    if value.lower() in {"null", "none", ""}:
        return None

    # Default: string
    return value


# Global config instance (lazy loaded)
_config: Optional[Config] = None


def get_config() -> Config:
    """Get or create global configuration instance."""
    global _config
    if _config is None:
        _config = load_config()
    return _config


def reload_config(config_path: Optional[str] = None) -> Config:
    """Reload configuration from file."""
    global _config
    _config = load_config(config_path)
    return _config
