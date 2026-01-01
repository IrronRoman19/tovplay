"""
Security configuration for TovPlay backend.
Implements security headers, CSRF protection, rate limiting, and other security measures.
"""

import hashlib
import html
import os
import re
import secrets
from collections import defaultdict, deque
from datetime import datetime, timedelta
from functools import wraps
from http import HTTPMethod, HTTPStatus
from typing import Any, List, Union

from flask import request, jsonify, g, session
from werkzeug.datastructures import ImmutableMultiDict

from .logging_config import get_logger

logger = get_logger('tovplay.auth')


class SecurityConfig:
    """Security configuration settings."""

    # Security headers
    SECURITY_HEADERS = {
        # Prevent clickjacking
        'X-Frame-Options': 'DENY',

        # Prevent MIME type sniffing
        'X-Content-Type-Options': 'nosniff',

        # XSS protection
        'X-XSS-Protection': '1; mode=block',

        # Referrer policy
        'Referrer-Policy': 'strict-origin-when-cross-origin',

        # Permissions policy (restrict browser features)
        'Permissions-Policy': 'camera=(), microphone=(), geolocation=(), payment=()',

        # Content Security Policy (will be set dynamically)
        # 'Content-Security-Policy': 'default-src \'self\'',
    }

    # Rate limiting settings
    RATE_LIMIT_REQUESTS = 100  # requests per window
    RATE_LIMIT_WINDOW = 3600   # 1 hour in seconds
    RATE_LIMIT_BURST = 20      # burst limit for short periods

    # CORS settings
    CORS_ORIGINS = [
        'http://localhost:3000',  # Development frontend
        'http://127.0.0.1:3000',  # Development frontend
        'http://localhost:3001',  # Vite dev server (alt port)
        'http://localhost:3002',  # Vite dev server (alt port)
        'http://localhost:5173',  # Vite dev server
        'https://tovplay.vps.webdock.cloud',  # Production frontend
        'https://staging.tovplay.vps.webdock.cloud',  # Staging frontend
        'https://app.tovplay.org'  # Production frontend
    ]


class RateLimiter:
    """Simple in-memory rate limiter."""

    def __init__(self):
        self.requests = defaultdict(deque)
        self.burst_requests = defaultdict(deque)

    def is_allowed(self, key, requests_limit=100, window_seconds=3600, burst_limit=20, burst_window=60):
        """Check if request is allowed based on rate limits."""
        now = datetime.now()

        # Clean old requests
        self._clean_old_requests(key, now, window_seconds, burst_window)

        # Check burst limit (short-term)
        if len(self.burst_requests[key]) >= burst_limit:
            return False, 'burst_limit_exceeded'

        # Check general rate limit (long-term)
        if len(self.requests[key]) >= requests_limit:
            return False, 'rate_limit_exceeded'

        # Add current request
        self.requests[key].append(now)
        self.burst_requests[key].append(now)

        return True, 'allowed'

    def _clean_old_requests(self, key, now, window_seconds, burst_window):
        """Remove old requests outside the time windows."""
        # Clean general rate limit window
        cutoff = now - timedelta(seconds=window_seconds)
        while self.requests[key] and self.requests[key][0] < cutoff:
            self.requests[key].popleft()

        # Clean burst limit window
        burst_cutoff = now - timedelta(seconds=burst_window)
        while self.burst_requests[key] and self.burst_requests[key][0] < burst_cutoff:
            self.burst_requests[key].popleft()


# Global rate limiter instance
rate_limiter = RateLimiter()


def get_client_identifier(request):
    """Get a unique identifier for the client."""
    # Use X-Forwarded-For if behind proxy, otherwise use remote_addr
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    if ip and ',' in ip:
        ip = ip.split(',')[0].strip()

    # Include User-Agent to distinguish different clients from same IP
    user_agent = request.headers.get('User-Agent', '')[:100]

    # Create hash of IP + User-Agent
    identifier = f"{ip}:{hashlib.sha256(user_agent.encode()).hexdigest()[:16]}"
    return identifier


def setup_security_headers(app):
    """Setup security headers for all responses."""

    @app.after_request
    def add_security_headers(response):
        # Add basic security headers
        for header, value in SecurityConfig.SECURITY_HEADERS.items():
            response.headers[header] = value

        # Set Content Security Policy based on environment
        csp_policy = build_csp_policy()
        response.headers['Content-Security-Policy'] = csp_policy

        # Add HSTS header for HTTPS
        if request.is_secure:
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'

        return response

    logger.info("Security headers configured")


