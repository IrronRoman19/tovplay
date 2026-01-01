import datetime
import os
import smtplib
import ssl
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from functools import wraps

import bcrypt
from flask import request, jsonify
import jwt

from .error_handlers import ValidationError, AuthenticationError
from .models import GameRequest, ScheduledSession, db, User
from http import HTTPStatus
from .logging_config import get_logger

logger = get_logger('tovplay.services')

# For a production application, it's best to store the salt rounds
# in an environment variable. A higher number is more secure but slower.
SALT_ROUNDS = int(os.environ.get("BCRYPT_SALT_ROUNDS", 12))
JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY")
JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM")
WEBSITE_URL = os.environ.get("WEBSITE_URL")
def hash_password(password: str) -> str:
    hashed_password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=SALT_ROUNDS))
    return hashed_password.decode("utf-8")


def compare_password_hashed(password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))


def send_verification_email(receiver_email, verification_code):
    """
    Sends a verification email with a 6-digit code.
    This function uses environment variables for secure email credentials.
    """
    # Use environment variables for sensitive data
    sender_email = os.environ.get("EMAIL_SENDER")
    password = os.environ.get("EMAIL_PASSWORD")
    smtp_server = os.environ.get("SMTP_SERVER")
    smtp_port = os.environ.get("SMTP_PORT")

    if not sender_email or not password:
        print("Email credentials not found in environment variables. Cannot send email.")
        return False

    message = MIMEMultipart("alternative")
    message["Subject"] = "Tovplay: Email Verification"
    message["From"] = sender_email
    message["To"] = receiver_email

    # Plain-text version of the email
    text = f"""\
    Hi there,

    Thank you for signing up for Tovplay! Please use the following code to verify your email address:

    {verification_code}

    If you did not sign up for this service, please ignore this email.

    Thanks,
    The Tovplay Team
    """

    # HTML version of the email for better formatting
    html = f"""\
    <html>
      <body style="font-family: sans-serif; background-color: #f4f4f4; padding: 20px; text-align: center;">
        <div style="background-color: #ffffff; max-width: 600px; margin: auto; padding: 40px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);">
          <h1 style="color: #333333;">Tovplay: Email Verification</h1>
          <p style="color: #555555; font-size: 16px;">Thank you for signing up! Please use the code below to verify your email address:</p>
          <div style="background-color: #f0f8ff; border: 1px solid #c0d8f0; border-radius: 5px; padding: 20px; margin: 30px 0;">
            <p style="color: #333333; font-size: 32px; font-weight: bold; margin: 0; letter-spacing: 5px;">
                <a href="{WEBSITE_URL}/verifyOTP?email={receiver_email}&otp={verification_code}">Verify Email</a>
            </p>
          </div>
          <p style="color: #888888; font-size: 14px;">If you did not sign up for this service, please ignore this email.</p>
          <hr style="border: none; border-top: 1px solid #dddddd; margin: 20px 0;">
          <p style="color: #555555; font-size: 14px;">Thanks,<br>The Tovplay Team</p>
        </div>
      </body>
    </html>
    """

    part1 = MIMEText(text, "plain")
    part2 = MIMEText(html, "html")

    message.attach(part1)
    message.attach(part2)

    # Defensive: ensure there are no attachments in the message payload.
    # Some library or earlier code could accidentally add attachments —
    # filter them out so verification emails remain clean.
    try:
        clean_parts = []
        removed_attachments = 0
        for part in message.get_payload():
            disposition = None
            try:
                disposition = part.get_content_disposition()
            except Exception:
                disposition = None
            if disposition == 'attachment':
                removed_attachments += 1
                continue
            clean_parts.append(part)
        if removed_attachments:
            logger.warning(f"Removed {removed_attachments} attachment(s) from verification email to {receiver_email}")
        # Replace payload with filtered parts (keeps plain/html parts)
        message.set_payload(clean_parts)
    except Exception as e:
        # If defensive cleaning fails for any reason, log and continue — do not block sending.
        logger.error("Failed to sanitize email parts before sending: %s", str(e))

    context = ssl.create_default_context()
    try:
        with smtplib.SMTP_SSL(smtp_server, smtp_port, context=context) as server:
            server.login(sender_email, password)
            server.sendmail(sender_email, receiver_email, message.as_string())
        print(f"Verification email sent to {receiver_email}")
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False


def expire_old_game_requests(app):
    with app.app_context():
        cutoff_time = datetime.datetime.now() - datetime.timedelta(hours=24)
        expired_requests = GameRequest.query.filter(
            GameRequest.status == "pending", GameRequest.suggested_time < cutoff_time
        ).all()

        for request in expired_requests:
            request.status = "expired"

        db.session.commit()
        print(f"Expired {len(expired_requests)} game requests.")


def update_scheduled_session_statuses(app):
    """
    TODO: Verify that the code works
    https://tovplay.atlassian.net/browse/TVPL-133
    """
    with app.app_context():
        current_time = datetime.now()
        active_sessions = ScheduledSession.query.filter(ScheduledSession.status != "cancelled").all()
        for session in active_sessions:
            session_start = datetime.combine(session.scheduled_date, session.start_time)
            session_end = datetime.combine(session.scheduled_date, session.end_time)
            original_status = session.status

            if session_start - timedelta(minutes=30) <= current_time < session_start:
                session.status = "upcoming"
            elif session_start <= current_time < session_end:
                session.status = "in_progress"
            elif current_time >= session_end:
                session.status = "completed"

            if session.status != original_status:
                print(
                    f"Session {session.id}: Status changed from {original_status} to {session.status} "
                    f"(start: {session_start}, end: {session_end}, now: {current_time})"
                )
        db.session.commit()


