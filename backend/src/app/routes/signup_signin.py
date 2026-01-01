import collections
import secrets
from datetime import datetime, timedelta
import jwt
from sqlalchemy import or_
import threading

from src.app.models import EmailVerification, User, UserAvailability, db
from src.app.security import InputValidator
from src.app.services import compare_password_hashed, hash_password, send_verification_email


def check_password(password):
    """Strong password validation using the centralized InputValidator."""

    is_valid, issues = InputValidator.validate_password_strength(password)
    if not is_valid:
        # Join all validation issues into a single error message
        raise ValueError("; ".join(issues))

    return True


def check_username(username):
    """Enhanced username validation using centralized InputValidator."""
    if not username:
        raise ValueError("Username is required")
        
    # Validate username format
    is_valid, error_message = InputValidator.validate_username(username)
    if not is_valid:
        raise ValueError(error_message)

    # Check for existing username (case-insensitive)
    existing_user = User.query.filter(db.func.lower(User.username) == username.lower()).first()
    if existing_user:
        if existing_user.verified:
            raise ValueError("Username is already taken")
            
        verification_record = EmailVerification.query.filter_by(user_id=existing_user.id).first()
        if verification_record and verification_record.expires_at < datetime.utcnow():
            # Delete expired unverified account
            db.session.delete(existing_user)
            db.session.commit()
            print(f"Old unverified account for username '{username}' was deleted.")
        else:
            expiration_time = verification_record.expires_at.strftime("%I:%M %p") if verification_record else "soon"
            raise ValueError(
                f"Username is taken by an unverified account. It will be available {expiration_time} if not verified."
            )

    return True


def check_email(email, password):
    """Enhanced email validation using centralized InputValidator."""

    if not InputValidator.validate_email(email):
        raise ValueError("Invalid email format. Please provide a valid email address.")

    user = User.query.filter_by(email=email.lower()).first()
    if user:
        if user.verified:
            hashed_pw = hash_password(password)
            setattr(user, "hashed_password", hashed_pw)
            db.session.commit()
            db.session.refresh(user)
            return user

        raise ValueError("You have registered but haven't verified your email. Please verify your email.")

    return True


def send_verification_code(user_id, email):
    verification_code = secrets.randbelow(900000) + 100000
    verification_code = str(verification_code)

    expires_at = datetime.now() + timedelta(minutes=5)

    try:
        verification_record = EmailVerification.query.filter_by(user_id=user_id).first()
        check_send = send_verification_email(email, verification_code)
        if check_send:
            if verification_record:
                verification_record.verification_code = verification_code
                verification_record.expires_at = expires_at
                db.session.commit()
                print("Updated verification code to ", verification_code)
                return True
            verification_record = EmailVerification(
                user_id=user_id, verification_code=verification_code, expires_at=expires_at
            )
            db.session.add(verification_record)
            db.session.commit()
            return verification_record
    except Exception as e:
        print(f"Failed to send email during signup: {e}")


def validate_discord_username(discord_username):
    """Enhanced Discord username validation using centralized InputValidator."""

    if not InputValidator.validate_discord_username(discord_username):
        raise ValueError("Invalid Discord username format. Please use either: 'username' (3-30 chars, alphanumeric with underscores) or 'username#1234' (legacy format)")

    # Check for uniqueness
    existing_user = User.query.filter_by(discord_username=discord_username).first()
    if existing_user:
        raise ValueError("Discord username already registered")

    return True



def send_email_async(user_id, email):
    try:
        send_verification_code(user_id, email)
    except Exception as e:
        print(f"Async email sending failed: {e}")




def signup_user(data):
    email = data.get("Email", "").lower()  # Get email, default to empty string if not provided
    password = data["Password"]
    username = data["Username"]
    discord_username = data["DiscordUsername"]

    # Validate all fields using centralized validators
    if email:  # Only validate email if it's provided
        user = check_email(email, password)
        if isinstance(user, User):
            return user
    check_password(password)
    check_username(username)
    validate_discord_username(discord_username)

    hashed_pw = hash_password(password)

    user = User(
        email=email if email else None, hashed_password=hashed_pw, username=username, discord_username=discord_username
    )
    if not user:
        raise ValueError("Problem creating user")
    db.session.add(user)
    db.session.commit()
    db.session.refresh(user)

    if email:  # Send verification code asynchronously to avoid blocking signup
        send_email_async(user.id, email)
        
        # Start email sending in background thread - don't wait for it
        email_thread = threading.Thread(target=send_email_async, args=(user.id, email), daemon=True)
        email_thread.start()
    db.session.commit()
    return user


def continuous_time_blocks(times):
    times_to_save = {}
    for day in times:
        times[day].sort()
        start_time = datetime.strptime(times[day][0], "%H:%M").time()
        end_time = (datetime.combine(datetime.min, start_time) + timedelta(hours=1)).time()
        times_to_save[day] = {start_time.strftime("%H:%M"): end_time.strftime("%H:%M")}
        for time_slot in times[day][1:]:
            time_slot = datetime.strptime(time_slot, "%H:%M").time()
            current_end = (datetime.combine(datetime.min, time_slot) + timedelta(hours=1)).time()
            if time_slot != end_time:
                start_time = time_slot
            end_time = current_end
            times_to_save[day][start_time.strftime("%H:%M")] = end_time.strftime("%H:%M")
    return times_to_save


