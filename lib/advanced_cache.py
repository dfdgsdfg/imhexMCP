"""
Advanced Caching Optimizations for ImHex MCP

Provides multi-tier caching with predictive features for optimal performance.

Features:
- Multi-tier cache (L1/L2) with different eviction policies
- Predictive caching based on access patterns
- Sequential access detection and prefetching
- Adaptive cache sizing based on workload
- Cache warming and preloading
"""

import asyncio
import time
from typing import Dict, Any, Optional, List, Tuple, Callable, TypeVar
from dataclasses import dataclass, field
from collections import OrderedDict, deque
from enum import Enum
import logging

logger = logging.getLogger(__name__)

T = TypeVar("T")


# ============================================================================
# Cache Configuration
# ============================================================================


class CachePolicy(Enum):
    """Cache eviction policies."""

    LRU = "lru"  # Least Recently Used
    LFU = "lfu"  # Least Frequently Used
    FIFO = "fifo"  # First In First Out
    ADAPTIVE = "adaptive"  # Adaptive based on workload


@dataclass
class CacheTierConfig:
    """Configuration for a cache tier."""

    max_size: int = 100  # Maximum number of entries
    max_bytes: int = 10 * 1024 * 1024  # Maximum bytes (10MB default)
    ttl: float = 300.0  # Time to live in seconds
    policy: CachePolicy = CachePolicy.LRU
    promotion_threshold: int = 2  # Hits before promoting to higher tier


@dataclass
class PredictiveCacheConfig:
    """Configuration for predictive caching."""

    enable_prefetch: bool = True
    prefetch_distance: int = 5  # Chunks to prefetch ahead
    sequential_threshold: int = 3  # Accesses before pattern detected
    pattern_window: int = 10  # Size of pattern detection window
    enable_warming: bool = True  # Enable cache warming on startup


@dataclass
class CacheStats:
    """Cache statistics."""

    hits: int = 0
    misses: int = 0
    promotions: int = 0
    evictions: int = 0
    prefetches: int = 0
    total_bytes: int = 0

    @property
    def hit_rate(self) -> float:
        """Calculate hit rate."""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0


# ============================================================================
# Cache Entry
# ============================================================================


@dataclass
class CacheEntry:
    """Entry in cache with metadata."""

    key: str
    value: Any
    size: int  # Size in bytes
    access_count: int = 0
    last_access: float = field(default_factory=time.monotonic)
    created: float = field(default_factory=time.monotonic)

    def touch(self) -> None:
        """Update access metadata."""
        self.access_count += 1
        self.last_access = time.monotonic()

    def is_expired(self, ttl: float) -> bool:
        """Check if entry has expired."""
        return time.monotonic() - self.created > ttl


# ============================================================================
# Cache Tier
# ============================================================================


