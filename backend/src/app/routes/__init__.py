from flask import Blueprint

from .availability_routes import availability_bp
from .discord_auth import discord_bp
from .friend_routes import friend_request_bp
from .game_request_routes import game_request_bp, search_bp
from .game_routes import game_bp as game_bp
from .notifications_routes import notifications_bp
from .password_reset_routes import password_reset_bp
from .scheduled_session_routes import scheduled_session_bp
from .user_game_preference_routes import user_game_preference_bp
from .user_profile_routes import user_profile_bp
from .user_routes import auth_bp, user_bp
from .user_session_routes import user_session_bp

bp = Blueprint("api", __name__, url_prefix="/api")


@bp.route("/")
def index():
    return {"message": "TovPlay Backend API", "status": "running", "endpoints": {
        "health": "/health",
        "auth": "/auth",
        "users": "/users",
        "availability": "/availability",
        "games": "/games",
        "user_game_preferences": "/user_game_preferences",
        "user_profiles": "/user_profiles",
        "scheduled_sessions": "/scheduled_sessions",
        "game_requests": "/game_requests",
        "user_sessions": "/user_sessions",
        "find_players": "/findplayers",
        "password": "/password"
    }}, 200


@bp.route("/health")
def health_check():
    return {"status": "healthy"}, 200


# אפשר לרשום את ה-blueprints dentro אחד מרכזי
bp.register_blueprint(auth_bp, url_prefix="/auth")
bp.register_blueprint(user_bp, url_prefix="/users")
bp.register_blueprint(availability_bp, url_prefix="/availability")
bp.register_blueprint(game_bp, url_prefix="/games")
bp.register_blueprint(user_game_preference_bp, url_prefix="/user_game_preferences")
bp.register_blueprint(user_profile_bp, url_prefix="/user_profiles")
bp.register_blueprint(scheduled_session_bp, url_prefix="/scheduled_sessions")
bp.register_blueprint(game_request_bp, url_prefix="/game_requests")
bp.register_blueprint(notifications_bp, url_prefix="/notifications")
bp.register_blueprint(user_session_bp, url_prefix="/user_sessions")
bp.register_blueprint(search_bp, url_prefix="/findplayers")
bp.register_blueprint(discord_bp, url_prefix="/discord")
bp.register_blueprint(password_reset_bp, url_prefix="/password")
bp.register_blueprint(friend_request_bp, url_prefix="/friends")
