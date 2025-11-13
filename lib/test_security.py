"""
Tests for Security Module

Tests rate limiting, input validation, and security hardening.
"""

import asyncio
import pytest
from security import (
    SecurityManager,
    SecurityConfig,
    RateLimitConfig,
    ValidationConfig,
    RateLimitExceeded,
    InvalidInput,
    PayloadTooLarge,
    TokenBucket,
    InputValidator
)


class TestTokenBucket:
    """Tests for token bucket rate limiter."""

    @pytest.mark.asyncio
    async def test_basic_token_acquisition(self):
        """Test basic token acquisition."""
        bucket = TokenBucket(rate=10.0, capacity=10)

        # Should be able to acquire tokens immediately
        assert await bucket.acquire(1) is True
        assert await bucket.acquire(5) is True

    @pytest.mark.asyncio
    async def test_rate_limit_enforcement(self):
        """Test rate limit is enforced."""
        bucket = TokenBucket(rate=10.0, capacity=10)

        # Exhaust all tokens
        assert await bucket.acquire(10) is True

        # Next acquisition should fail
        assert await bucket.acquire(1) is False

    @pytest.mark.asyncio
    async def test_token_replenishment(self):
        """Test tokens are replenished over time."""
        bucket = TokenBucket(rate=100.0, capacity=10)

        # Exhaust tokens
        await bucket.acquire(10)

        # Wait for replenishment
        await asyncio.sleep(0.2)  # 20 tokens should be added

        # Should be able to acquire again
        assert await bucket.acquire(10) is True

    @pytest.mark.asyncio
    async def test_wait_for_tokens(self):
        """Test waiting for tokens."""
        bucket = TokenBucket(rate=100.0, capacity=5)

        # Exhaust tokens
        await bucket.acquire(5)

        # Wait for tokens (should succeed within timeout)
        success = await bucket.wait_for_tokens(tokens=3, timeout=0.1)
        assert success is True

    @pytest.mark.asyncio
    async def test_wait_for_tokens_timeout(self):
        """Test wait timeout."""
        bucket = TokenBucket(rate=1.0, capacity=5)

        # Exhaust tokens
        await bucket.acquire(5)

        # Wait should timeout (need 10 tokens but only 1/sec)
        success = await bucket.wait_for_tokens(tokens=10, timeout=0.1)
        assert success is False


class TestInputValidator:
    """Tests for input validator."""

    def test_validate_string_success(self):
        """Test successful string validation."""
        validator = InputValidator(ValidationConfig())

        result = validator.validate_string("test_value")
        assert result == "test_value"

    def test_validate_string_too_long(self):
        """Test string length validation."""
        config = ValidationConfig(max_string_length=10)
        validator = InputValidator(config)

        with pytest.raises(InvalidInput, match="exceeds maximum length"):
            validator.validate_string("x" * 100)

    def test_validate_string_sanitization(self):
        """Test string sanitization."""
        validator = InputValidator(ValidationConfig())

        # Test control character removal
        result = validator.validate_string("test\x00value\x01end")
        assert "\x00" not in result
        assert "\x01" not in result

    def test_validate_integer_success(self):
        """Test successful integer validation."""
        validator = InputValidator(ValidationConfig())

        result = validator.validate_integer(42)
        assert result == 42

        result = validator.validate_integer("123")
        assert result == 123

    def test_validate_integer_range(self):
        """Test integer range validation."""
        validator = InputValidator(ValidationConfig())

        with pytest.raises(InvalidInput, match="must be >= 0"):
            validator.validate_integer(-5, min_value=0)

        with pytest.raises(InvalidInput, match="must be <= 100"):
            validator.validate_integer(200, max_value=100)

    def test_validate_hex_string(self):
        """Test hex string validation."""
        validator = InputValidator(ValidationConfig())

        result = validator.validate_hex_string("ABCDEF123")
        assert result == "ABCDEF123"

        with pytest.raises(InvalidInput, match="hex characters"):
            validator.validate_hex_string("GHIJKL")

    def test_validate_path_traversal_protection(self):
        """Test path traversal protection."""
        validator = InputValidator(ValidationConfig())

        with pytest.raises(InvalidInput, match="path traversal"):
            validator.validate_path("../etc/passwd")

        with pytest.raises(InvalidInput, match="path traversal"):
            validator.validate_path("~/sensitive")

    def test_validate_path_blocked_patterns(self):
        """Test blocked path patterns."""
        validator = InputValidator(ValidationConfig())

        with pytest.raises(InvalidInput, match="forbidden pattern"):
            validator.validate_path("/etc/shadow")

        with pytest.raises(InvalidInput, match="forbidden pattern"):
            validator.validate_path("/proc/self/environ")

    def test_validate_payload_size(self):
        """Test payload size validation."""
        config = ValidationConfig(max_payload_size=1000)
        validator = InputValidator(config)

        # Small payload should pass
        validator.validate_payload_size("x" * 100)

        # Large payload should fail
        with pytest.raises(PayloadTooLarge):
            validator.validate_payload_size("x" * 2000)

    def test_validate_endpoint_data(self):
        """Test endpoint data validation."""
        validator = InputValidator(ValidationConfig(
            allowed_path_patterns=[".*"]
        ))

        data = {
            "provider_id": "0",
            "offset": "100",
            "size": "1024",
            "pattern": "ABCD1234"
        }

        result = validator.validate_endpoint_data("file/read", data)

        assert result["provider_id"] == 0
        assert result["offset"] == 100
        assert result["size"] == 1024
        assert result["pattern"] == "ABCD1234"


