"""
Tests for Structured Logging Module

Tests logging configuration, formatters, and context management.
"""

import logging
import json
import tempfile
from pathlib import Path
import pytest
from logging_config import (
    JSONFormatter,
    ConsoleFormatter,
    setup_logging,
    get_logger,
)


class TestJSONFormatter:
    """Tests for JSON log formatter."""

    def test_basic_formatting(self):
        """Test basic log record formatting."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        output = formatter.format(record)
        data = json.loads(output)

        assert data["level"] == "INFO"
        assert data["message"] == "Test message"
        assert data["logger"] == "test"
        assert data["module"] == "test"
        assert data["line"] == 10
        assert "timestamp" in data

    def test_context_formatting(self):
        """Test log record with context."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.context = {"client_id": "client_123", "request_id": "req_456"}

        output = formatter.format(record)
        data = json.loads(output)

        assert "context" in data
        assert data["context"]["client_id"] == "client_123"
        assert data["context"]["request_id"] == "req_456"

    def test_exception_formatting(self):
        """Test log record with exception."""
        formatter = JSONFormatter()

        try:
            raise ValueError("Test error")
        except ValueError:
            import sys

            record = logging.LogRecord(
                name="test",
                level=logging.ERROR,
                pathname="test.py",
                lineno=10,
                msg="Error occurred",
                args=(),
                exc_info=sys.exc_info(),
            )

        output = formatter.format(record)
        data = json.loads(output)

        assert "exception" in data
        assert data["exception"]["type"] == "ValueError"
        assert data["exception"]["message"] == "Test error"
        assert "traceback" in data["exception"]


class TestConsoleFormatter:
    """Tests for console log formatter."""

    def test_basic_formatting(self):
        """Test basic console formatting."""
        formatter = ConsoleFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        output = formatter.format(record)

        assert "INFO" in output
        assert "test" in output
        assert "Test message" in output

    def test_colored_output(self):
        """Test that color codes are applied."""
        formatter = ConsoleFormatter()

        # Test different log levels
        for level_name in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            record = logging.LogRecord(
                name="test",
                level=getattr(logging, level_name),
                pathname="test.py",
                lineno=10,
                msg="Test message",
                args=(),
                exc_info=None,
            )

            output = formatter.format(record)
            # Check that ANSI codes are present (color + reset)
            assert "\033[" in output


class TestLoggingSetup:
    """Tests for logging setup."""

    def test_console_logging(self):
        """Test console logging setup."""
        logger = setup_logging(
            name="test_console", level="DEBUG", console=True, json_output=False
        )

        assert logger.level == logging.DEBUG
        assert len(logger.handlers) >= 1
        assert any(
            isinstance(h, logging.StreamHandler) for h in logger.handlers
        )

    def test_file_logging(self):
        """Test file logging setup."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = setup_logging(
                name="test_file",
                level="INFO",
                log_dir=Path(tmpdir),
                console=False,
            )

            assert len(logger.handlers) == 2  # Main log + error log

            # Check log files were created
            log_files = list(Path(tmpdir).glob("*.log"))
            assert len(log_files) == 2

            # Test writing logs
            logger.info("Test message")
            logger.error("Test error")

            # Check main log file has content
            main_log = Path(tmpdir) / "test_file.log"
            assert main_log.exists()
            assert main_log.stat().st_size > 0

    def test_json_console_output(self):
        """Test JSON output to console."""
        logger = setup_logging(
            name="test_json", level="INFO", console=True, json_output=True
        )

        # Find the console handler
        console_handler = None
        for handler in logger.handlers:
            if isinstance(handler, logging.StreamHandler):
                console_handler = handler
                break

        assert console_handler is not None
        assert isinstance(console_handler.formatter, JSONFormatter)


class TestLoggerAdapter:
    """Tests for logger adapter with context."""

    def test_get_logger_with_context(self):
        """Test getting logger with context."""
        setup_logging(name="imhex_mcp", level="INFO", console=False)
        logger = get_logger("security", {"component": "rate_limiter"})

        assert logger.extra["component"] == "rate_limiter"

    def test_logger_adds_context(self, caplog):
        """Test that logger adds context to log records."""
        setup_logging(name="imhex_mcp", level="DEBUG", console=True)
        logger = get_logger("test", {"session_id": "sess_123"})

        with caplog.at_level(logging.INFO):
            logger.info("Test message", extra={"user_id": "user_456"})

        # Context should be merged
        record = caplog.records[0]
        assert hasattr(record, "context")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
