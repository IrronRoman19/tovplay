"""
Comprehensive logging configuration for TovPlay backend.
Provides structured logging with different levels, formatters, and handlers.
"""

import os
import logging
import logging.config
from datetime import datetime
from pathlib import Path
import json


def get_log_level(env_level=None):
    """Get appropriate log level based on environment."""
    env_level = env_level or os.getenv('LOG_LEVEL', '').upper()
    env = os.getenv('FLASK_ENV', 'development').lower()
    
    # Environment-specific defaults
    default_levels = {
        'production': 'WARNING',
        'staging': 'INFO', 
        'development': 'DEBUG',
        'testing': 'ERROR'
    }
    
    # Use explicit level if provided, otherwise use environment default
    level_str = env_level or default_levels.get(env, 'INFO')
    
    # Convert string to logging level
    level_map = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL
    }
    
    return level_map.get(level_str, logging.INFO)


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record):
        log_entry = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'thread': record.thread,
            'thread_name': record.threadName,
            'process': record.process
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields if present
        if hasattr(record, 'user_id'):
            log_entry['user_id'] = record.user_id
        if hasattr(record, 'request_id'):
            log_entry['request_id'] = record.request_id
        if hasattr(record, 'ip_address'):
            log_entry['ip_address'] = record.ip_address
        if hasattr(record, 'endpoint'):
            log_entry['endpoint'] = record.endpoint
        if hasattr(record, 'method'):
            log_entry['method'] = record.method
        if hasattr(record, 'status_code'):
            log_entry['status_code'] = record.status_code
        if hasattr(record, 'response_time'):
            log_entry['response_time'] = record.response_time
        if hasattr(record, 'database_query_time'):
            log_entry['database_query_time'] = record.database_query_time
        
        return json.dumps(log_entry, separators=(',', ':'))


class ColoredFormatter(logging.Formatter):
    """Colored formatter for console output in development."""
    
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'        # Reset
    }
    
    def format(self, record):
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset = self.COLORS['RESET']
        
        # Format timestamp
        timestamp = datetime.fromtimestamp(record.created).strftime('%H:%M:%S')
        
        # Create colored level name
        colored_level = f"{color}{record.levelname:8}{reset}"
        
        # Format message
        message = super().format(record)
        
        return f"{timestamp} | {colored_level} | {record.name:20} | {message}"


def ensure_log_directory():
    """Ensure log directory exists."""
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)
    return log_dir


