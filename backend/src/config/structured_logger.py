"""
============================================================================
STRUCTURED LOGGING MODULE - TovPlay Production
============================================================================
World-class structured logging with correlation IDs, user context, and
forensic capabilities for instant root cause analysis.

Features:
- JSON-formatted logs for machine parsing
- Correlation IDs to trace requests across services
- User context (who, when, what, why)
- Automatic field enrichment (timestamp, hostname, service)
- Performance metrics (duration tracking)
- Integration with Grafana Loki for centralized logging

Usage:
    from structured_logger import get_logger, log_context, log_performance

    logger = get_logger(__name__)

    @log_performance
    def my_function():
        with log_context(user_id=123, action="create_game"):
            logger.info("Creating game", game_id=456, game_name="Chess")

Deploy:
    Place this file in: backend/src/app/structured_logger.py
    Import in __init__.py: from .structured_logger import setup_logging
    Call in app factory: setup_logging(app)
============================================================================
"""

import logging
import json
import sys
import os
import time
import uuid
import traceback
from datetime import datetime, timezone
from functools import wraps
from typing import Any, Dict, Optional
from contextlib import contextmanager
from threading import local

# Thread-local storage for correlation ID and context
_thread_local = local()

# ============================================================================
# CORRELATION ID MANAGEMENT
# ============================================================================

def generate_correlation_id() -> str:
    """Generate a unique correlation ID for request tracking."""
    return str(uuid.uuid4())

def get_correlation_id() -> Optional[str]:
    """Get the current correlation ID from thread-local storage."""
    return getattr(_thread_local, 'correlation_id', None)

def set_correlation_id(correlation_id: str) -> None:
    """Set the correlation ID in thread-local storage."""
    _thread_local.correlation_id = correlation_id

def clear_correlation_id() -> None:
    """Clear the correlation ID from thread-local storage."""
    if hasattr(_thread_local, 'correlation_id'):
        delattr(_thread_local, 'correlation_id')

# ============================================================================
# CONTEXT MANAGEMENT
# ============================================================================

def get_log_context() -> Dict[str, Any]:
    """Get the current logging context from thread-local storage."""
    return getattr(_thread_local, 'log_context', {})

def set_log_context(**kwargs) -> None:
    """Set logging context in thread-local storage."""
    if not hasattr(_thread_local, 'log_context'):
        _thread_local.log_context = {}
    _thread_local.log_context.update(kwargs)

def clear_log_context() -> None:
    """Clear the logging context from thread-local storage."""
    if hasattr(_thread_local, 'log_context'):
        delattr(_thread_local, 'log_context')

@contextmanager
def log_context(**kwargs):
    """
    Context manager for scoped logging context.

    Usage:
        with log_context(user_id=123, action="create_game"):
            logger.info("Creating game")
    """
    original_context = get_log_context().copy()
    set_log_context(**kwargs)
    try:
        yield
    finally:
        _thread_local.log_context = original_context

# ============================================================================
# JSON FORMATTER
# ============================================================================

class StructuredFormatter(logging.Formatter):
    """
    JSON formatter for structured logging.

    Output format:
    {
        "timestamp": "2025-12-15T10:30:45.123456Z",
        "level": "INFO",
        "logger": "app.routes.game",
        "message": "Game created successfully",
        "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
        "user_id": 123,
        "action": "create_game",
        "game_id": 456,
        "duration_ms": 45.2,
        "hostname": "production-01",
        "service": "backend",
        "environment": "production",
        "file": "game_routes.py",
        "line": 42,
        "function": "create_game"
    }
    """

    def __init__(self, service_name: str = "backend", environment: str = None):
        super().__init__()
        self.service_name = service_name
        self.environment = environment or os.getenv("ENVIRONMENT", "development")
        self.hostname = os.getenv("HOSTNAME", os.uname().nodename)

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""

        # Base log entry
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": self.service_name,
            "environment": self.environment,
            "hostname": self.hostname,
        }

        # Add correlation ID if available
        correlation_id = get_correlation_id()
        if correlation_id:
            log_data["correlation_id"] = correlation_id

        # Add logging context
        context = get_log_context()
        if context:
            log_data.update(context)

        # Add source location
        log_data.update({
            "file": record.filename,
            "line": record.lineno,
            "function": record.funcName,
        })

        # Add extra fields from record
        if hasattr(record, 'extra_fields'):
            log_data.update(record.extra_fields)

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info)
            }

        # Add stack trace for errors
        if record.levelno >= logging.ERROR and not record.exc_info:
            log_data["stack_trace"] = traceback.format_stack()

        return json.dumps(log_data, default=str)