def delete_user_cascade(user_id):
    user = User.query.filter_by(id=user_id).first()
    if not user:
        raise ValueError("User not found.")
    print("user_id is: ", user_id, "email is: ", user.email)

    db.session.query(User).filter_by(id=user_id).delete()
    db.session.commit()


def delete_all_time_slots(user_id):
    if not User.query.filter_by(id=user_id).first():
        raise ValueError("User not found.")
    db.session.query(UserAvailability).filter_by(user_id=user_id).delete()
    db.session.commit()


def save_user_availability(user_id, slots, is_recurring):
    if not User.query.filter_by(id=user_id).first():
        raise ValueError("User not found.")
    delete_all_time_slots(user_id)
    for day in slots:
        for start_time in slots[day]:
            user_availability_record = UserAvailability(
                user_id=user_id,
                day_of_week=day,
                start_time=start_time,
                end_time=slots[day][start_time],
                is_recurring=is_recurring,
            )
            if not user_availability_record:
                raise ValueError("Problem creating user_availability_record")
            db.session.add(user_availability_record)
            db.session.commit()


def set_user_availability(user_id, data, is_recurring):
    if not data:
        raise ValueError("No availability times selected.")
    user = User.query.filter_by(id=user_id).first()
    if not user:
        raise ValueError("User not found.")
    availability_by_day = collections.defaultdict(list)
    for key in data:
        day, time = key.split("-")
        # time_obj = datetime.strptime(time, '%H:%M').time()
        availability_by_day[day].append(time)
    continuous_slots = continuous_time_blocks(availability_by_day)
    try:
        save_user_availability(user_id, continuous_slots, is_recurring)
        db.session.commit()
        print("All new slots committed successfully.")
        return True
    except Exception as e:
        print("there was a problem saving the time slots! ", e)
        db.session.rollback()
        return False


def email_verification_code(email, code):
    user = User.query.filter_by(email=email).first()
    if not user:
        raise ValueError("User not found.")
    email_verification = EmailVerification.query.filter_by(user_id=user.id).first()
    if not email_verification:
        raise ValueError("Verification record not found. Please try signing up again.")
    if email_verification.is_verified or user.verified:
        raise ValueError("Email already verified!")
    saved_code = email_verification.verification_code
    print(f"check times: {type(email_verification.expires_at)};  datetime.now(): {type(datetime.now())}")
    if email_verification.expires_at < datetime.now():
        print(email_verification.expires_at, datetime.now())
        send_verification_code(user.id, email)
        raise ValueError("Verification code has expired.")
    if not saved_code == code:
        raise ValueError("Verification code incorrect!")

    email_verification.is_verified = True
    user.verified = True
    db.session.commit()
    return True


def create_jwt(user_id, jwt_secret_key=None, jwt_algorithm=None):
    """
    Create a JWT token for a given user_id.
    Uses the app's configured JWT settings or default values.
    """
    import os
    from flask import current_app

    # Use the app's config if available, otherwise fallback to environment variables
    if jwt_secret_key is None:
        jwt_secret_key = current_app.config.get('JWT_SECRET_KEY') or os.getenv("JWT_SECRET_KEY", "dev-secret-key")
    if jwt_algorithm is None:
        jwt_algorithm = current_app.config.get('JWT_ALGORITHM') or os.getenv("JWT_ALGORITHM", "HS256")

    payload = {
        "user_id": str(user_id),  # UUID needs to be a string
        "exp": datetime.utcnow() + timedelta(hours=24),  # Token expires in 24 hours
        "iat": datetime.utcnow(),  # Issued at time
        "sub": str(user_id),  # Subject (user ID)
    }
    jwt_token = jwt.encode(payload, jwt_secret_key, algorithm=jwt_algorithm)
    return jwt_token


def signin(data, jwt_secret_key, jwt_algorithm):
    """Secure login function with input validation."""
    email_or_username = data.get("Email")
    password = data.get("Password")
    users = db.session.query(User).filter(
        or_(
            User.email == email_or_username,
            User.username == email_or_username
        )
    ).all()
    user = None

    # set priority to email match since someone can create
    # a username same as another user's email and block login
    for u in users:
        if u.email == email_or_username:
            user = u
            break
    for u in users:
        if u.username == email_or_username:
            user = u
            break
    if user:
        if compare_password_hashed(password, user.hashed_password):
            if not user.verified:
                verification = EmailVerification.query.filter_by(user_id=user.id).first()
                if verification is None or verification.expires_at < datetime.now():
                    send_verification_code(user.id, email_or_username)
                raise ValueError("Your email has not been verified. Please check your inbox.")

            # return user.id
            jwt_token = create_jwt(user.id, jwt_secret_key, jwt_algorithm)
            print(jwt_token)

            return user.id, jwt_token
    raise ValueError("Incorrect email or password. Please try again.")
