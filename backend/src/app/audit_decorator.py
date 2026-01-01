"""
============================================================================
AUDIT LOG DECORATOR - TovPlay Production
============================================================================
Automatic audit logging for database operations with forensic capabilities.

Features:
- Automatic tracking of WHO/WHEN/WHAT/WHY for all operations
- Database-level audit trail (PostgreSQL audit tables)
- Application-level audit logging (structured logs)
- Integration with Flask user context
- Support for compliance requirements (GDPR, SOC2, etc.)

Usage:
    from audit_decorator import audit_log, AuditAction

    @audit_log(action=AuditAction.DELETE, resource_type="Game")
    def delete_game(game_id: int):
        # ... delete logic
        return True

Deploy:
    Place this file in: backend/src/app/audit_decorator.py
    Import where needed: from .audit_decorator import audit_log
============================================================================
"""

import functools
import inspect
import json
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, Optional

from flask import request, g, has_request_context
from sqlalchemy import text

from .structured_logger import get_logger, get_correlation_id, get_log_context

logger = get_logger(__name__)

# ============================================================================
# AUDIT ACTION TYPES
# ============================================================================

class AuditAction(str, Enum):
    """Standard audit action types."""
    CREATE = "CREATE"
    READ = "READ"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    EXPORT = "EXPORT"
    IMPORT = "IMPORT"
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    SHARE = "SHARE"
    UNSHARE = "UNSHARE"
    PERMISSION_CHANGE = "PERMISSION_CHANGE"
    SETTINGS_CHANGE = "SETTINGS_CHANGE"
    PASSWORD_CHANGE = "PASSWORD_CHANGE"
    PASSWORD_RESET = "PASSWORD_RESET"
    EMAIL_VERIFY = "EMAIL_VERIFY"
    TWO_FACTOR_ENABLE = "TWO_FACTOR_ENABLE"
    TWO_FACTOR_DISABLE = "TWO_FACTOR_DISABLE"
    API_KEY_CREATE = "API_KEY_CREATE"
    API_KEY_REVOKE = "API_KEY_REVOKE"
    BACKUP = "BACKUP"
    RESTORE = "RESTORE"

# ============================================================================
# AUDIT SEVERITY LEVELS
# ============================================================================

class AuditSeverity(str, Enum):
    """Audit event severity levels."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

# ============================================================================
# AUDIT LOG DECORATOR
# ============================================================================

def audit_log(
    action: AuditAction,
    resource_type: str,
    resource_id_param: Optional[str] = None,
    severity: AuditSeverity = AuditSeverity.MEDIUM,
    include_args: bool = False,
    include_result: bool = False,
    sensitive_params: Optional[list] = None,
    db_session: Optional[Any] = None
):
    """
    Decorator to automatically audit function calls.

    Args:
        action: The type of action being performed (CREATE, UPDATE, DELETE, etc.)
        resource_type: The type of resource being acted upon (User, Game, etc.)
        resource_id_param: Parameter name containing the resource ID (default: auto-detect)
        severity: Severity level of the audit event
        include_args: Include function arguments in audit log
        include_result: Include function result in audit log
        sensitive_params: List of parameter names to redact from logs
        db_session: SQLAlchemy session for database audit logging

    Returns:
        Decorator function

    Usage:
        @audit_log(action=AuditAction.DELETE, resource_type="Game")
        def delete_game(game_id: int):
            Game.query.filter_by(id=game_id).delete()
            return True

        @audit_log(
            action=AuditAction.UPDATE,
            resource_type="User",
            resource_id_param="user_id",
            include_args=True,
            sensitive_params=["password", "token"]
        )
        def update_user(user_id: int, username: str, password: str):
            # ... update logic
            return user
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Start timing
            start_time = time.perf_counter()

            # Extract function signature
            sig = inspect.signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()

            # Get resource ID
            resource_id = _extract_resource_id(resource_id_param, bound_args)

            # Get user context
            user_context = _get_user_context()

            # Build audit entry
            audit_entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "correlation_id": get_correlation_id(),
                "action": action.value,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "severity": severity.value,
                "user_id": user_context.get("user_id"),
                "username": user_context.get("username"),
                "user_email": user_context.get("email"),
                "ip_address": user_context.get("ip_address"),
                "user_agent": user_context.get("user_agent"),
                "function": f"{func.__module__}.{func.__name__}",
                "request_path": user_context.get("request_path"),
                "request_method": user_context.get("request_method"),
            }

            # Add arguments if requested
            if include_args:
                args_dict = dict(bound_args.arguments)
                if sensitive_params:
                    args_dict = _redact_sensitive_params(args_dict, sensitive_params)
                audit_entry["arguments"] = args_dict

            # Execute function
            try:
                result = func(*args, **kwargs)
                success = True
                error = None

                # Add result if requested
                if include_result:
                    audit_entry["result"] = _sanitize_result(result)

            except Exception as e:
                success = False
                error = str(e)
                result = None
                raise

            finally:
                # Calculate duration
                duration_ms = (time.perf_counter() - start_time) * 1000

                # Update audit entry
                audit_entry.update({
                    "success": success,
                    "error": error,
                    "duration_ms": round(duration_ms, 2)
                })

                # Log to application logs
                _log_audit_entry(audit_entry, success)

                # Log to database
                if db_session:
                    _save_audit_to_database(db_session, audit_entry)

            return result

        return wrapper

    return decorator

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _extract_resource_id(resource_id_param: Optional[str], bound_args) -> Optional[Any]:
    """Extract resource ID from function arguments."""
    if resource_id_param and resource_id_param in bound_args.arguments:
        return bound_args.arguments[resource_id_param]

    # Auto-detect common ID parameter names
    common_id_params = ['id', 'resource_id', 'user_id', 'game_id', 'session_id']
    for param in common_id_params:
        if param in bound_args.arguments:
            return bound_args.arguments[param]

    return None

