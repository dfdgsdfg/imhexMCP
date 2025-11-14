"""
Tests for Configuration Validator Module

Tests validation logic for server configuration including:
- Connection settings validation
- Timeout validation
- Retry settings validation
- Performance optimization validation
- Cache settings validation
- Configuration consistency checks
"""

import pytest
from dataclasses import dataclass

from config_validator import (
    ValidationLevel,
    ValidationResult,
    ConfigValidator,
    validate_config,
    validate_and_log,
    print_validation_report,
)


@dataclass
class MockConfig:
    """Mock configuration object for testing."""

    # Connection settings
    imhex_host: str = "localhost"
    imhex_port: int = 31337

    # Timeout settings
    connection_timeout: float = 5.0
    read_timeout: float = 30.0

    # Retry settings
    max_retries: int = 3
    retry_delay: float = 1.0

    # Performance settings
    enable_profiling: bool = False
    enable_performance_optimizations: bool = True
    enable_lazy_loading: bool = True

    # Cache settings
    enable_cache: bool = True
    cache_max_size: int = 1000


class TestValidationResult:
    """Tests for ValidationResult dataclass."""

    def test_validation_result_creation(self):
        """Test creating ValidationResult."""
        result = ValidationResult(
            level=ValidationLevel.ERROR,
            field="test_field",
            message="Test message",
            suggestion="Test suggestion",
        )

        assert result.level == ValidationLevel.ERROR
        assert result.field == "test_field"
        assert result.message == "Test message"
        assert result.suggestion == "Test suggestion"

    def test_validation_result_no_suggestion(self):
        """Test ValidationResult without suggestion."""
        result = ValidationResult(
            level=ValidationLevel.INFO,
            field="test_field",
            message="Test message",
        )

        assert result.suggestion is None


class TestConnectionValidation:
    """Tests for connection settings validation."""

    def test_valid_localhost_connection(self):
        """Test valid localhost connection."""
        config = MockConfig(imhex_host="localhost", imhex_port=31337)
        validator = ConfigValidator()
        validator._validate_connection(config)

        # Should have no errors, possibly 1 info about default port
        errors = [
            r for r in validator.results if r.level == ValidationLevel.ERROR
        ]
        assert len(errors) == 0

    def test_empty_host(self):
        """Test empty host generates error."""
        config = MockConfig(imhex_host="")
        validator = ConfigValidator()
        validator._validate_connection(config)

        errors = [
            r for r in validator.results if r.level == ValidationLevel.ERROR
        ]
        assert len(errors) == 1
        assert errors[0].field == "imhex_host"
        assert "cannot be empty" in errors[0].message.lower()

    def test_remote_host_warning(self):
        """Test remote host generates warning."""
        config = MockConfig(imhex_host="remote.example.com")
        validator = ConfigValidator()
        validator._validate_connection(config)

        warnings = [
            r for r in validator.results if r.level == ValidationLevel.WARNING
        ]
        assert len(warnings) >= 1
        assert any("remote host" in w.message.lower() for w in warnings)

    def test_invalid_port_zero(self):
        """Test port 0 is invalid."""
        config = MockConfig(imhex_port=0)
        validator = ConfigValidator()
        validator._validate_connection(config)

        errors = [
            r for r in validator.results if r.level == ValidationLevel.ERROR
        ]
        assert len(errors) == 1
        assert errors[0].field == "imhex_port"
        assert "invalid port" in errors[0].message.lower()

    def test_invalid_port_too_high(self):
        """Test port > 65535 is invalid."""
        config = MockConfig(imhex_port=70000)
        validator = ConfigValidator()
        validator._validate_connection(config)

        errors = [
            r for r in validator.results if r.level == ValidationLevel.ERROR
        ]
        assert len(errors) == 1
        assert errors[0].field == "imhex_port"

    def test_privileged_port_warning(self):
        """Test privileged port generates warning."""
        config = MockConfig(imhex_port=80)
        validator = ConfigValidator()
        validator._validate_connection(config)

        warnings = [
            r for r in validator.results if r.level == ValidationLevel.WARNING
        ]
        assert len(warnings) >= 1
        assert any("privileged port" in w.message.lower() for w in warnings)

    def test_non_standard_port_info(self):
        """Test non-standard port generates info."""
        config = MockConfig(imhex_port=8080)
        validator = ConfigValidator()
        validator._validate_connection(config)

        infos = [
            r for r in validator.results if r.level == ValidationLevel.INFO
        ]
        assert len(infos) >= 1
        assert any("non-standard port" in i.message.lower() for i in infos)