def build_csp_policy():
    """Build strict Content Security Policy based on environment."""
    env = os.getenv('FLASK_ENV', 'development').lower()

    if env == 'development':
        # Moderately restrictive CSP for development
        return (
            "default-src 'self'; "
            "script-src 'self' http://localhost:* ws://localhost:*; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: blob: https:; "
            "connect-src 'self' ws://localhost:* http://localhost:* https:; "
            "frame-ancestors 'none'; "
            "form-action 'self'; "
            "base-uri 'self'; "
            "object-src 'none'; "
            "media-src 'self'; "
            "worker-src 'self' blob:; "
            "manifest-src 'self'; "
            "upgrade-insecure-requests;"
        )
    else:
        # Very strict CSP for production
        return (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: blob:; "
            "connect-src 'self' https://app.tovplay.org https://staging.tovplay.org; "
            "frame-ancestors 'none'; "
            "form-action 'self'; "
            "base-uri 'self'; "
            "object-src 'none'; "
            "media-src 'self'; "
            "worker-src 'self'; "
            "manifest-src 'self'; "
            "upgrade-insecure-requests;"
        )


def setup_cors(app):
    """Setup CORS with security considerations."""
    from flask_cors import CORS

    # Get allowed origins from environment or use defaults
    allowed_origins = os.getenv('CORS_ORIGINS', '').split(',')
    allowed_origins = [origin.strip() for origin in allowed_origins if origin.strip()]

    if not allowed_origins:
        allowed_origins = SecurityConfig.CORS_ORIGINS

    # Configure CORS
    cors_config = {
        'origins': allowed_origins,
        'methods': ['GET', HTTPMethod.POST, HTTPMethod.PUT, HTTPMethod.DELETE, HTTPMethod.PATCH, 'OPTIONS'],
        'allow_headers': [
            'Content-Type',
            'Authorization',
            'X-Requested-With',
            'X-API-Key',
            'X-Request-ID'
        ],
        'expose_headers': [
            'X-Request-ID',
            'X-Rate-Limit-Remaining',
            'X-Rate-Limit-Reset'
        ],
        'supports_credentials': True,
        'max_age': 86400  # Cache preflight for 24 hours
    }

    CORS(app, **cors_config)

    logger.info(f"CORS configured for origins: {allowed_origins}")


