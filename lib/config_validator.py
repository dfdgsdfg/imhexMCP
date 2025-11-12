"""
Configuration Validation Module

Validates server configuration at startup to catch issues early.
"""

import logging
from typing import List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ValidationLevel(Enum):
    """Validation message severity levels."""
    ERROR = "error"      # Invalid configuration, must fix
    WARNING = "warning"  # Suboptimal configuration, should review
    INFO = "info"        # Informational message


@dataclass
class ValidationResult:
    """Result of configuration validation."""
    level: ValidationLevel
    field: str
    message: str
    suggestion: Optional[str] = None


class ConfigValidator:
    """Validates server configuration."""

    def __init__(self):
        self.results: List[ValidationResult] = []

    def validate_all(self, config) -> Tuple[bool, List[ValidationResult]]:
        """
        Validate entire configuration.

        Returns:
            Tuple of (is_valid, validation_results)
            is_valid is False if any ERROR level validations failed
        """
        self.results = []

        # Validate each configuration section
        self._validate_connection(config)
        self._validate_timeouts(config)
        self._validate_retry_settings(config)
        self._validate_performance(config)
        self._validate_cache(config)
        self._validate_consistency(config)

        # Check if any errors
        has_errors = any(r.level == ValidationLevel.ERROR for r in self.results)
        return (not has_errors, self.results)

    def _validate_connection(self, config):
        """Validate connection settings."""
        # Host validation
        if not config.imhex_host:
            self.results.append(ValidationResult(
                level=ValidationLevel.ERROR,
                field="imhex_host",
                message="Host cannot be empty",
                suggestion="Set to 'localhost' for local connections"
            ))
        elif config.imhex_host not in ["localhost", "127.0.0.1"] and \
             not config.imhex_host.startswith("192.168.") and \
             not config.imhex_host.startswith("10."):
            self.results.append(ValidationResult(
                level=ValidationLevel.WARNING,
                field="imhex_host",
                message=f"Remote host '{config.imhex_host}' detected",
                suggestion="Ensure ImHex is accessible and firewall allows connection"
            ))

        # Port validation
        if config.imhex_port <= 0 or config.imhex_port > 65535:
            self.results.append(ValidationResult(
                level=ValidationLevel.ERROR,
                field="imhex_port",
                message=f"Invalid port {config.imhex_port}",
                suggestion="Port must be between 1 and 65535 (ImHex default: 31337)"
            ))
        elif config.imhex_port < 1024:
            self.results.append(ValidationResult(
                level=ValidationLevel.WARNING,
                field="imhex_port",
                message=f"Privileged port {config.imhex_port} requires root",
                suggestion="Use port >= 1024 (ImHex default: 31337)"
            ))
        elif config.imhex_port != 31337:
            self.results.append(ValidationResult(
                level=ValidationLevel.INFO,
                field="imhex_port",
                message=f"Non-standard port {config.imhex_port}",
                suggestion="ImHex default is 31337"
            ))

    def _validate_timeouts(self, config):
        """Validate timeout settings."""
        # Connection timeout
        if config.connection_timeout <= 0:
            self.results.append(ValidationResult(
                level=ValidationLevel.ERROR,
                field="connection_timeout",
                message="Connection timeout must be positive",
                suggestion="Set to 5.0 seconds or higher"
            ))
        elif config.connection_timeout < 1.0:
            self.results.append(ValidationResult(
                level=ValidationLevel.WARNING,
                field="connection_timeout",
                message=f"Very short connection timeout: {config.connection_timeout}s",
                suggestion="May cause failures on slow networks. Recommended: >= 5.0s"
            ))
        elif config.connection_timeout > 30.0:
            self.results.append(ValidationResult(
                level=ValidationLevel.WARNING,
                field="connection_timeout",
                message=f"Very long connection timeout: {config.connection_timeout}s",
                suggestion="May delay error detection. Recommended: 5-10s"
            ))

        # Read timeout
        if config.read_timeout <= 0:
            self.results.append(ValidationResult(
                level=ValidationLevel.ERROR,
                field="read_timeout",
                message="Read timeout must be positive",
                suggestion="Set to 30.0 seconds or higher"
            ))
        elif config.read_timeout < 5.0:
            self.results.append(ValidationResult(
                level=ValidationLevel.WARNING,
                field="read_timeout",
                message=f"Very short read timeout: {config.read_timeout}s",
                suggestion="May cause timeouts for large operations. Recommended: >= 30.0s"
            ))
        elif config.read_timeout > 300.0:
            self.results.append(ValidationResult(
                level=ValidationLevel.WARNING,
                field="read_timeout",
                message=f"Very long read timeout: {config.read_timeout}s",
                suggestion="May mask hung connections. Recommended: 30-60s"
            ))

        # Timeout relationship
        if config.read_timeout < config.connection_timeout:
            self.results.append(ValidationResult(
                level=ValidationLevel.WARNING,
                field="read_timeout",
                message="Read timeout shorter than connection timeout",
                suggestion="read_timeout should be >= connection_timeout"
            ))

    def _validate_retry_settings(self, config):
        """Validate retry settings."""
        # Max retries
        if config.max_retries < 0:
            self.results.append(ValidationResult(
                level=ValidationLevel.ERROR,
                field="max_retries",
                message="max_retries cannot be negative",
                suggestion="Set to 0 to disable retries, or >= 1 to enable"
            ))
        elif config.max_retries > 10:
            self.results.append(ValidationResult(
                level=ValidationLevel.WARNING,
                field="max_retries",
                message=f"High retry count: {config.max_retries}",
                suggestion="May cause long delays on persistent failures. Recommended: 1-3"
            ))

        # Retry delay
        if config.retry_delay < 0:
            self.results.append(ValidationResult(
                level=ValidationLevel.ERROR,
                field="retry_delay",
                message="retry_delay cannot be negative",
                suggestion="Set to 0.5-2.0 seconds"
            ))
        elif config.retry_delay == 0:
            self.results.append(ValidationResult(
                level=ValidationLevel.WARNING,
                field="retry_delay",
                message="Zero retry delay may hammer the server",
                suggestion="Use exponential backoff or delay >= 0.5s"
            ))
        elif config.retry_delay > 10.0:
            self.results.append(ValidationResult(
                level=ValidationLevel.WARNING,
                field="retry_delay",
                message=f"Very long retry delay: {config.retry_delay}s",
                suggestion="May cause long delays. Recommended: 0.5-2.0s"
            ))

    def _validate_performance(self, config):
        """Validate performance optimization settings."""
        # Profiling in production
        if config.enable_profiling and config.enable_performance_optimizations:
            self.results.append(ValidationResult(
                level=ValidationLevel.WARNING,
                field="enable_profiling",
                message="Profiling enabled in optimized mode",
                suggestion="Disable profiling in production for maximum performance"
            ))

        # Performance optimizations without cache
        if config.enable_performance_optimizations and not config.enable_cache:
            self.results.append(ValidationResult(
                level=ValidationLevel.WARNING,
                field="enable_cache",
                message="Performance optimizations enabled but cache disabled",
                suggestion="Enable cache for best performance"
            ))

        # Lazy loading warning
        if config.enable_performance_optimizations and not config.enable_lazy_loading:
            self.results.append(ValidationResult(
                level=ValidationLevel.INFO,
                field="enable_lazy_loading",
                message="Lazy loading disabled",
                suggestion="Enable for faster startup"
            ))

    def _validate_cache(self, config):
        """Validate cache settings."""
        # Cache size
        if config.cache_max_size <= 0:
            self.results.append(ValidationResult(
                level=ValidationLevel.ERROR,
                field="cache_max_size",
                message="cache_max_size must be positive",
                suggestion="Set to 1000 or higher"
            ))
        elif config.cache_max_size < 100:
            self.results.append(ValidationResult(
                level=ValidationLevel.WARNING,
                field="cache_max_size",
                message=f"Small cache size: {config.cache_max_size}",
                suggestion="May cause low hit rate. Recommended: >= 1000"
            ))
        elif config.cache_max_size > 10000:
            self.results.append(ValidationResult(
                level=ValidationLevel.WARNING,
                field="cache_max_size",
                message=f"Large cache size: {config.cache_max_size}",
                suggestion="May consume significant memory. Monitor usage"
            ))

        # Cache enabled but performance optimizations disabled
        if config.enable_cache and not config.enable_performance_optimizations:
            self.results.append(ValidationResult(
                level=ValidationLevel.INFO,
                field="enable_cache",
                message="Cache enabled but performance optimizations disabled",
                suggestion="Enable performance_optimizations to use enhanced client with cache"
            ))

    def _validate_consistency(self, config):
        """Validate configuration consistency."""
        # Total timeout calculation
        total_timeout = (config.connection_timeout +
                        config.read_timeout +
                        config.max_retries * config.retry_delay)

        if total_timeout > 300:  # 5 minutes
            self.results.append(ValidationResult(
                level=ValidationLevel.WARNING,
                field="total_timeout",
                message=f"Combined timeouts are very long: {total_timeout:.1f}s",
                suggestion="May cause long waits on failures. Review timeout settings"
            ))


