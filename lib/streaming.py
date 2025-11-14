#!/usr/bin/env python3
"""
ImHex MCP Memory-Efficient Streaming

Provides generator-based streaming for large data operations to reduce memory usage.
Enables processing files larger than available RAM through chunked transfers.
"""

from error_handling import retry_with_backoff
import socket
import json
import sys
from pathlib import Path
from typing import Iterator, Optional, Dict, Any, Tuple, Callable
from dataclasses import dataclass

# Add lib directory to path
sys.path.insert(0, str(Path(__file__).parent))


@dataclass
class StreamChunk:
    """Single chunk from a streaming operation."""

    offset: int
    size: int
    data: bytes
    is_last: bool
    total_size: Optional[int] = None


class StreamingClient:
    """
    Memory-efficient streaming client for large data operations.

    Features:
    - Generator-based data reads (no full buffering)
    - Configurable chunk sizes for memory control
    - Progress tracking for long operations
    - Automatic retry with exponential backoff
    - Stream processing patterns (map, filter, reduce)
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 31337,
        timeout: int = 30,
        default_chunk_size: int = 4096,
    ):
        """
        Initialize streaming client.

        Args:
            host: ImHex MCP host
            port: ImHex MCP port
            timeout: Socket timeout in seconds
            default_chunk_size: Default chunk size for streaming reads
        """
        self.host = host
        self.port = port
        self.timeout = timeout
        self.default_chunk_size = default_chunk_size

    @retry_with_backoff(
        max_attempts=3, initial_delay=0.5, exponential_base=2.0
    )
    def _send_request(
        self, endpoint: str, data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Send single request with retry."""
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
            raise  # Let retry decorator handle
        except Exception as e:
            return {"status": "error", "data": {"error": str(e)}}

    def stream_read(
        self,
        provider_id: int,
        offset: int = 0,
        total_size: Optional[int] = None,
        chunk_size: Optional[int] = None,
    ) -> Iterator[StreamChunk]:
        """
        Stream data from provider in chunks (generator).

        Args:
            provider_id: Provider to read from
            offset: Starting offset
            total_size: Total bytes to read (None = read to end)
            chunk_size: Size of each chunk (None = use default)

        Yields:
            StreamChunk objects with data and metadata

        Example:
            >>> client = StreamingClient()
            >>> for chunk in client.stream_read(0, offset=0, total_size=1024*1024):
            ...     process(chunk.data)  # Process 4KB at a time
        """
        chunk_size = chunk_size or self.default_chunk_size

        # Get file size if not specified
        if total_size is None:
            info = self._send_request(
                "file/info", {"provider_id": provider_id}
            )
            if info.get("status") != "success":
                raise ValueError(
                    f"Failed to get file info: {info.get('data', {}).get('error')}"
                )
            total_size = info["data"]["size"]

        current_offset = offset
        bytes_remaining = total_size

        while bytes_remaining > 0:
            read_size = min(chunk_size, bytes_remaining)

            result = self._send_request(
                "data/read",
                {
                    "provider_id": provider_id,
                    "offset": current_offset,
                    "size": read_size,
                },
            )

            if result.get("status") != "success":
                raise IOError(
                    f"Read failed at offset {current_offset}: {result.get('data', {}).get('error')}"
                )

            # Decode hex data
            hex_data = result["data"]["data"]
            chunk_data = bytes.fromhex(hex_data)

            yield StreamChunk(
                offset=current_offset,
                size=len(chunk_data),
                data=chunk_data,
                is_last=(bytes_remaining <= read_size),
                total_size=total_size,
            )

            current_offset += len(chunk_data)
            bytes_remaining -= len(chunk_data)

    def stream_search(
        self,
        provider_id: int,
        pattern: str,
        pattern_type: str = "hex",
        chunk_size: Optional[int] = None,
        overlap_size: int = 256,
    ) -> Iterator[Tuple[int, bytes]]:
        """
        Stream-search for pattern in large files.

        Searches through file in chunks with overlapping regions to avoid
        missing patterns that span chunk boundaries.

        Args:
            provider_id: Provider to search
            pattern: Pattern to search for
            pattern_type: Pattern type (hex, ascii, regex)
            chunk_size: Size of each search chunk
            overlap_size: Overlap between chunks to catch boundary matches

        Yields:
            Tuples of (offset, matched_data)

        Example:
            >>> for offset, match in client.stream_search(0, "deadbeef", "hex"):
            ...     print(f"Found at offset: {offset}")
        """
        chunk_size = chunk_size or self.default_chunk_size

        # Get file size
        info = self._send_request("file/info", {"provider_id": provider_id})
        if info.get("status") != "success":
            raise ValueError(
                f"Failed to get file info: {info.get('data', {}).get('error')}"
            )

        file_size = info["data"]["size"]
        current_offset = 0

        while current_offset < file_size:
            # Search in current chunk
            search_size = min(chunk_size, file_size - current_offset)

            result = self._send_request(
                "data/search",
                {
                    "provider_id": provider_id,
                    "pattern": pattern,
                    "type": pattern_type,
                    "offset": current_offset,
                    "size": search_size,
                },
            )

            if result.get("status") == "success":
                matches = result.get("data", {}).get("matches", [])
                for match in matches:
                    match_offset = match.get("offset", 0)
                    match_data = bytes.fromhex(match.get("data", ""))
                    yield (match_offset, match_data)

            # Move to next chunk with overlap
            current_offset += search_size - overlap_size
            if current_offset + overlap_size >= file_size:
                break

    def stream_hash(
        self,
        provider_id: int,
        chunk_size: Optional[int] = None,
        algorithm: str = "md5",
    ) -> Iterator[Tuple[int, str]]:
        """
        Stream hash calculation over file regions.

        Args:
            provider_id: Provider to hash
            chunk_size: Size of each hashed region
            algorithm: Hash algorithm (md5, sha1, sha256, etc.)

        Yields:
            Tuples of (offset, hash_value)

        Example:
            >>> for offset, hash_val in client.stream_hash(0, chunk_size=1024*1024):
            ...     print(f"Hash at {offset}: {hash_val}")
        """
        chunk_size = chunk_size or self.default_chunk_size

        # Get file size
        info = self._send_request("file/info", {"provider_id": provider_id})
        if info.get("status") != "success":
            raise ValueError(
                f"Failed to get file info: {info.get('data', {}).get('error')}"
            )

        file_size = info["data"]["size"]
        current_offset = 0

        while current_offset < file_size:
            hash_size = min(chunk_size, file_size - current_offset)

            result = self._send_request(
                "data/hash",
                {
                    "provider_id": provider_id,
                    "offset": current_offset,
                    "size": hash_size,
                    "algorithm": algorithm,
                },
            )

            if result.get("status") == "success":
                hash_value = result["data"]["hash"]
                yield (current_offset, hash_value)

            current_offset += hash_size

    def stream_entropy(
        self,
        provider_id: int,
        chunk_size: Optional[int] = None,
        block_size: int = 256,
    ) -> Iterator[Tuple[int, float]]:
        """
        Stream entropy calculation over file regions.

        Args:
            provider_id: Provider to analyze
            chunk_size: Size of each analyzed region
            block_size: Block size for entropy calculation

        Yields:
            Tuples of (offset, entropy_value)

        Example:
            >>> for offset, entropy in client.stream_entropy(0):
            ...     if entropy > 7.5:
            ...         print(f"High entropy at {offset}: {entropy}")
        """
        chunk_size = chunk_size or self.default_chunk_size

        # Get file size
        info = self._send_request("file/info", {"provider_id": provider_id})
        if info.get("status") != "success":
            raise ValueError(
                f"Failed to get file info: {info.get('data', {}).get('error')}"
            )

        file_size = info["data"]["size"]
        current_offset = 0

        while current_offset < file_size:
            entropy_size = min(chunk_size, file_size - current_offset)

            result = self._send_request(
                "data/entropy",
                {
                    "provider_id": provider_id,
                    "offset": current_offset,
                    "size": entropy_size,
                    "block_size": block_size,
                },
            )

            if result.get("status") == "success":
                entropy_value = result["data"]["entropy"]
                yield (current_offset, entropy_value)

            current_offset += entropy_size