def require_api_key(f):
    """Decorator to require API key authentication."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')

        if not api_key:
            logger.warning("API request without API key", extra={
                'ip_address': request.remote_addr,
                'endpoint': request.endpoint,
                'user_agent': request.headers.get('User-Agent', '')
            })
            return jsonify({'error': 'API key required'}), HTTPStatus.UNAUTHORIZED

        # Validate API key (implement your own logic)
        if not validate_api_key(api_key):
            logger.warning("Invalid API key used", extra={
                'ip_address': request.remote_addr,
                'endpoint': request.endpoint,
                'api_key_hash': hashlib.sha256(api_key.encode()).hexdigest()[:16]
            })
            return jsonify({'error': 'Invalid API key'}), HTTPStatus.UNAUTHORIZED

        return f(*args, **kwargs)

    return decorated_function


def rate_limit(requests_per_hour=100, burst_limit=20):
    """Decorator for rate limiting endpoints."""

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            client_id = get_client_identifier(request)

            allowed, reason = rate_limiter.is_allowed(
                client_id,
                requests_limit=requests_per_hour,
                burst_limit=burst_limit
            )

            if not allowed:
                logger.warning(f"Rate limit exceeded: {reason}", extra={
                    'client_id': client_id,
                    'endpoint': request.endpoint,
                    'ip_address': request.remote_addr
                })

                return jsonify({
                    'error': 'Rate limit exceeded',
                    'reason': reason,
                    'retry_after': 3600 if reason == 'rate_limit_exceeded' else 60
                }), 429

            # Add rate limit headers to response
            response = f(*args, **kwargs)

            if hasattr(response, 'headers'):
                remaining = max(0, requests_per_hour - len(rate_limiter.requests[client_id]))
                response.headers['X-Rate-Limit-Remaining'] = str(remaining)
                response.headers['X-Rate-Limit-Limit'] = str(requests_per_hour)

            return response

        return decorated_function

    return decorator


def validate_api_key(api_key):
    """Validate API key with secure environment-based validation."""
    # In production, check against environment variables
    api_keys_env = os.getenv('API_KEYS', '')
    if not api_keys_env:
        logger.error("API_KEYS environment variable is not set")
        return False

    valid_keys = [key.strip() for key in api_keys_env.split(',') if key.strip()]

    if not valid_keys:
        logger.error("No valid API keys found in API_KEYS environment variable")
        return False

    # Reject any default or test keys in production
    forbidden_keys = ['dev-api-key-change-in-production', 'test-key', 'example-key']
    if api_key.lower() in [key.lower() for key in forbidden_keys]:
        logger.warning(f"Forbidden development API key used: {api_key[:8]}...")
        return False

    return api_key in valid_keys


def generate_secure_api_key():
    """Generate a secure random API key for development/testing."""
    return secrets.token_urlsafe(32)


def secure_filename(filename):
    """Secure file upload filenames."""
    import re

    # Remove path components
    filename = os.path.basename(filename)

    # Remove or replace dangerous characters
    filename = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)

    # Limit length
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        filename = name[:255 - len(ext)] + ext

    return filename


def generate_csrf_token():
    """Generate CSRF token."""
    return secrets.token_urlsafe(32)


def validate_csrf_token(token):
    """Validate CSRF token against session."""
    # Get token from session
    session_token = session.get('csrf_token')
    if not session_token or not token:
        return False

    # Time-based validation (optional)
    return secrets.compare_digest(session_token, token)


def sanitize_input(text: Union[str, Any], max_length: int = 1000, remove_html: bool = True) -> Union[str, Any]:
    """Comprehensive input sanitization."""
    if not isinstance(text, str):
        return text

    # Limit length first
    if len(text) > max_length:
        text = text[:max_length]

    # Remove null bytes and control characters (except newlines/tabs)
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)

    # Remove potential script content
    dangerous_patterns = [
        r'<script[^>]*>.*?</script>',
        r'javascript:',
        r'vbscript:',
        r'onload\s*=',
        r'onerror\s*=',
        r'onclick\s*=',
        r'onmouseover\s*=',
        r'data:text/html',
    ]

    for pattern in dangerous_patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.DOTALL)

    # HTML escape if requested
    if remove_html:
        text = html.escape(text, quote=True)

    # Remove potential SQL injection patterns (when not using parameterized queries)
    sql_patterns = [
        r'(\b(UNION|SELECT|INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|EXEC)\b)',
        r'(--|\#|\/\*|\*\/)',
        r'(\bOR\b\s+1\s*=\s*1|\bAND\b\s+1\s*=\s*1)',
        r'(\'.*\'|".*")',
    ]

    for pattern in sql_patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)

    return text.strip()


class InputValidator:
    """Centralized input validation class."""

    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format with strict regex."""
        if not email or not isinstance(email, str):
            return False

        # RFC 5322 compliant email regex
        email_pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9._-]*[a-zA-Z0-9])?@[a-zA-Z0-9]([a-zA-Z0-9.-]*[a-zA-Z0-9])?\.[a-zA-Z]{2,}$'
        match = re.match(email_pattern, email.strip())
        return bool(match)

    @staticmethod
    def validate_username(username: str) -> tuple[bool, str]:
        """Validate username format.
        
        Returns:
            tuple: (is_valid, error_message)
        """
        if not username or not isinstance(username, str):
            return False, "Username is required"
            
        username = username.strip()
        
        # Length check
        if len(username) < 3 or len(username) > 30:
            return False, "Username must be between 3 and 30 characters"
            
        # Allowed characters: Hebrew letters, English letters, numbers, underscores, hyphens, dots
        # Hebrew letters: \u0590-\u05FF
        # English letters: a-zA-Z
        # Numbers: 0-9
        # Special chars: _-.
        if not re.match(r'^[\u0590-\u05FFa-zA-Z0-9_\-.]{3,30}$', username):
            return False, "Username can only contain Hebrew/English letters, numbers, underscores, hyphens, and dots"
            
        # Prevent consecutive special characters
        if re.search(r'[_.-]{2,}', username):
            return False, "Username cannot contain consecutive special characters"
            
        return True, ""

    @staticmethod
    def validate_password_strength(password: str) -> tuple[bool, List[str]]:
        """Validate password strength and return issues."""
        if not password or not isinstance(password, str):
            return False, ["Password is required"]

        issues = []

        if len(password) < 8:
            issues.append("Password must be at least 8 characters long")

        if len(password) > 128:
            issues.append("Password cannot exceed 128 characters")

        if not re.search(r'[A-Z]', password):
            issues.append("Password must contain at least one uppercase letter")

        if not re.search(r'[a-z]', password):
            issues.append("Password must contain at least one lowercase letter")

        if not re.search(r'\d', password):
            issues.append("Password must contain at least one digit")

        if not re.search(r'[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\/?]', password):
            issues.append("Password must contain at least one special character")

        # Check for common patterns
        if password.lower() in ['password', '12345678', 'qwerty123', 'admin123']:
            issues.append("Password is too common")

        # Check for sequential characters
        if re.search(r'(012|123|234|345|456|567|678|789)', password):
            issues.append("Password contains sequential characters")

        return len(issues) == 0, issues

    @staticmethod
    def validate_discord_username(username: str) -> bool:
        """Validate Discord username format.
        
        Supports both formats:
        - Username#1234 (legacy format)
        - Username (new format, alphanumeric with underscores, 3-30 chars)
        """
        if not username or not isinstance(username, str):
            return False
            
        username = username.strip()
        
        # Check for new format (username only)
        username_pattern = r'^[a-zA-Z0-9_]{3,30}$'
        if re.match(username_pattern, username):
            return True
            
        # Check for legacy format (username#1234)
        legacy_pattern = r'^[a-zA-Z0-9_.]{2,32}#\d{4}$'
        return bool(re.match(legacy_pattern, username))

    @staticmethod
    def validate_game_name(game_name: str) -> bool:
        """Validate game name."""
        if not game_name or not isinstance(game_name, str):
            return False

        # Allow letters, numbers, spaces, and common punctuation
        game_name = game_name.strip()
        if len(game_name) < 1 or len(game_name) > 100:
            return False

        return bool(re.match(r'^[a-zA-Z0-9\s\-\:._\'+&"]+$', game_name))

    @staticmethod
    def validate_otp_code(code: str) -> bool:
        """Validate OTP code format."""
        if not code or not isinstance(code, str):
            return False

        # 6-digit numeric code
        return bool(re.match(r'^\d{6}$', code.strip()))

    @staticmethod
    def validate_uuid(uuid_str: str) -> bool:
        """Validate UUID format."""
        if not uuid_str or not isinstance(uuid_str, str):
            return False

        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        return bool(re.match(uuid_pattern, uuid_str.lower()))


