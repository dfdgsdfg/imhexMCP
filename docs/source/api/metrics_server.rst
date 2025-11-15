Metrics Server
==============

The ``metrics_server`` module provides a Prometheus-compatible metrics server for
exposing ImHex MCP performance metrics and statistics.

Features
--------

* Prometheus metrics export
* HTTP metrics endpoint
* Custom metric collectors
* Automatic metric registration
* Real-time performance tracking
* Grafana dashboard support

Module Reference
----------------

.. automodule:: metrics_server
   :members:
   :undoc-members:
   :show-inheritance:

Classes
-------

.. autoclass:: metrics_server.MetricsServer
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: metrics_server.MetricsCollector
   :members:
   :undoc-members:
   :show-inheritance:

Functions
---------

.. autofunction:: metrics_server.start_metrics_server
.. autofunction:: metrics_server.register_collector

Usage Example
-------------

.. code-block:: python

   from metrics_server import start_metrics_server, MetricsServer
   import asyncio

   async def main():
       # Start metrics server on port 8000
       server = await start_metrics_server(
           port=8000,
           host="0.0.0.0"
       )

       print("Metrics available at http://localhost:8000/metrics")

       # Keep server running
       try:
           while True:
               await asyncio.sleep(1)
       except KeyboardInterrupt:
           await server.stop()

   asyncio.run(main())

   # Metrics can be scraped by Prometheus:
   # - http://localhost:8000/metrics