# ============================================================================
# STRUCTURED LOGGER ADAPTER
# ============================================================================

class StructuredLogger(logging.LoggerAdapter):
    """
    Logger adapter that adds structured fields to log records.

    Usage:
        logger = get_logger(__name__)
        logger.info("User logged in", user_id=123, ip="192.168.1.1")
    """

    def process(self, msg, kwargs):
        """Process log message and add extra fields."""
        # Extract structured fields from kwargs
        extra_fields = {}

        # Standard fields to exclude from extra
        standard_keys = {'exc_info', 'stack_info', 'stacklevel', 'extra'}

        for key, value in list(kwargs.items()):
            if key not in standard_keys:
                extra_fields[key] = kwargs.pop(key)

        # Add extra_fields to the record
        if 'extra' not in kwargs:
            kwargs['extra'] = {}
        kwargs['extra']['extra_fields'] = extra_fields

        return msg, kwargs

# ============================================================================
# LOGGER FACTORY
# ============================================================================

def get_logger(name: str) -> StructuredLogger:
    """
    Get a structured logger instance.

    Args:
        name: Logger name (typically __name__)

    Returns:
        StructuredLogger instance

    Usage:
        logger = get_logger(__name__)
        logger.info("Application started")
    """
    base_logger = logging.getLogger(name)
    return StructuredLogger(base_logger, {})

# ============================================================================
# PERFORMANCE TRACKING DECORATOR
# ============================================================================

