import uuid
from datetime import datetime

from flask import Blueprint, jsonify, request

from src.app.db import db
from src.app.models import UserSession

user_session_bp = Blueprint("user_session", __name__)


@user_session_bp.route("/", methods=["POST"])
def create_user_session():
    data = request.get_json()
    if not data or "user_id" not in data or "user_agent" not in data:
        return jsonify({"error": "Missing user_id or user_agent"}), 400

    new_session = UserSession(
        user_id=data.get("user_id"),
        session_token=data.get("session_token", str(uuid.uuid4())),
        expires_at=data.get("expires_at"),
        last_activity=data.get("last_activity", datetime.now()),
        user_agent=data.get("user_agent"),
        ip_address=data.get("ip_address"),
    )
    db.session.add(new_session)
    db.session.commit()
    return jsonify(new_session.to_dict()), 201


@user_session_bp.route("/<session_id>", methods=["GET"])
def get_user_session(session_id):
    session = UserSession.query.get_or_404(session_id)
    return jsonify(session.to_dict()), 200


@user_session_bp.route("/<session_id>", methods=["DELETE"])
def delete_user_session(session_id):
    session = UserSession.query.get_or_404(session_id)
    db.session.delete(session)
    db.session.commit()
    return jsonify({"message": "Session deleted successfully"}), 200
