Request Batching (Async)
========================

The ``request_batching`` module provides asynchronous request batching and pipelining
with asyncio for high-performance concurrent operations.

Features
--------

* Asynchronous batch execution
* Multiple batching modes (sequential, concurrent, pipelined)
* Automatic retry with exponential backoff
* Performance metrics and statistics
* Builder pattern for batch construction

Module Reference
----------------

.. automodule:: request_batching
   :members:
   :undoc-members:
   :show-inheritance:

Classes
-------

.. autoclass:: request_batching.AsyncRequestBatcher
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: request_batching.AsyncBatchBuilder
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: request_batching.BatchRequest
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: request_batching.BatchResponse
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: request_batching.BatchMode
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: request_batching.BatchStats
   :members:
   :undoc-members:
   :show-inheritance:

Usage Example
-------------

.. code-block:: python

   from request_batching import AsyncRequestBatcher, AsyncBatchBuilder, BatchMode
   import asyncio

   async def main():
       # Create async batcher
       batcher = AsyncRequestBatcher(
           host="localhost",
           port=31337,
           max_concurrent=10
       )

       # Build batch
       batch = (AsyncBatchBuilder()
           .add("capabilities")
           .add("file/list")
           .add("data/read", {"provider_id": 0, "offset": 0, "size": 1024})
           .build())

       # Execute batch concurrently
       responses = await batcher.execute_batch(batch, BatchMode.CONCURRENT)

       # Process responses
       for response in responses:
           if response.success:
               print(f"Success: {response.result}")
           else:
               print(f"Error: {response.error}")

       # Get statistics
       stats = batcher.get_stats()
       print(f"Total requests: {stats.total_requests}")
       print(f"Average latency: {stats.average_latency_ms:.2f}ms")

       # Cleanup
       await batcher.close()

   asyncio.run(main())
