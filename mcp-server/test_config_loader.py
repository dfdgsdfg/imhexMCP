"""
Tests for configuration loader.

This module tests the configuration loading functionality including:
- YAML file parsing
- Environment variable overrides
- Pydantic validation
- Default values
- Singleton pattern
"""

import os
import sys
import tempfile
from pathlib import Path

import pytest
import yaml

# Add lib directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))

from config_loader import (
    AppConfig,
    CachingConfig,
    CompressionConfigModel,
    ConnectionPoolConfig,
    HealthConfig,
    LoggingConfig,
    SecurityConfig,
    ServerConfig,
    get_config,
    load_config,
    reload_config,
)


@pytest.fixture
def temp_config_file():
    """Create a temporary config file for testing."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        config_data = {
            "server": {"host": "test-host", "port": 9999},
            "compression": {"enabled": False, "algorithm": "gzip"},
            "logging": {"level": "DEBUG"},
        }
        yaml.dump(config_data, f)
        temp_path = f.name

    yield temp_path

    # Cleanup
    os.unlink(temp_path)


@pytest.fixture
def clean_env(monkeypatch):
    """Remove all IMHEX_MCP_* environment variables."""
    for key in list(os.environ.keys()):
        if key.startswith("IMHEX_MCP_"):
            monkeypatch.delenv(key)


class TestConfigModels:
    """Test Pydantic configuration models."""

    @pytest.mark.unit
    def test_server_config_defaults(self):
        """Test ServerConfig default values."""
        config = ServerConfig()
        assert config.host == "localhost"
        assert config.port == 31337
        assert config.timeout == 30
        assert config.max_connections == 100

    @pytest.mark.unit
    def test_server_config_custom(self):
        """Test ServerConfig with custom values."""
        config = ServerConfig(host="0.0.0.0", port=8080, timeout=60)
        assert config.host == "0.0.0.0"
        assert config.port == 8080
        assert config.timeout == 60

    @pytest.mark.unit
    def test_compression_config_defaults(self):
        """Test CompressionConfigModel default values."""
        config = CompressionConfigModel()
        assert config.enabled is True
        assert config.algorithm == "zstd"
        assert config.level == 3
        assert config.min_size == 1024
        assert config.adaptive is True

    @pytest.mark.unit
    def test_compression_algorithm_validation(self):
        """Test compression algorithm validation."""
        # Valid algorithms
        for algo in ["zstd", "gzip", "zlib"]:
            config = CompressionConfigModel(algorithm=algo)
            assert config.algorithm == algo

        # Invalid algorithm
        with pytest.raises(ValueError, match="Invalid compression algorithm"):
            CompressionConfigModel(algorithm="invalid")

    @pytest.mark.unit
    def test_logging_level_validation(self):
        """Test logging level validation."""
        # Valid levels
        for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            config = LoggingConfig(level=level)
            assert config.level == level

        # Case insensitive
        config = LoggingConfig(level="debug")
        assert config.level == "DEBUG"

        # Invalid level
        with pytest.raises(ValueError, match="Invalid log level"):
            LoggingConfig(level="INVALID")


class TestConfigLoading:
    """Test configuration loading from files and environment."""

    @pytest.mark.unit
    def test_load_default_config(self, clean_env):
        """Test loading config with all defaults (no file)."""
        # This should work even without a config file
        config = load_config(config_path="/nonexistent/path/config.yaml")

        assert isinstance(config, AppConfig)
        assert config.server.host == "localhost"
        assert config.server.port == 31337
        assert config.compression.enabled is True
        assert config.compression.algorithm == "zstd"

    @pytest.mark.unit
    def test_load_from_file(self, temp_config_file, clean_env):
        """Test loading config from YAML file."""
        config = load_config(config_path=temp_config_file)

        assert config.server.host == "test-host"
        assert config.server.port == 9999
        assert config.compression.enabled is False
        assert config.compression.algorithm == "gzip"
        assert config.logging.level == "DEBUG"

    @pytest.mark.unit
    def test_env_var_override_simple(self, clean_env, monkeypatch):
        """Test environment variable override for simple values."""
        monkeypatch.setenv("IMHEX_MCP_SERVER__PORT", "7777")
        monkeypatch.setenv("IMHEX_MCP_SERVER__HOST", "custom-host")

        config = load_config(config_path="/nonexistent/path/config.yaml")

        assert config.server.port == 7777
        assert config.server.host == "custom-host"

    @pytest.mark.unit
    def test_env_var_override_boolean(self, clean_env, monkeypatch):
        """Test environment variable override for boolean values."""
        monkeypatch.setenv("IMHEX_MCP_COMPRESSION__ENABLED", "false")
        monkeypatch.setenv("IMHEX_MCP_COMPRESSION__ADAPTIVE", "true")

        config = load_config(config_path="/nonexistent/path/config.yaml")

        assert config.compression.enabled is False
        assert config.compression.adaptive is True

    @pytest.mark.unit
    def test_env_var_override_nested(self, clean_env, monkeypatch):
        """Test environment variable override for nested values."""
        monkeypatch.setenv("IMHEX_MCP_SECURITY__RATE_LIMITING__ENABLED", "false")
        monkeypatch.setenv("IMHEX_MCP_SECURITY__RATE_LIMITING__REQUESTS_PER_MINUTE", "500")

        config = load_config(config_path="/nonexistent/path/config.yaml")

        assert config.security.rate_limiting.enabled is False
        assert config.security.rate_limiting.requests_per_minute == 500

    @pytest.mark.unit
    def test_env_var_override_file(self, temp_config_file, clean_env, monkeypatch):
        """Test that environment variables override file values."""
        # File has port=9999, env will set port=5555
        monkeypatch.setenv("IMHEX_MCP_SERVER__PORT", "5555")

        config = load_config(config_path=temp_config_file)

        assert config.server.port == 5555  # env var wins
        assert config.server.host == "test-host"  # file value preserved


class TestConfigSingleton:
    """Test configuration singleton pattern."""

    @pytest.mark.unit
    def test_get_config_singleton(self, clean_env):
        """Test that get_config returns the same instance."""
        # Reset global config
        import config_loader

        config_loader._config = None

        config1 = get_config()
        config2 = get_config()

        assert config1 is config2  # Same object instance

    @pytest.mark.unit
    def test_reload_config(self, temp_config_file, clean_env):
        """Test config reload functionality."""
        # Reset global config
        import config_loader

        config_loader._config = None

        # Load initial config
        config1 = get_config()
        assert config1.server.port == 31337  # default

        # Reload with custom file
        config2 = reload_config(config_path=temp_config_file)
        assert config2.server.port == 9999  # from file

        # get_config should return the reloaded config
        config3 = get_config()
        assert config3 is config2
        assert config3.server.port == 9999


class TestCompleteConfig:
    """Test complete configuration structure."""

    @pytest.mark.unit
    def test_all_sections_present(self, clean_env):
        """Test that all configuration sections are present."""
        config = load_config(config_path="/nonexistent/path/config.yaml")

        assert isinstance(config.server, ServerConfig)
        assert isinstance(config.compression, CompressionConfigModel)
        assert isinstance(config.connection_pool, ConnectionPoolConfig)
        assert isinstance(config.caching, CachingConfig)
        assert isinstance(config.health, HealthConfig)
        assert isinstance(config.logging, LoggingConfig)
        assert isinstance(config.security, SecurityConfig)

    @pytest.mark.unit
    def test_config_to_dict(self, clean_env):
        """Test that config can be serialized to dict."""
        config = load_config(config_path="/nonexistent/path/config.yaml")

        config_dict = config.model_dump()

        assert isinstance(config_dict, dict)
        assert "server" in config_dict
        assert "compression" in config_dict
        assert config_dict["server"]["host"] == "localhost"
        assert config_dict["server"]["port"] == 31337


class TestConfigValidation:
    """Test configuration validation."""

    @pytest.mark.unit
    def test_invalid_compression_algorithm(self, clean_env):
        """Test validation fails for invalid compression algorithm."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump({"compression": {"algorithm": "invalid"}}, f)
            temp_path = f.name

        try:
            with pytest.raises(ValueError):
                load_config(config_path=temp_path)
        finally:
            os.unlink(temp_path)

    @pytest.mark.unit
    def test_invalid_logging_level(self, clean_env):
        """Test validation fails for invalid logging level."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump({"logging": {"level": "INVALID"}}, f)
            temp_path = f.name

        try:
            with pytest.raises(ValueError):
                load_config(config_path=temp_path)
        finally:
            os.unlink(temp_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
