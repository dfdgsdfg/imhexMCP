#!/usr/bin/env python3
"""
Enhanced ImHex Client with All Performance Optimizations

Integrates caching, batching, streaming, lazy loading, and profiling
for maximum performance in the MCP server context.
"""

import sys
import socket
import json
from pathlib import Path
from typing import Dict, Any, Optional, List, Iterator
import threading

# Add lib directory to path
lib_path = Path(__file__).parent.parent / "lib"
sys.path.insert(0, str(lib_path))

from cache import ResponseCache
from cached_client import CachedImHexClient
from batching import RequestBatcher, BatchBuilder, BatchStrategy
from streaming import StreamingClient, StreamChunk, StreamProcessor
from lazy import LazyClient, LazyProvider, LazyProviderList
from profiling import PerformanceMonitor, HotPathAnalyzer, get_global_monitor
from error_handling import retry_with_backoff, ImHexMCPError as LibImHexError
from compression import CompressionConfig, DataCompressor


class EnhancedImHexClient:
    """
    Enhanced ImHex client with all performance optimizations enabled.

    Features:
    - Response caching with TTL and LRU eviction
    - Request batching with multiple strategies
    - Memory-efficient streaming for large data
    - Lazy loading of capabilities and providers
    - Performance monitoring and profiling
    - Thread-safe operations

    This client can be used as a drop-in replacement for the basic
    ImHexClient in the MCP server.
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 31337,
        timeout: int = 30,
        enable_cache: bool = True,
        cache_max_size: int = 1000,
        enable_profiling: bool = False,
        enable_lazy: bool = True,
        enable_compression: bool = False,
        compression_config: Optional[CompressionConfig] = None
    ):
        """
        Initialize enhanced client.

        Args:
            host: ImHex MCP host
            port: ImHex MCP port
            timeout: Socket timeout in seconds
            enable_cache: Enable response caching
            enable_profiling: Enable performance profiling
            enable_lazy: Enable lazy loading
            enable_compression: Enable data compression
            compression_config: Compression configuration (optional)
        """
        self.host = host
        self.port = port
        self.timeout = timeout

        # Performance monitoring
        self.enable_profiling = enable_profiling
        self.monitor = PerformanceMonitor() if enable_profiling else None
        self.hot_path_analyzer = HotPathAnalyzer() if enable_profiling else None

        # Caching layer
        self.enable_cache = enable_cache
        if enable_cache:
            self._cached_client = CachedImHexClient(
                host=host,
                port=port,
                timeout=timeout,
                cache_max_size=cache_max_size
            )

        # Batching layer
        self._batcher = RequestBatcher(timeout=timeout)

        # Streaming layer
        self._streaming_client = StreamingClient(
            host=host,
            port=port,
            timeout=timeout
        )

        # Lazy loading layer
        self.enable_lazy = enable_lazy
        if enable_lazy:
            self._lazy_client = LazyClient(host=host, port=port, timeout=timeout)

        # Compression layer
        self.enable_compression = enable_compression
        if enable_compression:
            config = compression_config or CompressionConfig(enabled=True)
            self._compressor = DataCompressor(config)
        else:
            self._compressor = None

        # Thread safety
        self._lock = threading.Lock()

    def send_request(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Send single request with caching and profiling.

        Args:
            endpoint: Endpoint to call
            data: Request data

        Returns:
            Response dictionary
        """
        # Profile if enabled
        if self.enable_profiling and self.monitor:
            with self.monitor.time(f"request:{endpoint}"):
                return self._send_request_impl(endpoint, data)
        else:
            return self._send_request_impl(endpoint, data)

    def _send_request_impl(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Implementation of send_request."""
        if self.enable_cache:
            # Use cached client
            return self._cached_client.send_request(endpoint, data)
        else:
            # Use basic uncached request
            return self._send_raw_request(endpoint, data)

    @retry_with_backoff(max_attempts=3, initial_delay=0.5, exponential_base=2.0)
    def _send_raw_request(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Send raw request without caching."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            sock.connect((self.host, self.port))

            request = json.dumps({
                "endpoint": endpoint,
                "data": data or {}
            }) + "\n"

            sock.sendall(request.encode())

            response = b""
            while b"\n" not in response:
                response += sock.recv(4096)

            sock.close()
            return json.loads(response.decode().strip())

        except (socket.error, socket.timeout, ConnectionRefusedError) as e:
            raise LibImHexError(f"Connection error: {e}")
        except Exception as e:
            return {"status": "error", "data": {"error": str(e)}}

    # Caching methods

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        if self.enable_cache and self._cached_client:
            return self._cached_client.get_cache_stats()
        return {"enabled": False}

    def clear_cache(self) -> None:
        """Clear all cached responses."""
        if self.enable_cache and self._cached_client:
            self._cached_client.clear_cache()

    def invalidate_cache_entry(self, endpoint: str, data: Optional[Dict[str, Any]] = None) -> None:
        """Invalidate specific cache entry."""
        if self.enable_cache and self._cached_client:
            self._cached_client.invalidate_cache_entry(endpoint, data)

    # Batching methods

    def execute_batch(
        self,
        requests: List[tuple],
        strategy: BatchStrategy = BatchStrategy.CONCURRENT
    ) -> List[Any]:
        """
        Execute batch of requests with specified strategy.

        Args:
            requests: List of (endpoint, data) tuples
            strategy: Batching strategy (SEQUENTIAL, CONCURRENT, PIPELINED)

        Returns:
            List of response objects
        """
        # Build batch
        builder = BatchBuilder()
        for endpoint, data in requests:
            builder.add(endpoint, data)
        batch = builder.build()

        # Execute with profiling if enabled
        if self.enable_profiling and self.monitor:
            with self.monitor.time(f"batch:{strategy.value}"):
                return self._batcher.execute_batch(batch, strategy=strategy)
        else:
            return self._batcher.execute_batch(batch, strategy=strategy)

    # Streaming methods

    def stream_read(
        self,
        provider_id: int,
        offset: int = 0,
        total_size: Optional[int] = None,
        chunk_size: Optional[int] = None
    ) -> Iterator[StreamChunk]:
        """
        Stream data from provider in chunks.

        Args:
            provider_id: Provider to read from
            offset: Starting offset
            total_size: Total bytes to read
            chunk_size: Size of each chunk

        Yields:
            StreamChunk objects
        """
        if self.enable_profiling and self.hot_path_analyzer:
            with self.hot_path_analyzer.trace(f"stream_read:provider_{provider_id}"):
                yield from self._streaming_client.stream_read(
                    provider_id, offset, total_size, chunk_size
                )
        else:
            yield from self._streaming_client.stream_read(
                provider_id, offset, total_size, chunk_size
            )

    def stream_to_file(
        self,
        provider_id: int,
        output_path: str,
        offset: int = 0,
        total_size: Optional[int] = None,
        chunk_size: Optional[int] = None
    ) -> int:
        """
        Stream provider data to file.

        Args:
            provider_id: Provider to read
            output_path: Output file path
            offset: Starting offset
            total_size: Total bytes to read
            chunk_size: Chunk size for reading

        Returns:
            Total bytes written
        """
        stream = self.stream_read(provider_id, offset, total_size, chunk_size)

        bytes_written = 0
        with open(output_path, 'wb') as f:
            for chunk in stream:
                f.write(chunk.data)
                bytes_written += chunk.size

        return bytes_written

    # Lazy loading methods

    @property
    def lazy_capabilities(self) -> Dict[str, Any]:
        """Get capabilities with lazy loading."""
        if self.enable_lazy and self._lazy_client:
            return self._lazy_client.capabilities
        else:
            return self.send_request("capabilities").get("data", {})

    @property
    def lazy_endpoints(self) -> List[str]:
        """Get endpoints with lazy loading."""
        if self.enable_lazy and self._lazy_client:
            return self._lazy_client.endpoints
        else:
            return self.lazy_capabilities.get("endpoints", [])

    @property
    def lazy_providers(self) -> LazyProviderList:
        """Get lazy provider list."""
        if self.enable_lazy and self._lazy_client:
            return self._lazy_client.providers
        else:
            raise RuntimeError("Lazy loading not enabled")

    def invalidate_lazy_cache(self) -> None:
        """Invalidate all lazy-loaded data."""
        if self.enable_lazy and self._lazy_client:
            self._lazy_client.invalidate_cache()

    # Performance profiling methods

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        if not self.enable_profiling or not self.monitor:
            return {"enabled": False}

        stats = self.monitor.get_stats()
        return {
            "enabled": True,
            "operations": {
                name: {
                    "call_count": stat.call_count,
                    "avg_time_ms": stat.avg_time_ms,
                    "p95_time_ms": stat.percentile_95_ms,
                    "p99_time_ms": stat.percentile_99_ms,
                    "total_time_ms": stat.total_time_ms
                }
                for name, stat in stats.items()
            }
        }

    def get_hot_paths(self, min_calls: int = 5) -> List[tuple]:
        """Get hot paths (frequently executed code paths)."""
        if not self.enable_profiling or not self.hot_path_analyzer:
            return []
        return self.hot_path_analyzer.get_hot_paths(min_calls=min_calls)

    def print_performance_report(self) -> None:
        """Print comprehensive performance report."""
        if not self.enable_profiling:
            print("Profiling not enabled")
            return

        print("\n" + "=" * 70)
        print("Enhanced ImHex Client Performance Report")
        print("=" * 70)

        # Cache stats
        if self.enable_cache:
            cache_stats = self.get_cache_stats()
            print(f"\nCache Statistics:")
            print(f"  Hit rate: {cache_stats.get('hit_rate', 0):.1f}%")
            print(f"  Hits: {cache_stats.get('hits', 0)}")
            print(f"  Misses: {cache_stats.get('misses', 0)}")
            print(f"  Size: {cache_stats.get('size', 0)}/{cache_stats.get('max_size', 0)}")

        # Performance stats
        if self.monitor:
            print(f"\nPerformance Statistics:")
            self.monitor.print_stats()

        # Hot paths
        if self.hot_path_analyzer:
            hot_paths = self.get_hot_paths(min_calls=1)
            if hot_paths:
                print(f"\nHot Paths (top 5):")
                for path, stats in hot_paths[:5]:
                    print(f"  {path}:")
                    print(f"    Calls: {stats['call_count']}")
                    print(f"    Total: {stats['total_time_ms']:.2f}ms")
                    print(f"    Avg: {stats['avg_time_ms']:.2f}ms")

        print("=" * 70)

    # Compression methods

    def get_compression_stats(self) -> Dict[str, Any]:
        """Get compression statistics."""
        if not self.enable_compression or not self._compressor:
            return {"enabled": False}

        return {
            "enabled": True,
            **self._compressor.get_stats()
        }

    def print_compression_stats(self) -> None:
        """Print compression statistics."""
        if not self.enable_compression or not self._compressor:
            print("Compression not enabled")
            return

        self._compressor.print_stats()

    # Convenience methods compatible with basic ImHexClient

    def get_capabilities(self) -> Dict[str, Any]:
        """Get capabilities (compatible with basic client)."""
        return self.send_request("capabilities")

    def list_files(self) -> Dict[str, Any]:
        """List open files (compatible with basic client)."""
        return self.send_request("file/list")

    def get_file_info(self, provider_id: int) -> Dict[str, Any]:
        """Get file info (compatible with basic client)."""
        return self.send_request("file/info", {"provider_id": provider_id})

    def read_data(
        self,
        provider_id: int,
        offset: int,
        size: int,
        use_streaming: bool = False
    ) -> Dict[str, Any]:
        """
        Read data from file.

        Args:
            provider_id: Provider to read from
            offset: Starting offset
            size: Number of bytes to read
            use_streaming: If True and size > 4096, use streaming

        Returns:
            Response dictionary
        """
        # Use streaming for large reads
        if use_streaming and size > 4096:
            chunks = []
            for chunk in self.stream_read(provider_id, offset, size):
                chunks.append(chunk.data)

            combined_data = b"".join(chunks)
            return {
                "status": "success",
                "data": {
                    "data": combined_data.hex(),
                    "size": len(combined_data),
                    "streaming": True
                }
            }
        else:
            # Use regular request
            return self.send_request("data/read", {
                "provider_id": provider_id,
                "offset": offset,
                "size": size
            })

    def open_file(self, path: str) -> Dict[str, Any]:
        """Open file (compatible with basic client)."""
        return self.send_request("file/open", {"path": path})

    def close_file(self, provider_id: int) -> Dict[str, Any]:
        """Close file (compatible with basic client)."""
        return self.send_request("file/close", {"provider_id": provider_id})

    # Context manager support

    def __enter__(self):
        """Enter context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager."""
        if self.enable_profiling:
            self.print_performance_report()
        return False


# Factory functions for easy integration

def create_enhanced_client(
    host: str = "localhost",
    port: int = 31337,
    config: Optional[Dict[str, Any]] = None
) -> EnhancedImHexClient:
    """
    Create enhanced client with configuration.

    Args:
        host: ImHex MCP host
        port: ImHex MCP port
        config: Optional configuration dictionary with keys:
            - timeout: Socket timeout in seconds
            - enable_cache: Enable response caching
            - cache_max_size: Maximum cache entries
            - enable_profiling: Enable performance profiling
            - enable_lazy: Enable lazy loading
            - enable_compression: Enable data compression
            - compression_algorithm: Compression algorithm (zstd, gzip, zlib)
            - compression_level: Compression level
            - compression_min_size: Minimum size to compress

    Returns:
        Configured EnhancedImHexClient

    Example:
        >>> client = create_enhanced_client(config={
        ...     'enable_cache': True,
        ...     'cache_max_size': 1000,
        ...     'enable_profiling': True,
        ...     'enable_compression': True
        ... })
    """
    config = config or {}

    # Build compression config if enabled
    compression_config = None
    if config.get('enable_compression', False):
        from compression import CompressionConfig
        compression_config = CompressionConfig(
            enabled=True,
            algorithm=config.get('compression_algorithm', 'zstd'),
            level=config.get('compression_level', 3),
            min_size=config.get('compression_min_size', 1024),
            adaptive=True
        )

    return EnhancedImHexClient(
        host=host,
        port=port,
        timeout=config.get('timeout', 30),
        enable_cache=config.get('enable_cache', True),
        cache_max_size=config.get('cache_max_size', 1000),
        enable_profiling=config.get('enable_profiling', False),
        enable_lazy=config.get('enable_lazy', True),
        enable_compression=config.get('enable_compression', False),
        compression_config=compression_config
    )


def create_optimized_client(
    host: str = "localhost",
    port: int = 31337
) -> EnhancedImHexClient:
    """
    Create client with all optimizations enabled.

    Args:
        host: ImHex MCP host
        port: ImHex MCP port

    Returns:
        Fully optimized EnhancedImHexClient
    """
    return EnhancedImHexClient(
        host=host,
        port=port,
        timeout=30,
        enable_cache=True,
        cache_max_size=5000,  # Large cache
        enable_profiling=True,
        enable_lazy=True
    )


def create_minimal_client(
    host: str = "localhost",
    port: int = 31337
) -> EnhancedImHexClient:
    """
    Create client with minimal optimizations (compatible mode).

    Args:
        host: ImHex MCP host
        port: ImHex MCP port

    Returns:
        EnhancedImHexClient with minimal optimizations
    """
    return EnhancedImHexClient(
        host=host,
        port=port,
        timeout=10,
        enable_cache=False,
        enable_profiling=False,
        enable_lazy=False
    )
