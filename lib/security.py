"""
Security Module for ImHex MCP

Provides rate limiting, input validation, and security hardening features.

Features:
- Token bucket rate limiting
- Input validation and sanitization
- Request size limits
- Path traversal protection
- JSON payload validation
"""

import asyncio
import time
import re
from typing import Dict, Any, Optional, List
from pathlib import Path
from dataclasses import dataclass, field


class SecurityViolation(Exception):
    """Exception raised for security violations."""


class RateLimitExceeded(SecurityViolation):
    """Exception raised when rate limit is exceeded."""


class InvalidInput(SecurityViolation):
    """Exception raised for invalid or malicious input."""


class PayloadTooLarge(SecurityViolation):
    """Exception raised when payload exceeds size limit."""


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""

    enabled: bool = True
    requests_per_second: float = 100.0  # Maximum requests per second
    burst_size: int = 200  # Maximum burst capacity
    per_client: bool = True  # Track limits per client (host:port)


@dataclass
class ValidationConfig:
    """Configuration for input validation."""

    enabled: bool = True
    max_payload_size: int = 10 * 1024 * 1024  # 10 MB max payload
    max_string_length: int = 10000  # Max string length
    max_path_length: int = 4096  # Max file path length
    allowed_path_patterns: List[str] = field(
        default_factory=lambda: [".*"]
    )  # Regex patterns
    blocked_path_patterns: List[str] = field(
        default_factory=lambda: [
            r"\.\./",  # Path traversal
            r"~",  # Home directory expansion
            r"/etc/",  # System files
            r"/proc/",  # Process info
            r"/sys/",  # System info
        ]
    )
    sanitize_strings: bool = True  # Remove control characters


class TokenBucket:
    """
    Token bucket rate limiter.

    Implements the token bucket algorithm for rate limiting.
    Allows bursts while maintaining average rate.
    """

    def __init__(self, rate: float, capacity: int):
        """
        Initialize token bucket.

        Args:
            rate: Tokens added per second (requests per second)
            capacity: Maximum tokens (burst size)
        """
        self.rate = rate
        self.capacity = capacity
        self.tokens = float(capacity)
        self.last_update = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self, tokens: int = 1) -> bool:
        """
        Try to acquire tokens from bucket.

        Args:
            tokens: Number of tokens to acquire

        Returns:
            True if tokens acquired, False if rate limit exceeded
        """
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self.last_update

            # Add new tokens based on elapsed time
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
            self.last_update = now

            # Try to acquire tokens
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True

            return False

    async def wait_for_tokens(
        self, tokens: int = 1, timeout: Optional[float] = None
    ) -> bool:
        """
        Wait until tokens are available.

        Args:
            tokens: Number of tokens to acquire
            timeout: Maximum time to wait in seconds

        Returns:
            True if tokens acquired, False if timeout
        """
        start_time = time.monotonic()

        while True:
            if await self.acquire(tokens):
                return True

            # Check timeout
            if timeout is not None:
                elapsed = time.monotonic() - start_time
                if elapsed >= timeout:
                    return False

            # Wait a bit before retrying
            await asyncio.sleep(0.01)


