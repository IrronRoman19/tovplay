import json
import os
import time
from http import HTTPStatus
from threading import Thread
from urllib.parse import quote

import requests
from flask import Blueprint, Flask, jsonify, request, redirect
from flask_cors import CORS
from sqlalchemy.orm import Session

from bot import bot
from src.app import db
from src.app.extensions import limiter
from src.app.models import User
from src.app.routes.signup_signin import (
    delete_user_cascade,
    email_verification_code,
    signin,
    signup_user, check_password,
)
from src.app.services import get_user_id_from_token, check_admin
from src.app.services import hash_password
from src.app.custom_metrics import (
    auth_login_attempts,
    auth_login_duration,
    auth_login_failure_reasons,
    auth_signup_attempts,
    auth_signup_duration,
    auth_email_verification_attempts,
    auth_password_change_attempts,
    user_deletion_attempts,
    username_availability_checks,
    discord_oauth_callbacks,
    discord_token_exchange_duration,
    discord_api_errors,
)

basedir = os.path.abspath(os.path.dirname(__file__))
WEBSITE_URL = os.environ.get("WEBSITE_URL")


def run_discord_bot():
    TOKEN = os.getenv("DISCORD_TOKEN")  # שמי אותו ב-.env שלך
    bot.run(TOKEN)


Thread(target=run_discord_bot, daemon=True).start()

app = Flask(__name__)
CORS(app)
user_bp = Blueprint("users", __name__)


@app.route('/')
def home():
    return "Hello from my backend!"


@user_bp.route("/", methods=["GET"])
def get_users():
    check_admin()
    users = User.query.all()
    return jsonify(
        [
            {
                "id": user.id,
                "email": user.email,
                "discord_username": user.discord_username,
            }
            for user in users
        ]
    )


import logging

logger = logging.getLogger(__name__)


@user_bp.route("/<uuid:user_id>", methods=["GET"])
def get_user_by_id(user_id):
    try:
        user = User.query.get_or_404(user_id)
        logger.debug(f"User found: {user.email}")
        return jsonify(user.to_dict()), HTTPStatus.OK
    except Exception as e:
        logger.error(f"Error fetching user by ID {user_id}: {e}", exc_info=True)
        return jsonify({"message": "Error fetching user profile", "error": str(e)}), HTTPStatus.BAD_REQUEST


@user_bp.route("/login", methods=["POST"])
@limiter.limit("5/minute")
def login():
    
    start_time = time.time()
    environment = os.environ.get("FLASK_ENV", "production")

    
    try:
        if request.content_type != "application/json":
            
            auth_login_attempts.labels(
                environment=environment,
                status='error',
                method='email'
            ).inc()
            return jsonify({"message": "Content-Type must be 'application/json'"}), HTTPStatus.UNSUPPORTED_MEDIA_TYPE
        
        data = request.get_json()
        db_session: Session = db.session
        jwt_secret_key = os.environ.get("JWT_SECRET_KEY")
        jwt_algorithm = os.environ.get("JWT_ALGORITHM")

        print("jwt_secret_key: ", type(jwt_secret_key), jwt_secret_key)
        
        
        user_id, jwt_token = signin(data, jwt_secret_key, jwt_algorithm)
        
        
        auth_login_attempts.labels(
            environment=environment,
            status='success',
            method='email'
        ).inc()
        
        duration = time.time() - start_time
        auth_login_duration.labels(
            environment=environment,
            status='success'
        ).observe(duration)

        return jsonify({
            "message": "User signed in successfully!", 
            "user_id": user_id, 
            "jwt_token": jwt_token
        }), HTTPStatus.OK

    
    except ValueError as e:
        
        auth_login_attempts.labels(
            environment=environment,
            status='failure',
            method='email'
        ).inc()

        error_msg = str(e).lower()
        if 'incorrect' in error_msg or 'password' in error_msg:
            reason = 'invalid_password'
        elif 'not found' in error_msg or 'email' in error_msg:
            reason = 'user_not_found'
        elif 'verified' in error_msg:
            reason = 'email_not_verified'
        else:
            reason = 'other'

        auth_login_failure_reasons.labels(
            environment=environment,
            reason=reason,
            method='email'
        ).inc()

        duration = time.time() - start_time
        auth_login_duration.labels(
            environment=environment,
            status='failure'
        ).observe(duration)

        return jsonify({"message": str(e)}), HTTPStatus.UNAUTHORIZED

    
    except Exception as e:
        
        auth_login_attempts.labels(
            environment=environment,
            status='error',
            method='email'
        ).inc()

        duration = time.time() - start_time
        auth_login_duration.labels(
            environment=environment,
            status='error'
        ).observe(duration)

        logger = logging.getLogger(__name__)
        logger.error(f"Login error: {str(e)}")
        return jsonify({"message": "Server error during login"}), HTTPStatus.INTERNAL_SERVER_ERROR


