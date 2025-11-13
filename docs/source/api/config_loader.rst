Configuration Module
====================

The config_loader module provides centralized YAML-based configuration management with
Pydantic validation and singleton pattern.

Overview
--------

Configuration is loaded from ``config.yaml`` and validated against Pydantic models, providing:

* Type-safe configuration access
* Validation with helpful error messages
* Default values for optional settings
* Singleton pattern for global access

Configuration Structure
-----------------------

The configuration file supports these sections:

Server Settings
^^^^^^^^^^^^^^^

.. code-block:: yaml

   server:
     host: "localhost"
     port: 31337
     max_connections: 100

Performance Tuning
^^^^^^^^^^^^^^^^^^

.. code-block:: yaml

   performance:
     connection_pool:
       enabled: true
       min_size: 2
       max_size: 10
       acquire_timeout: 5.0

     batching:
       enabled: true
       max_batch_size: 50
       max_wait_time: 0.01

     compression:
       enabled: true
       algorithm: "zstd"
       level: 3
       min_size: 1024

Monitoring
^^^^^^^^^^

.. code-block:: yaml

   metrics:
     enabled: true
     port: 9090
     endpoint: "/metrics"

   logging:
     level: "INFO"
     format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

Usage Example
-------------

.. code-block:: python

   from config_loader import get_config

   # Load configuration (singleton)
   config = get_config()

   # Access settings with type safety
   if config.performance.connection_pool.enabled:
       pool = ConnectionPool(
           min_size=config.performance.connection_pool.min_size,
           max_size=config.performance.connection_pool.max_size
       )

API Reference
-------------

.. automodule:: config_loader
   :members:
   :undoc-members:
   :show-inheritance:
