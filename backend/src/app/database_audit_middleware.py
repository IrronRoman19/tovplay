"""
Database Audit Middleware
Tracks all database operations with team member attribution
Created: Dec 17, 2025 (in response to database wipe incident)
"""

import logging
import json
from datetime import datetime
from functools import wraps
from flask import g, request
from sqlalchemy import event
from sqlalchemy.engine import Engine
import time

logger = logging.getLogger(__name__)

# Team member mapping (GitHub username -> name)
TEAM_MEMBERS = {
    'romanfesu': 'Roman Fesunenko',
    'lilachHerzog': 'Lilach Herzog',
    'sharon': 'Sharon Keinar',
    'yuval': 'Yuval Zeyger',
    'michael': 'Michael Fedorovsky',
    'avi': 'Avi Wasserman',
    'itamar': 'Itamar Bar',
}

class DatabaseAuditLogger:
    """Logs all database operations with user attribution"""

    def __init__(self, app=None):
        self.app = app
        if app:
            self.init_app(app)

    def init_app(self, app):
        """Initialize the audit logger with Flask app"""

        # Log all SQL statements with user context
        @event.listens_for(Engine, "before_cursor_execute")
        def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            conn.info.setdefault('query_start_time', []).append(time.time())

            # Get user context
            user_email = getattr(g, 'user_email', 'unknown')
            user_id = getattr(g, 'user_id', 'unknown')
            team_member = self._identify_team_member()

            # Log the query
            self._log_query(statement, parameters, user_email, user_id, team_member)

        @event.listens_for(Engine, "after_cursor_execute")
        def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            total = time.time() - conn.info['query_start_time'].pop(-1)

            # Alert on slow queries
            if total > 1.0:  # 1 second
                logger.warning(f"SLOW_QUERY: {total:.2f}s - {statement[:200]}")

    def _identify_team_member(self):
        """Identify which team member is making the request"""

        # Check JWT token for user info
        user_email = getattr(g, 'user_email', '')

        # Map common email patterns to team members
        if 'roman' in user_email.lower():
            return TEAM_MEMBERS['romanfesu']
        elif 'lilach' in user_email.lower() or 'herzog' in user_email.lower():
            return TEAM_MEMBERS['lilachHerzog']
        elif 'sharon' in user_email.lower():
            return TEAM_MEMBERS['sharon']

        # Check user agent
        user_agent = request.headers.get('User-Agent', '').lower()
        if 'claude' in user_agent or 'anthropic' in user_agent:
            return 'Claude AI'

        # Check for direct database connections
        if not hasattr(g, 'user_email'):
            return 'DIRECT_DB_CONNECTION'

        return user_email or 'unknown'

    def _log_query(self, statement, parameters, user_email, user_id, team_member):
        """Log query with full context"""

        statement_upper = statement.upper().strip()

        # Determine operation type
        operation = 'SELECT'
        if statement_upper.startswith('INSERT'):
            operation = 'INSERT'
        elif statement_upper.startswith('UPDATE'):
            operation = 'UPDATE'
        elif statement_upper.startswith('DELETE'):
            operation = 'DELETE'
        elif statement_upper.startswith('TRUNCATE'):
            operation = 'TRUNCATE'
        elif statement_upper.startswith('DROP'):
            operation = 'DROP'
        elif statement_upper.startswith('ALTER'):
            operation = 'ALTER'
        elif statement_upper.startswith('CREATE'):
            operation = 'CREATE'

        # Extract table name
        table = self._extract_table(statement, operation)

        # Build audit log entry
        audit_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'operation': operation,
            'table': table,
            'user_email': user_email,
            'user_id': user_id,
            'team_member': team_member,
            'ip_address': request.remote_addr if request else 'N/A',
            'user_agent': request.headers.get('User-Agent', 'N/A') if request else 'N/A',
            'endpoint': request.endpoint if request else 'N/A',
            'statement': statement[:500],  # First 500 chars
        }

        # Log at appropriate level
        if operation in ['DELETE', 'TRUNCATE', 'DROP', 'ALTER']:
            logger.warning(f"🚨 CRITICAL_DB_OPERATION: {json.dumps(audit_entry)}")
        elif operation in ['UPDATE', 'INSERT']:
            logger.info(f"DB_WRITE: {json.dumps(audit_entry)}")
        else:
            logger.debug(f"DB_READ: {json.dumps(audit_entry)}")

        # Alert on dangerous operations
        if operation in ['TRUNCATE', 'DROP']:
            self._send_alert(audit_entry)

    def _extract_table(self, statement, operation):
        """Extract table name from SQL statement"""
        try:
            statement_upper = statement.upper()

            if operation == 'SELECT':
                if 'FROM' in statement_upper:
                    parts = statement_upper.split('FROM')[1].split()
                    return parts[0].strip('";').replace('"', '')
            elif operation in ['INSERT', 'UPDATE', 'DELETE']:
                if operation in statement_upper:
                    parts = statement_upper.split(operation)[1].split()
                    if operation == 'INSERT' and 'INTO' in statement_upper:
                        parts = statement_upper.split('INTO')[1].split()
                    return parts[0].strip('";').replace('"', '')
            elif operation in ['TRUNCATE', 'DROP']:
                parts = statement_upper.split(operation)[1].split()
                if 'TABLE' in parts[0]:
                    return parts[1].strip('";').replace('"', '')
                return parts[0].strip('";').replace('"', '')

            return 'unknown'
        except Exception as e:
            logger.error(f"Error extracting table name: {e}")
            return 'parse_error'

    def _send_alert(self, audit_entry):
        """Send alert for critical operations"""
        alert_message = (
            f"⚠️ CRITICAL DATABASE OPERATION DETECTED ⚠️\n"
            f"Operation: {audit_entry['operation']}\n"
            f"Table: {audit_entry['table']}\n"
            f"Team Member: {audit_entry['team_member']}\n"
            f"User: {audit_entry['user_email']} (ID: {audit_entry['user_id']})\n"
            f"IP: {audit_entry['ip_address']}\n"
            f"Statement: {audit_entry['statement']}\n"
            f"Timestamp: {audit_entry['timestamp']}"
        )

        logger.critical(alert_message)

        # TODO: Send to Slack/Discord/Email
        # For now, just log it prominently


def log_database_operation(operation_name):
    """Decorator to log specific database operations"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_email = getattr(g, 'user_email', 'unknown')
            user_id = getattr(g, 'user_id', 'unknown')

            logger.info(
                f"DB_OPERATION_START: {operation_name} by {user_email} (ID: {user_id})"
            )

            try:
                result = f(*args, **kwargs)
                logger.info(
                    f"DB_OPERATION_SUCCESS: {operation_name} by {user_email}"
                )
                return result
            except Exception as e:
                logger.error(
                    f"DB_OPERATION_FAILED: {operation_name} by {user_email} - {str(e)}"
                )
                raise

        return decorated_function
    return decorator
