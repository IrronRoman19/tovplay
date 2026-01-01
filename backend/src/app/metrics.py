"""
Custom Prometheus metrics for TovPlay business logic monitoring.

This module defines custom metrics for tracking:
- Discord OAuth flows
- Authentication (login, JWT, sessions)
- Rate limiting
- Database operations
- Email delivery
- Game requests and sessions
- WebSocket connections
- SSL/TLS monitoring
- Notifications

Author: TovPlay Team
Last Updated: 2025-11-12
"""

import os
import time
from functools import wraps
from prometheus_client import Counter, Histogram, Gauge, Summary

# Get environment for labels
def get_environment():
    """Get current Flask environment."""
    return os.getenv('FLASK_ENV', 'development')

# ========================================
# DISCORD OAUTH METRICS
# ========================================

discord_oauth_redirects = Counter(
    'discord_oauth_redirects_total',
    'Total Discord OAuth login redirects initiated',
    ['environment']
)

discord_oauth_callbacks = Counter(
    'discord_oauth_callbacks_total',
    'Total Discord OAuth callbacks received',
    ['environment', 'status']  # status: success, error, cancelled
)

discord_token_exchanges = Counter(
    'discord_token_exchanges_total',
    'Total Discord token exchange attempts',
    ['environment', 'status']  # status: success, failure
)

discord_token_exchange_duration = Histogram(
    'discord_token_exchange_duration_seconds',
    'Time spent exchanging OAuth code for token',
    ['environment'],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

discord_guild_operations = Counter(
    'discord_guild_operations_total',
    'Total Discord guild membership operations',
    ['environment', 'operation', 'status']  # operation: add_user, check_membership
)

discord_event_creations = Counter(
    'discord_event_creations_total',
    'Total Discord event creation attempts',
    ['environment', 'status']
)

# ========================================
# AUTHENTICATION METRICS
# ========================================

auth_login_attempts = Counter(
    'auth_login_attempts_total',
    'Total login attempts',
    ['environment', 'method', 'status']  # method: email, discord; status: success, failure, invalid
)

auth_login_duration = Histogram(
    'auth_login_duration_seconds',
    'Time spent processing login requests',
    ['environment', 'method'],
    buckets=[0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0]
)

auth_jwt_validations = Counter(
    'auth_jwt_validations_total',
    'Total JWT token validations',
    ['environment', 'status']  # status: valid, expired, invalid
)

auth_jwt_refreshes = Counter(
    'auth_jwt_refreshes_total',
    'Total JWT token refresh attempts',
    ['environment', 'status']
)

auth_signup_attempts = Counter(
    'auth_signup_attempts_total',
    'Total signup attempts',
    ['environment', 'status']
)

auth_active_sessions = Gauge(
    'auth_active_sessions',
    'Current number of active user sessions',
    ['environment']
)

auth_password_reset_requests = Counter(
    'auth_password_reset_requests_total',
    'Total password reset requests',
    ['environment', 'status']
)

# ========================================
# RATE LIMITING METRICS
# ========================================

rate_limit_hits = Counter(
    'rate_limit_hits_total',
    'Total requests checked by rate limiter',
    ['environment', 'endpoint', 'result']  # result: allowed, burst_exceeded, rate_exceeded
)

rate_limit_blocks = Counter(
    'rate_limit_blocks_total',
    'Total requests blocked by rate limiter',
    ['environment', 'endpoint', 'reason']
)

# ========================================
# DATABASE METRICS
# ========================================

db_query_duration = Histogram(
    'db_query_duration_seconds',
    'Database query execution time',
    ['environment', 'operation', 'table'],  # operation: select, insert, update, delete
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0]
)

db_connection_pool_size = Gauge(
    'db_connection_pool_size',
    'Current database connection pool size',
    ['environment', 'state']  # state: active, idle
)

db_query_errors = Counter(
    'db_query_errors_total',
    'Total database query errors',
    ['environment', 'error_type', 'table']
)

db_transaction_duration = Histogram(
    'db_transaction_duration_seconds',
    'Database transaction completion time',
    ['environment', 'status'],  # status: commit, rollback
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0]
)

db_slow_queries = Counter(
    'db_slow_queries_total',
    'Total slow database queries (>1s)',
    ['environment', 'table']
)

# ========================================
# EMAIL METRICS
# ========================================

