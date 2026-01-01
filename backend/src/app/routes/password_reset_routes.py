from flask import Blueprint, request, jsonify, current_app, has_app_context
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from datetime import datetime, timedelta, timezone
from src.app.models import db, User
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.exc import SQLAlchemyError
import smtplib
import socket
from email.mime.text import MIMEText
from dotenv import load_dotenv
from pathlib import Path
import os
import re
import time
from collections import defaultdict, deque
from functools import wraps
import bcrypt
from src.app.extensions import limiter

# ---------------- ENV fallback (dev) ----------------
def _maybe_load_local_env():
    """Load environment variables from a local .env file if needed (dev only)."""
    needed = (
        "SECRET_KEY",
        "SMTP_SERVER",
        "SMTP_PORT",
        "EMAIL_SENDER",
        "EMAIL_PASSWORD",
        "APP_URL",
    )
    if all(os.getenv(k) for k in needed):
        return

    here = Path(__file__).resolve()
    for depth in range(1, 6):
        try:
            base = here.parents[depth]
        except IndexError:
            # In Docker or other environments, parent structure may differ
            break
        try:
            for name in (".dev", ".env", ".env.development"):
                cand = base / name
                if cand.exists():
                    load_dotenv(cand.as_posix(), override=False)
                    msg = f"[password_reset] loaded fallback env: {cand}"
                    if has_app_context():
                        current_app.logger.info(msg)
                    else:
                        print(msg)
                    return
        except (OSError, PermissionError):
            # Skip inaccessible directories
            continue


_maybe_load_local_env()
# ----------------------------------------------------


def _set_user_password(user, plaintext: str) -> None:
    """Hash the plaintext password and set it on the user."""
    rounds = int(os.getenv("BCRYPT_ROUNDS", "12"))
    salt = bcrypt.gensalt(rounds=rounds)
    hashed = bcrypt.hashpw(plaintext.encode("utf-8"), salt).decode("utf-8")
    user.hashed_password = hashed  # store hashed password in DB


def _check_user_password(user, plaintext: str) -> bool:
    """Verify a plaintext password against the user's stored hash."""
    hpw = (user.hashed_password or "").encode("utf-8")
    try:
        return bcrypt.checkpw(plaintext.encode("utf-8"), hpw)
    except ValueError:
        # If hashed_password is invalid or empty
        return False


password_reset_bp = Blueprint("password_reset_bp", __name__)
SECRET_KEY = os.environ.get("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY is missing")

serializer = URLSafeTimedSerializer(SECRET_KEY)
TOKEN_EXPIRATION_MINUTES = int(os.environ.get("RESET_TOKEN_MINUTES", "60"))


# --- time helpers to avoid naive/aware comparison issues ---
def _utcnow():
    return datetime.now(timezone.utc)


def _ensure_aware(dt: datetime) -> datetime:
    if dt is None:
        return _utcnow()
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


# -----------------------------------------------------------


