
from flask import Blueprint, request, jsonify
import uuid
from datetime import datetime, timedelta

from sqlalchemy import or_, not_, and_

from src.api.scheduled_session_api import find_duplicate_session, create_session
from src.app.db import db
from src.app.error_handlers import ValidationError
from src.app.models import ScheduledSession, User, Game, UserGamePreference, UserAvailability, UserNotifications, \
    GameRequest
from src.app.services import get_user_id_from_token, check_admin

scheduled_session_bp = Blueprint('scheduled_session', __name__)




@scheduled_session_bp.route('/', methods=['POST'])
def create_scheduled_session():
    data = request.get_json()
    new_session = create_session(data)
    return jsonify(new_session.to_dict()), 201


# ---


@scheduled_session_bp.route('cancel_session/<uuid:session_id>', methods=['PUT'])
def cancel_scheduled_session(session_id):
    user_id = get_user_id_from_token()
    data = request.get_json()
    session = ScheduledSession.query.get_or_404(session_id)
    if session.status == 'completed':
        return jsonify({"message": "This session's time has already passed, can't cancel session"}), 409
    if session.status == 'cancelled':
        return jsonify({"message": "This session's has already been cancelled"}), 409

    other_user = list({session.second_player_id, session.organizer_user_id} - set(user_id))[0]
    game_name = Game.query.get_or_404(session.game_id).game_name
    other_username = User.query.get_or_404(other_user).username
    suggested_time = f"{session.scheduled_date} {session.start_time}"
    message = data.get("message")
    canceller_message = (f"You have cancelled a session with '{other_username}' playing {game_name} "
                      f" at {suggested_time}). {f'The message you sent: {message}' if message else 'The game session has been canceled.'}")
    print(canceller_message)
    sender_notification = UserNotifications(
        user_id=other_user,
        message=canceller_message,
        title="Game session cancelled"
    )
    db.session.add(sender_notification)
    # Push notification via websocket
    from src.app.routes.notifications_routes import notify_websocket
    notify_websocket(
        str(other_user),
        {
            "message": canceller_message,
            "title": "Game session cancelled"
        }
    )

    cancelling_message = (f"'{User.query.get_or_404(user_id).username}' has cancelled a session playing {game_name} "
                      f"at {suggested_time}). message:{message if message else 'The game session has been canceled'}")
    print(cancelling_message)
    sender_notification = UserNotifications(
        user_id=other_user,
        message=cancelling_message,
        title="Game session cancelled"
    )
    db.session.add(sender_notification)
    # Push notification via websocket
    from src.app.routes.notifications_routes import notify_websocket
    notify_websocket(
        str(other_user),
        {
            "message": cancelling_message,
            "title": "Game session cancelled"
        }
    )
    setattr(session, "status", "cancelled")
    setattr(GameRequest.query.get_or_404(session.session_id), "status", "cancelled")

    db.session.commit()
    return jsonify(session.to_dict()), 201


@scheduled_session_bp.route('/<uuid:session_id>', methods=['PUT'])
def update_scheduled_session(session_id):
    """
    PUT /sessions/<session_id>
    Updates an existing scheduled session.
    Allows for partial updates.
    """
    user_id = get_user_id_from_token()
    session = ScheduledSession.query.get(session_id)
    if user_id != session.organizer_user_id and user_id != session.second_player_id:
        raise ValidationError
    if not session:
        return jsonify({"error": "Scheduled session not found"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided for update"}), 400


    # Dynamically update fields based on the provided data
    for field, value in data.items():
        if field in ['scheduled_date', 'start_time', 'end_time']:
            try:
                if field == 'scheduled_date':
                    setattr(session, field, datetime.strptime(value, '%Y-%m-%d').date())
                elif field == 'start_time' or field == 'end_time':
                    setattr(session, field, datetime.strptime(value, '%H:%M:%S').time())
            except (ValueError, TypeError):
                return jsonify(
                    {"error": f"Invalid format for {field}. Expected YYYY-MM-DD for date or HH:MM:SS for time."}), 400
        elif hasattr(session, field):
            setattr(session, field, value)

    db.session.commit()
    return jsonify(session.to_dict()), 200


# ---

@scheduled_session_bp.route('/<uuid:session_id>', methods=['DELETE'])
def delete_scheduled_session(session_id):
    """
    DELETE /sessions/<session_id>
    Deletes a scheduled session by its UUID.
    """
    session = ScheduledSession.query.get(session_id)
    if not session:
        return jsonify({"error": "Scheduled session not found"}), 404

    db.session.delete(session)
    db.session.commit()
    return jsonify({"message": "Scheduled session deleted successfully"}), 200

@scheduled_session_bp.route('all', methods=['GET'])
def get_all_scheduled_sessions():
    check_admin()
    sessions = ScheduledSession.query.all()
    return jsonify([s.to_dict() for s in sessions]), 200

@scheduled_session_bp.route('/', methods=['GET'])
def get_user_sessions( organizer=True, participant=True):
    user_id = get_user_id_from_token()
    all_sessions = []
    if organizer:
        for session in ScheduledSession.query.filter_by(organizer_user_id=user_id).all():
            session_dict = session.to_dict_essentials()
            session_dict["discord_username"] = User.query.get_or_404(session.second_player_id).discord_username
            all_sessions.append(session_dict)
    if participant:
        for session in ScheduledSession.query.filter_by(second_player_id=user_id).all():
            session_dict = session.to_dict_essentials()
            session_dict["discord_username"] = User.query.get_or_404(session.organizer_user_id).discord_username
            all_sessions.append(session_dict)
    return jsonify(all_sessions), 200


@scheduled_session_bp.route('/<session_id>', methods=['GET'])
def get_scheduled_session(session_id):
    session = ScheduledSession.query.get_or_404(session_id)
    user_id = get_user_id_from_token()
    user = User.query.get_or_404(user_id)
    if  user_id != session.sender_user_id and user_id != session.recipient_user_id and user.role != "Admin":
        raise ValidationError("Not authorized")
    return jsonify(session.to_dict()), 200
