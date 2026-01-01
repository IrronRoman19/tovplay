import json

from flask import Blueprint, jsonify, request
from sqlalchemy import or_, and_

from src.api.user_game_preference_api import put_games
from src.app.db import db
from src.app.models import CommunicationPreferences, UserProfile, User, Game, UserGamePreference, UserFriends
from src.app.services import get_user_id_from_token, check_admin
from src.app.security import rate_limit

user_profile_bp = Blueprint("user_profile", __name__)


@user_profile_bp.route("/", methods=["POST"])
@rate_limit(requests_per_hour=10, burst_limit=3)
def create_user_profile():
    user_id = get_user_id_from_token()
    if not user_id:
        return jsonify({"error": "Authentication required"}), 401
    
    existing_profile = UserProfile.query.filter_by(user_id=user_id).first()
    if existing_profile:
        return update_user_profile()

    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing data"}), 400
    
    # Validate input lengths
    bio = data.get("bio", "")
    if len(bio) > 500:
        return jsonify({"error": "Bio too long (max 500 characters)"}), 400
    
    communication_preferences = data.get("communication_preferences")
    if communication_preferences:
        try:
            communication_preferences = CommunicationPreferences(
                communication_preferences
            ).value
        except ValueError:
            return jsonify({"error": "Invalid communication preference"}), 400
    
    new_profile = UserProfile(
        user_id=user_id,
        bio=bio,
        avatar_url=data.get("avatar_url"),
        language=data.get("language"),
        timezone=data.get("timezone"),
        communication_preferences=communication_preferences,
    )
    
    db.session.add(new_profile)
    db.session.commit()
    return jsonify(new_profile.to_dict()), 201

@user_profile_bp.route("/all", methods=["GET"])
def get_all_user_profile():
    check_admin()
    profiles = UserProfile.query.all()
    return jsonify(
        [profile.to_dict() for profile in profiles ]
    )

@user_profile_bp.route("/", methods=["GET"])
def get_user_profile():
    user_id = get_user_id_from_token()
    print(user_id)
    profile = UserProfile.query.filter_by(user_id=user_id).first()
    if not profile:
        profile = UserProfile(user_id=user_id)
        db.session.add(profile)
        db.session.commit()
        return jsonify(profile.to_dict()), 201
    return jsonify(profile.to_dict()), 200

@user_profile_bp.route("/public/<username>", methods=["GET"])
def get_public_user_profile(username):
    user_id = get_user_id_from_token()
    public_user = User.query.filter_by(username=username).first()
    if not public_user:
        return jsonify({"error": "User not found"}), 404
    public_profile = {"username": public_user.username, "discord_username": public_user.discord_username, "avatar_url": public_user.avatar_url}
    user_profile = UserProfile.query.filter_by(user_id=public_user.id).first()
    if user_profile:
        public_profile["bio"] = user_profile.bio
        public_profile["communication_preferences"] = user_profile.communication_preferences
        public_profile["language"] = user_profile.language
    public_profile["games"] = [Game.query.get_or_404(pref.game_id).game_name for pref in 
                               UserGamePreference.query.filter_by(user_id=public_user.id).all()]

    return json.dumps(public_profile), 200


@user_profile_bp.route("/", methods=["PUT"])
@rate_limit(requests_per_hour=30, burst_limit=10)
def update_user_profile():
    user_id = get_user_id_from_token()
    if not user_id:
        return jsonify({"error": "Authentication required"}), 401
    
    profile = UserProfile.query.filter_by(user_id=user_id).first()
    if not profile:
        return jsonify({"error": "Profile not found"}), 404
    
    data = request.get_json()
    if not data:
        return jsonify({"error": "No update data provided"}), 400
    
    # Whitelist of allowed fields
    allowed_fields = {'bio', 'avatar_url', 'language', 'timezone', 'communication_preferences', 'games'}
    sets = {}
    
    for field, value in data.items():
        if field not in allowed_fields:
            continue
            
        if field == "games":
            try:
                added, deleted = put_games(user_id, value)
                sets[field] = {"added": added, "removed": deleted}
                continue
            except ValueError:
                return jsonify({"error": f"Problem saving game preference: {value}"}), 400
        
        # Validate input lengths
        if field == "bio" and len(str(value)) > 500:
            return jsonify({"error": "Bio too long (max 500 characters)"}), 400

        if hasattr(profile, field):
            setattr(profile, field, value)
            sets[field] = value

    try:
        db.session.commit()
        return jsonify(sets), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Could not update profile"}), 500