class PasswordResetToken(db.Model):
    __tablename__ = "password_reset_tokens"
    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey(User.id), nullable=False)
    token = db.Column(db.String(256), unique=True, nullable=False)
    created_at = db.Column(
        db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    used = db.Column(db.Boolean, default=False)

    def is_expired(self) -> bool:
        """Check if this token is past the expiration time."""
        created = _ensure_aware(self.created_at)
        return _utcnow() > created + timedelta(minutes=TOKEN_EXPIRATION_MINUTES)

def validate_new_password(pw: str) -> list[str]:
    """Apply password strength rules. Returns a list of error messages, or empty if valid."""
    errors = []

    if not pw or not isinstance(pw, str):
        errors.append("Password is required.")
    else:
        if len(pw) < 8:
            errors.append("Password must be at least 8 characters.")
        if len(pw) > 64:
            errors.append("Password must be at most 64 characters.")
        if " " in pw:
            errors.append("Password must not contain spaces.")
        if not re.search(r"[A-Za-z]", pw):
            errors.append("Password must contain at least one letter.")
        if not re.search(r"\d", pw):
            errors.append("Password must contain at least one number.")

    return errors


def send_email(to_email: str, subject: str, body: str):
    """Send an email via SMTP. Requires SMTP config to be set."""
    required = ["SMTP_SERVER", "SMTP_PORT", "EMAIL_SENDER", "EMAIL_PASSWORD"]
    missing = [k for k in required if not os.environ.get(k)]
    if missing:
        raise RuntimeError(f"Missing email config: {missing}")

    host = os.environ["SMTP_SERVER"]
    port = int(os.environ["SMTP_PORT"])
    user = os.environ["EMAIL_SENDER"]
    pwd = os.environ["EMAIL_PASSWORD"]

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = user
    msg["To"] = to_email

    try:
        if port == 465:
            # Use SSL for port 465
            with smtplib.SMTP_SSL(host, port, timeout=30) as s:
                s.login(user, pwd)
                s.send_message(msg)
        else:
            # Start TLS for port 587 or use plain for other ports
            with smtplib.SMTP(host, port, timeout=30) as s:
                s.ehlo()
                if port == 587:
                    s.starttls()
                    s.ehlo()
                s.login(user, pwd)
                s.send_message(msg)

        current_app.logger.info(f"Sent email to {to_email} - {subject}")
    except (smtplib.SMTPException, OSError, socket.gaierror) as e:
        current_app.logger.error(
            f"Failed to send email to {to_email}: {type(e).__name__}: {e}"
        )
        raise


def send_password_changed_notice(to_email: str):
    """Notify user that their password was changed (non-fatal if email fails)."""
    try:
        send_email(
            to_email,
            "Your password was changed",
            "If you did not perform this change, please contact support immediately.",
        )
    except (smtplib.SMTPException, OSError, socket.gaierror):
        # If this fails, log and ignore to avoid interrupting the flow
        current_app.logger.warning(
            "Password change notification email could not be sent."
        )


def cleanup_tokens_for_user(user_id):
    """Mark expired reset tokens as used for a given user (cleanup)."""
    try:
        rows = PasswordResetToken.query.filter_by(user_id=user_id, used=False).all()
        changed = False
        for t in rows:
            if t.is_expired():
                t.used = True
                changed = True
        if changed:
            db.session.commit()
    except SQLAlchemyError as e:
        current_app.logger.warning(f"cleanup_tokens_for_user rollback: {e}")
        db.session.rollback()


@password_reset_bp.route("/validate", methods=["GET"])
@limiter.limit("30/minute")
def validate_reset_token():
    """Validate a password reset token and retrieve the associated email (if valid)."""
    token = (request.args.get("token") or "").strip()
    if not token:
        return jsonify({"ok": False, "error": "Missing token"}), 400

    try:
        # Decode the token to get the email (will raise if invalid or expired)
        email = serializer.loads(
            token,
            salt="password-reset",
            max_age=TOKEN_EXPIRATION_MINUTES * 60,
        )
    except SignatureExpired:
        return jsonify({"ok": False, "error": "Token expired"}), 400
    except BadSignature:
        return jsonify({"ok": False, "error": "Invalid token"}), 400

    # Check token existence and unused status in DB
    row = PasswordResetToken.query.filter_by(token=token, used=False).first()
    if not row or row.is_expired():
        return jsonify({"ok": False, "error": "Invalid or already used"}), 400

    return jsonify({"ok": True, "email": email}), 200


@password_reset_bp.route("/request", methods=["POST"])
@limiter.limit("3/hour")  
def request_password_reset():
    """
    Initiate a password reset by generating a token and emailing a reset link.
    Always returns 200 with a generic message to prevent email enumeration.
    """
    data = request.get_json(force=True, silent=False) or {}
    email_input = (data.get("email") or "").strip().lower()
    user = User.query.filter_by(email=email_input).first()

    # Respond with success even if user not found (security measure)
    if not user:
        return jsonify({"message": "If the email exists, a reset link was sent."}), 200

    # Invalidate any expired tokens for this user
    cleanup_tokens_for_user(user.id)

    # Create a new reset token and store it
    token = serializer.dumps(email_input, salt="password-reset")
    reset_token = PasswordResetToken(user_id=user.id, token=token)

    try:
        db.session.add(reset_token)
        db.session.commit()
    except SQLAlchemyError as e:
        current_app.logger.error(f"DB error creating reset token: {e}")
        db.session.rollback()
        return jsonify({"error": "Database error. Try again later."}), 503

    # Build the password reset URL to email to the user
    base_url = (os.environ.get("APP_URL") or "").rstrip("/")
    if not base_url:
        current_app.logger.error(
            "APP_URL is not configured; cannot send reset link."
        )
        reset_url = token  # fallback: send raw token if no base URL
    else:
        reset_url = f"{base_url}/reset-password?token={token}"

    body = f"Click the link to reset your password:\n{reset_url}"

    try:
        send_email(email_input, "Password Reset Request", body)
    except (smtplib.SMTPException, OSError, socket.gaierror) as e:
        current_app.logger.error(f"Failed to send password reset email: {e}")

    return jsonify({"message": "If the email exists, a reset link was sent."}), 200


@password_reset_bp.route("/reset", methods=["POST"])
@limiter.limit("20/5minute")
def reset_password():
    """
    Complete the password reset by validating the token and setting a new password.
    """
    data = request.get_json(force=True, silent=False) or {}
    token_input = (data.get("token") or "").strip()
    new_password = data.get("password") or ""
    confirm_password = data.get("confirm_password") or ""

    if new_password != confirm_password:
        return jsonify({"error": "Passwords do not match."}), 400

    pw_errors = validate_new_password(new_password)
    if pw_errors:
        return jsonify(
            {"error": "Invalid password.", "details": pw_errors}
        ), 400

    try:
        # Decode token to get email (raises if token invalid or expired)
        email = serializer.loads(
            token_input,
            salt="password-reset",
            max_age=TOKEN_EXPIRATION_MINUTES * 60,
        )
    except SignatureExpired:
        return jsonify({"error": "Token expired."}), 400
    except BadSignature:
        return jsonify({"error": "Invalid token."}), 400

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({"error": "User not found."}), 404

    reset_token = PasswordResetToken.query.filter_by(
        token=token_input, used=False
    ).first()
    if not reset_token or reset_token.is_expired():
        return jsonify({"error": "Invalid or expired token."}), 400

    try:
        _set_user_password(user, new_password)
        reset_token.used = True

        # Invalidate all other active reset tokens for this user
        other_tokens = PasswordResetToken.query.filter(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used.is_(False),
            PasswordResetToken.id != reset_token.id,
        ).all()
        for t in other_tokens:
            t.used = True

        db.session.commit()
    except SQLAlchemyError as e:
        current_app.logger.error(f"DB error saving new password: {e}")
        db.session.rollback()
        return jsonify({"error": "Database error. Try again later."}), 503

    # Notify user of password change (no impact on response if it fails)
    send_password_changed_notice(user.email)

    return jsonify({"message": "Password successfully reset."}), 200
