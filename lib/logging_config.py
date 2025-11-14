"""
Structured Logging Module

Provides structured logging with JSON formatting, context management,
and multiple output handlers for the ImHex MCP server.
"""

import logging
import logging.handlers
import json
import sys
import traceback
from datetime import datetime, timezone
from typing import Any, Dict, Optional, MutableMapping
from pathlib import Path


class JSONFormatter(logging.Formatter):
    """Format log records as JSON for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON.

        Args:
            record: Log record to format

        Returns:
            JSON-formatted log string
        """
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add extra context if available
        if hasattr(record, "context"):
            log_data["context"] = record.context

        # Add exception information if present
        if record.exc_info and record.exc_info[0] is not None:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info),
            }

        # Add any custom fields from extra
        for key, value in record.__dict__.items():
            if key not in [
                "name",
                "msg",
                "args",
                "created",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "message",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "thread",
                "threadName",
                "exc_info",
                "exc_text",
                "stack_info",
                "context",
            ]:
                log_data[key] = value

        return json.dumps(log_data)


class ConsoleFormatter(logging.Formatter):
    """Colored console formatter for human-readable logs."""

    # ANSI color codes
    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record with colors for console.

        Args:
            record: Log record to format

        Returns:
            Colored log string
        """
        color = self.COLORS.get(record.levelname, "")
        reset = self.RESET

        # Format timestamp
        timestamp = datetime.fromtimestamp(record.created).strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        # Build message
        message = f"{color} [{record.levelname: 8s}] {reset}  {timestamp}  - {
            record.name}  - {record.getMessage()} "

        # Add context if available
        if hasattr(record, "context"):
            message += f" | Context: {json.dumps(record.context)}"

        # Add exception if present
        if record.exc_info:
            message += "\n" + "".join(traceback.format_exception(*record.exc_info))

        return message


def setup_logging(
    name: str = "imhex_mcp",
    level: str = "INFO",
    log_dir: Optional[Path] = None,
    console: bool = True,
    json_output: bool = False,
) -> logging.Logger:
    """
    Setup structured logging with multiple handlers.

    Args:
        name: Logger name
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory for log files (None to disable file logging)
        console: Enable console logging
        json_output: Use JSON formatting for console (default: human-readable)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    logger.handlers = []  # Clear existing handlers

    # Console handler
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)

        if json_output:
            console_handler.setFormatter(JSONFormatter())
        else:
            console_handler.setFormatter(ConsoleFormatter())

        logger.addHandler(console_handler)

    # File handler (JSON formatted)
    if log_dir:
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)

        # Main log file with rotation
        file_handler = logging.handlers.RotatingFileHandler(
            log_dir / f"{name}.log",
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(JSONFormatter())
        logger.addHandler(file_handler)

        # Error log file (errors and above)
        error_handler = logging.handlers.RotatingFileHandler(
            log_dir / f"{name}_errors.log",
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(JSONFormatter())
        logger.addHandler(error_handler)

    return logger


class LoggerAdapter(logging.LoggerAdapter):
    """Logger adapter that adds context to all log records."""

    def process(
        self, msg: str, kwargs: MutableMapping[str, Any]
    ) -> tuple[str, MutableMapping[str, Any]]:
        """
        Add context to log record.

        Args:
            msg: Log message
            kwargs: Additional keyword arguments

        Returns:
            Processed message and kwargs
        """
        # Merge adapter context with extra context
        extra = kwargs.get("extra", {})
        adapter_context = dict(self.extra) if self.extra else {}
        extra_context = extra.get(
            "context", {}) if isinstance(
            extra, dict) else {}
        extra["context"] = {**adapter_context, **extra_context}
        kwargs["extra"] = extra
        return msg, kwargs


def get_logger(
    name: str, context: Optional[Dict[str, Any]] = None
) -> logging.LoggerAdapter:
    """
    Get a logger with optional context.

    Args:
        name: Logger name (e.g., "security", "caching")
        context: Optional context dict to add to all log messages

    Returns:
        Logger adapter with context
    """
    logger = logging.getLogger(f"imhex_mcp.{name}")
    return LoggerAdapter(logger, context or {})


# Example usage and module-level logger
if __name__ == "__main__":
    # Setup root logger
    root_logger = setup_logging(
        name="imhex_mcp", level="DEBUG", log_dir=Path("/tmp/imhex_mcp_logs")
    )

    # Get module loggers with context
    security_logger = get_logger("security", {"component": "security_manager"})
    cache_logger = get_logger("caching", {"component": "cache_manager"})

    # Test different log levels
    root_logger.debug("Debug message")
    root_logger.info("Info message")
    root_logger.warning("Warning message")
    root_logger.error("Error message")

    # Test with context
    security_logger.info("Rate limit check", extra={"client_id": "client_123"})
    cache_logger.info("Cache hit", extra={"key": "data_0x1000", "size": 1024})

    # Test exception logging
    try:
        raise ValueError("Test exception")
    except Exception:
        root_logger.exception("An error occurred")

    print("\nLogs written to /tmp/imhex_mcp_logs/")