email_sent = Counter(
    'email_sent_total',
    'Total emails sent',
    ['environment', 'email_type', 'status']  # email_type: verification, notification, reset
)

email_send_duration = Histogram(
    'email_send_duration_seconds',
    'Time spent sending emails',
    ['environment', 'email_type'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
)

email_queue_depth = Gauge(
    'email_queue_depth',
    'Current email queue depth',
    ['environment']
)

smtp_connection_errors = Counter(
    'smtp_connection_errors_total',
    'Total SMTP connection errors',
    ['environment', 'error_type']
)

# ========================================
# GAME REQUEST METRICS
# ========================================

game_requests = Counter(
    'game_requests_total',
    'Total game requests',
    ['environment', 'action']  # action: created, accepted, rejected, expired, cancelled
)

game_request_duration = Histogram(
    'game_request_duration_seconds',
    'Time from request creation to resolution',
    ['environment', 'resolution'],  # resolution: accepted, rejected, expired
    buckets=[60, 300, 600, 1800, 3600, 7200, 21600, 86400]  # 1m to 24h
)

game_sessions_scheduled = Counter(
    'game_sessions_scheduled_total',
    'Total game sessions scheduled',
    ['environment', 'status']
)

game_sessions_active = Gauge(
    'game_sessions_active',
    'Currently active game sessions',
    ['environment', 'status']  # status: upcoming, in_progress
)

# ========================================
# WEBSOCKET METRICS
# ========================================

websocket_connections = Gauge(
    'websocket_connections_active',
    'Current active WebSocket connections',
    ['environment']
)

websocket_messages = Counter(
    'websocket_messages_total',
    'Total WebSocket messages',
    ['environment', 'direction', 'event_type']  # direction: sent, received
)

websocket_connection_duration = Histogram(
    'websocket_connection_duration_seconds',
    'WebSocket connection lifetime',
    ['environment'],
    buckets=[10, 60, 300, 600, 1800, 3600, 7200]
)

# ========================================
# SSL/TLS METRICS
# ========================================

ssl_certificate_expiry_days = Gauge(
    'ssl_certificate_expiry_days',
    'Days until SSL certificate expires',
    ['environment', 'domain']
)

ssl_handshake_duration = Histogram(
    'ssl_handshake_duration_seconds',
    'TLS handshake duration',
    ['environment'],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0]
)

# ========================================
# NOTIFICATION METRICS
# ========================================

notifications_sent = Counter(
    'notifications_sent_total',
    'Total notifications sent',
    ['environment', 'notification_type', 'channel']  # channel: websocket, email, in_app
)

notifications_delivered = Counter(
    'notifications_delivered_total',
    'Total notifications successfully delivered',
    ['environment', 'notification_type', 'channel']
)

# ========================================
# METRIC DECORATORS
# ========================================

def track_login_attempt(method='email'):
    """
    Decorator to track login attempts.

    Args:
        method: Login method ('email' or 'discord')

    Usage:
        @track_login_attempt(method='email')
        def login():
            ...
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            env = get_environment()
            start_time = time.time()

            try:
                result = f(*args, **kwargs)
                duration = time.time() - start_time

                # Determine status from response
                if isinstance(result, tuple) and len(result) >= 2:
                    status_code = result[1]
                elif hasattr(result, 'status_code'):
                    status_code = result.status_code
                else:
                    status_code = 200

                status = 'success' if status_code == 200 else 'failure'
                auth_login_attempts.labels(environment=env, method=method, status=status).inc()
                auth_login_duration.labels(environment=env, method=method).observe(duration)

                return result
            except Exception as e:
                duration = time.time() - start_time
                auth_login_attempts.labels(environment=env, method=method, status='error').inc()
                auth_login_duration.labels(environment=env, method=method).observe(duration)
                raise

        return wrapper
    return decorator


def track_db_query(operation='select', table='unknown'):
    """
    Decorator to track database query performance.

    Args:
        operation: Database operation ('select', 'insert', 'update', 'delete')
        table: Database table name

    Usage:
        @track_db_query(operation='select', table='User')
        def get_user():
            ...
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            env = get_environment()
            start_time = time.time()

            try:
                result = f(*args, **kwargs)
                duration = time.time() - start_time

                db_query_duration.labels(environment=env, operation=operation, table=table).observe(duration)

                if duration > 1.0:
                    db_slow_queries.labels(environment=env, table=table).inc()

                return result
            except Exception as e:
                duration = time.time() - start_time
                error_type = type(e).__name__
                db_query_errors.labels(environment=env, error_type=error_type, table=table).inc()
                db_query_duration.labels(environment=env, operation=operation, table=table).observe(duration)
                raise

        return wrapper
    return decorator