class RateLimiter:
    """
    Rate limiter with per-client tracking.

    Manages rate limits for multiple clients using token buckets.
    """

    def __init__(self, config: RateLimitConfig):
        """Initialize rate limiter with configuration."""
        self.config = config
        self.global_bucket: Optional[TokenBucket] = None
        self.client_buckets: Dict[str, TokenBucket] = {}
        self._cleanup_task: Optional[asyncio.Task] = None

        if config.enabled:
            # Create global rate limiter
            self.global_bucket = TokenBucket(
                rate=config.requests_per_second, capacity=config.burst_size
            )

    async def check_rate_limit(self, client_id: Optional[str] = None) -> None:
        """
        Check if request is within rate limit.

        Args:
            client_id: Optional client identifier (host:port)

        Raises:
            RateLimitExceeded: If rate limit exceeded
        """
        if not self.config.enabled:
            return

        # Check global rate limit
        if self.global_bucket and not await self.global_bucket.acquire():
            raise RateLimitExceeded("Global rate limit exceeded")

        # Check per-client rate limit
        if self.config.per_client and client_id:
            if client_id not in self.client_buckets:
                self.client_buckets[client_id] = TokenBucket(
                    rate=self.config.requests_per_second
                    / 10,  # 10% of global per client
                    capacity=self.config.burst_size // 10,
                )

            if not await self.client_buckets[client_id].acquire():
                raise RateLimitExceeded(
                    f"Rate limit exceeded for client {client_id}"
                )

    async def cleanup_old_clients(self, max_age: float = 300.0) -> None:
        """
        Periodically clean up old client buckets.

        Args:
            max_age: Maximum age in seconds before removing client
        """
        while True:
            await asyncio.sleep(60)  # Clean up every minute

            now = time.monotonic()
            to_remove = [
                client_id
                for client_id, bucket in self.client_buckets.items()
                if now - bucket.last_update > max_age
            ]

            for client_id in to_remove:
                del self.client_buckets[client_id]


