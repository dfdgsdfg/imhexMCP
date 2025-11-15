Connection Pool
===============

The ``connection_pool`` module provides efficient connection pooling for ImHex MCP,
reducing connection overhead and improving throughput.

Features
--------

* Connection reuse with configurable pool size
* Automatic connection health checking
* Thread-safe connection management
* Graceful connection cleanup
* Connection timeout handling

Module Reference
----------------

.. automodule:: connection_pool
   :members:
   :undoc-members:
   :show-inheritance:

Classes
-------

.. autoclass:: connection_pool.ConnectionPool
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: connection_pool.PooledConnection
   :members:
   :undoc-members:
   :show-inheritance:

Usage Example
-------------

.. code-block:: python

   from connection_pool import ConnectionPool

   # Create connection pool
   pool = ConnectionPool(
       host="localhost",
       port=31337,
       max_size=10,
       timeout=30
   )

   # Get connection from pool
   with pool.get_connection() as conn:
       # Use connection
       response = conn.send_request("capabilities")

   # Connection automatically returned to pool

   # Cleanup when done
   pool.close_all()
