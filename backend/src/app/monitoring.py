"""
Backend Monitoring and Observability
Production-ready monitoring, logging, and metrics collection
"""

import functools
import json
import logging
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import psutil
from flask import Flask, g, jsonify, request
from werkzeug.exceptions import HTTPException


class MonitoringService:
    """Centralized monitoring service for the backend application."""

    def __init__(self, app: Optional[Flask] = None):
        self.app = app
        self.metrics = {}
        self.error_count = 0
        self.request_count = 0
        self.active_connections = 0
        self.start_time = datetime.now(timezone.utc)

        # Setup structured logging
        self.logger = self._setup_logging()

        if app:
            self.init_app(app)

    def init_app(self, app: Flask):
        """Initialize monitoring with Flask app."""
        self.app = app

        # Register middleware
        app.before_request(self._before_request)
        app.after_request(self._after_request)
        app.teardown_appcontext(self._teardown_request)

        # Register error handlers
        self._register_error_handlers(app)

        # Register monitoring endpoints
        self._register_monitoring_endpoints(app)

        # Start background metrics collection
        self._start_background_monitoring()

    def _setup_logging(self) -> logging.Logger:
        """Setup structured logging."""
        logger = logging.getLogger("tovplay_monitoring")
        logger.setLevel(logging.INFO)

        # Create formatter for structured logs
        formatter = logging.Formatter(
            json.dumps(
                {
                    "timestamp": "%(asctime)s",
                    "level": "%(levelname)s",
                    "logger": "%(name)s",
                    "message": "%(message)s",
                    "module": "%(module)s",
                    "function": "%(funcName)s",
                    "line": "%(lineno)d",
                }
            )
        )

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        return logger

    def _before_request(self):
        """Before each request."""
        g.start_time = time.time()
        g.request_id = self._generate_request_id()

        self.request_count += 1
        self.active_connections += 1

        # Log request
        self._log_request_start()

    def _after_request(self, response):
        """After each request."""
        duration = time.time() - g.start_time if hasattr(g, "start_time") else 0

        # Track metrics
        self._track_request_metrics(response.status_code, duration)

        # Log response
        self._log_request_end(response, duration)

        # Add monitoring headers
        response.headers["X-Request-ID"] = getattr(g, "request_id", "unknown")
        response.headers["X-Response-Time"] = f"{duration:.3f}s"

        return response

    def _teardown_request(self, exception=None):
        """Cleanup after request."""
        self.active_connections = max(0, self.active_connections - 1)

        if exception:
            self._track_error(exception)

    def _generate_request_id(self) -> str:
        """Generate unique request ID."""
        import uuid

        return str(uuid.uuid4())[:8]

    def _log_request_start(self):
        """Log request start."""
        self.logger.info(
            "Request started",
            extra={
                "request_id": getattr(g, "request_id", "unknown"),
                "method": request.method,
                "path": request.path,
                "remote_addr": request.remote_addr,
                "user_agent": request.user_agent.string,
                "content_length": request.content_length,
            },
        )

    def _log_request_end(self, response, duration: float):
        """Log request completion."""
        self.logger.info(
            "Request completed",
            extra={
                "request_id": getattr(g, "request_id", "unknown"),
                "status_code": response.status_code,
                "duration_ms": round(duration * 1000, 2),
                "content_length": response.content_length,
                "method": request.method,
                "path": request.path,
            },
        )

    def _track_request_metrics(self, status_code: int, duration: float):
        """Track request metrics."""
        # Response time buckets
        if duration < 0.1:
            bucket = "fast"
        elif duration < 0.5:
            bucket = "medium"
        elif duration < 2.0:
            bucket = "slow"
        else:
            bucket = "very_slow"

        self._increment_metric(f"requests_by_duration_{bucket}")
        self._increment_metric(f"requests_by_status_{status_code // 100}xx")

        # Track average response time
        self._update_average_metric("avg_response_time", duration)

        # Track slow requests
        if duration > 1.0:
            self.logger.warning(
                "Slow request detected",
                extra={
                    "request_id": getattr(g, "request_id", "unknown"),
                    "duration_ms": round(duration * 1000, 2),
                    "path": request.path,
                },
            )

    def _track_error(self, error: Exception):
        """Track application errors."""
        self.error_count += 1
        self._increment_metric("errors_total")

        error_data = {
            "request_id": getattr(g, "request_id", "unknown"),
            "error_type": type(error).__name__,
            "error_message": str(error),
            "path": getattr(request, "path", "unknown"),
            "method": getattr(request, "method", "unknown"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        self.logger.error("Application error", extra=error_data)

    def _register_error_handlers(self, app: Flask):
        """Register global error handlers."""

        @app.errorhandler(Exception)
        def handle_exception(error):
            """Handle all exceptions."""
            self._track_error(error)

            # Return JSON error for API endpoints
            if request.path.startswith("/api/"):
                if isinstance(error, HTTPException):
                    return (
                        jsonify(
                            {
                                "error": error.description,
                                "status_code": error.code,
                                "request_id": getattr(g, "request_id", "unknown"),
                            }
                        ),
                        error.code,
                    )
                else:
                    return (
                        jsonify(
                            {
                                "error": "Internal server error",
                                "status_code": 500,
                                "request_id": getattr(g, "request_id", "unknown"),
                            }
                        ),
                        500,
                    )

            # Re-raise for non-API endpoints
            raise error

    def _register_monitoring_endpoints(self, app: Flask):
        """Register monitoring and health check endpoints."""

        @app.route("/api/health")
        def health_check():
            """Health check endpoint."""
            health_data = self.get_health_metrics()

            # Determine health status
            is_healthy = (
                health_data["memory"]["usage_percent"] < 90
                and health_data["disk"]["usage_percent"] < 95
                and health_data["error_rate"] < 0.05
            )

            status_code = 200 if is_healthy else 503
            return (
                jsonify(
                    {
                        "status": "healthy" if is_healthy else "unhealthy",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "checks": health_data,
                    }
                ),
                status_code,
            )

        @app.route("/api/metrics")
        def metrics_endpoint():
            """Prometheus-style metrics endpoint."""
            return self._format_prometheus_metrics()

        @app.route("/api/monitoring/errors", methods=["POST"])
        def log_frontend_error():
            """Log frontend errors."""
            try:
                error_data = request.get_json()
                self.logger.error("Frontend error", extra={"source": "frontend", **error_data})
                return jsonify({"status": "logged"}), 200
            except Exception as e:
                self.logger.error(f"Failed to log frontend error: {e}")
                return jsonify({"error": "Failed to log error"}), 500

        @app.route("/api/monitoring/metrics", methods=["POST"])
        def log_frontend_metric():
            """Log frontend metrics."""
            try:
                metric_data = request.get_json()
                self._increment_metric(f"frontend_{metric_data['name']}")
                return jsonify({"status": "logged"}), 200
            except Exception as e:
                return jsonify({"error": "Failed to log metric"}), 500

    def get_health_metrics(self) -> Dict[str, Any]:
        """Get comprehensive health metrics."""
        # System metrics
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        cpu_percent = psutil.cpu_percent(interval=1)

        # Application metrics
        uptime = datetime.now(timezone.utc) - self.start_time
        error_rate = self.error_count / max(self.request_count, 1)

        return {
            "uptime_seconds": uptime.total_seconds(),
            "request_count": self.request_count,
            "error_count": self.error_count,
            "error_rate": error_rate,
            "active_connections": self.active_connections,
            "memory": {
                "total_mb": round(memory.total / 1024 / 1024, 2),
                "available_mb": round(memory.available / 1024 / 1024, 2),
                "usage_percent": memory.percent,
            },
            "disk": {
                "total_gb": round(disk.total / 1024 / 1024 / 1024, 2),
                "free_gb": round(disk.free / 1024 / 1024 / 1024, 2),
                "usage_percent": (disk.used / disk.total) * 100,
            },
            "cpu": {"usage_percent": cpu_percent},
            "custom_metrics": dict(self.metrics),
        }

    def _start_background_monitoring(self):
        """Start background thread for periodic monitoring."""

        def monitor_loop():
            while True:
                try:
                    # System resource monitoring
                    memory = psutil.virtual_memory()
                    self._update_gauge_metric("system_memory_usage_percent", memory.percent)

                    cpu = psutil.cpu_percent(interval=None)
                    self._update_gauge_metric("system_cpu_usage_percent", cpu)

                    # Log system metrics periodically
                    if int(time.time()) % 300 == 0:  # Every 5 minutes
                        self.logger.info(
                            "System metrics",
                            extra={
                                "memory_usage_percent": memory.percent,
                                "cpu_usage_percent": cpu,
                                "active_connections": self.active_connections,
                                "request_count": self.request_count,
                            },
                        )

                    time.sleep(10)  # Check every 10 seconds

                except Exception as e:
                    self.logger.error(f"Background monitoring error: {e}")
                    time.sleep(30)  # Wait longer on error

        thread = threading.Thread(target=monitor_loop, daemon=True)
        thread.start()

    def _increment_metric(self, name: str, value: float = 1):
        """Increment a counter metric."""
        self.metrics[name] = self.metrics.get(name, 0) + value

    def _update_gauge_metric(self, name: str, value: float):
        """Update a gauge metric."""
        self.metrics[name] = value

    def _update_average_metric(self, name: str, value: float):
        """Update a rolling average metric."""
        current = self.metrics.get(name, {"sum": 0, "count": 0})
        current["sum"] += value
        current["count"] += 1
        current["average"] = current["sum"] / current["count"]
        self.metrics[name] = current

    def _format_prometheus_metrics(self) -> str:
        """Format metrics in Prometheus format."""
        lines = []

        for name, value in self.metrics.items():
            if isinstance(value, dict):
                if "average" in value:
                    lines.append(f"# TYPE {name}_average gauge")
                    lines.append(f"{name}_average {value['average']}")
                    lines.append(f"# TYPE {name}_count counter")
                    lines.append(f"{name}_count {value['count']}")
            else:
                metric_type = "counter" if "total" in name or "count" in name else "gauge"
                lines.append(f"# TYPE {name} {metric_type}")
                lines.append(f"{name} {value}")

        return "\n".join(lines) + "\n"


def monitor_function(func_name: Optional[str] = None):
    """Decorator to monitor function execution."""

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            name = func_name or f"{func.__module__}.{func.__name__}"
            start_time = time.time()

            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time

                # Log successful execution
                logging.getLogger("tovplay_monitoring").info(
                    f"Function executed: {name}",
                    extra={"function": name, "duration_ms": round(duration * 1000, 2)},
                )

                return result

            except Exception as e:
                duration = time.time() - start_time

                # Log failed execution
                logging.getLogger("tovplay_monitoring").error(
                    f"Function failed: {name}",
                    extra={
                        "function": name,
                        "duration_ms": round(duration * 1000, 2),
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                )
                raise

        return wrapper

    return decorator


# Global monitoring instance
monitoring_service = MonitoringService()
