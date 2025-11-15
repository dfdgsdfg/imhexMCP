"""
Comprehensive tests for ConnectionPool

Tests cover:
- ConnectionStats calculation
- PooledConnection lifecycle
- Pool initialization and configuration
- Connection acquire/release
- Health checking
- Idle connection cleanup
- Pool statistics
- Context manager usage
- Error handling
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from connection_pool import (
    ConnectionStats,
    PooledConnection,
    ConnectionPool,
)
import sys
from pathlib import Path

# Add lib to path
sys.path.insert(0, str(Path(__file__).parent))


class TestConnectionStats:
    """Test ConnectionStats dataclass and methods."""

    def test_stats_initialization(self):
        """Test default initialization of stats."""
        stats = ConnectionStats()

        assert stats.total_created == 0
        assert stats.total_reused == 0
        assert stats.total_closed == 0
        assert stats.total_failed == 0
        assert stats.active_connections == 0
        assert stats.idle_connections == 0

    def test_stats_custom_values(self):
        """Test stats with custom values."""
        stats = ConnectionStats(
            total_created=10,
            total_reused=20,
            total_closed=5,
            total_failed=2,
            active_connections=3,
            idle_connections=7,
        )

        assert stats.total_created == 10
        assert stats.total_reused == 20

    def test_reuse_rate_no_connections(self):
        """Test reuse rate with no connections."""
        stats = ConnectionStats()

        assert stats.reuse_rate() == 0.0

    def test_reuse_rate_with_connections(self):
        """Test reuse rate calculation."""
        stats = ConnectionStats(total_created=10, total_reused=20)

        # 20 / (10 + 20) * 100 = 66.67%
        assert abs(stats.reuse_rate() - 66.67) < 0.01

    def test_reuse_rate_only_created(self):
        """Test reuse rate with only created connections."""
        stats = ConnectionStats(total_created=10, total_reused=0)

        assert stats.reuse_rate() == 0.0

    def test_reuse_rate_only_reused(self):
        """Test reuse rate with only reused connections."""
        stats = ConnectionStats(total_created=0, total_reused=10)

        assert stats.reuse_rate() == 100.0


class TestPooledConnection:
    """Test PooledConnection wrapper class."""

    @pytest.fixture
    def mock_connection(self):
        """Create mock reader/writer."""
        reader = AsyncMock(spec=asyncio.StreamReader)
        writer = MagicMock(spec=asyncio.StreamWriter)
        writer.is_closing.return_value = False
        writer.close = Mock()
        writer.wait_closed = AsyncMock()
        return reader, writer

    def test_connection_initialization(self, mock_connection):
        """Test PooledConnection initialization."""
        reader, writer = mock_connection
        conn = PooledConnection(reader=reader, writer=writer)

        assert conn.reader == reader
        assert conn.writer == writer
        assert conn.use_count == 0
        assert conn.is_healthy is True
        assert conn.created_at > 0
        assert conn.last_used > 0

    def test_mark_used(self, mock_connection):
        """Test marking connection as used."""
        reader, writer = mock_connection
        conn = PooledConnection(reader=reader, writer=writer)

        initial_last_used = conn.last_used
        initial_use_count = conn.use_count

        time.sleep(0.01)  # Small delay
        conn.mark_used()

        assert conn.last_used > initial_last_used
        assert conn.use_count == initial_use_count + 1

    def test_age_calculation(self, mock_connection):
        """Test connection age calculation."""
        reader, writer = mock_connection
        conn = PooledConnection(reader=reader, writer=writer)

        time.sleep(0.1)
        age = conn.age()

        assert age >= 0.1
        assert age < 1.0  # Sanity check

    def test_idle_time_calculation(self, mock_connection):
        """Test idle time calculation."""
        reader, writer = mock_connection
        conn = PooledConnection(reader=reader, writer=writer)

        time.sleep(0.1)
        idle = conn.idle_time()

        assert idle >= 0.1
        assert idle < 1.0

    def test_idle_time_after_use(self, mock_connection):
        """Test idle time resets after use."""
        reader, writer = mock_connection
        conn = PooledConnection(reader=reader, writer=writer)

        time.sleep(0.1)
        conn.mark_used()

        idle = conn.idle_time()
        assert idle < 0.1  # Should be very small after mark_used

    @pytest.mark.asyncio
    async def test_close_connection(self, mock_connection):
        """Test closing a connection."""
        reader, writer = mock_connection
        conn = PooledConnection(reader=reader, writer=writer)

        await conn.close()

        writer.close.assert_called_once()
        writer.wait_closed.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_already_closing(self, mock_connection):
        """Test closing connection that's already closing."""
        reader, writer = mock_connection
        writer.is_closing.return_value = True
        conn = PooledConnection(reader=reader, writer=writer)

        await conn.close()

        # Should not call close if already closing
        writer.close.assert_not_called()


