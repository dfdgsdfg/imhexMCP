Logging Configuration
=====================

The ``logging_config`` module provides centralized logging configuration with
structured logging, multiple handlers, and log level management.

Features
--------

* Structured logging support
* Multiple log handlers (console, file, syslog)
* Configurable log levels
* JSON log formatting
* Request/response logging
* Performance logging

Module Reference
----------------

.. automodule:: logging_config
   :members:
   :undoc-members:
   :show-inheritance:

Classes
-------

.. autoclass:: logging_config.LogConfig
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: logging_config.StructuredLogger
   :members:
   :undoc-members:
   :show-inheritance:

Functions
---------

.. autofunction:: logging_config.setup_logging
.. autofunction:: logging_config.get_logger

Usage Example
-------------

.. code-block:: python

   from logging_config import setup_logging, get_logger

   # Setup logging with configuration
   setup_logging(
       log_level="INFO",
       log_file="imhex_mcp.log",
       structured=True
   )

   # Get logger for module
   logger = get_logger(__name__)

   # Use logger
   logger.info("Starting ImHex MCP client")
   logger.debug("Debug information", extra={"request_id": "123"})
   logger.error("Error occurred", exc_info=True)