class CacheTier:
    """
    Single tier in multi-tier cache system.

    Implements configurable eviction policy and size limits.
    """

    def __init__(self, name: str, config: CacheTierConfig):
        """Initialize cache tier."""
        self.name = name
        self.config = config
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._size_bytes = 0
        self._lock = asyncio.Lock()
        self.stats = CacheStats()

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        async with self._lock:
            entry = self._cache.get(key)

            if entry is None:
                self.stats.misses += 1
                return None

            # Check expiration
            if entry.is_expired(self.config.ttl):
                await self._evict(key)
                self.stats.misses += 1
                return None

            # Update access metadata
            entry.touch()
            self.stats.hits += 1

            # Move to end for LRU
            if self.config.policy == CachePolicy.LRU:
                self._cache.move_to_end(key)

            return entry.value

    async def put(self, key: str, value: Any, size: int) -> None:
        """Put value in cache."""
        async with self._lock:
            # Check if already exists
            if key in self._cache:
                old_entry = self._cache[key]
                self._size_bytes -= old_entry.size

            # Create new entry
            entry = CacheEntry(key=key, value=value, size=size)

            # Evict if necessary
            while (
                len(self._cache) >= self.config.max_size
                or self._size_bytes + size > self.config.max_bytes
            ):
                if not self._cache:
                    break
                await self._evict_one()

            # Add to cache
            self._cache[key] = entry
            self._size_bytes += size
            self.stats.total_bytes = self._size_bytes

    async def remove(self, key: str) -> None:
        """Remove entry from cache."""
        async with self._lock:
            await self._evict(key)

    async def _evict(self, key: str) -> None:
        """Evict specific entry."""
        entry = self._cache.pop(key, None)
        if entry:
            self._size_bytes -= entry.size
            self.stats.evictions += 1
            self.stats.total_bytes = self._size_bytes

    async def _evict_one(self) -> None:
        """Evict one entry based on policy."""
        if not self._cache:
            return

        if self.config.policy == CachePolicy.LRU:
            # Remove least recently used (first item)
            key = next(iter(self._cache))
            await self._evict(key)

        elif self.config.policy == CachePolicy.LFU:
            # Remove least frequently used
            key = min(
                self._cache.keys(), key=lambda k: self._cache[k].access_count
            )
            await self._evict(key)

        elif self.config.policy == CachePolicy.FIFO:
            # Remove oldest (first item)
            key = next(iter(self._cache))
            await self._evict(key)

        else:  # ADAPTIVE
            # Adaptive: balance between LRU and LFU
            # Remove entries with low access count and old access time
            def score(k):
                e = self._cache[k]
                age = time.monotonic() - e.last_access
                return e.access_count / (age + 1)

            key = min(self._cache.keys(), key=score)
            await self._evict(key)

    async def get_entry(self, key: str) -> Optional[CacheEntry]:
        """Get cache entry with metadata."""
        async with self._lock:
            return self._cache.get(key)

    async def clear(self) -> None:
        """Clear all entries."""
        async with self._lock:
            self._cache.clear()
            self._size_bytes = 0
            self.stats.total_bytes = 0


# ============================================================================
# Access Pattern Detector
# ============================================================================


@dataclass
class AccessPattern:
    """Detected access pattern."""

    pattern_type: str  # "sequential", "strided", "random"
    stride: int = 1  # Stride for sequential/strided access
    confidence: float = 0.0  # Confidence in pattern (0-1)


class PatternDetector:
    """
    Detects access patterns for predictive prefetching.

    Analyzes recent accesses to identify sequential, strided, or random patterns.
    """

    def __init__(self, config: PredictiveCacheConfig):
        """Initialize pattern detector."""
        self.config = config
        self._history: deque[Tuple[str, int]] = deque(
            maxlen=config.pattern_window
        )
        self._lock = asyncio.Lock()

    async def record_access(self, key: str, offset: int) -> None:
        """Record an access."""
        async with self._lock:
            self._history.append((key, offset))

    async def detect_pattern(self) -> Optional[AccessPattern]:
        """Detect access pattern from history."""
        async with self._lock:
            if len(self._history) < self.config.sequential_threshold:
                return None

            # Get recent offsets
            recent = list(self._history)[-self.config.sequential_threshold :]
            offsets = [offset for _, offset in recent]

            # Check for sequential access
            differences = [
                offsets[i + 1] - offsets[i] for i in range(len(offsets) - 1)
            ]

            if not differences:
                return None

            # Calculate stride
            avg_diff = sum(differences) / len(differences)

            # Check if consistent stride
            variance = sum((d - avg_diff) ** 2 for d in differences) / len(
                differences
            )

            if variance < 0.1 * abs(
                avg_diff
            ):  # Low variance = consistent stride
                if abs(avg_diff) < 2:  # Small stride = sequential
                    return AccessPattern(
                        pattern_type="sequential",
                        stride=int(avg_diff) if avg_diff != 0 else 1,
                        confidence=1.0 - min(variance, 1.0),
                    )
                else:  # Larger stride
                    return AccessPattern(
                        pattern_type="strided",
                        stride=int(avg_diff),
                        confidence=1.0 - min(variance / abs(avg_diff), 1.0),
                    )

            # Random access
            return AccessPattern(
                pattern_type="random", stride=0, confidence=0.5
            )