def validate_config(config) -> Tuple[bool, List[ValidationResult]]:
    """
    Validate configuration and return results.

    Returns:
        Tuple of (is_valid, results)
        - is_valid: True if no ERROR level issues
        - results: List of validation results
    """
    validator = ConfigValidator()
    return validator.validate_all(config)


def validate_and_log(config, logger_obj: Optional[logging.Logger] = None) -> bool:
    """
    Validate configuration and log results.

    Returns:
        True if configuration is valid (no errors)
    """
    if logger_obj is None:
        logger_obj = logger

    is_valid, results = validate_config(config)

    if not results:
        logger_obj.info("Configuration validation: PASSED (no issues)")
        return True

    # Group by level
    errors = [r for r in results if r.level == ValidationLevel.ERROR]
    warnings = [r for r in results if r.level == ValidationLevel.WARNING]
    infos = [r for r in results if r.level == ValidationLevel.INFO]

    # Log errors
    if errors:
        logger_obj.error(f"Configuration validation: FAILED ({len(errors)} errors)")
        for result in errors:
            logger_obj.error(f"  [ERROR] {result.field}: {result.message}")
            if result.suggestion:
                logger_obj.error(f"    → {result.suggestion}")

    # Log warnings
    if warnings:
        logger_obj.warning(f"Configuration warnings: {len(warnings)}")
        for result in warnings:
            logger_obj.warning(f"  [WARN] {result.field}: {result.message}")
            if result.suggestion:
                logger_obj.warning(f"    → {result.suggestion}")

    # Log infos
    if infos:
        logger_obj.info(f"Configuration notes: {len(infos)}")
        for result in infos:
            logger_obj.info(f"  [INFO] {result.field}: {result.message}")

    # Summary
    if is_valid:
        logger_obj.info(f"Configuration validation: PASSED ({len(warnings)} warnings, {len(infos)} notes)")
    else:
        logger_obj.error("Configuration validation: FAILED - Cannot start with errors")

    return is_valid


