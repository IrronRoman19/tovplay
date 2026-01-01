from http import HTTPStatus

from src.app.db import db
from src.app.models import User
import requests
import os

from src.app.services import logger


def get_discord_user(access_token):
    headers = {"Authorization": f"Bearer {access_token}"}
    res = requests.get("https://discord.com/api/users/@me", headers=headers)
    res.raise_for_status()
    return res.json()

def get_discord_token(data):
    # Log the request data (excluding sensitive client_secret)
    safe_data = {k: v for k, v in data.items() if k != 'client_secret'}
    logger.info(f"Discord token exchange request data: {safe_data}")
    logger.info(f"Redirect URI being sent: {data.get('redirect_uri')}")

    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    res = requests.post("https://discord.com/api/oauth2/token", data=data, headers=headers)

    # Log response status for debugging
    logger.info(f"Discord token response status: {res.status_code}")
    if res.status_code != 200:
        logger.error(f"Discord token exchange failed: {res.status_code} - {res.text}")

    res.raise_for_status()
    return res.json()


def save_discord_to_db(user_data):
    print("user_data:", user_data)
    print("user_data keys:", user_data.keys())
    discord_id = user_data.get("id")
    discord_username = user_data.get("username")
    user = User.query.filter_by(discord_username=discord_username).all()
    if user:
        raise ValueError(f"An account with discord username {discord_username} already exists")
    user = User(
        discord_id=discord_id,
        avatar_url=f'https://cdn.discordapp.com/avatars{discord_id}/{user_data.get("avatar")}.png',
        username=discord_username,
        discord_username=discord_username,
        email = user_data.get("email"),
        verified = True
    )
    if not user:
        raise ValueError("Problem creating user")
    db.session.add(user)
    db.session.commit()

    return user


def add_user_to_guild(user_access_token: str, discord_user_id: str, guild_id: str):
    """Add a user to a guild using the bot token and the user's OAuth2 access token.

    Discord API endpoint: PUT /guilds/{guild_id}/members/{user_id}
    Body: {"access_token": "<user_access_token>"}

    Raises requests.HTTPError on failure. Returns the response JSON or status code on success.
    """
    bot_token = os.getenv("DISCORD_BOT_TOKEN") or os.getenv("DISCORD_TOKEN")
    if not bot_token:
        raise ValueError("DISCORD_BOT_TOKEN (or DISCORD_TOKEN) environment variable not set")

    url = f"https://discord.com/api/guilds/{guild_id}/members/{discord_user_id}"
    headers = {
        "Authorization": f"Bot {bot_token}",
        "Content-Type": "application/json",
    }
    payload = {"access_token": user_access_token}

    res = requests.put(url, json=payload, headers=headers)
    # If user is already in guild, Discord may return 204 No Content.
    if res.status_code in (HTTPStatus.OK, HTTPStatus.CREATED, HTTPStatus.NO_CONTENT):
        # Some success responses have no body (204); return True for success
        try:
            return res.json()
        except ValueError:
            return True
    else:
        # Raise for HTTP errors to let caller handle/log
        res.raise_for_status()
        return res.json()


def check_guild_membership(discord_user_id: str, guild_id: str) -> bool:
    """Check if a user is a member of a specific guild.

    Discord API endpoint: GET /guilds/{guild.id}/members/{user.id}

    Args:
        discord_user_id: The Discord user ID to check
        guild_id: The Discord guild (server) ID to check membership in

    Returns:
        bool: True if the user is a member, False otherwise.
    """
    try:
        bot_token = os.getenv("DISCORD_BOT_TOKEN") or os.getenv("DISCORD_TOKEN")
        if not bot_token:
            logger.error("DISCORD_BOT_TOKEN (or DISCORD_TOKEN) environment variable not set")
            return False

        url = f"https://discord.com/api/guilds/{guild_id}/members/{discord_user_id}"
        headers = {
            "Authorization": f"Bot {bot_token}",
            "Content-Type": "application/json",
        }

        res = requests.get(url, headers=headers, timeout=10)  # Add timeout
        
        if res.status_code == 200:
            logger.info(f"User {discord_user_id} is a member of guild {guild_id}")
            return True
        elif res.status_code == 404:
            logger.info(f"User {discord_user_id} is not a member of guild {guild_id}")
            return False
        else:
            logger.error(f"Error checking guild membership: {res.status_code} - {res.text}")
            return False
    except Exception as e:
        logger.error(f"Exception in check_guild_membership: {str(e)}")
        return False
