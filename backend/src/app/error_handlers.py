"""
Comprehensive error handling for TovPlay backend.
Handles database failures, API errors, and system exceptions gracefully.
"""

import logging
import traceback
from datetime import datetime
from functools import wraps

from flask import jsonify, request, current_app, g
from sqlalchemy.exc import (
    SQLAlchemyError, 
    OperationalError, 
    IntegrityError, 
    DataError,
    DatabaseError,
    DisconnectionError,
    TimeoutError as SQLTimeoutError
)
from werkzeug.exceptions import HTTPException

from .db import db

logger = logging.getLogger('tovplay.errors')


class TovPlayError(Exception):
    """Base exception class for TovPlay-specific errors."""
    def __init__(self, message, status_code=500, payload=None):
        super().__init__()
        self.message = message
        self.status_code = status_code
        self.payload = payload or {}

    def to_dict(self):
        return {
            'error': self.message,
            'status_code': self.status_code,
            'timestamp': datetime.utcnow().isoformat(),
            **self.payload
        }


class DatabaseError(TovPlayError):
    """Database-related errors."""
    def __init__(self, message, original_error=None, status_code=503):
        super().__init__(message, status_code)
        self.original_error = original_error


class ValidationError(TovPlayError):
    """Data validation errors."""
    def __init__(self, message, field=None, status_code=400):
        payload = {'field': field} if field else {}
        super().__init__(message, status_code, payload)


class AuthenticationError(TovPlayError):
    """Authentication-related errors."""
    def __init__(self, message, status_code=401):
        super().__init__(message, status_code)


class AuthorizationError(TovPlayError):
    """Authorization-related errors."""
    def __init__(self, message, status_code=403):
        super().__init__(message, status_code)


def handle_database_error(error):
    """
    Handle various database errors with appropriate responses.
    """
    logger.error(f"Database error: {str(error)}", exc_info=True)
    
    if isinstance(error, DisconnectionError):
        return jsonify({
            'error': 'Database connection lost. Please try again.',
            'type': 'connection_lost',
            'status_code': 503,
            'timestamp': datetime.utcnow().isoformat(),
            'retry_after': 30
        }), 503
    
    elif isinstance(error, SQLTimeoutError):
        return jsonify({
            'error': 'Database operation timed out. Please try again.',
            'type': 'timeout',
            'status_code': 504,
            'timestamp': datetime.utcnow().isoformat(),
            'retry_after': 5
        }), 504
    
    elif isinstance(error, IntegrityError):
        # Handle unique constraint violations, foreign key errors, etc.
        error_msg = str(error.orig) if hasattr(error, 'orig') else str(error)
        
        if 'unique constraint' in error_msg.lower() or 'duplicate key' in error_msg.lower():
            return jsonify({
                'error': 'This data already exists. Please use unique values.',
                'type': 'duplicate_data',
                'status_code': 409,
                'timestamp': datetime.utcnow().isoformat()
            }), 409
        
        elif 'foreign key' in error_msg.lower():
            return jsonify({
                'error': 'Invalid reference to related data.',
                'type': 'invalid_reference',
                'status_code': 400,
                'timestamp': datetime.utcnow().isoformat()
            }), 400
        
        else:
            return jsonify({
                'error': 'Data validation failed. Please check your input.',
                'type': 'validation_error',
                'status_code': 400,
                'timestamp': datetime.utcnow().isoformat()
            }), 400
    
    elif isinstance(error, DataError):
        return jsonify({
            'error': 'Invalid data format. Please check your input.',
            'type': 'data_format_error',
            'status_code': 400,
            'timestamp': datetime.utcnow().isoformat()
        }), 400
    
    elif isinstance(error, OperationalError):
        error_msg = str(error.orig) if hasattr(error, 'orig') else str(error)
        
        if 'connection' in error_msg.lower():
            return jsonify({
                'error': 'Unable to connect to database. Please try again later.',
                'type': 'connection_error',
                'status_code': 503,
                'timestamp': datetime.utcnow().isoformat(),
                'retry_after': 30
            }), 503
        
        else:
            return jsonify({
                'error': 'Database operation failed. Please try again.',
                'type': 'operational_error',
                'status_code': 503,
                'timestamp': datetime.utcnow().isoformat(),
                'retry_after': 10
            }), 503
    
    else:
        # Generic database error
        return jsonify({
            'error': 'Database error occurred. Please try again later.',
            'type': 'database_error',
            'status_code': 503,
            'timestamp': datetime.utcnow().isoformat(),
            'retry_after': 30
        }), 503


