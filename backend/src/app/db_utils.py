"""
Database utility functions with robust error handling.
Provides safe database operations with automatic retry and proper error handling.
"""

import logging
from functools import wraps
from sqlalchemy.exc import SQLAlchemyError, DisconnectionError, TimeoutError as SQLTimeoutError

from .db import db
from .error_handlers import DatabaseError, safe_database_operation

logger = logging.getLogger(__name__)


def get_or_404(model, **kwargs):
    """
    Get a single record or raise a 404-like error.
    """
    def _get():
        instance = model.query.filter_by(**kwargs).first()
        if not instance:
            from .error_handlers import TovPlayError
            raise TovPlayError(
                f"{model.__name__} not found", 
                status_code=404,
                payload={'model': model.__name__, 'filters': kwargs}
            )
        return instance
    
    return safe_database_operation(_get)


def create_record(model, **kwargs):
    """
    Create a new record with error handling.
    """
    def _create():
        instance = model(**kwargs)
        db.session.add(instance)
        db.session.flush()  # Get ID without committing
        return instance
    
    return safe_database_operation(_create)


def update_record(instance, **kwargs):
    """
    Update a record with error handling.
    """
    def _update():
        for key, value in kwargs.items():
            if hasattr(instance, key):
                setattr(instance, key, value)
        db.session.flush()
        return instance
    
    return safe_database_operation(_update)


def delete_record(instance):
    """
    Delete a record with error handling.
    """
    def _delete():
        db.session.delete(instance)
        db.session.flush()
        return True
    
    return safe_database_operation(_delete)


def paginated_query(query, page=1, per_page=20, max_per_page=100):
    """
    Execute a paginated query with error handling.
    """
    def _paginate():
        if per_page > max_per_page:
            from .error_handlers import ValidationError
            raise ValidationError(f"per_page cannot exceed {max_per_page}")
        
        return query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
    
    return safe_database_operation(_paginate)


def execute_raw_sql(sql, params=None):
    """
    Execute raw SQL with error handling.
    Use sparingly and only for complex queries.
    """
    def _execute():
        from sqlalchemy import text
        result = db.session.execute(text(sql), params or {})
        return result
    
    return safe_database_operation(_execute)


def bulk_insert(model, records_data):
    """
    Perform bulk insert with error handling.
    """
    def _bulk_insert():
        if not records_data:
            return []
        
        # Create instances but don't add to session yet
        instances = [model(**data) for data in records_data]
        
        # Add all at once for better performance
        db.session.add_all(instances)
        db.session.flush()
        
        return instances
    
    return safe_database_operation(_bulk_insert)


def transaction(func):
    """
    Decorator to wrap a function in a database transaction.
    Automatically commits on success, rolls back on error.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
            db.session.commit()
            return result
        except SQLAlchemyError:
            db.session.rollback()
            raise
        except Exception:
            db.session.rollback()
            raise
    
    return wrapper


def retry_on_connection_error(max_retries=3):
    """
    Decorator to retry database operations on connection errors.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except (DisconnectionError, SQLTimeoutError) as e:
                    last_exception = e
                    logger.warning(
                        f"Database connection error on attempt {attempt + 1}/{max_retries}: {e}"
                    )
                    
                    if attempt < max_retries - 1:
                        # Try to reset the connection
                        try:
                            db.session.rollback()
                            db.engine.dispose()
                        except Exception as e:
                            import logging
                            logger = logging.getLogger(__name__)
                            logger.warning(f"Failed to reset database connection: {str(e)}")
                    else:
                        # Final attempt failed
                        raise DatabaseError(
                            f"Database operation failed after {max_retries} attempts",
                            original_error=last_exception
                        )
                except SQLAlchemyError:
                    # Don't retry other database errors
                    raise
            
            # This shouldn't be reached, but just in case
            raise DatabaseError(
                "Database operation failed after retries",
                original_error=last_exception
            )
        
        return wrapper
    return decorator


def safe_query_count(query):
    """
    Get query count with error handling.
    """
    def _count():
        return query.count()
    
    return safe_database_operation(_count)


def safe_query_all(query):
    """
    Execute query.all() with error handling.
    """
    def _all():
        return query.all()
    
    return safe_database_operation(_all)


def safe_query_first(query):
    """
    Execute query.first() with error handling.
    """
    def _first():
        return query.first()
    
    return safe_database_operation(_first)


def check_connection_health():
    """
    Check if database connection is healthy and attempt to reconnect if not.
    """
    from sqlalchemy import text
    
    try:
        # Simple connectivity test
        db.session.execute(text("SELECT 1"))
        db.session.commit()
        return True
        
    except (DisconnectionError, SQLTimeoutError):
        logger.warning("Database connection unhealthy, attempting to reconnect...")
        
        try:
            # Try to dispose and reconnect
            db.session.rollback()
            db.engine.dispose()
            
            # Test new connection
            db.session.execute(text("SELECT 1"))
            db.session.commit()
            
            logger.info("Database connection restored")
            return True
            
        except Exception as e:
            logger.error(f"Failed to restore database connection: {e}")
            raise DatabaseError("Database connection cannot be established")
    
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        raise DatabaseError(f"Database health check failed: {str(e)}")


class DatabaseHealthChecker:
    """
    Context manager for database health checking.
    """
    
    def __enter__(self):
        check_connection_health()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type and issubclass(exc_type, SQLAlchemyError):
            logger.error(f"Database error in context: {exc_val}")
            db.session.rollback()
        return False  # Don't suppress exceptions