class StreamProcessor:
    """
    Stream processing utilities for data transformation pipelines.

    Provides functional programming patterns (map, filter, reduce) for
    processing large files without loading them entirely into memory.
    """

    @staticmethod
    def map_chunks(
        stream: Iterator[StreamChunk], transform: Callable[[bytes], bytes]
    ) -> Iterator[StreamChunk]:
        """
        Transform each chunk's data through a function.

        Args:
            stream: Input chunk stream
            transform: Function to transform chunk data

        Yields:
            Transformed chunks

        Example:
            >>> stream = client.stream_read(0)
            >>> uppercase_stream = StreamProcessor.map_chunks(stream, lambda data: data.upper())
        """
        for chunk in stream:
            transformed_data = transform(chunk.data)
            yield StreamChunk(
                offset=chunk.offset,
                size=len(transformed_data),
                data=transformed_data,
                is_last=chunk.is_last,
                total_size=chunk.total_size,
            )

    @staticmethod
    def filter_chunks(
        stream: Iterator[StreamChunk], predicate: Callable[[bytes], bool]
    ) -> Iterator[StreamChunk]:
        """
        Filter chunks based on predicate.

        Args:
            stream: Input chunk stream
            predicate: Function to test chunk data

        Yields:
            Chunks that pass the predicate

        Example:
            >>> stream = client.stream_read(0)
            >>> high_entropy = StreamProcessor.filter_chunks(
            ...     stream, lambda data: calculate_entropy(data) > 7.0
            ... )
        """
        for chunk in stream:
            if predicate(chunk.data):
                yield chunk

    @staticmethod
    def reduce_stream(
        stream: Iterator[StreamChunk],
        reducer: Callable[[Any, bytes], Any],
        initial: Any,
    ) -> Any:
        """
        Reduce stream to single value.

        Args:
            stream: Input chunk stream
            reducer: Function to accumulate values
            initial: Initial accumulator value

        Returns:
            Final accumulated value

        Example:
            >>> stream = client.stream_read(0)
            >>> total_bytes = StreamProcessor.reduce_stream(
            ...     stream, lambda acc, data: acc + len(data), 0
            ... )
        """
        accumulator = initial
        for chunk in stream:
            accumulator = reducer(accumulator, chunk.data)
        return accumulator

    @staticmethod
    def collect_stream(
        stream: Iterator[StreamChunk], output_path: Optional[str] = None
    ) -> bytes:
        """
        Collect entire stream into bytes or file.

        Args:
            stream: Input chunk stream
            output_path: If specified, write to file instead of returning bytes

        Returns:
            Complete data as bytes (if output_path is None)

        Example:
            >>> stream = client.stream_read(0, offset=0, total_size=1024*1024)
            >>> StreamProcessor.collect_stream(stream, "/tmp/output.bin")
        """
        if output_path:
            with open(output_path, "wb") as f:
                for chunk in stream:
                    f.write(chunk.data)
            return b""
        else:
            chunks = []
            for chunk in stream:
                chunks.append(chunk.data)
            return b"".join(chunks)

    @staticmethod
    def progress_tracker(
        stream: Iterator[StreamChunk], callback: Callable[[int, int], None]
    ) -> Iterator[StreamChunk]:
        """
        Track progress of stream processing.

        Args:
            stream: Input chunk stream
            callback: Function called with (bytes_processed, total_bytes)

        Yields:
            Original chunks with progress tracking

        Example:
            >>> stream = client.stream_read(0, total_size=1024*1024)
            >>> def progress(current, total):
            ...     print(f"Progress: {current}/{total} ({100*current//total}%)")
            >>> tracked = StreamProcessor.progress_tracker(stream, progress)
            >>> for chunk in tracked:
            ...     process(chunk.data)
        """
        bytes_processed = 0
        for chunk in stream:
            bytes_processed += chunk.size
            if chunk.total_size:
                callback(bytes_processed, chunk.total_size)
            yield chunk