class TestTimeoutValidation:
    """Tests for timeout settings validation."""

    def test_valid_timeouts(self):
        """Test valid timeout configuration."""
        config = MockConfig(connection_timeout=5.0, read_timeout=30.0)
        validator = ConfigValidator()
        validator._validate_timeouts(config)

        errors = [
            r for r in validator.results if r.level == ValidationLevel.ERROR
        ]
        assert len(errors) == 0

    def test_negative_connection_timeout(self):
        """Test negative connection timeout is invalid."""
        config = MockConfig(connection_timeout=-1.0)
        validator = ConfigValidator()
        validator._validate_timeouts(config)

        errors = [
            r for r in validator.results if r.level == ValidationLevel.ERROR
        ]
        assert len(errors) >= 1
        assert any("connection_timeout" in e.field for e in errors)

    def test_zero_connection_timeout(self):
        """Test zero connection timeout is invalid."""
        config = MockConfig(connection_timeout=0.0)
        validator = ConfigValidator()
        validator._validate_timeouts(config)

        errors = [
            r for r in validator.results if r.level == ValidationLevel.ERROR
        ]
        assert len(errors) >= 1

    def test_short_connection_timeout_warning(self):
        """Test very short connection timeout generates warning."""
        config = MockConfig(connection_timeout=0.5)
        validator = ConfigValidator()
        validator._validate_timeouts(config)

        warnings = [
            r for r in validator.results if r.level == ValidationLevel.WARNING
        ]
        assert len(warnings) >= 1
        assert any("short" in w.message.lower() for w in warnings)

    def test_long_connection_timeout_warning(self):
        """Test very long connection timeout generates warning."""
        config = MockConfig(connection_timeout=60.0)
        validator = ConfigValidator()
        validator._validate_timeouts(config)

        warnings = [
            r for r in validator.results if r.level == ValidationLevel.WARNING
        ]
        assert len(warnings) >= 1
        assert any("long" in w.message.lower() for w in warnings)

    def test_negative_read_timeout(self):
        """Test negative read timeout is invalid."""
        config = MockConfig(read_timeout=-1.0)
        validator = ConfigValidator()
        validator._validate_timeouts(config)

        errors = [
            r for r in validator.results if r.level == ValidationLevel.ERROR
        ]
        assert len(errors) >= 1

    def test_read_timeout_shorter_than_connection(self):
        """Test read timeout < connection timeout generates warning."""
        config = MockConfig(connection_timeout=10.0, read_timeout=5.0)
        validator = ConfigValidator()
        validator._validate_timeouts(config)

        warnings = [
            r for r in validator.results if r.level == ValidationLevel.WARNING
        ]
        assert len(warnings) >= 1
        assert any(
            "shorter than connection" in w.message.lower() for w in warnings
        )


class TestRetryValidation:
    """Tests for retry settings validation."""

    def test_valid_retry_settings(self):
        """Test valid retry configuration."""
        config = MockConfig(max_retries=3, retry_delay=1.0)
        validator = ConfigValidator()
        validator._validate_retry_settings(config)

        errors = [
            r for r in validator.results if r.level == ValidationLevel.ERROR
        ]
        assert len(errors) == 0

    def test_negative_max_retries(self):
        """Test negative max_retries is invalid."""
        config = MockConfig(max_retries=-1)
        validator = ConfigValidator()
        validator._validate_retry_settings(config)

        errors = [
            r for r in validator.results if r.level == ValidationLevel.ERROR
        ]
        assert len(errors) == 1
        assert errors[0].field == "max_retries"

    def test_high_retry_count_warning(self):
        """Test high retry count generates warning."""
        config = MockConfig(max_retries=15)
        validator = ConfigValidator()
        validator._validate_retry_settings(config)

        warnings = [
            r for r in validator.results if r.level == ValidationLevel.WARNING
        ]
        assert len(warnings) >= 1
        assert any("high retry count" in w.message.lower() for w in warnings)

    def test_negative_retry_delay(self):
        """Test negative retry_delay is invalid."""
        config = MockConfig(retry_delay=-1.0)
        validator = ConfigValidator()
        validator._validate_retry_settings(config)

        errors = [
            r for r in validator.results if r.level == ValidationLevel.ERROR
        ]
        assert len(errors) == 1
        assert errors[0].field == "retry_delay"

    def test_zero_retry_delay_warning(self):
        """Test zero retry delay generates warning."""
        config = MockConfig(retry_delay=0.0)
        validator = ConfigValidator()
        validator._validate_retry_settings(config)

        warnings = [
            r for r in validator.results if r.level == ValidationLevel.WARNING
        ]
        assert len(warnings) >= 1
        assert any("zero retry delay" in w.message.lower() for w in warnings)

    def test_long_retry_delay_warning(self):
        """Test very long retry delay generates warning."""
        config = MockConfig(retry_delay=15.0)
        validator = ConfigValidator()
        validator._validate_retry_settings(config)

        warnings = [
            r for r in validator.results if r.level == ValidationLevel.WARNING
        ]
        assert len(warnings) >= 1
        assert any("long retry delay" in w.message.lower() for w in warnings)


