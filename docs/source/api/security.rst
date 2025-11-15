Security
========

The ``security`` module provides security features including authentication,
authorization, input validation, and rate limiting.

Features
--------

* Request authentication
* Token-based authorization
* Input sanitization and validation
* Rate limiting
* IP whitelisting/blacklisting
* Security audit logging

Module Reference
----------------

.. automodule:: security
   :members:
   :undoc-members:
   :show-inheritance:

Classes
-------

.. autoclass:: security.SecurityManager
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: security.RateLimiter
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: security.InputValidator
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: security.AuthToken
   :members:
   :undoc-members:
   :show-inheritance:

Functions
---------

.. autofunction:: security.sanitize_input
.. autofunction:: security.validate_request
.. autofunction:: security.check_rate_limit

Usage Example
-------------

.. code-block:: python

   from security import SecurityManager, RateLimiter, validate_request

   # Create security manager
   security = SecurityManager(
       require_auth=True,
       allowed_ips=["127.0.0.1", "192.168.1.0/24"]
   )

   # Create rate limiter
   rate_limiter = RateLimiter(
       max_requests=100,
       time_window=60.0  # 100 requests per minute
   )

   # Validate and process request
   def process_request(request_data, client_ip, auth_token):
       # Check authentication
       if not security.validate_token(auth_token):
           raise SecurityError("Invalid authentication token")

       # Check IP whitelist
       if not security.is_allowed_ip(client_ip):
           raise SecurityError("IP not allowed")

       # Check rate limit
       if not rate_limiter.check_limit(client_ip):
           raise SecurityError("Rate limit exceeded")

       # Validate input
       validated_data = validate_request(request_data)

       # Process request
       return process(validated_data)
