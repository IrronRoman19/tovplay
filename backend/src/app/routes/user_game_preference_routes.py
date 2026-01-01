from flask import Blueprint, jsonify, request
from sqlalchemy import and_

from src.api.user_game_preference_api import get_user_games, put_games, add_preference
from src.app.db import db
from src.app.models import Game, User, UserGamePreference
from src.app.services import get_user_id_from_token, check_admin

user_game_preference_bp = Blueprint("user_game_preference", __name__)


@user_game_preference_bp.route("/all_users", methods=["GET"])
def get_all_user_game_preferences():
    check_admin()
    preferences = UserGamePreference.query.all()
    return jsonify([{"Game": Game.query.get_or_404(p.game_id).game_name, "Username": User.query.get_or_404(p.user_id).username} for p in preferences]), 200


@user_game_preference_bp.route("/", methods=["POST"])
def add_user_game_preference():
    user_id = get_user_id_from_token()
    game_name = request.get_json().get("game_name")
    return add_user_game_preference(user_id, game_name)

@user_game_preference_bp.route('/get_games', methods=['GET'])
def get_games():
    user_id = get_user_id_from_token()
    games = get_user_games(user_id)
    return jsonify(games), 200

@user_game_preference_bp.route('/update_games', methods=['PUT'])
def update_games():
    user_id = get_user_id_from_token()
    games = request.get_json().get("games")
    print(games)
    added, deleted = put_games(user_id, games)
    return {"games added": added, "games removed": deleted}, 200


@user_game_preference_bp.route('/get_users_by_game', methods=['GET'])
def get_users_for_game():
    print("ht")
    game_id = request.get_json()["game_id"]
    print(game_id)
    preferences = UserGamePreference.query.filter_by(game_id=game_id).all()
    print(game_id, preferences)
    return jsonify([User.query.filter_by(id=p.user_id).first().username for p in preferences]), 200


@user_game_preference_bp.route('/', methods=['GET'])
def get_user_game_preference():
    user_id = get_user_id_from_token()
    preferences = UserGamePreference.query.filter_by(user_id=user_id).all()
    return jsonify([Game.query.filter_by(id=p.game_id).first().game_name for p in preferences]), 200


@user_game_preference_bp.route("/<pref_id>", methods=["DELETE"])
def delete_user_game_preference(pref_id):
    preference = UserGamePreference.query.get_or_404(pref_id)
    db.session.delete(preference)
    db.session.commit()
    return jsonify({"message": "Preference deleted successfully"}), 200

@user_game_preference_bp.route("/", methods=["DELETE"])
def delete_all_preferences():
    user_id = get_user_id_from_token()
    try:
        for pref in UserGamePreference.query.filter_by(user_id=user_id).all():
            delete_user_game_preference(pref.id)
        return (
            jsonify(
                {"message": "All user game preferences deleted successfully!", "user_id": user_id}
            ),
            201,
        )
    except Exception as e:
        print("DB error:", e)
        return jsonify({"message": "Failed to delete game preferences!", "error": str(e)}), 500