# ============================================================================
# Multi-Tier Cache
# ============================================================================


class MultiTierCache:
    """
    Multi-tier cache system with predictive prefetching.

    Features:
    - L1 (hot): Small, fast cache for frequently accessed data
    - L2 (warm): Larger cache for less frequently accessed data
    - Automatic promotion/demotion between tiers
    - Predictive prefetching based on access patterns
    """

    def __init__(
        self,
        l1_config: Optional[CacheTierConfig] = None,
        l2_config: Optional[CacheTierConfig] = None,
        predictive_config: Optional[PredictiveCacheConfig] = None,
        data_loader: Optional[Callable[[str], Any]] = None,
    ):
        """
        Initialize multi-tier cache.

        Args:
            l1_config: Configuration for L1 cache
            l2_config: Configuration for L2 cache
            predictive_config: Configuration for predictive features
            data_loader: Function to load data on cache miss
        """
        # Default configurations
        if l1_config is None:
            l1_config = CacheTierConfig(
                max_size=50,
                max_bytes=5 * 1024 * 1024,  # 5MB
                ttl=600.0,  # 10 minutes
                policy=CachePolicy.LRU,
                promotion_threshold=2,
            )

        if l2_config is None:
            l2_config = CacheTierConfig(
                max_size=200,
                max_bytes=20 * 1024 * 1024,  # 20MB
                ttl=1800.0,  # 30 minutes
                policy=CachePolicy.ADAPTIVE,
                promotion_threshold=1,
            )

        if predictive_config is None:
            predictive_config = PredictiveCacheConfig()

        self.l1 = CacheTier("L1", l1_config)
        self.l2 = CacheTier("L2", l2_config)
        self.predictive_config = predictive_config
        self.pattern_detector = PatternDetector(predictive_config)
        self.data_loader = data_loader

        self._prefetch_tasks: Dict[str, asyncio.Task] = {}
        self._lock = asyncio.Lock()

    async def get(
        self, key: str, offset: Optional[int] = None
    ) -> Optional[Any]:
        """
        Get value from cache with multi-tier lookup.

        Args:
            key: Cache key
            offset: Optional offset for pattern detection

        Returns:
            Cached value or None if not found
        """
        # Record access for pattern detection
        if offset is not None and self.predictive_config.enable_prefetch:
            await self.pattern_detector.record_access(key, offset)

        # Try L1 first
        value = await self.l1.get(key)
        if value is not None:
            logger.debug(f"Cache hit: L1 {key}")

            # Trigger predictive prefetch
            if offset is not None:
                await self._maybe_prefetch(key, offset)

            return value

        # Try L2
        value = await self.l2.get(key)
        if value is not None:
            logger.debug(f"Cache hit: L2 {key}")

            # Check for promotion to L1
            entry = await self.l2.get_entry(key)
            if (
                entry
                and entry.access_count >= self.l2.config.promotion_threshold
            ):
                await self._promote_to_l1(key, value, entry.size)

            # Trigger predictive prefetch
            if offset is not None:
                await self._maybe_prefetch(key, offset)

            return value

        logger.debug(f"Cache miss: {key}")

        # Cache miss - try to load data
        if self.data_loader:
            value = await self.data_loader(key)
            if value is not None:
                # Add to L2
                size = len(value) if isinstance(value, (bytes, str)) else 1024
                await self.l2.put(key, value, size)

                return value

        return None

    async def put(self, key: str, value: Any, tier: str = "L2") -> None:
        """
        Put value in cache.

        Args:
            key: Cache key
            value: Value to cache
            tier: Tier to place value in ("L1" or "L2")
        """
        size = len(value) if isinstance(value, (bytes, str)) else 1024

        if tier == "L1":
            await self.l1.put(key, value, size)
        else:
            await self.l2.put(key, value, size)

    async def _promote_to_l1(self, key: str, value: Any, size: int) -> None:
        """Promote entry from L2 to L1."""
        logger.debug(f"Promoting {key} to L1")
        await self.l1.put(key, value, size)
        self.l1.stats.promotions += 1

    async def _maybe_prefetch(self, key: str, offset: int) -> None:
        """Maybe trigger prefetch based on access pattern."""
        if not self.predictive_config.enable_prefetch:
            return

        # Detect pattern
        pattern = await self.pattern_detector.detect_pattern()

        if pattern is None or pattern.confidence < 0.7:
            return  # No confident pattern

        if pattern.pattern_type in ["sequential", "strided"]:
            # Prefetch ahead
            await self._prefetch_sequential(key, offset, pattern.stride)

    async def _prefetch_sequential(
        self, base_key: str, current_offset: int, stride: int
    ) -> None:
        """Prefetch data for sequential access pattern."""
        if not self.data_loader:
            return

        # Determine prefetch range
        distance = self.predictive_config.prefetch_distance

        for i in range(1, distance + 1):
            next_offset = current_offset + (stride * i)
            prefetch_key = f"{base_key}_{next_offset}"

            # Check if already cached
            if await self.l1.get(prefetch_key) or await self.l2.get(
                prefetch_key
            ):
                continue

            # Check if already prefetching
            if prefetch_key in self._prefetch_tasks:
                continue

            # Start prefetch task
            task = asyncio.create_task(self._prefetch_data(prefetch_key))
            self._prefetch_tasks[prefetch_key] = task

    async def _prefetch_data(self, key: str) -> None:
        """Prefetch data into cache."""
        try:
            if self.data_loader:
                value = await self.data_loader(key)
                if value is not None:
                    size = (
                        len(value) if isinstance(value, (bytes, str)) else 1024
                    )
                    await self.l2.put(key, value, size)
                    self.l2.stats.prefetches += 1
                    logger.debug(f"Prefetched: {key}")
        except Exception as e:
            logger.error(f"Prefetch error for {key}: {e}")
        finally:
            self._prefetch_tasks.pop(key, None)

    async def warm(self, keys: List[str]) -> None:
        """Warm cache with commonly accessed keys."""
        if not self.predictive_config.enable_warming or not self.data_loader:
            return

        logger.info(f"Warming cache with {len(keys)} keys")

        tasks = []
        for key in keys:
            tasks.append(self._prefetch_data(key))

        await asyncio.gather(*tasks, return_exceptions=True)

    async def clear(self) -> None:
        """Clear all cache tiers."""
        await self.l1.clear()
        await self.l2.clear()

        # Cancel prefetch tasks
        for task in self._prefetch_tasks.values():
            task.cancel()
        self._prefetch_tasks.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "l1": {
                "hits": self.l1.stats.hits,
                "misses": self.l1.stats.misses,
                "hit_rate": self.l1.stats.hit_rate,
                "evictions": self.l1.stats.evictions,
                "promotions": self.l1.stats.promotions,
                "size_bytes": self.l1.stats.total_bytes,
                "entries": len(self.l1._cache),
            },
            "l2": {
                "hits": self.l2.stats.hits,
                "misses": self.l2.stats.misses,
                "hit_rate": self.l2.stats.hit_rate,
                "evictions": self.l2.stats.evictions,
                "prefetches": self.l2.stats.prefetches,
                "size_bytes": self.l2.stats.total_bytes,
                "entries": len(self.l2._cache),
            },
            "total_hit_rate": (self.l1.stats.hits + self.l2.stats.hits)
            / max(
                self.l1.stats.hits
                + self.l1.stats.misses
                + self.l2.stats.hits
                + self.l2.stats.misses,
                1,
            ),
        }
