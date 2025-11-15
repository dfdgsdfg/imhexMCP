Configuration
=============

The ``config`` module provides centralized configuration management for ImHex MCP
with environment variable support and type-safe access.

Features
--------

* YAML configuration file support
* Environment variable overrides
* Type-safe configuration access
* Default value handling
* Validation and error reporting

Module Reference
----------------

.. automodule:: config
   :members:
   :undoc-members:
   :show-inheritance:

Classes
-------

.. autoclass:: config.Config
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: config.ServerConfig
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: config.ClientConfig
   :members:
   :undoc-members:
   :show-inheritance:

Functions
---------

.. autofunction:: config.load_config
.. autofunction:: config.get_config

Usage Example
-------------

.. code-block:: python

   from config import load_config, get_config

   # Load configuration from YAML file
   config = load_config("config.yaml")

   # Access configuration values
   host = config.server.host
   port = config.server.port
   timeout = config.client.timeout

   # Get global config instance
   global_config = get_config()

   print(f"Connecting to {host}:{port}")