def handle_tovplay_error(error):
    """Handle custom TovPlay errors."""
    logger.warning(f"TovPlay error: {error.message}")
    return jsonify(error.to_dict()), error.status_code


def handle_http_error(error):
    """Handle standard HTTP errors."""
    logger.warning(f"HTTP error {error.code}: {error.description}")
    return jsonify({
        'error': error.description,
        'status_code': error.code,
        'timestamp': datetime.utcnow().isoformat()
    }), error.code


def handle_generic_error(error):
    """Handle unexpected errors."""
    logger.error(f"Unexpected error: {str(error)}", exc_info=True)
    
    # Don't expose internal errors in production
    if current_app.config.get('ENV') == 'production':
        message = 'An unexpected error occurred. Please try again later.'
    else:
        message = f'Internal error: {str(error)}'
    
    return jsonify({
        'error': message,
        'type': 'internal_error',
        'status_code': 500,
        'timestamp': datetime.utcnow().isoformat()
    }), 500


def with_db_error_handling(f):
    """
    Decorator to add database error handling to routes.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except SQLAlchemyError as e:
            db.session.rollback()
            return handle_database_error(e)
        except TovPlayError as e:
            db.session.rollback()
            return handle_tovplay_error(e)
        except Exception as e:
            db.session.rollback()
            return handle_generic_error(e)
    
    return decorated_function


def with_transaction(f):
    """
    Decorator to wrap database operations in a transaction with proper error handling.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            # Start transaction
            result = f(*args, **kwargs)
            
            # Commit if no exception occurred
            db.session.commit()
            return result
            
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Database transaction failed: {str(e)}", exc_info=True)
            raise DatabaseError(
                "Database operation failed",
                original_error=e
            )
        except Exception as e:
            db.session.rollback()
            logger.error(f"Transaction failed with unexpected error: {str(e)}", exc_info=True)
            raise
    
    return decorated_function


def setup_error_handlers(app):
    """
    Register error handlers with the Flask app.
    """
    
    @app.errorhandler(SQLAlchemyError)
    def handle_sqlalchemy_error(error):
        db.session.rollback()
        return handle_database_error(error)
    
    @app.errorhandler(TovPlayError)
    def handle_custom_error(error):
        return handle_tovplay_error(error)
    
    @app.errorhandler(HTTPException)
    def handle_http_exception(error):
        # Don't override 404 errors - let Flask handle them normally
        if error.code == 404:
            return error
        return handle_http_error(error)
    
    @app.errorhandler(405)
    def handle_method_not_allowed(error):
        return jsonify({
            'error': 'Method not allowed',
            'status_code': 405,
            'timestamp': datetime.utcnow().isoformat(),
            'path': request.path,
            'method': request.method
        }), 405
    
    @app.errorhandler(500)
    def handle_internal_error(error):
        db.session.rollback()
        return handle_generic_error(error)
    
    logger.info("Error handlers registered successfully")


def check_database_health():
    """
    Check database connectivity and raise appropriate errors.
    """
    from sqlalchemy import text
    
    try:
        # Test basic connectivity
        db.session.execute(text("SELECT 1"))
        db.session.commit()
        
    except DisconnectionError:
        raise DatabaseError("Database connection lost")
    except SQLTimeoutError:
        raise DatabaseError("Database connection timeout")
    except OperationalError as e:
        if 'connection' in str(e).lower():
            raise DatabaseError("Unable to connect to database")
        raise DatabaseError("Database operational error")
    except Exception as e:
        raise DatabaseError(f"Database health check failed: {str(e)}")


def safe_database_operation(operation, *args, **kwargs):
    """
    Execute a database operation with automatic retry and error handling.
    """
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            return operation(*args, **kwargs)
            
        except DisconnectionError:
            retry_count += 1
            if retry_count >= max_retries:
                raise DatabaseError("Database connection lost after multiple retries")
            
            # Try to reconnect
            try:
                db.session.rollback()
                db.engine.dispose()
            except Exception as e:
                logger.warning(f"Failed to reset database connection: {str(e)}")
            
            logger.warning(f"Database disconnected, retrying ({retry_count}/{max_retries})")
            
        except SQLTimeoutError:
            retry_count += 1
            if retry_count >= max_retries:
                raise DatabaseError("Database operation timed out after multiple retries")
            
            logger.warning(f"Database timeout, retrying ({retry_count}/{max_retries})")
            
        except Exception as e:
            # For other errors, don't retry
            raise DatabaseError(f"Database operation failed: {str(e)}", original_error=e)