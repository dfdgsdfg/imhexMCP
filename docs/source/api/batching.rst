Batching
========

The ``batching`` module provides synchronous request batching and pipelining for
improved throughput when executing multiple ImHex MCP requests.

Features
--------

* Sequential execution with single connection
* Concurrent execution with connection pooling
* Pipelined execution for reduced latency
* Builder pattern for constructing batches
* Helper functions for common batch operations

Module Reference
----------------

.. automodule:: batching
   :members:
   :undoc-members:
   :show-inheritance:

Classes
-------

.. autoclass:: batching.RequestBatcher
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: batching.BatchBuilder
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: batching.BatchRequest
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: batching.BatchResponse
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: batching.BatchStrategy
   :members:
   :undoc-members:
   :show-inheritance:

Helper Functions
----------------

.. autofunction:: batching.batch_read_operations
.. autofunction:: batching.batch_hash_operations

Usage Example
-------------

.. code-block:: python

   from batching import RequestBatcher, BatchBuilder, BatchStrategy

   # Create batcher
   batcher = RequestBatcher(
       host="localhost",
       port=31337,
       max_workers=5
   )

   # Build batch using builder pattern
   batch = (BatchBuilder()
       .add("capabilities")
       .add("file/list")
       .add("data/read", {"provider_id": 0, "offset": 0, "size": 1024})
       .build())

   # Execute with sequential strategy
   responses = batcher.execute_batch(batch, BatchStrategy.SEQUENTIAL)

   # Or use concurrent strategy for parallel execution
   responses = batcher.execute_batch(batch, BatchStrategy.CONCURRENT)

   # Process responses
   for response in responses:
       if response.success:
           print(f"Success: {response.result}")
       else:
           print(f"Error: {response.error}")

   # Cleanup
   batcher.shutdown()
