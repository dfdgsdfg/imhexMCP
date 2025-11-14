#!/usr/bin/env python3
"""
ImHex MCP Cached Client

High-performance client wrapper with automatic response caching.
Reduces redundant requests and improves throughput for repeated operations.
"""

from error_handling import retry_with_backoff
from cache import ResponseCache, CachingStrategy
import socket
import json
import sys
from pathlib import Path
from typing import Dict, Any, Optional

# Add lib directory to path
sys.path.insert(0, str(Path(__file__).parent))


class CachedImHexClient:
    """
    ImHex MCP client with automatic response caching and retry logic.

    Combines error handling, retry logic, and response caching for optimal
    performance and reliability.

    Features:
    - Automatic response caching with endpoint-specific TTLs
    - Exponential backoff retry on transient failures
    - Cache statistics and monitoring
    - Configurable cache size and TTL policies
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 31337,
        timeout: int = 10,
        cache_enabled: bool = True,
        cache_max_size: int = 1000,
        default_ttl: Optional[float] = None,
    ):
        """
        Initialize cached client.

        Args:
            host: ImHex MCP host
            port: ImHex MCP port
            timeout: Socket timeout in seconds
            cache_enabled: Enable response caching
            cache_max_size: Maximum cache entries
            default_ttl: Default cache TTL in seconds (None = use strategy)
        """
        self.host = host
        self.port = port
        self.timeout = timeout
        self.cache_enabled = cache_enabled

        # Initialize cache
        self.cache = (
            ResponseCache(max_size=cache_max_size, default_ttl=default_ttl)
            if cache_enabled
            else None
        )

        # Track cacheable endpoints (read-only operations)
        self.cacheable_endpoints = {
            "capabilities",
            "file/list",
            "file/current",
            "file/info",
            "data/read",
            "data/hash",
            "data/entropy",
            "data/statistics",
            "data/search",
            "data/strings",
            "data/magic",
            "data/disassemble",
        }

        # Track invalidating endpoints (modify state)
        self.invalidating_endpoints = {
            "file/open": ["file/list", "file/current"],
            "file/close": ["file/list", "file/current"],
            "file/create": ["file/list"],
            "data/write": ["data/read", "data/hash"],
        }

    def _is_cacheable(self, endpoint: str) -> bool:
        """Check if endpoint response can be cached."""
        return endpoint in self.cacheable_endpoints

    def _get_cache_ttl(self, endpoint: str) -> float:
        """Get appropriate TTL for endpoint."""
        return CachingStrategy.get_ttl_for_endpoint(endpoint)

    @retry_with_backoff(
        max_attempts=3, initial_delay=0.5, exponential_base=2.0
    )
    def _send_request(
        self, endpoint: str, data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Send raw request to ImHex MCP.

        This method includes automatic retry with exponential backoff.

        Args:
            endpoint: API endpoint name
            data: Request parameters

        Returns:
            Response dictionary

        Raises:
            ImHexConnectionError: If connection fails after retries
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            sock.connect((self.host, self.port))

            request = (
                json.dumps({"endpoint": endpoint, "data": data or {}}) + "\n"
            )

            sock.sendall(request.encode())

            response = b""
            while b"\n" not in response:
                response += sock.recv(4096)

            sock.close()
            return json.loads(response.decode().strip())

        except (socket.error, socket.timeout, ConnectionRefusedError):
            # Let retry decorator handle these
            raise

        except Exception as e:
            return {"status": "error", "data": {"error": str(e)}}

    def send_request(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        bypass_cache: bool = False,
    ) -> Dict[str, Any]:
        """
        Send request with automatic caching.

        Args:
            endpoint: API endpoint name
            data: Request parameters
            bypass_cache: Force bypass cache for this request

        Returns:
            Response dictionary
        """
        # Check cache first (if enabled and cacheable)
        if (
            not bypass_cache
            and self.cache_enabled
            and self._is_cacheable(endpoint)
        ):
            cached_result = self.cache.get(endpoint, data)
            if cached_result is not None:
                return cached_result

        # Execute actual request
        result = self._send_request(endpoint, data)

        # Handle cache invalidation for state-changing endpoints
        if endpoint in self.invalidating_endpoints:
            for invalidated_endpoint in self.invalidating_endpoints[endpoint]:
                self.cache.invalidate(invalidated_endpoint)

        # Cache successful responses for cacheable endpoints
        if (
            self.cache_enabled
            and self._is_cacheable(endpoint)
            and result.get("status") == "success"
        ):
            ttl = self._get_cache_ttl(endpoint)
            self.cache.set(endpoint, data, result, ttl=ttl)

        return result

    def get_cache_stats(self) -> Optional[Dict[str, Any]]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats or None if caching disabled
        """
        if not self.cache_enabled or self.cache is None:
            return None

        return self.cache.get_stats()

    def clear_cache(self) -> None:
        """Clear all cached responses."""
        if self.cache_enabled and self.cache is not None:
            self.cache.clear()

    def invalidate_endpoint(
        self, endpoint: str, data: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Manually invalidate cached entries.

        Args:
            endpoint: Endpoint to invalidate
            data: Specific parameters to invalidate (None = all)

        Returns:
            Number of entries invalidated
        """
        if not self.cache_enabled or self.cache is None:
            return 0

        return self.cache.invalidate(endpoint, data)

    def cleanup_expired(self) -> int:
        """
        Remove expired cache entries.

        Returns:
            Number of entries removed
        """
        if not self.cache_enabled or self.cache is None:
            return 0

        return self.cache.cleanup_expired()

    # Convenience methods for common operations

    def get_capabilities(self) -> Dict[str, Any]:
        """Get ImHex MCP capabilities."""
        return self.send_request("capabilities")

    def list_files(self) -> Dict[str, Any]:
        """List open files."""
        return self.send_request("file/list")

    def get_current_file(self) -> Dict[str, Any]:
        """Get current file info."""
        return self.send_request("file/current")

    def get_file_info(self, provider_id: int) -> Dict[str, Any]:
        """Get file information."""
        return self.send_request("file/info", {"provider_id": provider_id})

    def read_data(
        self, provider_id: int, offset: int, size: int
    ) -> Dict[str, Any]:
        """Read data from provider."""
        return self.send_request(
            "data/read",
            {"provider_id": provider_id, "offset": offset, "size": size},
        )

    def hash_data(
        self, provider_id: int, offset: int, size: int, algorithm: str = "md5"
    ) -> Dict[str, Any]:
        """Calculate hash of data."""
        return self.send_request(
            "data/hash",
            {
                "provider_id": provider_id,
                "offset": offset,
                "size": size,
                "algorithm": algorithm,
            },
        )

    def search_data(
        self,
        provider_id: int,
        pattern: str,
        pattern_type: str = "hex",
        offset: int = 0,
        size: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Search for pattern in data."""
        params = {
            "provider_id": provider_id,
            "pattern": pattern,
            "type": pattern_type,
            "offset": offset,
        }
        if size is not None:
            params["size"] = size

        return self.send_request("data/search", params)

    def get_entropy(
        self, provider_id: int, offset: int, size: int, block_size: int = 256
    ) -> Dict[str, Any]:
        """Calculate entropy of data."""
        return self.send_request(
            "data/entropy",
            {
                "provider_id": provider_id,
                "offset": offset,
                "size": size,
                "block_size": block_size,
            },
        )

    def get_statistics(
        self, provider_id: int, offset: int, size: int
    ) -> Dict[str, Any]:
        """Get byte statistics for data."""
        return self.send_request(
            "data/statistics",
            {"provider_id": provider_id, "offset": offset, "size": size},
        )


def create_client(
    host: str = "localhost",
    port: int = 31337,
    cache_enabled: bool = True,
    **kwargs,
) -> CachedImHexClient:
    """
    Factory function to create cached client.

    Args:
        host: ImHex MCP host
        port: ImHex MCP port
        cache_enabled: Enable caching
        **kwargs: Additional client parameters

    Returns:
        Configured CachedImHexClient instance

    Example:
        >>> client = create_client()
        >>> result = client.get_capabilities()
        >>> print(result)
    """
    return CachedImHexClient(
        host=host, port=port, cache_enabled=cache_enabled, **kwargs
    )
