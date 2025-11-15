Cache
=====

The ``cache`` module provides response caching functionality with TTL support
and endpoint-specific caching strategies.

Features
--------

* Time-based cache expiration (TTL)
* Endpoint-specific caching strategies
* LRU eviction when cache is full
* Cache hit/miss statistics
* Selective cache invalidation

Module Reference
----------------

.. automodule:: cache
   :members:
   :undoc-members:
   :show-inheritance:

Classes
-------

.. autoclass:: cache.ResponseCache
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: cache.CachingStrategy
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: cache.CacheEntry
   :members:
   :undoc-members:
   :show-inheritance:

Usage Example
-------------

.. code-block:: python

   from cache import ResponseCache, CachingStrategy

   # Create cache with default TTL
   cache = ResponseCache(
       max_size=1000,
       default_ttl=60.0  # 60 seconds
   )

   # Set cached response
   cache.set(
       endpoint="file/list",
       params={},
       result={"status": "success", "data": {...}},
       ttl=CachingStrategy.get_ttl_for_endpoint("file/list")
   )

   # Get cached response
   result = cache.get(endpoint="file/list", params={})

   # Invalidate specific endpoint
   cache.invalidate("file/list")

   # Get statistics
   stats = cache.get_stats()
   print(f"Hit rate: {stats['hit_rate']:.2%}")