# Convenience functions for common streaming operations


def stream_to_file(
    client: StreamingClient,
    provider_id: int,
    output_path: str,
    offset: int = 0,
    total_size: Optional[int] = None,
    chunk_size: Optional[int] = None,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> int:
    """
    Stream provider data to file.

    Args:
        client: Streaming client
        provider_id: Provider to read
        output_path: Output file path
        offset: Starting offset
        total_size: Total bytes to read
        chunk_size: Chunk size for reading
        progress_callback: Optional progress callback

    Returns:
        Total bytes written

    Example:
        >>> client = StreamingClient()
        >>> bytes_written = stream_to_file(
        ...     client, 0, "/tmp/output.bin",
        ...     progress_callback=lambda cur, tot: print(f"{cur}/{tot}")
        ... )
    """
    stream = client.stream_read(provider_id, offset, total_size, chunk_size)

    if progress_callback:
        stream = StreamProcessor.progress_tracker(stream, progress_callback)

    bytes_written = 0
    with open(output_path, "wb") as f:
        for chunk in stream:
            f.write(chunk.data)
            bytes_written += chunk.size

    return bytes_written


def stream_compare(
    client: StreamingClient,
    provider_id1: int,
    provider_id2: int,
    chunk_size: Optional[int] = None,
) -> Iterator[Tuple[int, bytes, bytes]]:
    """
    Compare two providers by streaming both and yielding differences.

    Args:
        client: Streaming client
        provider_id1: First provider
        provider_id2: Second provider
        chunk_size: Chunk size for comparison

    Yields:
        Tuples of (offset, data1, data2) for differing chunks

    Example:
        >>> client = StreamingClient()
        >>> for offset, d1, d2 in stream_compare(client, 0, 1):
        ...     print(f"Difference at {offset}: {len(d1)} vs {len(d2)} bytes")
    """
    stream1 = client.stream_read(provider_id1, chunk_size=chunk_size)
    stream2 = client.stream_read(provider_id2, chunk_size=chunk_size)

    for chunk1, chunk2 in zip(stream1, stream2):
        if chunk1.data != chunk2.data:
            yield (chunk1.offset, chunk1.data, chunk2.data)


def create_streaming_client(
    host: str = "localhost",
    port: int = 31337,
    chunk_size: int = 4096,
    **kwargs,
) -> StreamingClient:
    """
    Factory function to create streaming client.

    Args:
        host: ImHex MCP host
        port: ImHex MCP port
        chunk_size: Default chunk size for streaming
        **kwargs: Additional client parameters

    Returns:
        Configured StreamingClient instance

    Example:
        >>> client = create_streaming_client(chunk_size=8192)
        >>> for chunk in client.stream_read(0):
        ...     process(chunk.data)
    """
    return StreamingClient(
        host=host, port=port, default_chunk_size=chunk_size, **kwargs
    )