class TestSecurityManager:
    """Tests for security manager."""

    @pytest.mark.asyncio
    async def test_rate_limiting(self):
        """Test rate limiting enforcement."""
        config = SecurityConfig(
            rate_limit=RateLimitConfig(
                enabled=True,
                requests_per_second=10.0,
                burst_size=10
            )
        )
        manager = SecurityManager(config)

        # First 10 requests should succeed
        for _ in range(10):
            await manager.check_request("test/endpoint", {})

        # 11th request should fail
        with pytest.raises(RateLimitExceeded):
            await manager.check_request("test/endpoint", {})

    @pytest.mark.asyncio
    async def test_input_validation(self):
        """Test input validation."""
        config = SecurityConfig(
            validation=ValidationConfig(
                allowed_path_patterns=[".*"]
            )
        )
        manager = SecurityManager(config)

        # Valid data should pass
        data = {"provider_id": 0, "offset": 100, "size": 1024}
        result = await manager.check_request("file/read", data)
        assert result["provider_id"] == 0

        # Invalid data should fail
        with pytest.raises(InvalidInput):
            await manager.check_request("file/read", {"offset": -100})

    @pytest.mark.asyncio
    async def test_payload_size_limit(self):
        """Test payload size limiting."""
        config = SecurityConfig(
            validation=ValidationConfig(max_payload_size=100)
        )
        manager = SecurityManager(config)

        # Small payload should pass
        await manager.check_request("test", {"data": "x" * 50})

        # Large payload should fail
        with pytest.raises(PayloadTooLarge):
            await manager.check_request("test", {"data": "x" * 500})

    @pytest.mark.asyncio
    async def test_per_client_rate_limiting(self):
        """Test per-client rate limiting."""
        config = SecurityConfig(
            rate_limit=RateLimitConfig(
                enabled=True,
                requests_per_second=100.0,
                burst_size=10,
                per_client=True
            )
        )
        manager = SecurityManager(config)

        # Exhaust one client's limit
        for _ in range(10):
            await manager.check_request("test", {}, client_id="client1")

        # Client 1 should be rate limited
        with pytest.raises(RateLimitExceeded):
            await manager.check_request("test", {}, client_id="client1")

        # Client 2 should still work
        await manager.check_request("test", {}, client_id="client2")

    @pytest.mark.asyncio
    async def test_disabled_security(self):
        """Test that disabled security allows all requests."""
        config = SecurityConfig(
            rate_limit=RateLimitConfig(enabled=False),
            validation=ValidationConfig(enabled=False)
        )
        manager = SecurityManager(config)

        # Even many requests should succeed with disabled rate limiting
        for _ in range(1000):
            await manager.check_request("test", {})


async def main():
    """Run all tests."""
    print("Running Security Module Tests...")
    print("=" * 70)

    # Test Token Bucket
    print("\n[1/10] Testing Token Bucket - Basic Acquisition...")
    test = TestTokenBucket()
    await test.test_basic_token_acquisition()
    print("  ✓ PASSED")

    print("[2/10] Testing Token Bucket - Rate Limit Enforcement...")
    await test.test_rate_limit_enforcement()
    print("  ✓ PASSED")

    print("[3/10] Testing Token Bucket - Token Replenishment...")
    await test.test_token_replenishment()
    print("  ✓ PASSED")

    # Test Input Validator
    print("\n[4/10] Testing Input Validator - String Validation...")
    validator_test = TestInputValidator()
    validator_test.test_validate_string_success()
    print("  ✓ PASSED")

    print("[5/10] Testing Input Validator - String Length...")
    validator_test.test_validate_string_too_long()
    print("  ✓ PASSED")

    print("[6/10] Testing Input Validator - Hex Validation...")
    validator_test.test_validate_hex_string()
    print("  ✓ PASSED")

    print("[7/10] Testing Input Validator - Path Traversal Protection...")
    validator_test.test_validate_path_traversal_protection()
    print("  ✓ PASSED")

    # Test Security Manager
    print("\n[8/10] Testing Security Manager - Rate Limiting...")
    manager_test = TestSecurityManager()
    await manager_test.test_rate_limiting()
    print("  ✓ PASSED")

    print("[9/10] Testing Security Manager - Input Validation...")
    await manager_test.test_input_validation()
    print("  ✓ PASSED")

    print("[10/10] Testing Security Manager - Per-Client Rate Limiting...")
    await manager_test.test_per_client_rate_limiting()
    print("  ✓ PASSED")

    print("\n" + "=" * 70)
    print("All Security Tests PASSED!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
