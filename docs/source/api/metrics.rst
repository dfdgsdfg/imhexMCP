Metrics Module
==============

The metrics module provides comprehensive Prometheus metrics collection and export for monitoring
the ImHex MCP server in production environments.

Overview
--------

The metrics system tracks:

* Request counts and latencies by endpoint
* Compression performance and ratios
* Connection pool utilization
* Cache hit/miss rates
* Error rates and types
* System health indicators

All metrics are exposed on a configurable HTTP endpoint for Prometheus scraping.

Quick Start
-----------

Initialize metrics on server startup:

.. code-block:: python

   from metrics import initialize_metrics
   from metrics_server import MetricsServer

   # Initialize with server info
   metrics = initialize_metrics(
       version="1.0.0",
       environment="production"
   )

   # Start metrics HTTP server
   server = MetricsServer(metrics, host="0.0.0.0", port=9090)
   server.start()

Track requests with decorators:

.. code-block:: python

   @metrics.track_request('file/read')
   async def handle_file_read(data):
       # ... implementation
       pass

API Reference
-------------

.. automodule:: metrics
   :members:
   :undoc-members:
   :show-inheritance:
