"""
Mutation Testing Configuration for ImHex MCP

Configures mutmut to run mutation testing on core modules.
"""


def pre_mutation(context):
    """
    Filter mutations to focus on critical code paths.

    Skip:
    - Test files
    - Documentation
    - Configuration files
    - Generated code
    """
    line = context.current_source_line.strip()

    # Skip documentation strings
    if line.startswith('"""') or line.startswith("'''"):
        context.skip = True
        return

    # Skip logging statements
    if 'logger.' in line or 'print(' in line:
        context.skip = True
        return

    # Skip type hints only lines
    if line.startswith('->') or line.endswith(':'):
        context.skip = True
        return

    # Skip imports
    if line.startswith('import ') or line.startswith('from '):
        context.skip = True
        return


def init():
    """Initialize mutation testing configuration."""
    return {
        # Paths to mutate
        'paths_to_mutate': 'lib/',

        # Test command
        'runner': 'python -m pytest lib/test_*.py -x --tb=short',

        # Test time multiplier (timeout)
        'test_time_multiplier': 3.0,

        # Test time base (minimum time to wait)
        'test_time_base': 5.0,

        # Number of parallel workers
        'workers': 4,

        # Cache directory
        'cache_only': False,
    }