class TestConnectionPoolInitialization:
    """Test ConnectionPool initialization."""

    def test_pool_default_initialization(self):
        """Test pool with default parameters."""
        pool = ConnectionPool()

        assert pool.host == "localhost"
        assert pool.port == 31337
        assert pool.max_size == 10
        assert pool.min_size == 2
        assert pool.connection_timeout == 30

    def test_pool_custom_initialization(self):
        """Test pool with custom parameters."""
        pool = ConnectionPool(
            host="192.168.1.100",
            port=12345,
            max_size=20,
            min_size=5,
            connection_timeout=60,
            max_idle_time=120,
            health_check_interval=10,
        )

        assert pool.host == "192.168.1.100"
        assert pool.port == 12345
        assert pool.max_size == 20
        assert pool.min_size == 5
        assert pool.connection_timeout == 60

    def test_pool_initial_state(self):
        """Test pool initial state."""
        pool = ConnectionPool()

        assert len(pool._idle) == 0
        assert len(pool._active) == 0
        assert pool._stats.total_created == 0


class TestConnectionPoolAcquireRelease:
    """Test connection acquire and release."""

    @pytest.mark.asyncio
    async def test_acquire_creates_connection(self):
        """Test that acquire creates a connection if pool is empty."""
        pool = ConnectionPool(min_size=0)

        with patch.object(pool, "_create_connection") as mock_create:
            mock_conn = Mock(spec=PooledConnection)
            mock_create.return_value = mock_conn

            conn = await pool.acquire()

            assert conn == mock_conn
            mock_create.assert_called_once()
            assert conn in pool._active

    @pytest.mark.asyncio
    async def test_acquire_reuses_idle_connection(self):
        """Test that acquire reuses idle connections."""
        pool = ConnectionPool()

        # Create mock connection and add to idle pool
        mock_conn = Mock(spec=PooledConnection)
        mock_conn.is_healthy = True
        pool._idle.append(mock_conn)

        with patch.object(pool, "_is_healthy") as mock_health:
            mock_health.return_value = True

            conn = await pool.acquire()

            assert conn == mock_conn
            assert len(pool._idle) == 0
            assert mock_conn in pool._active

    @pytest.mark.asyncio
    async def test_release_healthy_connection(self):
        """Test releasing a healthy connection."""
        pool = ConnectionPool()

        mock_conn = Mock(spec=PooledConnection)
        mock_conn.is_healthy = True
        pool._active.add(mock_conn)

        await pool.release(mock_conn, healthy=True)

        assert mock_conn not in pool._active
        assert mock_conn in pool._idle

    @pytest.mark.asyncio
    async def test_release_unhealthy_connection(self):
        """Test releasing an unhealthy connection."""
        pool = ConnectionPool()

        mock_conn = Mock(spec=PooledConnection)
        mock_conn.close = AsyncMock()
        pool._active.add(mock_conn)

        await pool.release(mock_conn, healthy=False)

        assert mock_conn not in pool._active
        assert mock_conn not in pool._idle
        mock_conn.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_release_unknown_connection(self):
        """Test releasing a connection not in active set."""
        pool = ConnectionPool()

        mock_conn = Mock(spec=PooledConnection)
        mock_conn.close = AsyncMock()

        # Should handle gracefully
        await pool.release(mock_conn)

        # Connection should be closed
        mock_conn.close.assert_called_once()


class TestConnectionPoolHealthChecks:
    """Test health checking functionality."""

    @pytest.mark.asyncio
    async def test_healthy_connection_check(self):
        """Test checking a healthy connection."""
        pool = ConnectionPool()

        reader = AsyncMock(spec=asyncio.StreamReader)
        writer = MagicMock(spec=asyncio.StreamWriter)
        writer.is_closing.return_value = False

        conn = PooledConnection(reader=reader, writer=writer)

        is_healthy = await pool._is_healthy(conn)

        assert is_healthy is True

    @pytest.mark.asyncio
    async def test_unhealthy_closing_connection(self):
        """Test checking a connection that's closing."""
        pool = ConnectionPool()

        reader = AsyncMock(spec=asyncio.StreamReader)
        writer = MagicMock(spec=asyncio.StreamWriter)
        writer.is_closing.return_value = True

        conn = PooledConnection(reader=reader, writer=writer)

        is_healthy = await pool._is_healthy(conn)

        assert is_healthy is False


