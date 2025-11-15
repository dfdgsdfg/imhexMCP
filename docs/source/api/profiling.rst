Profiling
=========

The ``profiling`` module provides performance profiling and benchmarking tools
for analyzing ImHex MCP client performance.

Features
--------

* Endpoint performance profiling
* Statistical analysis (mean, median, p95, p99)
* Throughput measurement
* Latency histograms
* Comparative benchmarking

Module Reference
----------------

.. automodule:: profiling
   :members:
   :undoc-members:
   :show-inheritance:

Classes
-------

.. autoclass:: profiling.EndpointProfiler
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: profiling.ProfileStats
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: profiling.BenchmarkRunner
   :members:
   :undoc-members:
   :show-inheritance:

Functions
---------

.. autofunction:: profiling.profile_endpoint
.. autofunction:: profiling.compare_implementations

Usage Example
-------------

.. code-block:: python

   from profiling import EndpointProfiler, profile_endpoint
   from cached_client import create_client

   # Create profiler
   profiler = EndpointProfiler()

   # Profile endpoint
   client = create_client()
   stats = profile_endpoint(
       client=client,
       endpoint="capabilities",
       iterations=100
   )

   # Print statistics
   print(f"Mean latency: {stats.mean_latency_ms:.2f}ms")
   print(f"P95 latency: {stats.p95_latency_ms:.2f}ms")
   print(f"P99 latency: {stats.p99_latency_ms:.2f}ms")
   print(f"Throughput: {stats.requests_per_second:.2f} req/s")

   # Get profiling report
   report = profiler.generate_report()
   print(report)