def track_email_send(email_type='notification'):
    """
    Decorator to track email sending.

    Args:
        email_type: Type of email ('verification', 'notification', 'reset')

    Usage:
        @track_email_send(email_type='verification')
        def send_verification_email():
            ...
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            env = get_environment()
            start_time = time.time()

            try:
                result = f(*args, **kwargs)
                duration = time.time() - start_time

                status = 'success' if result else 'failure'
                email_sent.labels(environment=env, email_type=email_type, status=status).inc()
                email_send_duration.labels(environment=env, email_type=email_type).observe(duration)

                return result
            except Exception as e:
                duration = time.time() - start_time
                email_sent.labels(environment=env, email_type=email_type, status='error').inc()
                email_send_duration.labels(environment=env, email_type=email_type).observe(duration)
                error_type = type(e).__name__
                smtp_connection_errors.labels(environment=env, error_type=error_type).inc()
                raise

        return wrapper
    return decorator


def track_discord_oauth():
    """
    Decorator to track Discord OAuth flow.

    Usage:
        @track_discord_oauth()
        def discord_callback():
            ...
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            env = get_environment()

            try:
                result = f(*args, **kwargs)

                # Determine status from response
                if isinstance(result, tuple) and len(result) >= 2:
                    status_code = result[1]
                elif hasattr(result, 'status_code'):
                    status_code = result.status_code
                else:
                    status_code = 200

                status = 'success' if status_code == 200 or status_code == 302 else 'error'
                discord_oauth_callbacks.labels(environment=env, status=status).inc()

                return result
            except Exception as e:
                discord_oauth_callbacks.labels(environment=env, status='error').inc()
                raise

        return wrapper
    return decorator


# ========================================
# HELPER FUNCTIONS
# ========================================

def track_active_sessions(count: int):
    """
    Update the active sessions gauge.

    Args:
        count: Number of active sessions
    """
    env = get_environment()
    auth_active_sessions.labels(environment=env).set(count)


def track_websocket_connection(connected: bool):
    """
    Track WebSocket connection/disconnection.

    Args:
        connected: True if connecting, False if disconnecting
    """
    env = get_environment()
    if connected:
        websocket_connections.labels(environment=env).inc()
    else:
        websocket_connections.labels(environment=env).dec()


def track_game_request_action(action: str):
    """
    Track game request action.

    Args:
        action: Action type ('created', 'accepted', 'rejected', 'expired', 'cancelled')
    """
    env = get_environment()
    game_requests.labels(environment=env, action=action).inc()


def track_notification(notification_type: str, channel: str, delivered: bool = True):
    """
    Track notification sent and delivery.

    Args:
        notification_type: Type of notification
        channel: Delivery channel ('websocket', 'email', 'in_app')
        delivered: Whether notification was successfully delivered
    """
    env = get_environment()
    notifications_sent.labels(environment=env, notification_type=notification_type, channel=channel).inc()
    if delivered:
        notifications_delivered.labels(environment=env, notification_type=notification_type, channel=channel).inc()


def update_ssl_certificate_expiry(domain: str, days_until_expiry: int):
    """
    Update SSL certificate expiry metric.

    Args:
        domain: Domain name
        days_until_expiry: Days until certificate expires
    """
    env = get_environment()
    ssl_certificate_expiry_days.labels(environment=env, domain=domain).set(days_until_expiry)


def track_rate_limit(endpoint: str, allowed: bool, reason: str = 'allowed'):
    """
    Track rate limiting decisions.

    Args:
        endpoint: API endpoint
        allowed: Whether request was allowed
        reason: Reason ('allowed', 'burst_exceeded', 'rate_exceeded')
    """
    env = get_environment()
    result = 'allowed' if allowed else reason
    rate_limit_hits.labels(environment=env, endpoint=endpoint, result=result).inc()

    if not allowed:
        rate_limit_blocks.labels(environment=env, endpoint=endpoint, reason=reason).inc()
