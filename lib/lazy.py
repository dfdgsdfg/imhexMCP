#!/usr/bin/env python3
"""
ImHex MCP Lazy Loading and Optimization Patterns

Provides lazy initialization, deferred loading, and memoization patterns
to reduce startup time and unnecessary operations.
"""

from error_handling import retry_with_backoff
import socket
import json
import sys
import functools
import threading
from pathlib import Path
from typing import Dict, Any, Optional, Callable, TypeVar, Generic

# Add lib directory to path
sys.path.insert(0, str(Path(__file__).parent))


T = TypeVar('T')


class LazyProperty(Generic[T]):
    """
    Descriptor for lazy-loading properties.

    Computes value on first access and caches it for subsequent accesses.
    Thread-safe with lock to prevent duplicate initialization.

    Example:
        >>> class MyClass:
        ...     @LazyProperty
        ...     def expensive_data(self):
        ...         return load_expensive_data()
    """

    def __init__(self, func: Callable[[Any], T]):
        self.func = func
        self.name = func.__name__
        self.lock = threading.Lock()

    def __get__(self, obj: Any, objtype: Any = None) -> T:
        if obj is None:
            return self

        # Check if already cached
        attr_name = f"_lazy_{self.name}"
        if hasattr(obj, attr_name):
            return getattr(obj, attr_name)

        # Load and cache with thread safety
        with self.lock:
            # Double-check after acquiring lock
            if hasattr(obj, attr_name):
                return getattr(obj, attr_name)

            value = self.func(obj)
            setattr(obj, attr_name, value)
            return value

    def __set_name__(self, owner: type, name: str):
        self.name = name


class LazyValue(Generic[T]):
    """
    Container for lazy-loaded values.

    Delays computation until value is accessed.
    Thread-safe with lock to prevent duplicate computation.

    Example:
        >>> expensive_config = LazyValue(lambda: load_config())
        >>> config = expensive_config.get()  # Loads on first access
        >>> config = expensive_config.get()  # Returns cached value
    """

    def __init__(self, factory: Callable[[], T]):
        self._factory = factory
        self._value: Optional[T] = None
        self._initialized = False
        self._lock = threading.Lock()

    def get(self) -> T:
        """Get value, computing it on first access."""
        if self._initialized:
            return self._value

        with self._lock:
            if self._initialized:
                return self._value

            self._value = self._factory()
            self._initialized = True
            return self._value

    def is_initialized(self) -> bool:
        """Check if value has been computed."""
        return self._initialized

    def reset(self) -> None:
        """Reset lazy value, forcing recomputation on next access."""
        with self._lock:
            self._value = None
            self._initialized = False


def memoize(func: Callable[..., T]) -> Callable[..., T]:
    """
    Memoization decorator for expensive computations.

    Caches function results based on arguments.
    Thread-safe with lock protection.

    Args:
        func: Function to memoize

    Returns:
        Memoized function

    Example:
        >>> @memoize
        ... def fibonacci(n):
        ...     if n <= 1:
        ...         return n
        ...     return fibonacci(n-1) + fibonacci(n-2)
    """
    cache = {}
    lock = threading.Lock()

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Create hashable key from arguments
        key = (args, tuple(sorted(kwargs.items())))

        if key in cache:
            return cache[key]

        with lock:
            # Double-check after acquiring lock
            if key in cache:
                return cache[key]

            result = func(*args, **kwargs)
            cache[key] = result
            return result

    # Add cache inspection methods
    wrapper.cache = cache
    wrapper.cache_clear = lambda: cache.clear()
    wrapper.cache_info = lambda: {
        "size": len(cache),
        "keys": list(cache.keys())}

    return wrapper


def memoize_with_ttl(ttl: float):
    """
    Memoization decorator with time-to-live expiration.

    Args:
        ttl: Time to live in seconds

    Returns:
        Decorator function

    Example:
        >>> @memoize_with_ttl(60.0)  # Cache for 60 seconds
        ... def get_current_state():
        ...     return query_expensive_state()
    """
    import time

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        cache = {}
        lock = threading.Lock()

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            key = (args, tuple(sorted(kwargs.items())))
            current_time = time.time()

            # Check if cached and not expired
            if key in cache:
                value, timestamp = cache[key]
                if current_time - timestamp < ttl:
                    return value

            with lock:
                # Double-check after acquiring lock
                if key in cache:
                    value, timestamp = cache[key]
                    if current_time - timestamp < ttl:
                        return value

                result = func(*args, **kwargs)
                cache[key] = (result, current_time)
                return result

        wrapper.cache = cache
        wrapper.cache_clear = lambda: cache.clear()
        wrapper.cache_info = lambda: {
            "size": len(cache),
            "keys": list(cache.keys()),
            "ttl": ttl
        }

        return wrapper

    return decorator


