Streaming
=========

The ``streaming`` module provides streaming data operations for processing large
binary files efficiently without loading entire contents into memory.

Features
--------

* Chunked data streaming
* Memory-efficient large file processing
* Async iteration support
* Configurable chunk sizes
* Progress tracking

Module Reference
----------------

.. automodule:: streaming
   :members:
   :undoc-members:
   :show-inheritance:

Classes
-------

.. autoclass:: streaming.StreamingClient
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: streaming.DataStream
   :members:
   :undoc-members:
   :show-inheritance:

Usage Example
-------------

.. code-block:: python

   from streaming import StreamingClient
   import asyncio

   async def main():
       client = StreamingClient(
           host="localhost",
           port=31337,
           chunk_size=4096
       )

       # Stream data from large file
       total_bytes = 0
       async for chunk in client.stream_data(provider_id=0, offset=0, size=10485760):
           total_bytes += len(chunk)
           # Process chunk without loading entire file
           process_chunk(chunk)

       print(f"Processed {total_bytes} bytes")

       await client.close()

   asyncio.run(main())