@user_bp.route("/delete_user", methods=["DELETE"])
def delete_user():
    environment = os.environ.get("FLASK_ENV", "production")
    try:
        user_id = str(get_user_id_from_token())
        user = User.query.get_or_404(user_id)
        print(str(user.id), str(user_id), str(user.id) != user_id)
        if user.role != "Admin" and str(user.id) != user_id:
            
            user_deletion_attempts.labels(
                environment=environment,
                status='unauthorized'
            ).inc()
            raise ValueError("Not authorized")
        user_id = request.get_json().get("user_id")
        delete_user_cascade(user_id)

        
        user_deletion_attempts.labels(
            environment=environment,
            status='success'
        ).inc()

        return jsonify({"message": "User deleted successfully!", "user_id": user_id}), HTTPStatus.DELETED
    except ValueError as e:
        
        return jsonify({"message": str(e)}), HTTPStatus.FORBIDDEN
    except Exception as e:
        
        user_deletion_attempts.labels(
            environment=environment,
            status='error'
        ).inc()
        print("DB error:", e)
        logger.error(f"User deletion error: {str(e)}")
        return jsonify({"message": "Failed to delete user!", "error": str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR


@user_bp.route("/signup", methods=["POST"])
@limiter.limit("10/minute")
def signup():
    start_time = time.time()
    environment = os.environ.get("FLASK_ENV", "production")
    data = request.get_json()
    db_session: Session = db.session
    try:
        user = signup_user(data)

        # Track successful signup
        auth_signup_attempts.labels(
            environment=environment,
            status='success'
        ).inc()

        duration = time.time() - start_time
        auth_signup_duration.labels(
            environment=environment,
            status='success'
        ).observe(duration)

        return jsonify({"message": "User created successfully!", "user_id": user.id}), HTTPStatus.CREATED

    except ValueError as e:
        db_session.rollback()
        return jsonify({"message": "Failed to create user", "error": str(e)}), HTTPStatus.BAD_REQUEST # <-- 400

    except Exception as e:
        db_session.rollback()

        # Track signup failure
        auth_signup_attempts.labels(
            environment=environment,
            status='failure'
        ).inc()

        duration = time.time() - start_time
        auth_signup_duration.labels(
            environment=environment,
            status='failure'
        ).observe(duration)

        print("DB error:", e)
        return jsonify({"message": "Failed to create user", "error": str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR


@user_bp.route('/username-availability', methods=['POST'])
def check_username_availability():
    environment = os.environ.get("FLASK_ENV", "production")
    data = request.get_json()
    username = data.get("Username")

    # Check if the username exists in the database
    try:
        user = User.query.filter_by(username=username).first()
        if user:
            # Track unavailable username check
            username_availability_checks.labels(
                environment=environment,
                result='unavailable'
            ).inc()
            return jsonify({"isAvailable": False}), HTTPStatus.OK

        # Track available username check
        username_availability_checks.labels(
            environment=environment,
            result='available'
        ).inc()
        return jsonify({"isAvailable": True}), HTTPStatus.OK
    except Exception as e:
        # Track error
        username_availability_checks.labels(
            environment=environment,
            result='error'
        ).inc()
        print("DB error:", e)
        logger.error(f"Username availability check error: {str(e)}")
        return jsonify(
            {"message": "Failed to check username availability", "error": str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR


auth_bp = Blueprint("auth", __name__)


# Helper: load Discord credentials from env or secrets file
def _load_discord_creds():
    """Load Discord OAuth credentials from environment variables or secrets file."""
    client_id = os.environ.get("DISCORD_CLIENT_ID")
    client_secret = os.environ.get("DISCORD_CLIENT_SECRET")
    if not (client_id and client_secret):
        try:
            # Try multiple common locations for secrets file
            routes_dir = os.path.dirname(__file__)
            app_dir = os.path.dirname(routes_dir)  # src/app
            src_dir = os.path.dirname(app_dir)  # src
            project_root = os.path.dirname(src_dir)  # backend
            candidate_paths = [
                os.path.join(project_root, "config", "discord.secrets.json"),
                os.path.join(app_dir, "config", "discord.secrets.json"),
            ]
            for secrets_path in candidate_paths:
                if os.path.exists(secrets_path):
                    with open(secrets_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        client_id = client_id or data.get("client_id")
                        client_secret = client_secret or data.get("client_secret")
                    break
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.debug(f"Could not load Discord OAuth secrets: {str(e)}")
    return client_id, client_secret


def _compute_redirect_uri():
    """Compute Discord OAuth redirect URI based on environment."""
    flask_env = os.environ.get("FLASK_ENV", "").lower()
    is_production = flask_env == "production"
    is_staging = flask_env == "staging"
    is_test = flask_env == "test"

    # Priority: Check for explicit redirect URI in environment
    explicit_redirect = os.environ.get("DISCORD_REDIRECT_URI")
    if explicit_redirect:
        return explicit_redirect

    # Environment-based redirect URIs
    if is_staging:
        redirect_uri = "https://staging.tovplay.org/api/auth/discord/callback"
    if is_production:
        redirect_uri = "https://app.tovplay.org/api/auth/discord/callback"
    elif is_test:
        # Test/staging environment: use test subdomain
        redirect_uri = "https://test.tovplay.org/api/auth/discord/callback"
    else:
        # Local development: use localhost callback
        # This must be whitelisted in Discord Developer Portal
        redirect_uri = "http://localhost:5001/api/auth/discord/callback"

    return redirect_uri


@auth_bp.route("/verify-otp", methods=["GET"])
def verify():
    environment = os.environ.get("FLASK_ENV", "production")
    try:
        email = request.args.get("email")
        code = request.args.get("otp_code")
        user = User.query.filter_by(email=email).first()
        if not user:
            # Track verification failure (user not found)
            auth_email_verification_attempts.labels(
                environment=environment,
                status='failure'
            ).inc()
            raise ValueError("User not found.")
        if not user.email:
            # Track verification failure (no email)
            auth_email_verification_attempts.labels(
                environment=environment,
                status='failure'
            ).inc()
            raise ValueError("User does not have an email for verification.")
        email_verification_code(user.email, code)

        # Track successful verification
        auth_email_verification_attempts.labels(
            environment=environment,
            status='success'
        ).inc()

        return jsonify({"message": "Email verified successfully!", "email": email}), HTTPStatus.CREATED
    except ValueError as e:
        # ValueError is already tracked above
        return jsonify({"message": str(e)}), HTTPStatus.BAD_REQUEST
    except requests.RequestException as e:
        # Track verification error (service unavailable)
        auth_email_verification_attempts.labels(
            environment=environment,
            status='error'
        ).inc()
        db.session.rollback()
        logger.error(f"Email verification error: {str(e)}")
        return jsonify(
            {"message": "Failed to contact verification service", "error": str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR


@user_bp.route("/change_password", methods=["PUT"])
def change_password():
    environment = os.environ.get("FLASK_ENV", "production")
    try:
        user_id = get_user_id_from_token()
        user = User.query.get_or_404(user_id)
        if not user:
            # Track password change failure
            auth_password_change_attempts.labels(
                environment=environment,
                status='failure'
            ).inc()
            return jsonify(
                {"message": "Couldn't find user"}), HTTPStatus.INTERNAL_SERVER_ERROR

        password = request.get_json().get("Password")
        print(password)
        check_password(password)
        hashed_pw = hash_password(password)
        setattr(user, "hashed_password", hashed_pw)
        db.session.commit()

        # Track successful password change
        auth_password_change_attempts.labels(
            environment=environment,
            status='success'
        ).inc()

        return jsonify({"message": "Password updated successfully!"}), HTTPStatus.ACCEPTED
    except Exception as e:
        # Track password change error
        auth_password_change_attempts.labels(
            environment=environment,
            status='error'
        ).inc()
        logger.error(f"Password change error: {str(e)}")
        return jsonify({"message": "Failed to change password", "error": str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR


@user_bp.route("/get_user", methods=["GET"])
def get_user():

    environment = os.environ.get("FLASK_ENV", "production")


    try:
        user_id = get_user_id_from_token()
        user = User.query.get_or_404(user_id)
        logger.debug(f"User found: {user.email}")
        return jsonify(user.to_dict()), HTTPStatus.OK
    except Exception as e:
        logger.error(f"Error fetching user by ID {user_id}: {e}", exc_info=True)
        return jsonify({"message": "Error fetching user profile", "error": str(e)}), HTTPStatus.BAD_REQUEST
    #
    #     # Track successful profile fetch
    #     user_profile_fetches.labels(
    #         environment=environment,
    #         status='success'
    #     ).inc()
    #
    #     return jsonify(user.to_dict()), HTTPStatus.OK
    # except Exception as e:
    #     # Track profile fetch error
    #     user_profile_fetches.labels(
    #         environment=environment,
    #         status='error'
    #     ).inc()
    #     logger.error(f"Get user profile error: {str(e)}")
    #     return jsonify({"message": "Failed to fetch user profile", "error": str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR


# --- Discord OAuth Routes ---
# NOTE: Environment variables required:
#   DISCORD_CLIENT_ID, DISCORD_CLIENT_SECRET, JWT_SECRET_KEY, JWT_ALGORITHM
# Scopes: identify, email

@auth_bp.route("/discord/login", methods=["GET"])
def discord_login():
    """Redirect user to Discord OAuth authorization page."""
    client_id, _ = _load_discord_creds()
    redirect_uri = _compute_redirect_uri()
    if not client_id or not redirect_uri:
        return jsonify({"message": "Discord OAuth not configured"}), HTTPStatus.INTERNAL_SERVER_ERROR
    auth_url = (
        "https://discord.com/api/oauth2/authorize?response_type=code"
        f"&client_id={client_id}"
        f"&scope=identify%20email"
        f"&redirect_uri={requests.utils.quote(redirect_uri, safe='')}"
        "&prompt=consent"
    )
    return redirect(auth_url, code=HTTPStatus.FOUND)


@auth_bp.route("/discord/callback", methods=["GET"])
def discord_callback():
    """
    Handle Discord OAuth callback.
    Exchanges authorization code for access token, fetches user info,
    creates/updates user in database, and redirects to frontend with JWT token.
    """
    start_time = time.time()
    environment = os.environ.get("FLASK_ENV", "production")
    logger = logging.getLogger(__name__)
    code = request.args.get("code")

    if not code:
        logger.error("Discord callback: Missing code parameter")
        discord_oauth_callbacks.labels(
            environment=environment,
            status='error'
        ).inc()
        return jsonify({"message": "Missing code"}), HTTPStatus.BAD_REQUEST

    try:
        client_id, client_secret = _load_discord_creds()
        redirect_uri = _compute_redirect_uri()
        jwt_secret_key = os.environ.get("JWT_SECRET_KEY")
        jwt_algorithm = os.environ.get("JWT_ALGORITHM")

        logger.info(
            f"Discord callback: client_id={client_id[:10] if client_id else None}..., redirect_uri={redirect_uri}")

        if not all([client_id, client_secret, redirect_uri, jwt_secret_key, jwt_algorithm]):
            missing = [k for k, v in [
                ("client_id", client_id), ("client_secret", client_secret),
                ("redirect_uri", redirect_uri), ("JWT_SECRET_KEY", jwt_secret_key),
                ("JWT_ALGORITHM", jwt_algorithm)
            ] if not v]
            logger.error(f"Discord callback: Missing config: {missing}")
            discord_oauth_callbacks.labels(
                environment=environment,
                status='error'
            ).inc()
            return jsonify({"message": "Server missing OAuth/JWT configuration",
                            "missing": missing}), HTTPStatus.INTERNAL_SERVER_ERROR

        # Token exchange
        logger.info("Discord callback: Exchanging code for access token")
        token_start = time.time()

        token_resp = requests.post(
            "https://discord.com/api/oauth2/token",
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=15,
        )

        token_duration = time.time() - token_start

        if token_resp.status_code != HTTPStatus.OK:
            logger.error(f"Discord token exchange failed: {token_resp.status_code} - {token_resp.text}")
            discord_oauth_callbacks.labels(
                environment=environment,
                status='failure'
            ).inc()
            discord_token_exchange_duration.labels(
                environment=environment,
                status='failure'
            ).observe(token_duration)
            discord_api_errors.labels(
                environment=environment,
                error_type='token_exchange_failed',
                endpoint='oauth2/token'
            ).inc()
            return jsonify(
                {"message": "Discord token exchange failed", "detail": token_resp.text}), HTTPStatus.BAD_GATEWAY

        token_json = token_resp.json()
        access_token = token_json.get("access_token")
        if not access_token:
            logger.error("Discord callback: No access_token in response")
            discord_oauth_callbacks.labels(
                environment=environment,
                status='failure'
            ).inc()
            discord_token_exchange_duration.labels(
                environment=environment,
                status='failure'
            ).observe(token_duration)
            return jsonify({"message": "No access_token received"}), HTTPStatus.BAD_GATEWAY

        # Track successful token exchange
        discord_token_exchange_duration.labels(
            environment=environment,
            status='success'
        ).observe(token_duration)

        # Fetch user info
        logger.info("Discord callback: Fetching user info from Discord")
        user_resp = requests.get(
            "https://discord.com/api/users/@me",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=15,
        )
        if user_resp.status_code != HTTPStatus.OK:
            logger.error(f"Failed to fetch Discord user: {user_resp.status_code} - {user_resp.text}")
            discord_oauth_callbacks.labels(
                environment=environment,
                status='failure'
            ).inc()
            discord_api_errors.labels(
                environment=environment,
                error_type='user_fetch_failed',
                endpoint='users/@me'
            ).inc()
            return jsonify({"message": "Failed to fetch Discord user"}), HTTPStatus.BAD_GATEWAY

        duser = user_resp.json()
        # Capture ALL Discord user fields for frontend
        discord_id = str(duser.get("id"))
        username = duser.get("username")
        email = duser.get("email")  # may be None if scope not granted
        logger.info(f"Discord callback: User fetched - discord_id={discord_id}, username={username}, email={email}")
        logger.info(f"Discord callback: Full Discord data available - {len(duser)} fields")

        # Upsert user by Discord ID or email
        user = None
        if email:
            user = User.query.filter_by(email=email).first()
        if not user and discord_id:
            user = User.query.filter_by(discord_username=discord_id).first()
        if not user:
            logger.info(f"Discord callback: Creating new user for discord_id={discord_id}")
            # Generate a secure random password for Discord OAuth users (they won't use it for login)
            # This satisfies the NOT NULL constraint on hashed_password
            import secrets
            random_password = secrets.token_urlsafe(32)  # Generate secure random password
            hashed_pw = hash_password(random_password)

            user = User(
                email=email or f"discord_{discord_id}@example.com",
                username=username or f"discord_{discord_id}",
                discord_username=discord_id,
                hashed_password=hashed_pw
            )
            db.session.add(user)
            db.session.commit()
            logger.info(f"Discord callback: Created user with id={user.id}")
        else:
            logger.info(f"Discord callback: Found existing user with id={user.id}")

        # Generate JWT token
        from datetime import datetime, timedelta
        import jwt as jwt_lib
        payload = {
            "user_id": str(user.id),
            "exp": datetime.utcnow() + timedelta(hours=24),
        }
        jwt_token = jwt_lib.encode(payload, jwt_secret_key, algorithm=jwt_algorithm)

        # Track successful Discord OAuth
        discord_oauth_callbacks.labels(
            environment=environment,
            status='success'
        ).inc()

        # Redirect to frontend Welcome with token, user_id, and all Discord data (URL-encoded)
        welcome_url = os.environ.get("FRONTEND_WELCOME_URL", "https://app.tovplay.org/Welcome")
        sep = '&' if '?' in welcome_url else '?'
        # Encode all Discord user data as JSON for frontend
        discord_data_json = json.dumps(duser)
        discord_data_encoded = quote(discord_data_json, safe='')
        redirect_url = f"{welcome_url}{sep}token={quote(jwt_token, safe='')}&user_id={quote(str(user.id), safe='')}&discord_data={discord_data_encoded}"

        logger.info(
            f"Discord callback: Redirecting to {welcome_url} (token length: {len(jwt_token)}, discord_data length: {len(discord_data_json)})")
        return redirect(redirect_url, code=HTTPStatus.FOUND)

    except requests.exceptions.ConnectionError as e:
        logger.exception(f"Discord API connection error: {str(e)}")
        discord_oauth_callbacks.labels(
            environment=environment,
            status='error'
        ).inc()
        discord_api_errors.labels(
            environment=environment,
            error_type='connection_error',
            endpoint='oauth2/token'
        ).inc()
        return jsonify({"message": "Cannot connect to Discord API",
                        "error": str(e)}), HTTPStatus.SERVICE_UNAVAILABLE

    except Exception as e:
        logger.exception(f"Discord callback error: {str(e)}")
        discord_oauth_callbacks.labels(
            environment=environment,
            status='error'
        ).inc()
        return jsonify({"message": "Internal server error during OAuth callback",
                        "error": str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR



# --- Custom 429 Error Handler ---
@app.errorhandler(429)
def ratelimit_handler(e):
    """
    Custom handler for '429 Too Many Requests' errors raised by Flask-Limiter.
    """
    # e is the RateLimitExceeded exception object provided by Flask-Limiter.
    
    # 1. Get the exceeded limit string (e.g., "3 per minute")
    exceeded_limit = e.description
    
    # 2. Get the suggested time to wait before retrying (in seconds)
    # retry_after is a property added by Flask-Limiter to the exception object.
    retry_after_seconds = e.retry_after
    
    # Announce the blocked request explicitly
    response_data = {
        "status": 429,
        "error": "Rate Limit Exceeded",
        "announcement": "Your request has been **blocked** because you exceeded the defined rate limit.",
        "exceeded_limit": exceeded_limit,
        "suggested_action": f"Please wait {retry_after_seconds:.2f} seconds before making another request.",
        "retry_after_seconds": retry_after_seconds
    }

    # Use jsonify to ensure the response is a JSON object
    return jsonify(response_data), 429