def _get_user_context() -> Dict[str, Any]:
    """Get current user context from Flask request/g object."""
    context = {}

    if has_request_context():
        # Get from request context
        context['ip_address'] = request.remote_addr
        context['user_agent'] = request.user_agent.string if request.user_agent else None
        context['request_path'] = request.path
        context['request_method'] = request.method

        # Get from g object (set by authentication middleware)
        if hasattr(g, 'current_user'):
            user = g.current_user
            context['user_id'] = getattr(user, 'id', None)
            context['username'] = getattr(user, 'username', None)
            context['email'] = getattr(user, 'email', None)

        # Get from JWT claims (if using JWT auth)
        if hasattr(g, 'jwt_claims'):
            claims = g.jwt_claims
            context['user_id'] = context.get('user_id') or claims.get('user_id')
            context['username'] = context.get('username') or claims.get('username')
            context['email'] = context.get('email') or claims.get('email')

    # Get from thread-local context (set by structured_logger)
    log_context = get_log_context()
    for key in ['user_id', 'username', 'email']:
        if key in log_context and key not in context:
            context[key] = log_context[key]

    return context

def _redact_sensitive_params(args_dict: Dict, sensitive_params: list) -> Dict:
    """Redact sensitive parameters from arguments."""
    redacted = args_dict.copy()
    for param in sensitive_params:
        if param in redacted:
            redacted[param] = "[REDACTED]"
    return redacted

def _sanitize_result(result: Any) -> Any:
    """Sanitize result for logging (avoid logging large objects)."""
    if result is None:
        return None

    # Limit string length
    if isinstance(result, str) and len(result) > 1000:
        return result[:1000] + "... [TRUNCATED]"

    # Convert to string for objects
    if hasattr(result, '__dict__'):
        return f"<{result.__class__.__name__} object>"

    # Return as-is for primitives
    if isinstance(result, (bool, int, float, str, list, dict)):
        return result

    return str(result)

def _log_audit_entry(audit_entry: Dict, success: bool) -> None:
    """Log audit entry to application logs."""
    level = "info" if success else "error"

    message = (
        f"Audit: {audit_entry['action']} {audit_entry['resource_type']}"
        f" (resource_id={audit_entry['resource_id']}) "
        f"by user_id={audit_entry['user_id']}"
    )

    if success:
        logger.info(message, **audit_entry)
    else:
        logger.error(message, **audit_entry)

def _save_audit_to_database(db_session, audit_entry: Dict) -> None:
    """Save audit entry to database audit table."""
    try:
        # Insert into audit log table
        sql = text("""
            INSERT INTO audit_log (
                timestamp, correlation_id, action, resource_type, resource_id,
                severity, user_id, username, user_email, ip_address, user_agent,
                function, request_path, request_method, arguments, result,
                success, error, duration_ms
            ) VALUES (
                :timestamp, :correlation_id, :action, :resource_type, :resource_id,
                :severity, :user_id, :username, :user_email, :ip_address, :user_agent,
                :function, :request_path, :request_method, :arguments, :result,
                :success, :error, :duration_ms
            )
        """)

        # Convert complex types to JSON
        audit_entry_db = audit_entry.copy()
        for key in ['arguments', 'result']:
            if key in audit_entry_db and audit_entry_db[key] is not None:
                audit_entry_db[key] = json.dumps(audit_entry_db[key])

        db_session.execute(sql, audit_entry_db)
        db_session.commit()

    except Exception as e:
        logger.error(f"Failed to save audit log to database: {str(e)}", exc_info=True)
        db_session.rollback()

