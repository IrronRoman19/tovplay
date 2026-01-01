from datetime import timedelta, datetime
from logging import exception

from flask import Blueprint, jsonify, request
from sqlalchemy import and_, or_
from sqlalchemy.orm import aliased

from src.api.game_request_api import find_availability_matches, accept_invite_api, create_game_request_api, \
    find_players_by_name_and_player_api
# Import moved inside function to avoid circular import
from src.app.db import db
from src.app.error_handlers import ValidationError
from src.app.models import Game, GameRequest, ScheduledSession, User, UserGamePreference
from src.app.services import get_user_id_from_token, check_admin

game_request_bp = Blueprint("game_request", __name__)

@game_request_bp.route("/all", methods=["GET"])
def get_all_game_requests():
    check_admin()
    return jsonify([request.id for request in GameRequest.query.all()])


@game_request_bp.route("/get_game_request/<game_request_id>", methods=["GET"])
def get_game_request(game_request_id):
    user_id = get_user_id_from_token()
    gameRequest = GameRequest.query.get_or_404(game_request_id).to_dict()
    user = User.query.get_or_404(user_id)
    if  user_id != gameRequest.sender_user_id and user_id != gameRequest.recipient_user_id and user.role != "Admin":
        raise ValidationError()


    return

@game_request_bp.route("/", methods=["GET"])
def get_user_game_requests():
    user_id = get_user_id_from_token()
    all_requests = {"sender": [], "recipient": []}
    # Perform the joins for sender and recipient

    sender_username_alias = aliased(User)
    recipient_username_alias = aliased(User)
    query = (
        db.session.query(
            GameRequest,
            sender_username_alias.username.label("sender_username"),
            recipient_username_alias.username.label("recipient_username")
            )
            .join(sender_username_alias, sender_username_alias.id == GameRequest.sender_user_id)  # Join for sender
            .join(recipient_username_alias, recipient_username_alias.id == GameRequest.recipient_user_id)  # Join for recipient
            .filter(or_(GameRequest.sender_user_id == user_id, GameRequest.recipient_user_id == user_id))
            .order_by(GameRequest.suggested_time)
    )

    for req, sender_username, recipient_username in query:
        all_values = req.to_dict()
        all_values["sender_username"] = sender_username
        all_values["recipient_username"] = recipient_username

        if all_values["recipient_user_id"] == user_id:
            all_requests["recipient"].append(all_values)
        else:
            all_requests["sender"].append(all_values)

    return jsonify(all_requests)


@game_request_bp.route("/sent_requests/", methods=["GET"])
def get_sent_game_requests():
    user_id = get_user_id_from_token()
    all_requests = {}
    for req in db.session.query(GameRequest).filter(
            and_(GameRequest.sender_user_id == user_id, GameRequest.status == "pending")
    ):
        all_values = req.to_dict()
        time = all_values.pop("suggested_time")

        all_values["recipient_username"] = User.query.get_or_404(all_values["recipient_user_id"]).username
        all_requests.setdefault(time, []).append(all_values)

    return all_requests  # jsonify([request.to_dict() ])



@game_request_bp.route("/received_requests", methods=["GET"])
def get_recipient_game_requests():
    user_id = get_user_id_from_token()
    all_requests = {}
    for req in db.session.query(GameRequest).filter(
            and_(GameRequest.recipient_user_id == user_id,  GameRequest.status == "pending")
    ):
        all_values = req.to_dict()
        time = all_values.pop("suggested_time")

        all_values["sender_username"] = User.query.get_or_404(all_values["sender_user_id"]).username
        all_requests.setdefault(time, []).append(all_values)

    return all_requests  # jsonify([request.to_dict() ])







@game_request_bp.route("/", methods=["POST"])
def create_game_request():
    sender_user_id = get_user_id_from_token()
    print(sender_user_id)
    return create_game_request_api(sender_user_id)




@game_request_bp.route("/accept_invite/<request_id>", methods=["PUT"])
def accept_invitation(request_id):
    user_id = get_user_id_from_token()
    user = User.query.get_or_404(user_id)
    game_request = GameRequest.query.get_or_404(request_id)
    if str(user_id) != str(game_request.recipient_user_id):
        print(str(user_id), str(game_request.recipient_user_id))
        raise ValidationError("Not authorized")
    accept_invite_bool = request.get_json()["accept_invite"]
    session, status_code = accept_invite_api(user_id, game_request, accept_invite_bool)
    if not accept_invite_bool:
        return {"message": "Request rejected successfully"}, 200
    try:
        return session.to_dict(), status_code
    except Exception as e:
        print(f"Request status is 'pending' but the session already exists: {e}")

# Note: this endpoint allows both sender and recipient to update the request
#       it can change *any* field of the request
#       This is generally a BAD practice.
#       Better use /accept_invite/<request_id> for canceling a request - Avihay
@game_request_bp.route("/<request_id>", methods=["PUT"])
def update_game_request(request_id):
    data = request.get_json()
    game_request = GameRequest.query.get_or_404(request_id)
    user_id = get_user_id_from_token()
    user = User.query.get_or_404(user_id)
    if  user_id != str(game_request.sender_user_id) and user_id != str(game_request.recipient_user_id) and user.role != "Admin":
        raise ValidationError("Not authorized")
    sets = {}
    wrong_fields = []
    for field, value in data.items():
        if hasattr(game_request, field):
            setattr(game_request, field, value)
            sets[field] = value
        else:
            print(f"Ignoring unknown field: {field}")
            wrong_fields.append(field)

    try:
        db.session.commit()
        if not sets:
            sets = {"message": "No changes were made"}
            if wrong_fields:
                sets["wrong field names"] = wrong_fields
        return jsonify(sets), 200
    except Exception as e:
        db.session.rollback()


@game_request_bp.route("/<request_id>", methods=["DELETE"])
def delete_game_request(request_id):
    check_admin()
    request_data = GameRequest.query.get_or_404(request_id)
    db.session.delete(request_data)
    db.session.commit()
    return jsonify({"message": "Request deleted successfully"}), 200


search_bp = Blueprint('findplayers', __name__)



@search_bp.route("/", methods=["GET"])
def find_players():
    """
    Universal endpoint to find players. 
    Can filter by game_name OR recipient_username.
    """
    current_user_id = get_user_id_from_token()
    game_name = request.args.get('game_name')
    recipient_username = request.args.get('recipient_username')
    
    try:
        matches = find_availability_matches(
            current_user_id, 
            game_name=game_name, 
            candidate_username=recipient_username
        )
        return jsonify(matches), 200

    except Exception as e:
        return jsonify({"error": f"An internal server error occurred: {str(e)}"}), 500


@search_bp.route("/<game_name>", methods=["GET"])
def find_players_by_name_and_player(game_name):
    # This route seems to do something slightly different (finding requests?), 
    # ensuring it stays as is but wrapped in try/except block just in case.
    try:
        current_user_id = get_user_id_from_token()
        all_requests = find_players_by_name_and_player_api(current_user_id, game_name)
        return jsonify(all_requests) , 200

    except Exception as e:
        return jsonify({"error": f"An internal server error occurred: {str(e)}"}), 500