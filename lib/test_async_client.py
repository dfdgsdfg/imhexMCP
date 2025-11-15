"""
Comprehensive tests for AsyncImHexClient

Tests cover:
- Client initialization with various configurations
- Request sending with/without pooling and caching
- Batch operations
- Streaming operations
- File operations
- Cache management
- Compression/decompression
- Error handling
- Context manager usage
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from async_client import AsyncImHexClient
import sys
from pathlib import Path

# Add lib to path
sys.path.insert(0, str(Path(__file__).parent))


class TestAsyncImHexClientInitialization:
    """Test client initialization with various configurations."""

    def test_init_default_params(self):
        """Test initialization with default parameters."""
        client = AsyncImHexClient()

        assert client.host == "localhost"
        assert client.port == 31337
        assert client.timeout == 30
        assert client.max_concurrent == 10
        assert client.use_connection_pool is True
        assert client.enable_cache is True

    def test_init_custom_params(self):
        """Test initialization with custom parameters."""
        client = AsyncImHexClient(
            host="192.168.1.100",
            port=12345,
            timeout=60,
            max_concurrent=20,
            use_connection_pool=False,
            enable_cache=False,
        )

        assert client.host == "192.168.1.100"
        assert client.port == 12345
        assert client.timeout == 60
        assert client.max_concurrent == 20
        assert client.use_connection_pool is False
        assert client.enable_cache is False

    def test_init_with_connection_pool(self):
        """Test that connection pool is created when enabled."""
        client = AsyncImHexClient(use_connection_pool=True)

        assert client._pool is not None
        assert client._semaphore is None

    def test_init_without_connection_pool(self):
        """Test that semaphore is created when pool disabled."""
        client = AsyncImHexClient(use_connection_pool=False)

        assert client._pool is None
        assert client._semaphore is not None
        assert client._semaphore._value == 10  # max_concurrent

    def test_init_with_cache(self):
        """Test that cache is created when enabled."""
        client = AsyncImHexClient(enable_cache=True)

        assert client._cache is not None

    def test_init_without_cache(self):
        """Test that cache is not created when disabled."""
        client = AsyncImHexClient(enable_cache=False)

        assert client._cache is None

    def test_init_with_compression(self):
        """Test that compressor is created when enabled."""
        client = AsyncImHexClient(enable_compression=True)

        assert client._compressor is not None

    def test_init_compression_config(self):
        """Test compression configuration."""
        client = AsyncImHexClient(
            enable_compression=True,
            compression_algorithm="gzip",
            compression_level=9,
            compression_min_size=2048,
        )

        assert client._compressor is not None
        # Config is passed to compressor constructor


class TestAsyncImHexClientBasicRequests:
    """Test basic request sending functionality."""

    @pytest.mark.asyncio
    async def test_send_request_success(self):
        """Test successful request without pooling."""
        client = AsyncImHexClient(
            use_connection_pool=False, enable_cache=False
        )

        # Mock the socket operations
        with patch.object(
            client, "_sync_send_request"
        ) as mock_send:
            mock_send.return_value = {"status": "success", "data": {"result": "ok"}}

            result = await client.send_request("test/endpoint", {"key": "value"})

            assert result["status"] == "success"
            assert result["data"]["result"] == "ok"
            mock_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_request_with_retry(self):
        """Test request retry on failure."""
        client = AsyncImHexClient(use_connection_pool=False, enable_cache=False)

        with patch.object(client, "_send_request_impl") as mock_send:
            # First call fails, second succeeds
            mock_send.side_effect = [
                Exception("Connection failed"),
                {"status": "success", "data": {}},
            ]

            result = await client._send_request_with_retry(
                "test/endpoint", {}, max_retries=2
            )

            assert result["status"] == "success"
            assert mock_send.call_count == 2

    @pytest.mark.asyncio
    async def test_send_request_max_retries_exceeded(self):
        """Test that exception is raised after max retries."""
        client = AsyncImHexClient(use_connection_pool=False, enable_cache=False)

        with patch.object(client, "_send_request_impl") as mock_send:
            mock_send.side_effect = Exception("Connection failed")

            with pytest.raises(Exception, match="Connection failed"):
                await client._send_request_with_retry(
                    "test/endpoint", {}, max_retries=2
                )

            assert mock_send.call_count == 3  # Initial + 2 retries


class TestAsyncImHexClientCaching:
    """Test caching functionality."""

    @pytest.mark.asyncio
    async def test_cache_hit(self):
        """Test that cached responses are returned."""
        client = AsyncImHexClient(enable_cache=True, use_connection_pool=False)

        with patch.object(client, "_sync_send_request") as mock_send:
            mock_send.return_value = {"status": "success", "data": {"value": 123}}

            # First request - cache miss
            result1 = await client.send_request("test/endpoint", {"id": 1})

            # Second request - should hit cache
            result2 = await client.send_request("test/endpoint", {"id": 1})

            assert result1 == result2
            # Should only call once due to cache
            assert mock_send.call_count == 1

    @pytest.mark.asyncio
    async def test_cache_different_params(self):
        """Test that different parameters result in cache miss."""
        client = AsyncImHexClient(enable_cache=True, use_connection_pool=False)

        with patch.object(client, "_sync_send_request") as mock_send:
            mock_send.return_value = {"status": "success", "data": {}}

            await client.send_request("test/endpoint", {"id": 1})
            await client.send_request("test/endpoint", {"id": 2})

            # Different params = different cache keys = 2 calls
            assert mock_send.call_count == 2

    @pytest.mark.asyncio
    async def test_cache_invalidate(self):
        """Test cache invalidation."""
        client = AsyncImHexClient(enable_cache=True)

        # Populate cache
        with patch.object(client, "_sync_send_request") as mock_send:
            mock_send.return_value = {"status": "success", "data": {}}
            await client.send_request("test/endpoint", {"id": 1})

        # Invalidate
        await client.cache_invalidate("test/endpoint", {"id": 1})

        # Next request should miss cache
        with patch.object(client, "_sync_send_request") as mock_send:
            mock_send.return_value = {"status": "success", "data": {}}
            await client.send_request("test/endpoint", {"id": 1})
            assert mock_send.call_count == 1

    @pytest.mark.asyncio
    async def test_cache_clear(self):
        """Test clearing entire cache."""
        client = AsyncImHexClient(enable_cache=True)

        with patch.object(client._cache, "clear") as mock_clear:
            await client.cache_clear()
            mock_clear.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_stats(self):
        """Test retrieving cache statistics."""
        client = AsyncImHexClient(enable_cache=True)

        with patch.object(client._cache, "get_stats") as mock_stats:
            mock_stats.return_value = {
                "hits": 10,
                "misses": 5,
                "size": 15,
            }

            stats = await client.cache_stats()

            assert stats["hits"] == 10
            assert stats["misses"] == 5
            mock_stats.assert_called_once()


class TestAsyncImHexClientBatchOperations:
    """Test batch operation functionality."""

    @pytest.mark.asyncio
    async def test_send_batch(self):
        """Test sending batch of requests."""
        client = AsyncImHexClient(use_connection_pool=False, enable_cache=False)

        requests = [
            ("endpoint1", {"id": 1}),
            ("endpoint2", {"id": 2}),
            ("endpoint3", {"id": 3}),
        ]

        with patch.object(client, "send_request") as mock_send:
            mock_send.side_effect = [
                {"status": "success", "data": {"result": 1}},
                {"status": "success", "data": {"result": 2}},
                {"status": "success", "data": {"result": 3}},
            ]

            results = await client.send_batch(requests)

            assert len(results) == 3
            assert all(r["status"] == "success" for r in results)
            assert mock_send.call_count == 3

    @pytest.mark.asyncio
    async def test_batch_multi_read(self):
        """Test batch reading from multiple providers."""
        client = AsyncImHexClient(use_connection_pool=False)

        reads = [
            (0, 0, 256),  # provider_id, offset, size
            (1, 100, 128),
            (2, 200, 512),
        ]

        with patch.object(client, "send_request") as mock_send:
            mock_send.side_effect = [
                {"status": "success", "data": {"data": "00" * 256}},
                {"status": "success", "data": {"data": "11" * 128}},
                {"status": "success", "data": {"data": "22" * 512}},
            ]

            results = await client.batch_multi_read(reads)

            assert len(results) == 3
            assert mock_send.call_count == 3


class TestAsyncImHexClientFileOperations:
    """Test file operation methods."""

    @pytest.mark.asyncio
    async def test_open_file(self):
        """Test opening a file."""
        client = AsyncImHexClient()

        with patch.object(client, "send_request") as mock_send:
            mock_send.return_value = {
                "status": "success",
                "data": {"provider_id": 0},
            }

            result = await client.open_file("/path/to/file.bin")

            assert result["status"] == "success"
            assert "provider_id" in result["data"]
            mock_send.assert_called_once_with("file/open", {"path": "/path/to/file.bin"})

    @pytest.mark.asyncio
    async def test_close_file(self):
        """Test closing a file."""
        client = AsyncImHexClient()

        with patch.object(client, "send_request") as mock_send:
            mock_send.return_value = {"status": "success", "data": {}}

            result = await client.close_file(0)

            assert result["status"] == "success"
            mock_send.assert_called_once_with("file/close", {"provider_id": 0})

    @pytest.mark.asyncio
    async def test_list_files(self):
        """Test listing open files."""
        client = AsyncImHexClient()

        with patch.object(client, "send_request") as mock_send:
            mock_send.return_value = {
                "status": "success",
                "data": {"providers": [{"id": 0, "name": "file.bin"}]},
            }

            result = await client.list_files()

            assert result["status"] == "success"
            assert "providers" in result["data"]
            mock_send.assert_called_once_with("file/list", {})

    @pytest.mark.asyncio
    async def test_read_data(self):
        """Test reading data from provider."""
        client = AsyncImHexClient()

        with patch.object(client, "send_request") as mock_send:
            mock_send.return_value = {
                "status": "success",
                "data": {"data": "0123456789abcdef"},
            }

            result = await client.read_data(provider_id=0, offset=0, size=8)

            assert result["status"] == "success"
            assert "data" in result["data"]
            mock_send.assert_called_once_with(
                "data/read", {"provider_id": 0, "offset": 0, "size": 8}
            )


class TestAsyncImHexClientCompression:
    """Test compression functionality."""

    def test_compress_binary_data(self):
        """Test compressing binary data."""
        client = AsyncImHexClient(enable_compression=True)

        # Large hex data to ensure compression is applied
        hex_data = "00" * 2048

        result = client.compress_binary_data(hex_data)

        assert "compressed" in result
        if result["compressed"]:
            assert "data" in result
            assert len(result["data"]) < len(hex_data)

    def test_decompress_binary_data(self):
        """Test decompressing binary data."""
        client = AsyncImHexClient(enable_compression=True)

        # Compress then decompress
        original_data = "00" * 2048
        compressed = client.compress_binary_data(original_data)

        if compressed["compressed"]:
            decompressed = client.decompress_binary_data(
                compressed["data"], compressed.get("algorithm", "zstd")
            )

            assert decompressed == original_data

    def test_compression_stats(self):
        """Test retrieving compression statistics."""
        client = AsyncImHexClient(enable_compression=True)

        stats = client.compression_stats()

        assert "total_compressed" in stats
        assert "total_decompressed" in stats
        assert "compression_ratio_avg" in stats


class TestAsyncImHexClientStreaming:
    """Test streaming operations."""

    @pytest.mark.asyncio
    async def test_stream_read(self):
        """Test streaming large file read."""
        client = AsyncImHexClient()

        with patch.object(client, "send_request") as mock_send:
            # Mock returning chunks
            mock_send.side_effect = [
                {"status": "success", "data": {"data": "00" * 1024}},
                {"status": "success", "data": {"data": "11" * 1024}},
                {"status": "success", "data": {"data": "22" * 1024}},
            ]

            chunks = []
            async for chunk in client.stream_read(
                provider_id=0, offset=0, total_size=3072, chunk_size=1024
            ):
                chunks.append(chunk)

            assert len(chunks) == 3
            assert mock_send.call_count == 3


class TestAsyncImHexClientConnectionPool:
    """Test connection pool integration."""

    def test_get_pool_stats(self):
        """Test retrieving pool statistics."""
        client = AsyncImHexClient(use_connection_pool=True)

        with patch.object(client._pool, "stats") as mock_stats:
            mock_stats.return_value = {
                "active": 2,
                "idle": 3,
                "total": 5,
            }

            stats = client.get_pool_stats()

            assert stats["active"] == 2
            assert stats["idle"] == 3
            mock_stats.assert_called_once()

    def test_get_pool_stats_no_pool(self):
        """Test pool stats when pool is disabled."""
        client = AsyncImHexClient(use_connection_pool=False)

        stats = client.get_pool_stats()

        assert stats["pool_enabled"] is False


class TestAsyncImHexClientContextManager:
    """Test context manager usage."""

    @pytest.mark.asyncio
    async def test_context_manager_enter(self):
        """Test async context manager entry."""
        client = AsyncImHexClient()

        async with client as c:
            assert c is client

    @pytest.mark.asyncio
    async def test_context_manager_exit(self):
        """Test async context manager exit."""
        client = AsyncImHexClient(use_connection_pool=True)

        with patch.object(client._pool, "close") as mock_close:
            async with client:
                pass

            mock_close.assert_called_once()

    @pytest.mark.asyncio
    async def test_context_manager_exception_handling(self):
        """Test that exceptions are properly handled."""
        client = AsyncImHexClient()

        with pytest.raises(ValueError):
            async with client:
                raise ValueError("Test exception")


class TestAsyncImHexClientErrorHandling:
    """Test error handling."""

    @pytest.mark.asyncio
    async def test_network_error_handling(self):
        """Test handling of network errors."""
        client = AsyncImHexClient(use_connection_pool=False, enable_cache=False)

        with patch.object(client, "_sync_send_request") as mock_send:
            mock_send.side_effect = ConnectionRefusedError("Connection refused")

            with pytest.raises(Exception):
                await client.send_request("test/endpoint", {})

    @pytest.mark.asyncio
    async def test_timeout_handling(self):
        """Test handling of timeout errors."""
        client = AsyncImHexClient(use_connection_pool=False, timeout=1)

        with patch.object(client, "_sync_send_request") as mock_send:
            async def slow_request(*args):
                await asyncio.sleep(2)
                return {"status": "success"}

            mock_send.side_effect = slow_request

            # Should timeout
            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(
                    client.send_request("test/endpoint", {}), timeout=1
                )

    @pytest.mark.asyncio
    async def test_invalid_json_response(self):
        """Test handling of invalid JSON responses."""
        client = AsyncImHexClient(use_connection_pool=False, enable_cache=False)

        with patch.object(client, "_sync_send_request") as mock_send:
            mock_send.return_value = "invalid json"

            # Should handle gracefully or raise appropriate error
            result = await client.send_request("test/endpoint", {})

            # Depending on implementation, might return error response
            assert result is not None


class TestAsyncImHexClientCapabilities:
    """Test capabilities method."""

    @pytest.mark.asyncio
    async def test_get_capabilities(self):
        """Test retrieving server capabilities."""
        client = AsyncImHexClient()

        with patch.object(client, "send_request") as mock_send:
            mock_send.return_value = {
                "status": "success",
                "data": {
                    "version": "1.0",
                    "endpoints": ["file/open", "data/read"],
                },
            }

            result = await client.get_capabilities()

            assert result["status"] == "success"
            assert "endpoints" in result["data"]
            mock_send.assert_called_once_with("capabilities", {})
