Error Handling
==============

The ``error_handling`` module provides comprehensive error handling with retry logic,
exponential backoff, and custom exception types.

Features
--------

* Automatic retry with exponential backoff
* Configurable retry policies
* Custom exception hierarchy
* Error classification
* Detailed error logging
* Graceful degradation

Module Reference
----------------

.. automodule:: error_handling
   :members:
   :undoc-members:
   :show-inheritance:

Exceptions
----------

.. autoexception:: error_handling.ImHexError
.. autoexception:: error_handling.ImHexConnectionError
.. autoexception:: error_handling.ImHexTimeoutError
.. autoexception:: error_handling.ImHexProtocolError
.. autoexception:: error_handling.ImHexValidationError

Decorators
----------

.. autofunction:: error_handling.retry_with_backoff
.. autofunction:: error_handling.async_retry_with_backoff

Classes
-------

.. autoclass:: error_handling.RetryPolicy
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: error_handling.ErrorHandler
   :members:
   :undoc-members:
   :show-inheritance:

Usage Example
-------------

.. code-block:: python

   from error_handling import retry_with_backoff, ImHexConnectionError

   # Synchronous retry decorator
   @retry_with_backoff(max_attempts=3, initial_delay=1.0, exponential_base=2.0)
   def connect_to_server():
       # This will retry up to 3 times with exponential backoff
       # if connection fails
       import socket
       sock = socket.create_connection(("localhost", 31337), timeout=5)
       return sock

   # Async retry
   from error_handling import async_retry_with_backoff
   import asyncio

   @async_retry_with_backoff(max_attempts=3)
   async def fetch_data():
       # Async operation with automatic retry
       async with aiohttp.ClientSession() as session:
           async with session.get("http://localhost:31337/api") as response:
               return await response.json()

   # Custom error handling
   try:
       result = connect_to_server()
   except ImHexConnectionError as e:
       print(f"Failed to connect after retries: {e}")
