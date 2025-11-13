Async Client Module
===================

The async_client module provides a high-performance async client for ImHex MCP with connection
pooling, request batching, and compression support.

Overview
--------

Features:

* **Connection Pooling**: Reuses TCP connections for reduced latency
* **Request Batching**: Groups concurrent requests for improved throughput
* **Automatic Compression**: Transparent compression for large data transfers
* **Type-Safe API**: Full type hints for IDE support
* **Context Manager**: Automatic resource cleanup with async context manager

Architecture
------------

The async client supports two modes:

1. **Connection Pool Mode** (recommended for production):

   * Maintains persistent connections
   * Automatically handles connection lifecycle
   * Better performance for high-throughput scenarios

2. **On-Demand Mode** (default):

   * Creates new connection per request
   * Simpler for low-frequency usage
   * Uses semaphore for concurrency control

Usage Examples
--------------

Basic Usage with Connection Pooling
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from async_client import ImHexAsyncClient

   async def main():
       # Create client with connection pool
       async with ImHexAsyncClient(
           host="localhost",
           port=31337,
           use_connection_pool=True
       ) as client:
           # List open files
           files = await client.file_list()

           # Read file data
           data = await client.file_read(
               provider_id=0,
               offset=0,
               size=256
           )

           # Search for pattern
           results = await client.file_search(
               provider_id=0,
               pattern="504B0304"  # ZIP signature
           )

Concurrent Requests
^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   import asyncio

   async def process_multiple_files():
       async with ImHexAsyncClient(use_connection_pool=True) as client:
           # Execute multiple requests concurrently
           results = await asyncio.gather(
               client.file_read(provider_id=0, offset=0, size=1024),
               client.file_read(provider_id=0, offset=1024, size=1024),
               client.file_read(provider_id=0, offset=2048, size=1024),
           )

Custom Configuration
^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from async_client import ImHexAsyncClient, ConnectionPoolConfig

   # Configure connection pool
   pool_config = ConnectionPoolConfig(
       min_size=5,
       max_size=20,
       acquire_timeout=10.0,
       idle_timeout=300.0
   )

   async with ImHexAsyncClient(
       host="localhost",
       port=31337,
       use_connection_pool=True,
       pool_config=pool_config,
       max_concurrent=50  # Max concurrent requests
   ) as client:
       # ... use client

Error Handling
^^^^^^^^^^^^^^

.. code-block:: python

   from async_client import ImHexAsyncClient, ImHexMCPError

   async def safe_request():
       async with ImHexAsyncClient() as client:
           try:
               data = await client.file_read(
                   provider_id=0,
                   offset=0,
                   size=1024
               )
           except ImHexMCPError as e:
               print(f"MCP error: {e}")
               # Handle error
           except Exception as e:
               print(f"Unexpected error: {e}")
               # Handle error

Performance Considerations
--------------------------

Connection Pool Settings
^^^^^^^^^^^^^^^^^^^^^^^^

* **min_size**: Keep warm connections ready (default: 2)
* **max_size**: Limit resource usage (default: 10)
* **acquire_timeout**: Prevent indefinite waits (default: 5.0s)
* **idle_timeout**: Clean up unused connections (default: 300.0s)

Batching Configuration
^^^^^^^^^^^^^^^^^^^^^^

* **max_batch_size**: Group up to N requests (default: 50)
* **max_wait_time**: Maximum batching delay (default: 10ms)

Compression
^^^^^^^^^^^

* Automatically enabled for payloads >1KB
* Uses zstd for best performance
* Falls back to sending uncompressed if ratio is poor

API Reference
-------------

.. automodule:: async_client
   :members:
   :undoc-members:
   :show-inheritance:
