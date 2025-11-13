"""
Configuration Loader for ImHex MCP

Loads configuration from YAML file with environment variable overrides.
Validates configuration using Pydantic models.
"""

import os
import yaml
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel, Field, validator


class ServerConfig(BaseModel):
    """Server configuration."""
    host: str = "localhost"
    port: int = 31337
    timeout: int = 30
    max_connections: int = 100


class CompressionConfigModel(BaseModel):
    """Compression configuration."""
    enabled: bool = True
    algorithm: str = "zstd"
    level: int = 3
    min_size: int = 1024
    adaptive: bool = True

    @validator('algorithm')
    def validate_algorithm(cls, v):
        if v not in ['zstd', 'gzip', 'zlib']:
            raise ValueError(f"Invalid compression algorithm: {v}")
        return v


class ConnectionPoolConfig(BaseModel):
    """Connection pool configuration."""
    enabled: bool = True
    min_size: int = 2
    max_size: int = 10
    timeout: float = 30.0


class CachingConfig(BaseModel):
    """Caching configuration."""
    enabled: bool = True
    max_size: int = 1000
    ttl: int = 300


class BatchingConfig(BaseModel):
    """Request batching configuration."""
    enabled: bool = True
    window_ms: int = 10
    max_batch_size: int = 50


class HealthConfig(BaseModel):
    """Health monitoring configuration."""
    enabled: bool = True
    check_interval: int = 60


class ProfilingConfig(BaseModel):
    """Performance profiling configuration."""
    enabled: bool = True
    log_slow_requests: bool = True
    slow_threshold_ms: int = 1000


class LoggingConfig(BaseModel):
    """Logging configuration."""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file: Optional[str] = None
    max_bytes: int = 10485760
    backup_count: int = 5

    @validator('level')
    def validate_level(cls, v):
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid log level: {v}")
        return v.upper()


class RateLimitingConfig(BaseModel):
    """Rate limiting configuration."""
    enabled: bool = True
    requests_per_minute: int = 1000
    burst_size: int = 100


class InputValidationConfig(BaseModel):
    """Input validation configuration."""
    enabled: bool = True
    max_payload_size: int = 104857600  # 100MB
    allowed_paths: List[str] = Field(default_factory=lambda: ["/tmp", "/Users", "/home"])


class CorsConfig(BaseModel):
    """CORS configuration."""
    enabled: bool = False
    allowed_origins: List[str] = Field(default_factory=list)


class SecurityConfig(BaseModel):
    """Security configuration."""
    rate_limiting: RateLimitingConfig = Field(default_factory=RateLimitingConfig)
    input_validation: InputValidationConfig = Field(default_factory=InputValidationConfig)
    cors: CorsConfig = Field(default_factory=CorsConfig)


class MetricsConfig(BaseModel):
    """Metrics configuration."""
    enabled: bool = False
    port: int = 9090
    endpoint: str = "/metrics"


class FeaturesConfig(BaseModel):
    """Feature flags."""
    lazy_loading: bool = True
    streaming: bool = True
    advanced_caching: bool = True
    request_prioritization: bool = False
    circuit_breaker: bool = False


class DevelopmentConfig(BaseModel):
    """Development settings."""
    debug: bool = False
    reload_on_change: bool = False
    mock_imhex: bool = False


class AppConfig(BaseModel):
    """Complete application configuration."""
    server: ServerConfig = Field(default_factory=ServerConfig)
    compression: CompressionConfigModel = Field(default_factory=CompressionConfigModel)
    connection_pool: ConnectionPoolConfig = Field(default_factory=ConnectionPoolConfig)
    caching: CachingConfig = Field(default_factory=CachingConfig)
    batching: BatchingConfig = Field(default_factory=BatchingConfig)
    health: HealthConfig = Field(default_factory=HealthConfig)
    profiling: ProfilingConfig = Field(default_factory=ProfilingConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    metrics: MetricsConfig = Field(default_factory=MetricsConfig)
    features: FeaturesConfig = Field(default_factory=FeaturesConfig)
    development: DevelopmentConfig = Field(default_factory=DevelopmentConfig)


def load_config(config_path: Optional[str] = None) -> AppConfig:
    """
    Load configuration from YAML file with environment variable overrides.

    Args:
        config_path: Path to YAML config file. Defaults to ./config.yaml

    Returns:
        AppConfig: Validated configuration object

    Environment Variables:
        IMHEX_MCP_CONFIG: Path to config file
        IMHEX_MCP_*: Override specific config values
            - Use double underscores (__) for nesting levels
            - Examples:
                IMHEX_MCP_SERVER__PORT=8080 -> config.server.port
                IMHEX_MCP_COMPRESSION__ENABLED=false -> config.compression.enabled
                IMHEX_MCP_SECURITY__RATE_LIMITING__ENABLED=true -> config.security.rate_limiting.enabled
    """
    # Determine config file path
    if config_path is None:
        config_path = os.getenv('IMHEX_MCP_CONFIG', 'config.yaml')

    config_file = Path(config_path)

    # Load from file if exists
    if config_file.exists():
        with open(config_file, 'r') as f:
            config_data = yaml.safe_load(f) or {}
    else:
        config_data = {}

    # Apply environment variable overrides
    # Example: IMHEX_MCP_SERVER__PORT=8080 overrides config.server.port
    # Note: Use double underscore (__) for nesting levels
    for env_key, env_value in os.environ.items():
        if env_key.startswith('IMHEX_MCP_'):
            # Parse nested key: IMHEX_MCP_SERVER__PORT -> server.port
            # Split by '__' for nesting, then lowercase each part
            key_parts = [part.lower() for part in env_key[10:].split('__')]

            # Navigate and set value in config_data
            current = config_data
            for part in key_parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]

            # Convert value to appropriate type
            final_key = key_parts[-1]
            if env_value.lower() in ('true', 'false'):
                current[final_key] = env_value.lower() == 'true'
            elif env_value.isdigit():
                current[final_key] = int(env_value)
            else:
                try:
                    current[final_key] = float(env_value)
                except ValueError:
                    current[final_key] = env_value

    # Create and validate config
    return AppConfig(**config_data)


# Global configuration instance
_config: Optional[AppConfig] = None


def get_config() -> AppConfig:
    """Get global configuration instance (singleton)."""
    global _config
    if _config is None:
        _config = load_config()
    return _config


def reload_config(config_path: Optional[str] = None):
    """Reload configuration from file."""
    global _config
    _config = load_config(config_path)
    return _config
