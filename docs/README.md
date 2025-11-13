# ImHex MCP Documentation

This directory contains the Sphinx documentation for the ImHex MCP project.

## Building the Documentation

### Prerequisites

Install Sphinx and dependencies (from mcp-server directory):

```bash
cd mcp-server
source venv/bin/activate
pip install sphinx sphinx-rtd-theme sphinx-autodoc-typehints
```

### Build HTML Documentation

From the docs directory:

```bash
cd docs
../mcp-server/venv/bin/sphinx-build -b html source build/html
```

Or using the Makefile from project root:

```bash
cd docs
make html SPHINXBUILD=../mcp-server/venv/bin/sphinx-build
```

### View Documentation

Open the generated documentation in your browser:

```bash
open build/html/index.html
```

## Documentation Structure

```
docs/
├── source/
│   ├── index.rst                # Main documentation page
│   ├── conf.py                  # Sphinx configuration
│   └── api/                     # API documentation
│       ├── metrics.rst          # Metrics module docs
│       ├── config_loader.rst    # Configuration module docs
│       ├── data_compression.rst # Compression module docs
│       └── async_client.rst     # Async client module docs
└── build/
    └── html/                    # Generated HTML documentation
```

## What's Documented

The documentation includes:

### Core Modules

* **metrics.py** - Prometheus metrics collection and export
* **config_loader.py** - YAML configuration management
* **data_compression.py** - Data compression/decompression
* **async_client.py** - Async client with connection pooling

### Features

* Comprehensive API reference with type hints
* Usage examples and code snippets
* Configuration guides
* Performance considerations
* Architecture overview

## Updating Documentation

### Adding New Modules

1. Create a new `.rst` file in `docs/source/api/`
2. Add module documentation using autodoc:

```rst
Module Name
===========

.. automodule:: module_name
   :members:
   :undoc-members:
   :show-inheritance:
```

3. Add the module to `index.rst` toctree
4. Rebuild documentation

### Editing Existing Pages

Edit the `.rst` files in `docs/source/` and rebuild the documentation.

## Continuous Integration

The GitHub Actions workflow automatically builds and validates documentation on every push:

* Checks for build warnings and errors
* Ensures all cross-references are valid
* Validates code examples

## Hosting

The documentation can be hosted on:

* **Read the Docs**: Connect your repository for automatic builds
* **GitHub Pages**: Deploy `build/html/` to `gh-pages` branch
* **Local Server**: Run `python -m http.server` in `build/html/`

## Troubleshooting

### Missing Python Modules

If autodoc can't find modules, ensure:

1. The lib directory is in Python path (check conf.py)
2. All dependencies are installed in venv
3. Module names are correct in .rst files

### Build Warnings

Common warnings:

* **toctree references nonexisting document**: Placeholder pages not yet created
* **Unexpected indentation**: Docstring formatting issues (use proper RST syntax)

To fix docstring issues, ensure proper indentation and RST formatting in Python docstrings.