def print_validation_report(results: List[ValidationResult]):
    """Print human-readable validation report."""
    if not results:
        print("\n✓ Configuration validation: PASSED (no issues)\n")
        return

    errors = [r for r in results if r.level == ValidationLevel.ERROR]
    warnings = [r for r in results if r.level == ValidationLevel.WARNING]
    infos = [r for r in results if r.level == ValidationLevel.INFO]

    print("\n" + "=" * 70)
    print("Configuration Validation Report")
    print("=" * 70)

    if errors:
        print(f"\n❌ ERRORS ({len(errors)}):")
        for result in errors:
            print(f"\n  Field: {result.field}")
            print(f"  Issue: {result.message}")
            if result.suggestion:
                print(f"  Fix:   {result.suggestion}")

    if warnings:
        print(f"\n⚠️  WARNINGS ({len(warnings)}):")
        for result in warnings:
            print(f"\n  Field: {result.field}")
            print(f"  Issue: {result.message}")
            if result.suggestion:
                print(f"  Suggestion: {result.suggestion}")

    if infos:
        print(f"\nℹ️  NOTES ({len(infos)}):")
        for result in infos:
            print(f"\n  Field: {result.field}")
            print(f"  Note: {result.message}")

    print("\n" + "=" * 70)
    if errors:
        print("Status: ❌ FAILED - Cannot start with errors")
    elif warnings:
        print(f"Status: ⚠️  PASSED with {len(warnings)} warnings")
    else:
        print(f"Status: ✓ PASSED ({len(infos)} notes)")
    print("=" * 70 + "\n")
