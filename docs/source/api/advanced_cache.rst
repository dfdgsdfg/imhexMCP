Advanced Cache
==============

The ``advanced_cache`` module provides a sophisticated async caching system with
TTL support, LRU eviction, and bloom filters for efficient cache lookups.

Features
--------

* Asynchronous cache operations
* Time-to-Live (TTL) expiration
* LRU (Least Recently Used) eviction
* Bloom filter for fast negative lookups
* Thread-safe with asyncio locks
* Cache statistics and monitoring

Module Reference
----------------

.. automodule:: advanced_cache
   :members:
   :undoc-members:
   :show-inheritance:

Classes
-------

.. autoclass:: advanced_cache.AdvancedCache
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: advanced_cache.CacheEntry
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: advanced_cache.CacheConfig
   :members:
   :undoc-members:
   :show-inheritance:

Usage Example
-------------

.. code-block:: python

   from advanced_cache import AdvancedCache, CacheConfig
   import asyncio

   async def main():
       # Create cache with custom configuration
       config = CacheConfig(
           max_size=10000,
           default_ttl=300.0,  # 5 minutes
           cleanup_interval=60.0
       )

       cache = AdvancedCache(config)

       # Set value
       await cache.set("key1", {"data": "value"}, ttl=60.0)

       # Get value
       value = await cache.get("key1")

       # Check if key exists (fast bloom filter check)
       exists = await cache.contains("key1")

       # Get statistics
       stats = await cache.get_stats()
       print(f"Size: {stats['size']}, Hits: {stats['hits']}")

       # Cleanup expired entries
       removed = await cache.cleanup_expired()

   asyncio.run(main())