class LazyProvider:
    """
    Lazy-loading wrapper for ImHex provider metadata.

    Defers loading provider information until actually accessed,
    improving startup time when dealing with many providers.

    Example:
        >>> provider = LazyProvider(0, client)
        >>> # No data loaded yet
        >>> name = provider.name  # Loads metadata on first access
        >>> size = provider.size  # Uses cached metadata
    """

    def __init__(
        self,
        provider_id: int,
        client: Any,
        preload_metadata: bool = False
    ):
        """
        Initialize lazy provider.

        Args:
            provider_id: Provider ID
            client: ImHex MCP client
            preload_metadata: If True, load metadata immediately
        """
        self.provider_id = provider_id
        self._client = client
        self._metadata: Optional[Dict[str, Any]] = None
        self._lock = threading.Lock()

        if preload_metadata:
            self._load_metadata()

    def _load_metadata(self) -> Dict[str, Any]:
        """Load provider metadata from server."""
        if self._metadata is not None:
            return self._metadata

        with self._lock:
            if self._metadata is not None:
                return self._metadata

            result = self._client.send_request(
                "file/info", {"provider_id": self.provider_id})

            if result.get("status") != "success":
                raise ValueError(
                    f"Failed to load provider {self.provider_id}: {result.get('data', {}).get('error')}")

            self._metadata = result["data"]
            return self._metadata

    @property
    def metadata(self) -> Dict[str, Any]:
        """Get provider metadata (lazy-loaded)."""
        return self._load_metadata()

    @property
    def name(self) -> str:
        """Get provider name (lazy-loaded)."""
        return self.metadata.get("name", f"Provider {self.provider_id}")

    @property
    def size(self) -> int:
        """Get provider size (lazy-loaded)."""
        return self.metadata.get("size", 0)

    @property
    def path(self) -> Optional[str]:
        """Get provider path (lazy-loaded)."""
        return self.metadata.get("path")

    @property
    def is_loaded(self) -> bool:
        """Check if metadata has been loaded."""
        return self._metadata is not None

    def invalidate(self) -> None:
        """Invalidate cached metadata, forcing reload on next access."""
        with self._lock:
            self._metadata = None

    def refresh(self) -> None:
        """Refresh metadata from server."""
        self.invalidate()
        self._load_metadata()


class LazyProviderList:
    """
    Lazy-loading list of providers.

    Loads provider list on first access and caches it.
    Individual provider metadata is loaded on-demand.

    Example:
        >>> providers = LazyProviderList(client)
        >>> # No data loaded yet
        >>> count = providers.count  # Loads provider list
        >>> provider = providers[0]  # Returns lazy provider
        >>> name = provider.name  # Loads provider metadata
    """

    def __init__(self, client: Any):
        """
        Initialize lazy provider list.

        Args:
            client: ImHex MCP client
        """
        self._client = client
        self._providers: Optional[list[LazyProvider]] = None
        self._lock = threading.Lock()

    def _load_providers(self) -> list[LazyProvider]:
        """Load provider list from server."""
        if self._providers is not None:
            return self._providers

        with self._lock:
            if self._providers is not None:
                return self._providers

            result = self._client.send_request("file/list")

            if result.get("status") != "success":
                raise ValueError(
                    f"Failed to load providers: {result.get('data', {}).get('error')}")

            provider_data = result["data"].get("providers", [])
            self._providers = [
                LazyProvider(p["id"], self._client)
                for p in provider_data
            ]

            return self._providers

    @property
    def providers(self) -> list[LazyProvider]:
        """Get provider list (lazy-loaded)."""
        return self._load_providers()

    @property
    def count(self) -> int:
        """Get provider count (lazy-loaded)."""
        return len(self.providers)

    def __len__(self) -> int:
        """Get provider count."""
        return self.count

    def __getitem__(self, index: int) -> LazyProvider:
        """Get provider by index."""
        return self.providers[index]

    def __iter__(self):
        """Iterate over providers."""
        return iter(self.providers)

    def is_loaded(self) -> bool:
        """Check if provider list has been loaded."""
        return self._providers is not None

    def invalidate(self) -> None:
        """Invalidate cached provider list."""
        with self._lock:
            self._providers = None

    def refresh(self) -> None:
        """Refresh provider list from server."""
        self.invalidate()
        self._load_providers()


class DeferredOperation:
    """
    Deferred operation that executes on demand.

    Useful for batching operations or delaying expensive work
    until absolutely necessary.

    Example:
        >>> op = DeferredOperation(lambda: expensive_computation())
        >>> # Work not done yet
        >>> result = op.execute()  # Executes now
        >>> result = op.result  # Returns cached result
    """

    def __init__(self, operation: Callable[[], T]):
        """
        Initialize deferred operation.

        Args:
            operation: Function to execute
        """
        self._operation = operation
        self._result: Optional[T] = None
        self._executed = False
        self._lock = threading.Lock()

    def execute(self) -> T:
        """Execute operation if not already done."""
        if self._executed:
            return self._result

        with self._lock:
            if self._executed:
                return self._result

            self._result = self._operation()
            self._executed = True
            return self._result

    @property
    def result(self) -> T:
        """Get result (executes if needed)."""
        return self.execute()

    @property
    def is_executed(self) -> bool:
        """Check if operation has been executed."""
        return self._executed

    def reset(self) -> None:
        """Reset operation, allowing re-execution."""
        with self._lock:
            self._result = None
            self._executed = False