class TestPerformanceValidation:
    """Tests for performance optimization validation."""

    def test_valid_performance_config(self):
        """Test valid performance configuration."""
        config = MockConfig(
            enable_profiling=False,
            enable_performance_optimizations=True,
            enable_cache=True,
            enable_lazy_loading=True,
        )
        validator = ConfigValidator()
        validator._validate_performance(config)

        errors = [
            r for r in validator.results if r.level == ValidationLevel.ERROR
        ]
        assert len(errors) == 0

    def test_profiling_with_optimizations_warning(self):
        """Test profiling enabled with optimizations generates warning."""
        config = MockConfig(
            enable_profiling=True, enable_performance_optimizations=True
        )
        validator = ConfigValidator()
        validator._validate_performance(config)

        warnings = [
            r for r in validator.results if r.level == ValidationLevel.WARNING
        ]
        assert len(warnings) >= 1
        assert any("profiling enabled" in w.message.lower() for w in warnings)

    def test_optimizations_without_cache_warning(self):
        """Test optimizations without cache generates warning."""
        config = MockConfig(
            enable_performance_optimizations=True, enable_cache=False
        )
        validator = ConfigValidator()
        validator._validate_performance(config)

        warnings = [
            r for r in validator.results if r.level == ValidationLevel.WARNING
        ]
        assert len(warnings) >= 1
        assert any("cache disabled" in w.message.lower() for w in warnings)

    def test_optimizations_without_lazy_loading_info(self):
        """Test optimizations without lazy loading generates info."""
        config = MockConfig(
            enable_performance_optimizations=True, enable_lazy_loading=False
        )
        validator = ConfigValidator()
        validator._validate_performance(config)

        infos = [
            r for r in validator.results if r.level == ValidationLevel.INFO
        ]
        assert len(infos) >= 1
        assert any("lazy loading disabled" in i.message.lower() for i in infos)


class TestCacheValidation:
    """Tests for cache settings validation."""

    def test_valid_cache_config(self):
        """Test valid cache configuration."""
        config = MockConfig(enable_cache=True, cache_max_size=1000)
        validator = ConfigValidator()
        validator._validate_cache(config)

        errors = [
            r for r in validator.results if r.level == ValidationLevel.ERROR
        ]
        assert len(errors) == 0

    def test_negative_cache_size(self):
        """Test negative cache size is invalid."""
        config = MockConfig(cache_max_size=-1)
        validator = ConfigValidator()
        validator._validate_cache(config)

        errors = [
            r for r in validator.results if r.level == ValidationLevel.ERROR
        ]
        assert len(errors) == 1
        assert errors[0].field == "cache_max_size"

    def test_zero_cache_size(self):
        """Test zero cache size is invalid."""
        config = MockConfig(cache_max_size=0)
        validator = ConfigValidator()
        validator._validate_cache(config)

        errors = [
            r for r in validator.results if r.level == ValidationLevel.ERROR
        ]
        assert len(errors) == 1

    def test_small_cache_warning(self):
        """Test small cache size generates warning."""
        config = MockConfig(cache_max_size=50)
        validator = ConfigValidator()
        validator._validate_cache(config)

        warnings = [
            r for r in validator.results if r.level == ValidationLevel.WARNING
        ]
        assert len(warnings) >= 1
        assert any("small cache" in w.message.lower() for w in warnings)

    def test_large_cache_warning(self):
        """Test large cache size generates warning."""
        config = MockConfig(cache_max_size=20000)
        validator = ConfigValidator()
        validator._validate_cache(config)

        warnings = [
            r for r in validator.results if r.level == ValidationLevel.WARNING
        ]
        assert len(warnings) >= 1
        assert any("large cache" in w.message.lower() for w in warnings)

    def test_cache_without_optimizations_info(self):
        """Test cache enabled without performance optimizations generates info."""
        config = MockConfig(
            enable_cache=True, enable_performance_optimizations=False
        )
        validator = ConfigValidator()
        validator._validate_cache(config)

        infos = [
            r for r in validator.results if r.level == ValidationLevel.INFO
        ]
        assert len(infos) >= 1
        assert any(
            "performance optimizations disabled" in i.message.lower()
            for i in infos
        )


