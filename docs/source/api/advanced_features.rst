Advanced Features
=================

The ``advanced_features`` module provides request prioritization and circuit breaker
patterns for resilient, production-ready operation.

Features
--------

* Priority-based request queuing with aging
* Circuit breaker for fault tolerance
* Fair scheduling to prevent starvation
* Automatic failure recovery
* Request scheduling and worker management

Module Reference
----------------

.. automodule:: advanced_features
   :members:
   :undoc-members:
   :show-inheritance:

Priority Queue
--------------

.. autoclass:: advanced_features.PriorityQueue
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: advanced_features.PriorityScheduler
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: advanced_features.PrioritizedRequest
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: advanced_features.Priority
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: advanced_features.PriorityConfig
   :members:
   :undoc-members:
   :show-inheritance:

Circuit Breaker
---------------

.. autoclass:: advanced_features.CircuitBreaker
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: advanced_features.CircuitState
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: advanced_features.CircuitBreakerConfig
   :members:
   :undoc-members:
   :show-inheritance:

.. autoexception:: advanced_features.CircuitBreakerError

Advanced Request Manager
-------------------------

.. autoclass:: advanced_features.AdvancedRequestManager
   :members:
   :undoc-members:
   :show-inheritance:

Usage Example
-------------

.. code-block:: python

   from advanced_features import (
       AdvancedRequestManager,
       Priority,
       PriorityConfig,
       CircuitBreakerConfig
   )
   import asyncio

   async def main():
       # Create manager with custom configuration
       priority_config = PriorityConfig(
           max_queue_size=1000,
           aging_interval=10.0,
           enable_aging=True
       )

       circuit_config = CircuitBreakerConfig(
           failure_threshold=5,
           success_threshold=2,
           timeout=60.0
       )

       manager = AdvancedRequestManager(
           priority_config=priority_config,
           circuit_config=circuit_config,
           num_workers=10
       )

       await manager.start()

       # Execute high-priority request
       async def critical_operation():
           # Your operation here
           return {"status": "success"}

       result = await manager.execute(
           critical_operation,
           priority=Priority.CRITICAL,
           use_circuit_breaker=True
       )

       # Get statistics
       stats = manager.get_stats()
       print(f"Queue size: {stats['queue_size']}")
       print(f"Circuit state: {stats['circuit_breaker']['state']}")

       await manager.stop()

   asyncio.run(main())