class InputValidator:
    """
    Input validation and sanitization.

    Validates and sanitizes all user inputs to prevent security vulnerabilities.
    """

    def __init__(self, config: ValidationConfig):
        """Initialize validator with configuration."""
        self.config = config

    def validate_string(self, value: str, field_name: str = "value") -> str:
        """
        Validate and sanitize string input.

        Args:
            value: String to validate
            field_name: Name of field for error messages

        Returns:
            Sanitized string

        Raises:
            InvalidInput: If validation fails
        """
        if not isinstance(value, str):
            raise InvalidInput(f"{field_name} must be a string")

        # Check length
        if len(value) > self.config.max_string_length:
            raise InvalidInput(
                f"{field_name} exceeds maximum length of {
                    self.config.max_string_length}"
            )

        # Sanitize control characters if enabled
        if self.config.sanitize_strings:
            # Remove null bytes and other control characters
            value = "".join(
                char for char in value if char >= " " or char in "\n\r\t"
            )

        return value

    def validate_integer(
        self,
        value: Any,
        field_name: str = "value",
        min_value: Optional[int] = None,
        max_value: Optional[int] = None,
    ) -> int:
        """
        Validate integer input.

        Args:
            value: Value to validate
            field_name: Name of field for error messages
            min_value: Minimum allowed value
            max_value: Maximum allowed value

        Returns:
            Validated integer

        Raises:
            InvalidInput: If validation fails
        """
        if not isinstance(value, int):
            try:
                value = int(value)
            except (TypeError, ValueError):
                raise InvalidInput(f"{field_name} must be an integer")

        if min_value is not None and value < min_value:
            raise InvalidInput(f"{field_name} must be >= {min_value}")

        if max_value is not None and value > max_value:
            raise InvalidInput(f"{field_name} must be <= {max_value}")

        return value

    def validate_path(self, path: str, field_name: str = "path") -> Path:
        """
        Validate file path for security.

        Args:
            path: File path to validate
            field_name: Name of field for error messages

        Returns:
            Validated Path object

        Raises:
            InvalidInput: If path is invalid or insecure
        """
        # Basic validation
        path = self.validate_string(path, field_name)

        # Check length
        if len(path) > self.config.max_path_length:
            raise InvalidInput(f"{field_name} exceeds maximum length")

        # Check for blocked patterns
        for pattern in self.config.blocked_path_patterns:
            if re.search(pattern, path):
                raise InvalidInput(
                    f"{field_name} contains forbidden pattern: {pattern}"
                )

        # Check allowed patterns
        allowed = False
        for pattern in self.config.allowed_path_patterns:
            if re.match(pattern, path):
                allowed = True
                break

        if not allowed:
            raise InvalidInput(f"{field_name} does not match allowed patterns")

        # Convert to absolute path and check for traversal
        try:
            resolved = Path(path).resolve()
        except Exception as e:
            raise InvalidInput(f"Invalid path: {e}")

        # Additional traversal check
        if ".." in path or path.startswith("~"):
            raise InvalidInput(
                f"{field_name} contains forbidden path traversal"
            )

        return resolved

    def validate_hex_string(
        self, value: str, field_name: str = "hex_value"
    ) -> str:
        """
        Validate hexadecimal string.

        Args:
            value: Hex string to validate
            field_name: Name of field for error messages

        Returns:
            Validated hex string

        Raises:
            InvalidInput: If not valid hex
        """
        value = self.validate_string(value, field_name)

        # Check if valid hex
        if not re.match(r"^[0-9A-Fa-f]*$", value):
            raise InvalidInput(
                f"{field_name} must contain only hex characters"
            )

        return value.upper()

    def validate_payload_size(self, payload: Any) -> None:
        """
        Validate payload size to prevent memory exhaustion.

        Args:
            payload: Payload to check (dict, string, bytes, etc.)

        Raises:
            PayloadTooLarge: If payload exceeds size limit
        """
        if not self.config.enabled:
            return

        # Estimate payload size
        if isinstance(payload, (str, bytes)):
            size = len(payload)
        elif isinstance(payload, dict):
            # Rough estimate for dict size
            import json

            size = len(json.dumps(payload))
        else:
            # For other types, skip check
            return

        if size > self.config.max_payload_size:
            raise PayloadTooLarge(
                f"Payload size {size} exceeds limit of {
                    self.config.max_payload_size}"
            )

    def validate_endpoint_data(
        self, endpoint: str, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate data for specific endpoint.

        Args:
            endpoint: Endpoint name
            data: Request data

        Returns:
            Validated data dictionary

        Raises:
            InvalidInput: If validation fails
        """
        validated: Dict[str, Any] = {}

        # Common validations for file operations
        if "provider_id" in data:
            validated["provider_id"] = self.validate_integer(
                data["provider_id"], "provider_id", min_value=0
            )

        if "offset" in data:
            validated["offset"] = self.validate_integer(
                data["offset"], "offset", min_value=0
            )

        if "size" in data:
            validated["size"] = self.validate_integer(
                data["size"],
                "size",
                min_value=0,
                max_value=100 * 1024 * 1024,  # 100 MB max read size
            )

        if "path" in data:
            validated["path"] = str(self.validate_path(data["path"]))

        if "pattern" in data:
            validated["pattern"] = self.validate_hex_string(data["pattern"])

        # Copy other fields with basic validation
        for key, value in data.items():
            if key not in validated:
                if isinstance(value, str):
                    validated[key] = self.validate_string(value, key)
                elif isinstance(value, int):
                    validated[key] = self.validate_integer(value, key)
                else:
                    validated[key] = value

        return validated


@dataclass
class SecurityConfig:
    """Master security configuration."""

    rate_limit: RateLimitConfig = field(default_factory=RateLimitConfig)
    validation: ValidationConfig = field(default_factory=ValidationConfig)


class SecurityManager:
    """
    Centralized security management.

    Combines rate limiting, input validation, and other security features.
    """

    def __init__(self, config: Optional[SecurityConfig] = None):
        """Initialize security manager."""
        self.config = config or SecurityConfig()
        self.rate_limiter = RateLimiter(self.config.rate_limit)
        self.validator = InputValidator(self.config.validation)

    async def check_request(
        self,
        endpoint: str,
        data: Dict[str, Any],
        client_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Perform all security checks on a request.

        Args:
            endpoint: Endpoint being accessed
            data: Request data
            client_id: Optional client identifier

        Returns:
            Validated and sanitized data

        Raises:
            SecurityViolation: If any security check fails
        """
        # Check rate limit
        await self.rate_limiter.check_rate_limit(client_id)

        # Validate payload size
        self.validator.validate_payload_size(data)

        # Validate endpoint data
        validated_data = self.validator.validate_endpoint_data(endpoint, data)

        return validated_data

    async def start(self) -> None:
        """Start security manager background tasks."""
        # Start cleanup task
        if self.config.rate_limit.enabled:
            asyncio.create_task(self.rate_limiter.cleanup_old_clients())

    async def stop(self) -> None:
        """Stop security manager background tasks."""
        # Cleanup task will be cancelled when event loop stops
