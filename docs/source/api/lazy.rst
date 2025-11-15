Lazy Evaluation
===============

The ``lazy`` module provides lazy evaluation patterns for deferred computation
and resource optimization.

Features
--------

* Lazy value computation
* Memoization support
* Resource-efficient loading
* Thread-safe lazy initialization
* Async lazy evaluation

Module Reference
----------------

.. automodule:: lazy
   :members:
   :undoc-members:
   :show-inheritance:

Classes
-------

.. autoclass:: lazy.Lazy
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: lazy.LazyAsync
   :members:
   :undoc-members:
   :show-inheritance:

Usage Example
-------------

.. code-block:: python

   from lazy import Lazy, LazyAsync
   import asyncio

   # Lazy evaluation (sync)
   def expensive_computation():
       print("Computing...")
       return sum(range(1000000))

   lazy_value = Lazy(expensive_computation)
   # Not computed yet

   result = lazy_value.value  # Computed on first access
   # "Computing..." printed

   result2 = lazy_value.value  # Cached result
   # No computation, value reused

   # Async lazy evaluation
   async def async_computation():
       await asyncio.sleep(1)
       return "result"

   async def main():
       lazy_async = LazyAsync(async_computation)
       result = await lazy_async.value  # Computed on first access
       result2 = await lazy_async.value  # Cached

   asyncio.run(main())
