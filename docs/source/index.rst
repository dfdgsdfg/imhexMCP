ImHex MCP Documentation
=======================

ImHex MCP (Model Context Protocol) Server provides a high-performance, feature-rich interface
to the ImHex hex editor through a network-based API. It enables programmatic access to ImHex's
powerful binary analysis capabilities with built-in optimizations for production use.

Features
--------

* **High-Performance Architecture**: Connection pooling, request batching, and compression
* **Comprehensive API**: File operations, data analysis, pattern matching, and more
* **Production-Ready**: Health monitoring, Prometheus metrics, and YAML configuration
* **Type-Safe**: Full type hints with mypy checking
* **Well-Tested**: Comprehensive test suite with pytest and CI/CD integration

Quick Start
-----------

Installation
^^^^^^^^^^^^

.. code-block:: bash

   # Clone repository
   git clone https://github.com/yourorg/imhex-mcp
   cd imhex-mcp

   # Install dependencies
   cd mcp-server
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt

Basic Usage
^^^^^^^^^^^

.. code-block:: python

   from async_client import ImHexAsyncClient

   # Create client with connection pooling
   async with ImHexAsyncClient(
       host="localhost",
       port=31337,
       use_connection_pool=True
   ) as client:
       # Read file data
       data = await client.file_read(provider_id=0, offset=0, size=256)

       # Search for patterns
       results = await client.file_search(
           provider_id=0,
           pattern="504B0304"  # ZIP signature
       )

Contents
--------

.. toctree::
   :maxdepth: 2
   :caption: User Guide

   getting_started
   configuration
   api_reference

.. toctree::
   :maxdepth: 2
   :caption: Architecture

   architecture/overview

.. toctree::
   :maxdepth: 2
   :caption: API Documentation

   api/metrics
   api/config_loader
   api/data_compression
   api/async_client

.. toctree::
   :maxdepth: 1
   :caption: Development

   testing
   contributing
   changelog

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