def create_logging_config():
    """Create comprehensive logging configuration."""
    env = os.getenv('FLASK_ENV', 'development').lower()
    log_level = get_log_level()
    log_dir = ensure_log_directory()
    
    # Base configuration
    config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'json': {
                '()': JSONFormatter
            },
            'colored': {
                '()': ColoredFormatter,
                'format': '%(message)s'
            },
            'detailed': {
                'format': '%(asctime)s | %(levelname)-8s | %(name)-20s | %(funcName)s:%(lineno)d | %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S'
            },
            'simple': {
                'format': '%(asctime)s | %(levelname)s | %(message)s',
                'datefmt': '%H:%M:%S'
            }
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'level': 'DEBUG',
                'formatter': 'colored' if env == 'development' else 'simple',
                'stream': 'ext://sys.stdout'
            },
            'file_all': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': 'DEBUG',
                'formatter': 'json' if env == 'production' else 'detailed',
                'filename': str(log_dir / 'tovplay.log'),
                'maxBytes': 10485760,  # 10MB
                'backupCount': 5,
                'encoding': 'utf-8'
            },
            'file_errors': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': 'ERROR',
                'formatter': 'detailed',
                'filename': str(log_dir / 'errors.log'),
                'maxBytes': 10485760,  # 10MB
                'backupCount': 10,
                'encoding': 'utf-8'
            },
            'file_database': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': 'INFO',
                'formatter': 'json' if env == 'production' else 'detailed',
                'filename': str(log_dir / 'database.log'),
                'maxBytes': 5242880,   # 5MB
                'backupCount': 5,
                'encoding': 'utf-8'
            },
            'file_api': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': 'INFO',
                'formatter': 'json' if env == 'production' else 'detailed',
                'filename': str(log_dir / 'api.log'),
                'maxBytes': 10485760,  # 10MB
                'backupCount': 5,
                'encoding': 'utf-8'
            }
        },
        'loggers': {
            'tovplay': {
                'level': log_level,
                'handlers': ['console', 'file_all'],
                'propagate': False
            },
            'tovplay.database': {
                'level': 'INFO',
                'handlers': ['file_database'],
                'propagate': True
            },
            'tovplay.api': {
                'level': 'INFO', 
                'handlers': ['file_api'],
                'propagate': True
            },
            'tovplay.auth': {
                'level': 'INFO',
                'handlers': ['console', 'file_all'],
                'propagate': False
            },
            'tovplay.errors': {
                'level': 'ERROR',
                'handlers': ['console', 'file_errors'],
                'propagate': False
            },
            'sqlalchemy.engine': {
                'level': 'WARNING' if env == 'production' else 'INFO',
                'handlers': ['file_database'],
                'propagate': False
            },
            'sqlalchemy.pool': {
                'level': 'WARNING',
                'handlers': ['file_database'],
                'propagate': False
            },
            'werkzeug': {
                'level': 'WARNING' if env == 'production' else 'INFO',
                'handlers': ['console'],
                'propagate': False
            }
        },
        'root': {
            'level': 'WARNING',
            'handlers': ['console', 'file_errors']
        }
    }
    
    # Add file handlers only in non-testing environments
    if env != 'testing':
        # Add structured logging handler for production
        if env == 'production':
            config['handlers']['structured'] = {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': 'INFO',
                'formatter': 'json',
                'filename': str(log_dir / 'structured.log'),
                'maxBytes': 20971520,  # 20MB
                'backupCount': 10,
                'encoding': 'utf-8'
            }
            config['loggers']['tovplay']['handlers'].append('structured')
    else:
        # Minimal logging for tests
        config['loggers']['tovplay']['handlers'] = ['console']
        config['handlers']['console']['level'] = 'ERROR'
    
    return config


def setup_logging(app=None):
    """Setup comprehensive logging for the application."""
    config = create_logging_config()
    logging.config.dictConfig(config)
    
    # Create application-specific loggers
    loggers = {
        'main': logging.getLogger('tovplay'),
        'database': logging.getLogger('tovplay.database'),
        'api': logging.getLogger('tovplay.api'), 
        'auth': logging.getLogger('tovplay.auth'),
        'errors': logging.getLogger('tovplay.errors')
    }
    
    if app:
        # Add request logging middleware
        setup_request_logging(app, loggers['api'])
        
        # Add database logging
        setup_database_logging(app, loggers['database'])
        
        # Add error logging
        setup_error_logging(app, loggers['errors'])
    
    # Log startup message
    env = os.getenv('FLASK_ENV', 'development')
    log_level = logging.getLevelName(get_log_level())
    loggers['main'].info(f"Logging initialized for {env} environment at {log_level} level")
    
    return loggers


def setup_request_logging(app, logger):
    """Setup request/response logging middleware."""
    import time
    from flask import request, g
    import uuid
    
    @app.before_request
    def before_request():
        g.start_time = time.time()
        g.request_id = str(uuid.uuid4())[:8]
        
        # Log incoming request
        logger.info(
            f"Request started",
            extra={
                'request_id': g.request_id,
                'method': request.method,
                'endpoint': request.endpoint or request.path,
                'ip_address': request.remote_addr,
                'user_agent': request.headers.get('User-Agent', ''),
                'content_length': request.content_length or 0
            }
        )
    
    @app.after_request
    def after_request(response):
        if hasattr(g, 'start_time'):
            response_time = (time.time() - g.start_time) * 1000  # milliseconds
            
            # Log response
            logger.info(
                f"Request completed",
                extra={
                    'request_id': getattr(g, 'request_id', 'unknown'),
                    'method': request.method,
                    'endpoint': request.endpoint or request.path,
                    'status_code': response.status_code,
                    'response_time': round(response_time, 2),
                    'response_size': len(response.get_data()) if response.get_data() else 0
                }
            )
            
            # Log slow requests
            if response_time > 1000:  # Slower than 1 second
                logger.warning(
                    f"Slow request detected",
                    extra={
                        'request_id': getattr(g, 'request_id', 'unknown'),
                        'endpoint': request.endpoint or request.path,
                        'response_time': round(response_time, 2)
                    }
                )
        
        return response