def log_performance(func):
    """
    Decorator to automatically log function performance.

    Usage:
        @log_performance
        def slow_function():
            time.sleep(1)
            return "done"

    Logs:
        {
            "message": "Function executed",
            "function": "slow_function",
            "duration_ms": 1002.5,
            "status": "success"
        }
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        start_time = time.perf_counter()

        try:
            result = func(*args, **kwargs)
            duration_ms = (time.perf_counter() - start_time) * 1000

            logger.info(
                f"Function executed: {func.__name__}",
                function=func.__name__,
                duration_ms=round(duration_ms, 2),
                status="success"
            )

            return result

        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000

            logger.error(
                f"Function failed: {func.__name__}",
                function=func.__name__,
                duration_ms=round(duration_ms, 2),
                status="error",
                error=str(e),
                exc_info=True
            )

            raise

    return wrapper

# ============================================================================
# FLASK INTEGRATION
# ============================================================================

def setup_logging(app, level=None, enable_console=True, enable_file=True):
    """
    Setup structured logging for Flask application.

    Args:
        app: Flask application instance
        level: Logging level (default: INFO)
        enable_console: Enable console output
        enable_file: Enable file output

    Usage:
        from structured_logger import setup_logging

        app = Flask(__name__)
        setup_logging(app)
    """
    # Determine log level
    if level is None:
        level_name = os.getenv("LOG_LEVEL", "INFO")
        level = getattr(logging, level_name.upper(), logging.INFO)

    # Get environment
    environment = os.getenv("ENVIRONMENT", "development")

    # Create formatter
    formatter = StructuredFormatter(
        service_name="backend",
        environment=environment
    )

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove existing handlers
    root_logger.handlers.clear()

    # Console handler (JSON format)
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    # File handler (JSON format)
    if enable_file:
        log_dir = os.getenv("LOG_DIR", "/var/log/tovplay")
        os.makedirs(log_dir, exist_ok=True)

        file_handler = logging.handlers.RotatingFileHandler(
            filename=f"{log_dir}/backend.log",
            maxBytes=100 * 1024 * 1024,  # 100MB
            backupCount=10,
            encoding='utf-8'
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Flask request logging middleware
    @app.before_request
    def before_request():
        """Generate correlation ID for each request."""
        from flask import request, g

        # Get or generate correlation ID
        correlation_id = request.headers.get('X-Correlation-ID', generate_correlation_id())
        set_correlation_id(correlation_id)
        g.correlation_id = correlation_id
        g.request_start_time = time.perf_counter()

        # Set initial context
        set_log_context(
            correlation_id=correlation_id,
            method=request.method,
            path=request.path,
            ip=request.remote_addr,
            user_agent=request.user_agent.string if request.user_agent else None
        )

        logger = get_logger('flask.request')
        logger.info(
            "Request started",
            method=request.method,
            path=request.path,
            query_string=request.query_string.decode('utf-8') if request.query_string else None
        )

    @app.after_request
    def after_request(response):
        """Log request completion."""
        from flask import request, g

        if hasattr(g, 'request_start_time'):
            duration_ms = (time.perf_counter() - g.request_start_time) * 1000

            logger = get_logger('flask.request')
            logger.info(
                "Request completed",
                method=request.method,
                path=request.path,
                status_code=response.status_code,
                duration_ms=round(duration_ms, 2)
            )

        # Add correlation ID to response headers
        if hasattr(g, 'correlation_id'):
            response.headers['X-Correlation-ID'] = g.correlation_id

        # Clear context
        clear_correlation_id()
        clear_log_context()

        return response

    @app.teardown_request
    def teardown_request(exception=None):
        """Log request errors."""
        if exception:
            from flask import request

            logger = get_logger('flask.request')
            logger.error(
                "Request failed",
                method=request.method,
                path=request.path,
                error=str(exception),
                exc_info=True
            )

        # Ensure context is cleared
        clear_correlation_id()
        clear_log_context()

    # Log startup
    logger = get_logger('flask.app')
    logger.info(
        "Flask application initialized",
        environment=environment,
        debug=app.debug,
        log_level=logging.getLevelName(level)
    )

# ============================================================================
# USER CONTEXT HELPER
# ============================================================================

def set_user_context(user_id: Optional[int] = None, username: Optional[str] = None,
                     email: Optional[str] = None, roles: Optional[list] = None):
    """
    Set user context for logging.

    Usage:
        from structured_logger import set_user_context

        @jwt_required()
        def protected_route():
            user = get_current_user()
            set_user_context(
                user_id=user.id,
                username=user.username,
                email=user.email
            )
            # ... rest of route
    """
    context = {}
    if user_id is not None:
        context['user_id'] = user_id
    if username is not None:
        context['username'] = username
    if email is not None:
        context['email'] = email
    if roles is not None:
        context['roles'] = roles

    set_log_context(**context)

# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    # Setup logging
    import logging.handlers

    formatter = StructuredFormatter()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.DEBUG)

    # Example 1: Basic logging
    logger = get_logger("example")
    logger.info("Application started")

    # Example 2: Logging with structured fields
    logger.info("User logged in", user_id=123, username="john_doe", ip="192.168.1.1")

    # Example 3: Logging with context
    set_correlation_id(generate_correlation_id())
    with log_context(user_id=123, action="create_game"):
        logger.info("Creating game", game_id=456, game_name="Chess")
        logger.debug("Validating game rules", rule_count=10)
        logger.info("Game created successfully", duration_ms=45.2)

    # Example 4: Performance logging
    @log_performance
    def slow_function():
        time.sleep(0.1)
        return "done"

    result = slow_function()

    # Example 5: Error logging
    try:
        raise ValueError("Something went wrong")
    except Exception as e:
        logger.error("Operation failed", error_code="ERR_001", exc_info=True)

    print("\n" + "="*80)
    print("See logs above in JSON format - ready for Grafana Loki ingestion!")
    print("="*80)