class TestConsistencyValidation:
    """Tests for configuration consistency validation."""

    def test_valid_total_timeout(self):
        """Test valid total timeout."""
        config = MockConfig(
            connection_timeout=5.0,
            read_timeout=30.0,
            max_retries=3,
            retry_delay=1.0,
        )
        validator = ConfigValidator()
        validator._validate_consistency(config)

        errors = [
            r for r in validator.results if r.level == ValidationLevel.ERROR
        ]
        assert len(errors) == 0

    def test_excessive_total_timeout_warning(self):
        """Test excessive total timeout generates warning."""
        config = MockConfig(
            connection_timeout=60.0,
            read_timeout=120.0,
            max_retries=10,
            retry_delay=20.0,
        )
        validator = ConfigValidator()
        validator._validate_consistency(config)

        warnings = [
            r for r in validator.results if r.level == ValidationLevel.WARNING
        ]
        assert len(warnings) >= 1
        assert any("total_timeout" in w.field for w in warnings)


class TestValidateAll:
    """Tests for complete configuration validation."""

    def test_valid_config_no_errors(self):
        """Test valid configuration produces no errors."""
        config = MockConfig()
        is_valid, results = validate_config(config)

        assert is_valid is True
        errors = [r for r in results if r.level == ValidationLevel.ERROR]
        assert len(errors) == 0

    def test_invalid_config_has_errors(self):
        """Test invalid configuration produces errors."""
        config = MockConfig(
            imhex_port=0, connection_timeout=-1.0, max_retries=-1
        )
        is_valid, results = validate_config(config)

        assert is_valid is False
        errors = [r for r in results if r.level == ValidationLevel.ERROR]
        assert len(errors) >= 3  # At least 3 errors

    def test_mixed_validation_results(self):
        """Test config with errors, warnings, and info."""
        config = MockConfig(
            imhex_port=8080,  # Info: non-standard port
            connection_timeout=0.5,  # Warning: very short
            max_retries=15,  # Warning: high retry count
        )
        is_valid, results = validate_config(config)

        # Should be valid (no errors), but have warnings and info
        assert is_valid is True
        warnings = [r for r in results if r.level == ValidationLevel.WARNING]
        infos = [r for r in results if r.level == ValidationLevel.INFO]
        assert len(warnings) > 0
        assert len(infos) > 0


class TestValidateAndLog:
    """Tests for validation with logging."""

    def test_validate_and_log_valid_config(self, caplog):
        """Test logging for valid configuration."""
        import logging

        logger = logging.getLogger("test_validator")
        config = MockConfig()

        with caplog.at_level(logging.INFO, logger="test_validator"):
            result = validate_and_log(config, logger)

        assert result is True
        assert "PASSED" in caplog.text or "no issues" in caplog.text.lower()

    def test_validate_and_log_invalid_config(self, caplog):
        """Test logging for invalid configuration."""
        import logging

        logger = logging.getLogger("test_validator_invalid")
        config = MockConfig(imhex_port=0)

        with caplog.at_level(logging.ERROR, logger="test_validator_invalid"):
            result = validate_and_log(config, logger)

        assert result is False
        assert "FAILED" in caplog.text or "ERROR" in caplog.text


class TestPrintValidationReport:
    """Tests for validation report printing."""

    def test_print_no_issues(self, capsys):
        """Test printing report with no issues."""
        results = []
        print_validation_report(results)

        captured = capsys.readouterr()
        assert "PASSED" in captured.out
        assert "no issues" in captured.out.lower()

    def test_print_with_errors(self, capsys):
        """Test printing report with errors."""
        results = [
            ValidationResult(
                level=ValidationLevel.ERROR,
                field="test_field",
                message="Test error",
                suggestion="Fix it",
            )
        ]
        print_validation_report(results)

        captured = capsys.readouterr()
        assert "ERROR" in captured.out
        assert "FAILED" in captured.out
        assert "test_field" in captured.out

    def test_print_with_warnings(self, capsys):
        """Test printing report with warnings."""
        results = [
            ValidationResult(
                level=ValidationLevel.WARNING,
                field="test_field",
                message="Test warning",
            )
        ]
        print_validation_report(results)

        captured = capsys.readouterr()
        assert "WARNING" in captured.out
        assert "PASSED" in captured.out  # Still passes with only warnings

    def test_print_with_info(self, capsys):
        """Test printing report with info messages."""
        results = [
            ValidationResult(
                level=ValidationLevel.INFO,
                field="test_field",
                message="Test info",
            )
        ]
        print_validation_report(results)

        captured = capsys.readouterr()
        assert "NOTE" in captured.out or "INFO" in captured.out


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