def setup_database_logging(app, logger):
    """Setup database query logging."""
    from sqlalchemy import event
    from sqlalchemy.engine import Engine
    import time
    
    @event.listens_for(Engine, "before_cursor_execute")
    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        context._query_start_time = time.time()
        
        # Log query start (debug level)
        logger.debug(
            f"Database query started",
            extra={
                'query': statement[:200] + '...' if len(statement) > 200 else statement,
                'parameters': str(parameters)[:100] if parameters else None
            }
        )
    
    @event.listens_for(Engine, "after_cursor_execute")
    def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        total_time = time.time() - context._query_start_time
        
        # Log query completion
        logger.debug(
            f"Database query completed",
            extra={
                'query_time': round(total_time * 1000, 2),  # milliseconds
                'query': statement[:100] + '...' if len(statement) > 100 else statement
            }
        )
        
        # Log slow queries
        if total_time > 0.5:  # Slower than 500ms
            logger.warning(
                f"Slow database query",
                extra={
                    'query_time': round(total_time * 1000, 2),
                    'query': statement
                }
            )


def setup_error_logging(app, logger):
    """Setup error logging with context."""
    from flask import request, g
    
    def log_error_with_context(error, error_type='unknown'):
        """Log error with full context."""
        context = {
            'error_type': error_type,
            'error_message': str(error),
            'request_id': getattr(g, 'request_id', 'unknown'),
            'endpoint': request.endpoint or request.path if request else 'unknown',
            'method': request.method if request else 'unknown',
            'ip_address': request.remote_addr if request else 'unknown'
        }
        
        if hasattr(error, '__traceback__'):
            import traceback
            context['traceback'] = traceback.format_exc()
        
        logger.error(f"Application error: {error}", extra=context, exc_info=True)
    
    # Store the error logger function for use in error handlers
    app.log_error_with_context = log_error_with_context


def get_logger(name='tovplay'):
    """Get a logger instance."""
    return logging.getLogger(name)


# Convenience functions for common logging operations
def log_user_action(user_id, action, details=None):
    """Log user actions for audit purposes."""
    logger = get_logger('tovplay.api')
    logger.info(
        f"User action: {action}",
        extra={
            'user_id': user_id,
            'action': action,
            'details': details or {}
        }
    )


def log_database_operation(operation, table=None, record_id=None, duration=None):
    """Log database operations."""
    logger = get_logger('tovplay.database')
    logger.info(
        f"Database operation: {operation}",
        extra={
            'operation': operation,
            'table': table,
            'record_id': record_id,
            'duration': duration
        }
    )


def log_security_event(event_type, details=None, severity='warning'):
    """Log security-related events."""
    logger = get_logger('tovplay.auth')
    
    log_func = getattr(logger, severity, logger.warning)
    log_func(
        f"Security event: {event_type}",
        extra={
            'event_type': event_type,
            'security_event': True,
            'details': details or {}
        }
    )


# Example usage:
"""
from app.logging_config import get_logger, log_user_action, log_security_event

# Get logger
logger = get_logger('tovplay.api')

# Basic logging
logger.info("User logged in successfully")
logger.error("Database connection failed", exc_info=True)

# Structured logging with extra context
logger.info("Order created", extra={
    'user_id': '123',
    'order_id': '456',
    'amount': 99.99
})

# Convenience functions
log_user_action('123', 'create_order', {'order_id': '456'})
log_security_event('failed_login', {'ip': '1.2.3.4', 'username': 'admin'}, 'warning')
"""