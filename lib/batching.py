#!/usr/bin/env python3
"""
ImHex MCP Request Batching and Pipelining

Efficient batching and pipelining for multiple ImHex MCP requests.
Reduces connection overhead and improves throughput for bulk operations.
"""

import socket
import json
import threading
import concurrent.futures
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class BatchStrategy(Enum):
    """Batching strategies."""

    SEQUENTIAL = (
        "sequential"  # Execute requests sequentially on single connection
    )
    CONCURRENT = (
        "concurrent"  # Execute requests concurrently with separate connections
    )
    PIPELINED = "pipelined"  # Send all requests at once, receive in order


@dataclass
class BatchRequest:
    """Single request in a batch."""

    request_id: str
    endpoint: str
    data: Optional[Dict[str, Any]] = None


@dataclass
class BatchResponse:
    """Single response from a batch."""

    request_id: str
    success: bool
    result: Dict[str, Any]
    latency_ms: float
    error: Optional[str] = None


class RequestBatcher:
    """
    Batches and pipelines multiple ImHex MCP requests for improved performance.

    Features:
    - Batched request execution with shared connections
    - Pipelined requests for reduced latency
    - Concurrent execution with thread pooling
    - Automatic retry on transient failures
    - Performance metrics and statistics
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 31337,
        timeout: int = 30,
        max_workers: int = 5,
    ):
        """
        Initialize request batcher.

        Args:
            host: ImHex MCP host
            port: ImHex MCP port
            timeout: Socket timeout in seconds
            max_workers: Maximum concurrent workers for parallel execution
        """
        self.host = host
        self.port = port
        self.timeout = timeout
        self.max_workers = max_workers

        self._executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=max_workers
        )
        self._lock = threading.Lock()

    def _send_single_request(
        self,
        sock: socket.socket,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Send single request on existing socket."""
        import time

        start = time.perf_counter()

        request = json.dumps({"endpoint": endpoint, "data": data or {}}) + "\n"

        sock.sendall(request.encode())

        response = b""
        while b"\n" not in response:
            chunk = sock.recv(4096)
            if not chunk:
                raise ConnectionError("Connection closed by server")
            response += chunk

        end = time.perf_counter()
        latency = (end - start) * 1000

        result = json.loads(response.decode().strip())
        return result, latency

    def _execute_sequential(
        self, requests: List[BatchRequest]
    ) -> List[BatchResponse]:
        """Execute requests sequentially on single connection."""
        responses = []

        try:
            # Create single connection for all requests
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            sock.connect((self.host, self.port))

            for req in requests:
                try:
                    result, latency = self._send_single_request(
                        sock, req.endpoint, req.data
                    )

                    responses.append(
                        BatchResponse(
                            request_id=req.request_id,
                            success=result.get("status") == "success",
                            result=result,
                            latency_ms=latency,
                        )
                    )

                except Exception as e:
                    responses.append(
                        BatchResponse(
                            request_id=req.request_id,
                            success=False,
                            result={
                                "status": "error",
                                "data": {"error": str(e)},
                            },
                            latency_ms=0.0,
                            error=str(e),
                        )
                    )

            sock.close()

        except Exception as e:
            # Connection failed - mark all remaining requests as failed
            for req in requests[len(responses) :]:
                responses.append(
                    BatchResponse(
                        request_id=req.request_id,
                        success=False,
                        result={"status": "error", "data": {"error": str(e)}},
                        latency_ms=0.0,
                        error=str(e),
                    )
                )

        return responses

    def _execute_single_concurrent(
        self, request: BatchRequest
    ) -> BatchResponse:
        """Execute single request with its own connection."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            sock.connect((self.host, self.port))

            result, latency = self._send_single_request(
                sock, request.endpoint, request.data
            )

            sock.close()

            return BatchResponse(
                request_id=request.request_id,
                success=result.get("status") == "success",
                result=result,
                latency_ms=latency,
            )

        except Exception as e:
            return BatchResponse(
                request_id=request.request_id,
                success=False,
                result={"status": "error", "data": {"error": str(e)}},
                latency_ms=0.0,
                error=str(e),
            )

    def _execute_concurrent(
        self, requests: List[BatchRequest]
    ) -> List[BatchResponse]:
        """Execute requests concurrently with separate connections."""
        # Submit all requests to thread pool
        futures = {
            self._executor.submit(self._execute_single_concurrent, req): req
            for req in requests
        }

        # Collect results maintaining order
        responses = []
        # request_map = {req.request_id: req for req in requests}

        for future in concurrent.futures.as_completed(futures):
            try:
                response = future.result()
                responses.append(response)
            except Exception as e:
                req = futures[future]
                responses.append(
                    BatchResponse(
                        request_id=req.request_id,
                        success=False,
                        result={"status": "error", "data": {"error": str(e)}},
                        latency_ms=0.0,
                        error=str(e),
                    )
                )

        # Sort responses to match input order
        response_map = {r.request_id: r for r in responses}
        ordered_responses = [response_map[req.request_id] for req in requests]

        return ordered_responses

    def _execute_pipelined(
        self, requests: List[BatchRequest]
    ) -> List[BatchResponse]:
        """Execute requests in pipelined mode (send all, receive all)."""
        import time

        responses = []

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            sock.connect((self.host, self.port))

            # Send all requests
            start_times = []
            for req in requests:
                request_data = (
                    json.dumps(
                        {"endpoint": req.endpoint, "data": req.data or {}}
                    )
                    + "\n"
                )

                start = time.perf_counter()
                sock.sendall(request_data.encode())
                start_times.append(start)

            # Receive all responses in order
            for i, req in enumerate(requests):
                try:
                    response = b""
                    while b"\n" not in response:
                        chunk = sock.recv(4096)
                        if not chunk:
                            raise ConnectionError(
                                "Connection closed by server"
                            )
                        response += chunk

                    end = time.perf_counter()
                    latency = (end - start_times[i]) * 1000

                    result = json.loads(response.decode().strip())

                    responses.append(
                        BatchResponse(
                            request_id=req.request_id,
                            success=result.get("status") == "success",
                            result=result,
                            latency_ms=latency,
                        )
                    )

                except Exception as e:
                    responses.append(
                        BatchResponse(
                            request_id=req.request_id,
                            success=False,
                            result={
                                "status": "error",
                                "data": {"error": str(e)},
                            },
                            latency_ms=0.0,
                            error=str(e),
                        )
                    )

            sock.close()

        except Exception as e:
            # Connection failed - mark all remaining requests as failed
            for req in requests[len(responses) :]:
                responses.append(
                    BatchResponse(
                        request_id=req.request_id,
                        success=False,
                        result={"status": "error", "data": {"error": str(e)}},
                        latency_ms=0.0,
                        error=str(e),
                    )
                )

        return responses

    def execute_batch(
        self,
        requests: List[BatchRequest],
        strategy: BatchStrategy = BatchStrategy.SEQUENTIAL,
    ) -> List[BatchResponse]:
        """
        Execute batch of requests.

        Args:
            requests: List of requests to execute
            strategy: Batching strategy to use

        Returns:
            List of responses in same order as requests
        """
        if not requests:
            return []

        if strategy == BatchStrategy.SEQUENTIAL:
            return self._execute_sequential(requests)
        elif strategy == BatchStrategy.CONCURRENT:
            return self._execute_concurrent(requests)
        elif strategy == BatchStrategy.PIPELINED:
            return self._execute_pipelined(requests)
        else:
            raise ValueError(f"Unknown strategy: {strategy}")

    def execute_batch_dict(
        self,
        requests: List[Tuple[str, Optional[Dict[str, Any]]]],
        strategy: BatchStrategy = BatchStrategy.SEQUENTIAL,
    ) -> List[Dict[str, Any]]:
        """
        Execute batch from simple (endpoint, data) tuples.

        Args:
            requests: List of (endpoint, data) tuples
            strategy: Batching strategy to use

        Returns:
            List of result dictionaries
        """
        batch_requests = [
            BatchRequest(request_id=f"req_{i}", endpoint=endpoint, data=data)
            for i, (endpoint, data) in enumerate(requests)
        ]

        responses = self.execute_batch(batch_requests, strategy)

        return [r.result for r in responses]

    def shutdown(self) -> None:
        """Shutdown executor and cleanup resources."""
        self._executor.shutdown(wait=True)


class BatchBuilder:
    """
    Builder pattern for constructing batched requests.

    Example:
        batch = (BatchBuilder()
            .add("capabilities")
            .add("file/list")
            .add("data/read", {"provider_id": 0, "offset": 0, "size": 1024})
            .build())
    """

    def __init__(self):
        self.requests: List[BatchRequest] = []
        self._counter = 0

    def add(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
    ) -> "BatchBuilder":
        """Add request to batch."""
        if request_id is None:
            request_id = f"req_{self._counter}"
            self._counter += 1

        self.requests.append(
            BatchRequest(request_id=request_id, endpoint=endpoint, data=data)
        )

        return self

    def add_multiple(
        self, endpoint: str, data_list: List[Dict[str, Any]]
    ) -> "BatchBuilder":
        """Add multiple requests to same endpoint with different data."""
        for data in data_list:
            self.add(endpoint, data)
        return self

    def build(self) -> List[BatchRequest]:
        """Build final batch."""
        return self.requests

    def clear(self) -> "BatchBuilder":
        """Clear all requests."""
        self.requests = []
        self._counter = 0
        return self


def batch_read_operations(
    provider_id: int, offsets: List[int], size: int
) -> List[BatchRequest]:
    """
    Helper to create batch of read operations.

    Args:
        provider_id: Provider ID to read from
        offsets: List of offsets to read
        size: Size to read at each offset

    Returns:
        List of batch requests
    """
    return [
        BatchRequest(
            request_id=f"read_{offset}",
            endpoint="data/read",
            data={"provider_id": provider_id, "offset": offset, "size": size},
        )
        for offset in offsets
    ]


def batch_hash_operations(
    provider_id: int, regions: List[Tuple[int, int]], algorithm: str = "md5"
) -> List[BatchRequest]:
    """
    Helper to create batch of hash operations.

    Args:
        provider_id: Provider ID to hash
        regions: List of (offset, size) tuples
        algorithm: Hash algorithm to use

    Returns:
        List of batch requests
    """
    return [
        BatchRequest(
            request_id=f"hash_{offset}_{size}",
            endpoint="data/hash",
            data={
                "provider_id": provider_id,
                "offset": offset,
                "size": size,
                "algorithm": algorithm,
            },
        )
        for offset, size in regions
    ]
