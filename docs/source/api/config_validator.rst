Configuration Validator
=======================

The ``config_validator`` module provides comprehensive validation for configuration
files with Pydantic models and custom validators.

Features
--------

* Pydantic-based validation
* Custom validation rules
* Type checking
* Range validation
* Descriptive error messages

Module Reference
----------------

.. automodule:: config_validator
   :members:
   :undoc-members:
   :show-inheritance:

Classes
-------

.. autoclass:: config_validator.ConfigValidator
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: config_validator.ValidationResult
   :members:
   :undoc-members:
   :show-inheritance:

Functions
---------

.. autofunction:: config_validator.validate_config
.. autofunction:: config_validator.validate_yaml_file

Usage Example
-------------

.. code-block:: python

   from config_validator import validate_yaml_file

   # Validate configuration file
   result = validate_yaml_file("config.yaml")

   if result.is_valid:
       print("Configuration is valid")
       config = result.config
   else:
       print("Validation errors:")
       for error in result.errors:
           print(f"  - {error}")
