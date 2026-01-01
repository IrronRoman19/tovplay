"""
============================================================================
LOGGING CONFIG - TovPlay Production
============================================================================
Compatibility shim that bridges old logging_config imports to new
structured_logger module. All new code uses structured_logger directly.

This file maintains backward compatibility with existing code that imports
from logging_config.
============================================================================
"""

# Re-export all structured logging functionality for backward compatibility
from .structured_logger import (
    # Main functions
    get_logger,
    setup_logging,
    generate_correlation_id,
    get_correlation_id,
    set_correlation_id,
    clear_correlation_id,

    # Context management
    get_log_context,
    set_log_context,
    clear_log_context,
    log_context,
    set_user_context,

    # Decorators
    log_performance,

    # Classes
    StructuredLogger,
    StructuredFormatter,
)

__all__ = [
    # Functions
    'get_logger',
    'setup_logging',
    'generate_correlation_id',
    'get_correlation_id',
    'set_correlation_id',
    'clear_correlation_id',
    'get_log_context',
    'set_log_context',
    'clear_log_context',
    'log_context',
    'set_user_context',
    'log_performance',

    # Classes
    'StructuredLogger',
    'StructuredFormatter',
]
