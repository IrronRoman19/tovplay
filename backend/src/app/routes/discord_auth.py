import asyncio
import os
from datetime import datetime, timedelta
from http import HTTPStatus
from urllib.parse import urlencode

from flask import Blueprint, redirect, request, jsonify

# Make Discord bot integration optional - only import if available
try:
    from bot import create_discord_event, check_in_guild
    DISCORD_BOT_AVAILABLE = True
except ImportError:
    DISCORD_BOT_AVAILABLE = False
    print("Warning: Discord bot integration not available (discord.py not installed)")

from src.api.discord_api import get_discord_token, get_discord_user, save_discord_to_db, add_user_to_guild, \
    check_guild_membership
from src.app.models import User, db, Game
from src.app.routes.signup_signin import create_jwt
from src.app.services import get_user_id_from_token, logger

discord_bp = Blueprint("discord", __name__, url_prefix="/discord")

CLIENT_ID = os.getenv("DISCORD_CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = os.getenv("DISCORD_REDIRECT_URI")
OAUTH_BASE_URL = "https://discord.com/api/oauth2"
TOKEN_URL = f"{OAUTH_BASE_URL}/token"
AUTH_URL = f"{OAUTH_BASE_URL}/authorize"
DISCORD_URL = os.getenv("DISCORD_URL")
GUILD_ID = os.getenv("DISCORD_GUILD_ID")


@discord_bp.route("/login")
def login():
    scope = "identify email guilds.join"
    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": scope,
        "prompt": "consent"
    }
    discord_auth_url = (
        f"{OAUTH_BASE_URL}/authorize?{urlencode(params)}"
    )
    return redirect(discord_auth_url)


@discord_bp.route("/callback", methods=["GET"])
def callback():
    error = request.args.get("error")
    if error:
        logger.warning(f"Discord OAuth cancelled: {request.args.get('error_description')}")
        return redirect(f"{os.getenv('APP_URL')}/signin")

    # 1. Exchange code for token
    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": (request.args.get("code")),
        "redirect_uri": REDIRECT_URI,
    }
    
    try:
        token_data = get_discord_token(data)
        access_token = token_data["access_token"]
        granted_scopes = token_data.get("scope", "")
        
        user_data = get_discord_user(access_token)
    except Exception as e:
        logger.error(f"Error exchanging token or getting user: {e}")
        return redirect(f"{os.getenv('APP_URL')}/signin?error=auth_failed")

    # 2. Login/Create User
    email = user_data.get("email")
    user = User.query.filter_by(email=email).first()
    
    if not user:
        user = save_discord_to_db(user_data)
    else:
        setattr(user, "discord_username", user_data.get("username"))
        setattr(user, "discord_id", user_data.get("id"))
        db.session.commit()

    # 3. Check Guild Membership logic
    if GUILD_ID:
        discord_user_id = user_data.get("id")
        
        # Check if we already have the join scope (Step 2 completed)
        if "guilds.join" in granted_scopes:
            try:
                add_user_to_guild(access_token, discord_user_id, GUILD_ID)
                user.in_community = True
                db.session.commit()
            except Exception as e:
                logger.error(f"Error adding user to guild: {e}")
                # Continue anyway, don't block login
        else:
            # Step 1 completed. Check if user is already in guild.
            is_member = check_guild_membership(discord_user_id, GUILD_ID)
            
            if is_member:
                user.in_community = True
                db.session.commit()
            else:
                # Not a member, and we don't have permission to join them.
                # Redirect to Step 2: Request guilds.join scope.
                logger.info(f"User {user.id} not in guild. Redirecting to authorize guilds.join.")
                scope = "identify email guilds.join"
                params = {
                    "client_id": CLIENT_ID,
                    "redirect_uri": REDIRECT_URI,
                    "response_type": "code",
                    "scope": scope
                }
                discord_auth_url = f"{OAUTH_BASE_URL}/authorize?{urlencode(params)}"
                return redirect(discord_auth_url)

    # 4. Redirect to Dashboard
    jwt_token = create_jwt(user.id)
    params = {
        "user_id": user.id,
        "token": jwt_token
    }
    frontend_url = f"{os.getenv('APP_URL')}/dashboard?{urlencode(params)}"
    return redirect(frontend_url)


@discord_bp.route("/create_event", methods=["POST"])
def create_event():
    if not DISCORD_BOT_AVAILABLE:
        return jsonify({"error": "Discord bot integration not available"}), HTTPStatus.SERVICE_UNAVAILABLE

    data = request.get_json()
    title = data.get("title", "TovPlay Game 🎮")
    game_name = data.get("game_name")
    if game_name:
        game_site_url = Game.query.filter_by(game_name=game_name).first().game_site_url
    else:
        game_name = "this awesome game!"
        game_site_url = DISCORD_URL

    other_user = data.get("other_user")
    description = f'Play {game_name} with {other_user}'
    start_time = datetime.fromisoformat(data["start_time"])  # לדוגמה: "2025-11-01T18:00:00"
    end_time = start_time + timedelta(hours=1)

    # מריצים את הפונקציה הא-סינכרונית של דיסקורד
    loop = asyncio.get_event_loop()
    event_url = loop.run_until_complete(
        create_discord_event(title, description, game_site_url, start_time, end_time)
    )

    return jsonify({"event_url": event_url})


@discord_bp.route("/in_community_route", methods=["GET"])
def in_community():
    if not DISCORD_BOT_AVAILABLE:
        return jsonify({"error": "Discord bot integration not available"}), HTTPStatus.SERVICE_UNAVAILABLE

    user_id = get_user_id_from_token()
    user = User.query.get_or_404(user_id)
    if not user.in_community:   
        try:
            # Check if user is in the guild using their Discord ID
            in_guild = check_in_guild(user.discord_username)
    
            # Update the user's community status if it has changed
            if in_guild != user.in_community:
                user.in_community = in_guild
                db.session.commit()
        except Exception as e:
            logger.error(f"Error checking guild membership for user {user.id}: {str(e)}")
            # Return the current status from DB if there's an error checking with Discord
            return jsonify({
                "in_community": user.in_community,
                "discord_username": user.discord_username,
                "error": "Error checking community status"
            }), HTTPStatus.OK

    return jsonify({
        "in_community": user.in_community,
        "discord_username": user.discord_username
    }), HTTPStatus.OK


@discord_bp.route("/get_in_community", methods=["PUT"])
def get_in_community():
    try:
        user_id = get_user_id_from_token()
        user = User.query.get_or_404(user_id)
        
        # Update the user's community status
        user.in_community = True
        db.session.commit()
        
        logger.info(f"Updated community status for user {user.id} (Discord: {user.discord_username}) to in_community=True")
        
        return jsonify({
            "message": f"User {user.discord_username} joined our community successfully!",
            "discord_username": user.discord_username,
            "in_community": True
        }), HTTPStatus.OK
        
    except Exception as e:
        logger.error(f"Error in get_in_community: {str(e)}")
        db.session.rollback()
        return jsonify({
            "error": "Failed to update community status",
            "details": str(e)
        }), HTTPStatus.INTERNAL_SERVER_ERROR