# Common validation schemas
USER_LOGIN_SCHEMA = {
    'Email': {
        'required': True,
        'type': 'str',
        'validator': InputValidator.validate_email,
        'max_length': 254,
        'sanitize': True
    },
    'Password': {
        'required': True,
        'type': 'str',
        'min_length': 8,
        'max_length': 128,
        'sanitize': False  # Don't sanitize passwords
    }
}

USER_SIGNUP_SCHEMA = {
    'Email': {
        'required': True,
        'type': 'str',
        'validator': InputValidator.validate_email,
        'max_length': 254,
        'sanitize': True
    },
    'Password': {
        'required': True,
        'type': 'str',
        'min_length': 8,
        'max_length': 128,
        'sanitize': False
    },
    'Username': {
        'required': True,
        'type': 'str',
        'validator': InputValidator.validate_username,
        'max_length': 30,
        'sanitize': True
    },
    'DiscordUsername': {
        'required': True,
        'type': 'str',
        'validator': InputValidator.validate_discord_username,
        'max_length': 37,
        'sanitize': True
    }
}

OTP_VERIFICATION_SCHEMA = {
    'email': {
        'required': True,
        'type': 'str',
        'validator': InputValidator.validate_email,
        'max_length': 254,
        'sanitize': True
    },
    'otp_code': {
        'required': True,
        'type': 'str',
        'validator': InputValidator.validate_otp_code,
        'sanitize': False
    }
}

GAME_REQUEST_SCHEMA = {
    'game_name': {
        'required': True,
        'type': 'str',
        'validator': InputValidator.validate_game_name,
        'max_length': 100,
        'sanitize': True
    },
    'recipient_username': {
        'required': True,
        'type': 'str',
        'validator': InputValidator.validate_username,
        'max_length': 30,
        'sanitize': True
    }
}