def validate_jwt_environment():
    """Validate JWT environment variables are properly set."""
    if not JWT_SECRET_KEY or JWT_SECRET_KEY in [
        'change-me-in-production',
        'dev-secret-key',
        'your-secret-key',
        'insecure-key'
    ]:
        logger.error("JWT_SECRET_KEY is not securely configured")
        raise AuthenticationError("JWT configuration error", status_code=HTTPStatus.INTERNAL_SERVER_ERROR)
    
    if not JWT_ALGORITHM:
        logger.error("JWT_ALGORITHM is not configured")
        raise AuthenticationError("JWT configuration error", status_code=HTTPStatus.INTERNAL_SERVER_ERROR)
    
    # Check JWT secret key strength
    if len(JWT_SECRET_KEY) < 32:
        logger.error("JWT_SECRET_KEY is too short (minimum 32 characters required)")
        raise AuthenticationError("JWT configuration error", status_code=HTTPStatus.INTERNAL_SERVER_ERROR)


def get_user_id_from_token():
    """Secure JWT token validation with environment validation."""
    # Validate JWT environment first
    validate_jwt_environment()
    
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        raise AuthenticationError("Authorization header required", status_code=HTTPStatus.UNAUTHORIZED)

    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != 'bearer':
        raise AuthenticationError("Invalid authorization header format. Use: Bearer <token>", status_code=HTTPStatus.UNAUTHORIZED)
    
    token = parts[1]
    
    if not token or len(token) < 10:
        raise AuthenticationError("Invalid token format", status_code=HTTPStatus.UNAUTHORIZED)

    try:
        # Decode the token to get the payload
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM], options={
            'verify_signature': True,
            'verify_exp': True,
            'verify_iat': True,
            'verify_sub': True,
            'require': ['user_id', 'exp', 'iat', 'sub']
        })
        
        user_id = payload.get('user_id')
        if not user_id:
            raise AuthenticationError("Invalid token payload", status_code=HTTPStatus.UNAUTHORIZED)
        
        # Log successful token validation if needed for security monitoring
        logger.info("JWT token validated successfully", extra={
            'user_id': user_id,
            'ip_address': request.remote_addr
        })
        
        return user_id
        
    except jwt.ExpiredSignatureError:
        logger.warning("Expired JWT token used", extra={
            'ip_address': request.remote_addr,
            'token_preview': token[:20] + "..." if len(token) > 20 else token
        })
        raise AuthenticationError("JWT token has expired", status_code=HTTPStatus.UNAUTHORIZED)
    except jwt.InvalidTokenError as e:
        logger.warning("Invalid JWT token used", extra={
            'ip_address': request.remote_addr,
            'error': str(e)
        })
        raise AuthenticationError("JWT token is invalid", status_code=HTTPStatus.UNAUTHORIZED)
    except Exception as e:
        logger.error("Unexpected JWT validation error", extra={
            'ip_address': request.remote_addr,
            'error': str(e)
        })
        raise AuthenticationError("JWT validation failed", status_code=HTTPStatus.UNAUTHORIZED)

def check_admin(current_user_id=None):
    """
    Strict admin authorization check.
    Only users with Admin role can access admin functions.
    """
    user_id = get_user_id_from_token()
    if not user_id:
        raise AuthenticationError("Authentication required for admin access", status_code=HTTPStatus.UNAUTHORIZED)
    
    user = User.query.get_or_404(user_id)
    
    # Strict check: user MUST be Admin role
    if user.role != "Admin":
        logger.warning(f"Non-admin user attempted admin access", extra={
            'user_id': user_id,
            'user_role': user.role,
            'ip_address': request.remote_addr if 'request' in globals() else None
        })
        raise AuthenticationError("Admin access required", status_code=HTTPStatus.FORBIDDEN)
    
    return user_id


def require_admin_role():
    """
    Decorator to require Admin role for endpoints.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_id = get_user_id_from_token()
            if not user_id:
                return jsonify({'error': 'Authentication required'}), 401
            
            user = User.query.get_or_404(user_id)
            if user.role != "Admin":
                logger.warning(f"Non-admin user attempted access to protected endpoint", extra={
                    'user_id': user_id,
                    'user_role': user.role,
                    'endpoint': request.endpoint if 'request' in globals() else None,
                    'ip_address': request.remote_addr if 'request' in globals() else None
                })
                return jsonify({'error': 'Admin access required'}), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def require_role_or_self(required_role="Admin", allow_self=True):
    """
    Decorator to require specific role or the user themselves.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_id = get_user_id_from_token()
            if not user_id:
                return jsonify({'error': 'Authentication required'}), 401
            
            # For self-allowed endpoints that specify a user_id parameter
            target_user_id = None
            if allow_self:
                # Try to get target user from route parameters or request data
                if 'user_id' in kwargs:
                    target_user_id = kwargs['user_id']
                elif request and request.is_json:
                    json_data = request.get_json() or {}
                    target_user_id = json_data.get('user_id')
                elif request and request.args:
                    target_user_id = request.args.get('user_id')
            
            user = User.query.get_or_404(user_id)
            
            # Check if user is admin or accessing their own data
            is_admin = user.role == required_role
            is_self = allow_self and target_user_id and str(user_id) == str(target_user_id)
            
            if not (is_admin or is_self):
                logger.warning(f"Unauthorized access attempt", extra={
                    'user_id': user_id,
                    'user_role': user.role,
                    'required_role': required_role,
                    'endpoint': request.endpoint if 'request' in globals() else None,
                    'ip_address': request.remote_addr if 'request' in globals() else None
                })
                return jsonify({'error': f'{required_role} access required'}), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator
