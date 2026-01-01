from datetime import datetime, timedelta

from alembic.util import status
from dotenv.main import rewrite
from flask import request, jsonify
from sqlalchemy import or_, and_

from src.app.db import db
from src.app.error_handlers import AuthorizationError
from src.app.models import User, UserNotifications, UserFriends, FriendStatus


def create_friend_request_api(sender_user_id, data):
    user = User.query.get_or_404(sender_user_id)
    if not user:
        return jsonify({"error": f"User with id {sender_user_id} doesn't exist"}), 409
    recipient_username = data.get("recipient_username")
    recipient_user = User.query.filter_by(username=recipient_username).first()
    if not recipient_user:
        return jsonify({"error": f"There is no user with the username of '{recipient_username}'"}), 409
    if recipient_username == user.username:
        return jsonify({"error": "You can't send a request to yourself!"}), 409
    friend_request = db.session.query(UserFriends).filter(
        and_(UserFriends.sender_user_id==recipient_user.id, UserFriends.recipient_user_id==sender_user_id)).first()
    if friend_request:
        return accept_invite_api(sender_user_id, friend_request, True) # todo do we want to ask his if he wants to accept? let him know somehow?

    friend_request = UserFriends.query.filter_by(recipient_user_id=recipient_user.id).first()
    if friend_request:
        if friend_request.status == FriendStatus.ACCEPTED:
            return jsonify({"message": f"You are already friends with '{recipient_username}"}), 204
        if friend_request.status == FriendStatus.PENDING:
            return jsonify({"message": f"Your request to be friends with '{recipient_username} is pending"}), 204
        if friend_request.status == FriendStatus.BLOCKED or friend_request.status == FriendStatus.DECLINED:
            return jsonify({"message": f"Your request to be friends with '{recipient_username} was declined"}), 204
    message = data.get("message", "Would you like to be my friend?")
    new_request = UserFriends(
        sender_user_id=sender_user_id,
        recipient_user_id=recipient_user.id,
        message=message,
        status=FriendStatus.PENDING
    )
    print(new_request)

    recipient_notification = UserNotifications(
        user_id=recipient_user.id,
        message=message,
        title=f"New friend request from {recipient_username}"

    )
    db.session.add(recipient_notification)

    db.session.add(new_request)
    db.session.commit()
    return jsonify(new_request.to_dict()), 201

def block_user_api(user_id, data):
    username_to_block = data.get("username_to_block")
    user_to_block = User.query.filter_by(username=username_to_block).first()
    if not user_to_block:
        return (
            jsonify({"error": f"There is no user with the username of '{username_to_block}'"}),
            409,
        )
    user_friend = db.session.query(UserFriends).filter(
        and_(UserFriends.recipient_user_id == user_id, UserFriends.sender_user_id == user_to_block.id)).first()
    if user_friend:
        setattr(user_friend, "status", FriendStatus.BLOCKED)
        setattr(user_friend, "recipient_user_id", user_to_block.id)
        setattr(user_friend, "sender_user_id", user_id)
        db.session.commit()
        return jsonify(user_friend.to_dict()), 200
    user_friend = db.session.query(UserFriends).filter(and_(UserFriends.sender_user_id == user_id, UserFriends.recipient_user_id == user_to_block.id)).first()
    if user_friend:
        setattr(user_friend, "status", FriendStatus.BLOCKED)
        db.session.commit()
        return jsonify(user_friend.to_dict()), 200
    user_friend = UserFriends(
        sender_user_id=user_id,
        recipient_user_id=user_to_block.id,
        message=data.get("blocking_reason", f"{User.query.get_or_404(user_id).username} has blocked {username_to_block}"),
        status=FriendStatus.BLOCKED
    )
    db.session.add(user_friend)
    db.session.commit()
    return jsonify(user_friend.to_dict()), 200


def cancel_friend_request_api(sender_user_id, username_to_cancel, request_id=None):
    if request_id:
        user_friend = UserFriends.query.get_or_404(request_id)
    else:
        user_to_cancel = User.query.filter_by(username=username_to_cancel).first()
        user_friend = db.session.query(UserFriends).filter(and_(UserFriends.sender_user_id == sender_user_id, UserFriends.recipient_user_id == user_to_cancel.id)).first()
    if not user_friend:
        return jsonify({"error": f"There is no friend request from '{request_id}'"}), 409
    db.session.delete(user_friend)
    db.session.commit()
    return jsonify(user_friend.to_dict()), 200

def accept_invite_api(user_id, friend_request, accept_invite_bool):
    print(friend_request.status)
    if friend_request.status == FriendStatus.ACCEPTED:
        return {"message": "You are already friends"}, 200
    if friend_request.status != FriendStatus.PENDING:
        return {"message": "The request isn't pending so it can't be accepted or declined"}, 200
    if str(user_id) != str(friend_request.recipient_user_id) and User.query.get_or_404(user_id).role != 'Admin':
        print(f"{user_id} != {friend_request.recipient_user_id}")
        raise AuthorizationError( f"{user_id} is not authorized!")
    recipient_username = User.query.get_or_404(friend_request.recipient_user_id).username
    sender_username = User.query.get_or_404(friend_request.sender_user_id).username
    if accept_invite_bool:
        sender_message = f"Your friend request to '{recipient_username}' was accepted!"
        sender_notification = UserNotifications(
            user_id=friend_request.sender_user_id,
            message=sender_message,
            title="Friend request accepted"
        )
        recipient_notification = UserNotifications(
            user_id = friend_request.recipient_user_id,
            message = f"You are now friends with '{sender_username}'!",
            title="You have accepted an invitation"

        )
        db.session.add(sender_notification)
        db.session.add(recipient_notification)
        setattr(friend_request, "status", FriendStatus.ACCEPTED)
        db.session.commit()
        return jsonify({"message": f"{recipient_username} and {sender_username} are now friends"}), 201
    setattr(friend_request, "status", FriendStatus.DECLINED)
    db.session.commit()
    return jsonify({"message": f"{recipient_username} declined {sender_username}'s friend request"}), 201

def get_blocked_players_for_player(current_user_id):
    return db.session.query(UserFriends).filter(
        and_(
            or_(UserFriends.sender_user_id == current_user_id, UserFriends.recipient_user_id == current_user_id),
            UserFriends.status == FriendStatus.BLOCKED
        )
    ).all()
        