def setup_input_validation(app):
    """Setup input validation middleware."""

    @app.before_request
    def validate_and_sanitize_input():
        # Skip validation for health checks, OPTIONS requests, and specific user endpoints
        if request.endpoint in ('health', 'health_check') or request.method == 'OPTIONS' or (
                request.method == 'GET' and request.path.startswith('/api/users/')):
            return

        # Validate JSON data
        if request.is_json and request.method in [HTTPMethod.POST, HTTPMethod.PUT,
                                                  HTTPMethod.PATCH] and request.get_json():
            try:
                json_data = request.get_json()

                # Sanitize all string fields in JSON
                def sanitize_dict(d):
                    if isinstance(d, dict):
                        return {k: sanitize_dict(v) if isinstance(v, (dict, list)) else v
                        if isinstance(v, str) else sanitize_input(v, 2000) for k, v in d.items()}
                    elif isinstance(d, list):
                        return [sanitize_dict(item) for item in d]
                    return d

                sanitized_data = sanitize_dict(json_data)
                request._cached_json = (sanitized_data, False)

            except Exception as e:
                logger.warning(f"Input validation error: {e}")
                return jsonify({'error': 'Invalid request data format'}), HTTPStatus.BAD_REQUEST

        # Sanitize query parameters
        if request.args:
            # Create a mutable copy of request.args
            mutable_args = request.args.copy()

            sanitized_args = {}
            for key, value in mutable_args.items():
                if isinstance(value, str):
                    sanitized_args[key] = sanitize_input(value, HTTPStatus.OK)
                else:
                    sanitized_args[key] = value

            # Replace request.args with a new ImmutableMultiDict created from the sanitized data
            request.args = ImmutableMultiDict(sanitized_args)

        # Log suspicious requests
        suspicious_patterns = [
            r'<script',
            r'javascript:',
            r'union\s+select',
            r'drop\s+table',
            r'exec\s*\(',
            r'eval\s*\(',
            r'system\s*\(',
        ]

        # Only try to get JSON for methods that support request bodies
        json_str = ''
        if request.is_json and request.method in [HTTPMethod.POST, HTTPMethod.PUT, HTTPMethod.PATCH]:
            try:
                json_str = str(request.get_json() or '')
            except:
                json_str = ''

        request_text = str(request.data) + str(request.args) + json_str

        for pattern in suspicious_patterns:
            if re.search(pattern, request_text, re.IGNORECASE):
                logger.warning(f"Suspicious request pattern detected: {pattern[:20]}...", extra={
                    'ip_address': request.remote_addr,
                    'path': request.path,
                    'method': request.method
                })
                break

    logger.info("Input validation middleware configured")


def setup_request_logging(app):
    """Setup security-focused request logging."""

    @app.before_request
    def log_request():
        g.request_start_time = datetime.now()

        # Log potentially suspicious requests
        suspicious_patterns = [
            'admin', 'wp-admin', 'phpMyAdmin', '.php',
            'shell', 'cmd', 'exec', 'eval',
            '<script', 'javascript:', 'vbscript:',
            'union select', 'drop table', 'or 1=1'
        ]

        path = request.path.lower()
        query = request.query_string.decode('utf-8', errors='ignore').lower()

        if any(pattern in path or pattern in query for pattern in suspicious_patterns):
            logger.warning("Suspicious request detected", extra={
                'ip_address': request.remote_addr,
                'path': request.path,
                'query_string': request.query_string.decode('utf-8', errors='ignore'),
                'user_agent': request.headers.get('User-Agent', ''),
                'referer': request.headers.get('Referer', '')
            })

    @app.after_request
    def log_response(response):
        if hasattr(g, 'request_start_time'):
            duration = (datetime.now() - g.request_start_time).total_seconds()

            # Log slow or failed requests
            if duration > 2.0 or response.status_code >= HTTPStatus.BAD_REQUEST:
                logger.info("Request completed", extra={
                    'ip_address': request.remote_addr,
                    'method': request.method,
                    'path': request.path,
                    'status_code': response.status_code,
                    'duration_seconds': round(duration, 3),
                    'content_length': response.content_length or 0
                })

        return response