# ============================================================================
# DATABASE AUDIT TABLE SCHEMA
# ============================================================================

AUDIT_TABLE_SQL = """
-- ============================================================================
-- AUDIT LOG TABLE - TovPlay Production
-- ============================================================================
-- Stores comprehensive audit trail for all operations
-- Used by @audit_log decorator for database-level audit logging
-- ============================================================================

CREATE TABLE IF NOT EXISTS audit_log (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    correlation_id VARCHAR(50),
    action VARCHAR(50) NOT NULL,
    resource_type VARCHAR(100) NOT NULL,
    resource_id VARCHAR(100),
    severity VARCHAR(20) NOT NULL DEFAULT 'MEDIUM',
    user_id INTEGER,
    username VARCHAR(100),
    user_email VARCHAR(255),
    ip_address INET,
    user_agent TEXT,
    function VARCHAR(255),
    request_path VARCHAR(500),
    request_method VARCHAR(10),
    arguments JSONB,
    result JSONB,
    success BOOLEAN NOT NULL DEFAULT TRUE,
    error TEXT,
    duration_ms NUMERIC(10,2),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Indexes for fast queries
CREATE INDEX IF NOT EXISTS idx_audit_log_timestamp ON audit_log (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_log_user_id ON audit_log (user_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_action ON audit_log (action);
CREATE INDEX IF NOT EXISTS idx_audit_log_resource ON audit_log (resource_type, resource_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_correlation_id ON audit_log (correlation_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_severity ON audit_log (severity);
CREATE INDEX IF NOT EXISTS idx_audit_log_success ON audit_log (success);

-- GIN index for JSONB columns (fast JSON queries)
CREATE INDEX IF NOT EXISTS idx_audit_log_arguments_gin ON audit_log USING GIN (arguments);
CREATE INDEX IF NOT EXISTS idx_audit_log_result_gin ON audit_log USING GIN (result);

-- Composite indexes for common queries
CREATE INDEX IF NOT EXISTS idx_audit_log_user_timestamp ON audit_log (user_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_log_resource_timestamp ON audit_log (resource_type, resource_id, timestamp DESC);

-- Retention policy (optional - delete old audit logs)
-- Run this as a scheduled job (e.g., weekly)
-- DELETE FROM audit_log WHERE timestamp < NOW() - INTERVAL '1 year';

COMMENT ON TABLE audit_log IS 'Comprehensive audit trail for all operations';
COMMENT ON COLUMN audit_log.correlation_id IS 'Request correlation ID for tracing';
COMMENT ON COLUMN audit_log.action IS 'Type of action: CREATE, UPDATE, DELETE, etc.';
COMMENT ON COLUMN audit_log.resource_type IS 'Type of resource: User, Game, etc.';
COMMENT ON COLUMN audit_log.resource_id IS 'ID of the resource being acted upon';
COMMENT ON COLUMN audit_log.severity IS 'Severity: LOW, MEDIUM, HIGH, CRITICAL';
COMMENT ON COLUMN audit_log.arguments IS 'Function arguments (JSONB)';
COMMENT ON COLUMN audit_log.result IS 'Function result (JSONB)';
COMMENT ON COLUMN audit_log.duration_ms IS 'Operation duration in milliseconds';
"""

# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    # Example 1: Basic audit logging
    @audit_log(action=AuditAction.DELETE, resource_type="Game")
    def delete_game(game_id: int):
        print(f"Deleting game {game_id}")
        return True

    delete_game(123)

    # Example 2: Audit with arguments
    @audit_log(
        action=AuditAction.UPDATE,
        resource_type="User",
        resource_id_param="user_id",
        include_args=True,
        sensitive_params=["password", "token"]
    )
    def update_user(user_id: int, username: str, password: str, email: str):
        print(f"Updating user {user_id}")
        return {"id": user_id, "username": username, "email": email}

    update_user(456, "john_doe", "secret123", "john@example.com")

    # Example 3: Critical severity audit
    @audit_log(
        action=AuditAction.PERMISSION_CHANGE,
        resource_type="User",
        severity=AuditSeverity.CRITICAL
    )
    def grant_admin_role(user_id: int):
        print(f"Granting admin role to user {user_id}")
        return True

    grant_admin_role(789)

    print("\n" + "="*80)
    print("See audit logs above - ready for forensic analysis!")
    print("="*80)