class LazyClient:
    """
    Lazy-loading client wrapper.

    Defers connection and capability checks until first request.
    Provides lazy access to common resources.

    Example:
        >>> client = LazyClient()
        >>> # No connection yet
        >>> result = client.get_capabilities()  # Connects on first request
        >>> providers = client.providers  # Returns lazy provider list
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 31337,
        timeout: int = 10
    ):
        """
        Initialize lazy client.

        Args:
            host: ImHex MCP host
            port: ImHex MCP port
            timeout: Socket timeout
        """
        self.host = host
        self.port = port
        self.timeout = timeout

        # Lazy-loaded resources
        self._capabilities = LazyValue(lambda: self._load_capabilities())
        self._providers = LazyProviderList(self)

    @retry_with_backoff(max_attempts=3, initial_delay=0.5,
                        exponential_base=2.0)
    def send_request(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Send request to ImHex MCP."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            sock.connect((self.host, self.port))

            request = json.dumps({
                "endpoint": endpoint,
                "data": data or {}
            }) + "\n"

            sock.sendall(request.encode())

            response = b""
            while b"\n" not in response:
                response += sock.recv(4096)

            sock.close()
            return json.loads(response.decode().strip())

        except (socket.error, socket.timeout, ConnectionRefusedError):
            raise
        except Exception as e:
            return {"status": "error", "data": {"error": str(e)}}

    def _load_capabilities(self) -> Dict[str, Any]:
        """Load capabilities from server."""
        result = self.send_request("capabilities")
        if result.get("status") != "success":
            raise ValueError(
                f"Failed to load capabilities: {result.get('data', {}).get('error')}")
        return result["data"]

    @property
    def capabilities(self) -> Dict[str, Any]:
        """Get capabilities (lazy-loaded)."""
        return self._capabilities.get()

    @property
    def endpoints(self) -> list[str]:
        """Get available endpoints (lazy-loaded)."""
        return self.capabilities.get("endpoints", [])

    @property
    def providers(self) -> LazyProviderList:
        """Get lazy provider list."""
        return self._providers

    def get_capabilities(self) -> Dict[str, Any]:
        """Get capabilities with lazy loading."""
        return {"status": "success", "data": self.capabilities}

    def invalidate_cache(self) -> None:
        """Invalidate all cached data."""
        self._capabilities.reset()
        self._providers.invalidate()


# Optimization utilities

def once(func: Callable[[], T]) -> Callable[[], T]:
    """
    Decorator that ensures function is only called once.

    Subsequent calls return cached result.
    Thread-safe.

    Args:
        func: Function to call once

    Returns:
        Wrapped function

    Example:
        >>> @once
        ... def initialize():
        ...     print("Initializing...")
        ...     return expensive_setup()
        >>> initialize()  # Prints "Initializing..."
        >>> initialize()  # Returns cached result, no print
    """
    result = []
    lock = threading.Lock()

    @functools.wraps(func)
    def wrapper():
        if result:
            return result[0]

        with lock:
            if result:
                return result[0]

            value = func()
            result.append(value)
            return value

    return wrapper


def lazy_import(module_name: str, attribute: Optional[str] = None):
    """
    Lazy import a module or attribute.

    Defers import until first use, improving startup time.

    Args:
        module_name: Module to import
        attribute: Optional attribute to extract

    Returns:
        Lazy import proxy

    Example:
        >>> numpy = lazy_import("numpy")
        >>> # numpy not imported yet
        >>> arr = numpy.array([1, 2, 3])  # Imports on first use
    """
    import importlib

    class LazyImport:
        def __init__(self):
            self._module = None
            self._lock = threading.Lock()

        def _import(self):
            if self._module is None:
                with self._lock:
                    if self._module is None:
                        self._module = importlib.import_module(module_name)
                        if attribute:
                            self._module = getattr(self._module, attribute)
            return self._module

        def __getattr__(self, name):
            return getattr(self._import(), name)

        def __call__(self, *args, **kwargs):
            return self._import()(*args, **kwargs)

    return LazyImport()


# Convenience functions

def create_lazy_client(
    host: str = "localhost",
    port: int = 31337,
    **kwargs
) -> LazyClient:
    """
    Factory function to create lazy client.

    Args:
        host: ImHex MCP host
        port: ImHex MCP port
        **kwargs: Additional client parameters

    Returns:
        Configured LazyClient instance

    Example:
        >>> client = create_lazy_client()
        >>> # No connection yet
        >>> caps = client.capabilities  # Connects on first access
    """
    return LazyClient(host=host, port=port, **kwargs)