class TestConnectionPoolCleanup:
    """Test idle connection cleanup."""

    @pytest.mark.asyncio
    async def test_cleanup_old_idle_connections(self):
        """Test cleanup of old idle connections."""
        pool = ConnectionPool(max_idle_time=0.1)  # 100ms

        # Create old connection
        mock_conn = Mock(spec=PooledConnection)
        mock_conn.idle_time.return_value = 0.2  # 200ms (over limit)
        mock_conn.close = AsyncMock()
        pool._idle.append(mock_conn)

        await pool._cleanup_idle_connections()

        # Old connection should be removed
        assert len(pool._idle) == 0
        mock_conn.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_keeps_recent_connections(self):
        """Test that recent connections are kept."""
        pool = ConnectionPool(max_idle_time=10.0)  # 10 seconds

        mock_conn = Mock(spec=PooledConnection)
        mock_conn.idle_time.return_value = 0.1  # 100ms (under limit)
        pool._idle.append(mock_conn)

        await pool._cleanup_idle_connections()

        # Recent connection should be kept
        assert mock_conn in pool._idle


class TestConnectionPoolStatistics:
    """Test pool statistics."""

    def test_get_stats(self):
        """Test retrieving pool statistics."""
        pool = ConnectionPool()

        # Add some mock connections
        pool._active.add(Mock())
        pool._active.add(Mock())
        pool._idle.append(Mock())
        pool._idle.append(Mock())
        pool._idle.append(Mock())

        pool._stats.total_created = 10
        pool._stats.total_reused = 20
        pool._stats.total_closed = 5

        stats = pool.get_stats()

        assert stats["active"] == 2
        assert stats["idle"] == 3
        assert stats["total"] == 5
        assert stats["created"] == 10
        assert stats["reused"] == 20
        assert stats["closed"] == 5

    def test_empty_pool_stats(self):
        """Test statistics of empty pool."""
        pool = ConnectionPool()

        stats = pool.get_stats()

        assert stats["active"] == 0
        assert stats["idle"] == 0
        assert stats["total"] == 0


class TestConnectionPoolContextManager:
    """Test context manager usage."""

    @pytest.mark.asyncio
    async def test_context_manager_enter(self):
        """Test async context manager entry."""
        pool = ConnectionPool()

        with patch.object(pool, "initialize") as mock_init:
            async with pool as p:
                assert p is pool
                mock_init.assert_called_once()

    @pytest.mark.asyncio
    async def test_context_manager_exit(self):
        """Test async context manager exit."""
        pool = ConnectionPool()

        with patch.object(pool, "close") as mock_close:
            with patch.object(pool, "initialize"):
                async with pool:
                    pass

                mock_close.assert_called_once()

    @pytest.mark.asyncio
    async def test_context_manager_exception(self):
        """Test exception handling in context manager."""
        pool = ConnectionPool()

        with patch.object(pool, "close") as mock_close:
            with patch.object(pool, "initialize"):
                with pytest.raises(ValueError):
                    async with pool:
                        raise ValueError("Test error")

                # Close should still be called
                mock_close.assert_called_once()


class TestConnectionPoolClose:
    """Test pool closing."""

    @pytest.mark.asyncio
    async def test_close_pool(self):
        """Test closing the pool."""
        pool = ConnectionPool()

        # Add mock connections
        mock_active = Mock(spec=PooledConnection)
        mock_active.close = AsyncMock()
        mock_idle = Mock(spec=PooledConnection)
        mock_idle.close = AsyncMock()

        pool._active.add(mock_active)
        pool._idle.append(mock_idle)

        await pool.close()

        # All connections should be closed
        mock_active.close.assert_called_once()
        mock_idle.close.assert_called_once()
        assert len(pool._active) == 0
        assert len(pool._idle) == 0

    @pytest.mark.asyncio
    async def test_close_empty_pool(self):
        """Test closing an empty pool."""
        pool = ConnectionPool()

        # Should not raise exception
        await pool.close()

        assert len(pool._active) == 0
        assert len(pool._idle) == 0


class TestConnectionPoolEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_acquire_with_max_size_limit(self):
        """Test acquire when pool is at max size."""
        pool = ConnectionPool(max_size=2)

        # Fill the pool
        with patch.object(pool, "_create_connection") as mock_create:
            mock_create.side_effect = [
                Mock(spec=PooledConnection),
                Mock(spec=PooledConnection),
            ]

            conn1 = await pool.acquire()
            conn2 = await pool.acquire()

            assert len(pool._active) == 2

    @pytest.mark.asyncio
    async def test_multiple_acquire_release_cycles(self):
        """Test multiple acquire/release cycles."""
        pool = ConnectionPool()

        with patch.object(pool, "_create_connection") as mock_create:
            mock_conn = Mock(spec=PooledConnection)
            mock_conn.is_healthy = True
            mock_create.return_value = mock_conn

            # First cycle
            conn1 = await pool.acquire()
            await pool.release(conn1, healthy=True)

            # Should reuse same connection
            with patch.object(pool, "_is_healthy") as mock_health:
                mock_health.return_value = True
                conn2 = await pool.acquire()

                assert conn2 == conn1
                # Should only create once
                assert mock_create.call_count == 1
