import uuid
from flask import Blueprint, request, jsonify
from datetime import datetime
import asyncio
import logging

from src.app.models import UserNotifications, User, db
from src.app.services import get_user_id_from_token

try:
    import websockets
except ImportError:
    websockets = None
    logging.warning("websockets library not installed. WebSocket notifications will not work.")

notifications_bp = Blueprint('notifications', __name__)

import uuid

def serialize_payload(obj):
    if isinstance(obj, uuid.UUID):
        return str(obj)
    if isinstance(obj, dict):
        return {k: serialize_payload(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [serialize_payload(v) for v in obj]
    return obj

def notify_websocket(user_id, payload):
    import requests
    payload_with_user = dict(payload)
    payload_with_user["user_id"] = user_id
    payload_serialized = serialize_payload(payload_with_user)
    logging.info(f"[DEBUG] Attempting websocket notify for user_id={user_id} with payload={payload_serialized}")
    try:
        resp = requests.post(
            "http://localhost:8081/notify_user",
            json=payload_serialized,
            timeout=2
        )
        logging.info(f"[DEBUG] Websocket server response: {resp.status_code} {resp.text}")
        if resp.status_code != 200:
            logging.error(f"[ERROR] Websocket server returned non-200: {resp.status_code} {resp.text}")
    except Exception as notify_exc:
        logging.error(f"[ERROR] Failed to notify websocket server: {notify_exc}")

@notifications_bp.route('/remove_all', methods=['DELETE'])
def remove_all_notifications():
    """
    Removes all notifications for the CURRENT USER only (not all users).
    Requires authentication.
    """
    import os

    # SECURITY: Require authentication
    try:
        user_id = get_user_id_from_token()
        if not user_id:
            return jsonify({"error": "Authentication required"}), 401
    except Exception:
        return jsonify({"error": "Authentication required"}), 401

    try:
        # SECURITY: Only delete notifications for the current user (not all!)
        deleted = UserNotifications.query.filter_by(user_id=user_id).delete()
        db.session.commit()

        # Notify user via websocket
        notify_websocket(
            str(user_id),
            {
                "user_id": str(user_id),
                "action": "removed_all"
            }
        )

        return jsonify({"message": f"Removed {deleted} notifications for current user."}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# Route to get all notifications for a specific user
@notifications_bp.route('/', methods=['GET'])
def get_user_notifications():
    """
    Retrieves a user's notifications, with an option to filter by read status.

    Query Parameters:
        is_read (boolean): 'true' for read notifications, 'false' for unread.
    """
    user_id = get_user_id_from_token()
    try:
        query = UserNotifications.query.filter_by(user_id=user_id, is_read=False).order_by(UserNotifications.created_at.desc())

        is_read_filter = request.args.get('is_read')
        if is_read_filter is not None:
            is_read_value = is_read_filter.lower() in ['true', '1', 't']
            query = query.filter_by(is_read=is_read_value)

        notifications = query.all()

        return jsonify([
            {
                "id": str(n.id),
                "user_id": str(n.user_id),
                "user_name": User.query.get(n.user_id).username if User.query.get(n.user_id) else "",
                "message": n.message,
                "is_read": n.is_read,
                "created_at": n.created_at.isoformat()
            } for n in notifications
        ]), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# Route to mark one or more notifications as read
@notifications_bp.route('/mark_read', methods=['POST'])
def mark_notifications_read():
    """
    Marks notifications as read.

    Request body should be a JSON array of UUIDs.
    """
    try:
        notification_ids_str = request.json
        if not isinstance(notification_ids_str, list):
            return jsonify({"error": "Invalid request body. Expected a list of IDs."}), 400

        # Convert string IDs to UUID objects
        notification_ids = [uuid.UUID(id_str) for id_str in notification_ids_str]

        # Update notifications in the database
        notifications_to_update = UserNotifications.query.filter(UserNotifications.id.in_(notification_ids)).all()
        for notification in notifications_to_update:
            notification.is_read = True

        db.session.commit()

        # Notify affected users via websocket
        notified_users = set(n.user_id for n in notifications_to_update)
        for user_id in notified_users:
            notify_websocket(
                str(user_id),
                {
                    "user_id": str(user_id),
                    "action": "marked_read",
                    "notification_ids": notification_ids_str
                }
            )

        return jsonify({"message": f"Successfully marked {len(notifications_to_update)} notifications as read."}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# Route to delete a notification
@notifications_bp.route('/<uuid:notification_id>', methods=['DELETE'])
def delete_notification(notification_id):
    """
    Deletes a specific notification by its ID.
    """
    try:
        notification = UserNotifications.query.get(notification_id)

        if not notification:
            return jsonify({"error": "Notification not found."}), 404

        db.session.delete(notification)
        db.session.commit()

        # Notify affected user via websocket
        notify_websocket(
            str(notification.user_id),
            {
                "user_id": str(notification.user_id),
                "action": "deleted",
                "notification_id": str(notification_id)
            }
        )

        return jsonify({"message": "Notification deleted successfully."}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# Optional: Endpoint to create a notification (for testing purposes, if not using a trigger)
@notifications_bp.route('/', methods=['POST'])
def create_notification():
    """
    Creates a new notification. For testing purposes.
    """
    import requests

    data = request.json
    try:
        new_notification = UserNotifications(
            user_id=data['user_id'],
            title=data.get('title', "General"),
            message=data['message'],
            is_read=data.get('is_read', False)
        )
        db.session.add(new_notification)
        db.session.commit()

        # Log before attempting to notify websocket server
        logging.info(f"Attempting to notify websocket server for user {data['user_id']}")
        try:
            resp = requests.post(
                "http://localhost:8081/notify_user",
                json={
                    "user_id": str(data['user_id']),
                    "message": data['message']
                },
                timeout=2
            )
            logging.info(f"Websocket server response: {resp.status_code} {resp.text}")
        except Exception as notify_exc:
            logging.error(f"Failed to notify websocket server: {notify_exc}")

        return jsonify({"message": "Notification created.", "id": str(new_notification.id)}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400
