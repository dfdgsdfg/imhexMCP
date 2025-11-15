Health Monitor
==============

The ``health_monitor`` module provides health checking and monitoring capabilities
for ImHex MCP services with automatic alerting and status reporting.

Features
--------

* Continuous health checking
* Connection validation
* Service availability monitoring
* Automatic failure detection
* Health status reporting
* Alert notifications

Module Reference
----------------

.. automodule:: health_monitor
   :members:
   :undoc-members:
   :show-inheritance:

Classes
-------

.. autoclass:: health_monitor.HealthMonitor
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: health_monitor.HealthStatus
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: health_monitor.HealthCheck
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: health_monitor.HealthCheckResult
   :members:
   :undoc-members:
   :show-inheritance:

Usage Example
-------------

.. code-block:: python

   from health_monitor import HealthMonitor
   import asyncio

   async def main():
       # Create health monitor
       monitor = HealthMonitor(
           host="localhost",
           port=31337,
           check_interval=30.0  # Check every 30 seconds
       )

       # Start monitoring
       await monitor.start()

       # Get current health status
       status = await monitor.get_status()
       print(f"Service is {status.state}")
       print(f"Uptime: {status.uptime_seconds}s")
       print(f"Last check: {status.last_check_time}")

       # Stop monitoring
       await monitor.stop()

   asyncio.run(main())