def setup_csrf_protection(app):
    """Setup CSRF protection for Flask app without external dependencies."""

    # Get CSRF secret key from environment
    csrf_secret_key = os.getenv('CSRF_SECRET_KEY')
    if not csrf_secret_key:
        logger.warning("CSRF_SECRET_KEY not found in environment, generating temporary key")
        csrf_secret_key = secrets.token_urlsafe(32)

    app.config['CSRF_SECRET_KEY'] = csrf_secret_key

    @app.after_request
    def add_csrf_token(response):
        """Add CSRF token to response headers for AJAX requests."""
        if request.method in ['GET', HTTPMethod.POST, HTTPMethod.PUT, HTTPMethod.DELETE, HTTPMethod.PATCH]:
            # Generate new CSRF token for each request
            csrf_token = generate_csrf_token()
            session['csrf_token'] = csrf_token
            response.headers['X-CSRF-Token'] = csrf_token
        return response

    @app.before_request
    def validate_csrf_for_state_changes():
        """Validate CSRF token for state-changing requests."""
        # Skip CSRF validation for safe methods, health checks, and specific auth endpoints
        if (request.method in ['GET', 'HEAD', 'OPTIONS'] or
                request.endpoint in ('health', 'health_check') or
                request.path.startswith('/api/auth/') or
                request.path.startswith('/api/users/login')):
            return

        # For API requests, check CSRF token in header first
        if request.path.startswith('/api/'):
            csrf_token = request.headers.get('X-CSRF-Token')
            if not csrf_token or not validate_csrf_token(csrf_token):
                # Fallback to checking JSON body
                if request.is_json:
                    json_data = request.get_json() or {}
                    csrf_token = json_data.get('csrf_token')
                    if not csrf_token or not validate_csrf_token(csrf_token):
                        return jsonify({'error': 'CSRF token validation failed'}), HTTPStatus.FORBIDDEN
                else:
                    return jsonify({'error': 'CSRF token validation failed'}), HTTPStatus.FORBIDDEN

        # For form submissions, check form field
        elif request.form:
            csrf_token = request.form.get('csrf_token')
            if not csrf_token or not validate_csrf_token(csrf_token):
                return jsonify({'error': 'CSRF token validation failed'}), HTTPStatus.FORBIDDEN

        # For JSON requests, check JSON body
        elif request.is_json:
            json_data = request.get_json() or {}
            csrf_token = json_data.get('csrf_token')
            if not csrf_token or not validate_csrf_token(csrf_token):
                return jsonify({'error': 'CSRF token validation failed'}), HTTPStatus.FORBIDDEN

    logger.info("CSRF protection configured")


def csrf_protect(f):
    """Decorator to add CSRF protection to specific routes."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Skip CSRF for GET requests
        if request.method == 'GET':
            return f(*args, **kwargs)

        # Validate CSRF token
        csrf_token = None

        # Check various sources for CSRF token
        if request.is_json:
            json_data = request.get_json() or {}
            csrf_token = json_data.get('csrf_token')
        elif request.form:
            csrf_token = request.form.get('csrf_token')
        elif request.headers:
            csrf_token = request.headers.get('X-CSRF-Token')

        if not csrf_token or not validate_csrf_token(csrf_token):
            return jsonify({'error': 'CSRF token validation failed'}), HTTPStatus.FORBIDDEN

        return f(*args, **kwargs)

    return decorated_function


def setup_security(app):
    """Setup all security measures."""
    logger.info("Setting up security configuration...")

    # Setup security headers
    setup_security_headers(app)

    # Setup CORS
    setup_cors(app)

    # Setup CSRF protection
    # setup_csrf_protection(app)
    #Note: CSRF protection is currently disabled for API routes due to client limitations.

    # Setup input validation
    setup_input_validation(app)

    # Setup request logging
    setup_request_logging(app)

    logger.info("Security configuration completed")


# Security utility functions for use in routes
def get_secure_headers():
    """Get secure headers for manual application."""
    return SecurityConfig.SECURITY_HEADERS.copy()


def is_safe_url(url, allowed_hosts=None):
    """Check if URL is safe for redirects."""
    from urllib.parse import urlparse

    if not url:
        return False

    parsed = urlparse(url)

    # Only allow relative URLs or URLs from allowed hosts
    if not parsed.netloc:
        return True  # Relative URL

    if allowed_hosts:
        return parsed.netloc in allowed_hosts

    # Default allowed hosts
    default_hosts = ['app.tovplay.org', 'tovplay.vps.webdock.cloud', 'staging.tovplay.vps.webdock.cloud']
    return parsed.netloc in default_hosts


def hash_password(password):
    """Hash password securely."""
    import bcrypt
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(password, hashed):
    """Verify password against hash."""
    import bcrypt
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))


# Example usage:
"""
from src.app.security import rate_limit, require_api_key, sanitize_input

@app.route('/api/sensitive')
@rate_limit(requests_per_hour=50)
@require_api_key
def sensitive_endpoint():
    data = request.get_json()
    data['message'] = sanitize_input(data.get('message', ''))
    return jsonify(data)

"""
