from datetime import timedelta, datetime
from logging import exception

from flask import Blueprint, jsonify, request
from sqlalchemy import and_, or_
from sqlalchemy.orm import aliased

from src.api.friend_request_api import accept_invite_api, create_friend_request_api, block_user_api, \
    cancel_friend_request_api
# Import moved inside function to avoid circular import
from src.app.db import db
from src.app.error_handlers import ValidationError, AuthorizationError
from src.app.models import UserFriends, User, FriendStatus
from src.app.services import get_user_id_from_token, check_admin

friend_request_bp = Blueprint("friend_request", __name__)

@friend_request_bp.route("/all", methods=["GET"])
def get_all_friend_requests():
    check_admin()
    return jsonify([request.id for request in UserFriends.query.all()])


@friend_request_bp.route("/get_friend_request/<friend_request_id>", methods=["GET"])
def get_friend_request(friend_request_id):
    user_id = get_user_id_from_token()
    userFriends = UserFriends.query.get_or_404(friend_request_id).to_dict()
    user = User.query.get_or_404(user_id)
    if  user_id != userFriends.sender_user_id and user_id != userFriends.recipient_user_id and user.role != "Admin":
        raise ValidationError()
    return userFriends.to_dict()

@friend_request_bp.route("/", methods=["GET"])
def get_user_friend_requests():
    user_id = get_user_id_from_token()
    all_requests = {"sender": [], "recipient": []}
    # Perform the joins for sender and recipient

    sender_username_alias = aliased(User)
    recipient_username_alias = aliased(User)
    query = (
        db.session.query(
            UserFriends,
            sender_username_alias.username.label("sender_username"),
            recipient_username_alias.username.label("recipient_username")
            )
            .join(sender_username_alias, sender_username_alias.id == UserFriends.sender_user_id)  # Join for sender
            .join(recipient_username_alias, recipient_username_alias.id == UserFriends.recipient_user_id)  # Join for recipient
            .filter(or_(UserFriends.sender_user_id == user_id, UserFriends.recipient_user_id == user_id))
            .order_by(UserFriends.suggested_time)
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


@friend_request_bp.route("/friends", methods=["GET"])
def get_friends():
    user_id = get_user_id_from_token()
    reqs = {}
    for req in db.session.query(UserFriends).filter(
            and_(or_(UserFriends.sender_user_id == user_id, UserFriends.recipient_user_id == user_id, ),
                 UserFriends.status == FriendStatus.ACCEPTED)).all():
        ids = [str(req.sender_user_id), str(req.recipient_user_id)]
        ids.remove(str(user_id))
        username = User.query.get_or_404(ids[0]).username
        reqs[username] = req.to_dict()

    return jsonify(reqs), 200


@friend_request_bp.route("/blocked_users", methods=["GET"])
def get_blocked_users():
    user_id = get_user_id_from_token()
    return jsonify([req.to_dict() for req in db.session.query(UserFriends).filter(
        and_(or_(UserFriends.sender_user_id == user_id, UserFriends.recipient_user_id == user_id),
             UserFriends.status == FriendStatus.BLOCKED)).all()]), 200

@friend_request_bp.route("/check_relationship/<other_player_username>", methods=["GET"])
def check_relationship(other_player_username):
    user_id = get_user_id_from_token()
    other_player = User.query.filter_by(username=other_player_username).first()
    if not other_player:
        return jsonify({"status":"Error", "message": f"User {other_player_username} not found"}), 404
    relationship = db.session.query(UserFriends).filter(or_(
        and_(UserFriends.sender_user_id == user_id,  UserFriends.recipient_user_id == other_player.id),
        and_(UserFriends.sender_user_id == other_player.id,  UserFriends.recipient_user_id == user_id))).first()
    if relationship:
        return jsonify({"status":relationship.status, "message": relationship.message, "request_id": relationship.id}), 200
    return jsonify({"status":"None", "message": "None", "request_id": "None"}), 200


@friend_request_bp.route("/sent_requests", methods=["GET"])
def get_sent_friend_requests():
    user_id = get_user_id_from_token()
    return jsonify([req.to_dict() for req in db.session.query(UserFriends).filter(
            and_(UserFriends.sender_user_id == user_id,  UserFriends.status == FriendStatus.PENDING)).all()]), 200


@friend_request_bp.route("/received_requests", methods=["GET"])
def get_recipient_friend_requests():
    user_id = get_user_id_from_token()
    return jsonify([req.to_dict() for req in db.session.query(UserFriends).filter(
            and_(UserFriends.recipient_user_id == user_id,  UserFriends.status == FriendStatus.PENDING)).all()]), 200


@friend_request_bp.route("/request", methods=["POST"])
def create_friend_request():
    sender_user_id = get_user_id_from_token()
    data = request.get_json()
    return create_friend_request_api(sender_user_id, data)


@friend_request_bp.route("/unblock", methods=["PUT"])
def unblock_user():
    sender_user_id = get_user_id_from_token()
    data = request.get_json()
    request_id = data.get("request_id", None)
    username_to_unblock = data.get("username_to_unblock")
    return cancel_friend_request_api(sender_user_id, username_to_unblock, request_id)


@friend_request_bp.route("/block", methods=["PUT"])
def block_user():
    sender_user_id = get_user_id_from_token()
    data = request.get_json()
    return block_user_api(sender_user_id, data)





@friend_request_bp.route("/accept/<request_id>", methods=["PUT"])
def accept_invitation(request_id):
    user_id = get_user_id_from_token()
    user = User.query.get_or_404(user_id)
    friend_request = UserFriends.query.get_or_404(request_id)
    if str(user_id) != str(friend_request.recipient_user_id):
        print(str(user_id), str(friend_request.recipient_user_id))
        raise ValidationError("Not authorized")
    accept_invite_bool = request.get_json()["accept_invite"]
    return accept_invite_api(user_id, friend_request, accept_invite_bool)



@friend_request_bp.route("/request/<request_id>", methods=["DELETE"])
def delete_friend_request(request_id):
    user_id = str(get_user_id_from_token())
    request_data = UserFriends.query.get_or_404(request_id)
    if not request_data:
        raise ValueError("No friend request found!")
    if (str(request_data.sender_user_id) != user_id
            and str(request_data.recipient_user_id) != user_id
            and User.query.get_or_404(user_id).role != "Admin"):
        raise AuthorizationError("You are not authorized to do this action")
    db.session.delete(request_data)
    db.session.commit()
    return jsonify({"message": "Request deleted successfully"}), 200


