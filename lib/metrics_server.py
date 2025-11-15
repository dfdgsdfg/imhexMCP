"""
Metrics HTTP Server for Prometheus

Simple HTTP server that exposes Prometheus metrics on a configurable endpoint.
Runs in a separate thread to avoid blocking the main event loop.
"""

import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Optional

from metrics import ImHexMCPMetrics  # type: ignore[import-not-found]

logger = logging.getLogger(__name__)


class MetricsHandler(BaseHTTPRequestHandler):
    """HTTP request handler for metrics endpoint."""

    metrics: Optional[ImHexMCPMetrics] = None

    def do_GET(self) -> None:
        """Handle GET requests."""
        if self.path == "/metrics" and self.metrics:
            # Return metrics
            try:
                metrics_data = self.metrics.get_metrics()
                content_type = self.metrics.get_content_type()

                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(metrics_data)))
                self.end_headers()
                self.wfile.write(metrics_data)
            except Exception as e:
                logger.error(f"Error generating metrics: {e}")
                self.send_error(500, f"Internal Server Error: {e}")
        elif self.path == "/":
            # Root path - show simple index
            response = b"""<!DOCTYPE html>
<html>
<head>
    <title>ImHex MCP Metrics</title>
</head>
<body>
    <h1>ImHex MCP Metrics Server</h1>
    <p>Prometheus metrics are available at <a href="/metrics">/metrics</a></p>
</body>
</html>"""
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(response)))
            self.end_headers()
            self.wfile.write(response)
        else:
            self.send_error(404, "Not Found")

    def log_message(self, format: str, *args) -> None:
        """Override to use custom logger."""
        logger.debug(f"{self.client_address[0]} - {format % args}")


class MetricsServer:
    """Prometheus metrics HTTP server."""

    def __init__(
        self, metrics: ImHexMCPMetrics, host: str = "0.0.0.0", port: int = 9090
    ):
        """Initialize metrics server.

        Args:
            metrics: Metrics instance to expose
            host: Host to bind to (default: 0.0.0.0 for all interfaces)
            port: Port to bind to (default: 9090)
        """
        self.metrics = metrics
        self.host = host
        self.port = port
        self.server: Optional[HTTPServer] = None
        self.thread: Optional[threading.Thread] = None
        self._running = False

    def start(self) -> None:
        """Start the metrics server in a background thread."""
        if self._running:
            logger.warning("Metrics server already running")
            return

        # Set metrics instance on handler class
        MetricsHandler.metrics = self.metrics

        try:
            self.server = HTTPServer((self.host, self.port), MetricsHandler)
            self._running = True

            # Start server in background thread
            self.thread = threading.Thread(
                target=self._run_server, daemon=True, name="MetricsServer"
            )
            self.thread.start()

            logger.info(
                f"Metrics server started on http://{self.host}:{self.port}/metrics"
            )

        except Exception as e:
            logger.error(f"Failed to start metrics server: {e}")
            self._running = False
            raise

    def _run_server(self) -> None:
        """Run the HTTP server (called in background thread)."""
        try:
            if self.server:
                self.server.serve_forever()
        except Exception as e:
            logger.error(f"Metrics server error: {e}")
        finally:
            self._running = False

    def stop(self) -> None:
        """Stop the metrics server."""
        if not self._running:
            return

        logger.info("Stopping metrics server...")
        self._running = False

        if self.server:
            self.server.shutdown()
            self.server.server_close()
            self.server = None

        if self.thread:
            self.thread.join(timeout=5)
            self.thread = None

        logger.info("Metrics server stopped")

    def is_running(self) -> bool:
        """Check if server is running.

        Returns:
            True if server is running
        """
        return self._running
