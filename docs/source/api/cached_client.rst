Cached Client
=============

The ``cached_client`` module provides a high-performance client wrapper with automatic
response caching and retry logic.

Features
--------

* Automatic response caching with endpoint-specific TTLs
* Exponential backoff retry on transient failures
* Cache statistics and monitoring
* Smart cache invalidation on state-changing operations
* Configurable cache size and TTL policies

Module Reference
----------------

.. automodule:: cached_client
   :members:
   :undoc-members:
   :show-inheritance:

Classes
-------

.. autoclass:: cached_client.CachedImHexClient
   :members:
   :undoc-members:
   :show-inheritance:

Factory Functions
-----------------

.. autofunction:: cached_client.create_client

Usage Example
-------------

.. code-block:: python

   from cached_client import create_client

   # Create client with caching enabled
   client = create_client(
       host="localhost",
       port=31337,
       cache_enabled=True,
       cache_max_size=1000
   )

   # First call - fetches from server
   result1 = client.get_capabilities()

   # Second call - served from cache
   result2 = client.get_capabilities()

   # Check cache statistics
   stats = client.get_cache_stats()
   print(f"Cache hit rate: {stats['hit_rate']:.2%}")

   # Clear cache manually
   client.clear_cache()
