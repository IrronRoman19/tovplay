from flask import Blueprint, jsonify, request
from requests import Session

from src.app.routes.signup_signin import delete_all_time_slots, set_user_availability
from src.app.models import UserAvailability, db
from src.app.services import get_user_id_from_token, check_admin

availability_bp = Blueprint("availability", __name__)


@availability_bp.route("/all", methods=["GET"])
def get_availability():
    check_admin()
    return jsonify([rec.to_dict() for rec in UserAvailability.query.all()]), 200


@availability_bp.route("/", methods=["GET"])
def get_availability_for_user():
    user_id = get_user_id_from_token()

    records = UserAvailability.query.filter_by(user_id=user_id).all()
    return [
        {
            "day_of_week": rec.day_of_week,
            "start_time": rec.start_time.strftime("%H:%M"),
            "end_time": rec.end_time.strftime("%H:%M"),
        }
        for rec in records
    ]


@availability_bp.route("/", methods=["POST"])
def userAvailability():
    user_id = get_user_id_from_token()
    data = request.get_json()
    slots = data.get("slots")
    is_recurring = data.get("is_recurring")
    db_session: Session = db.session
    try:
        set_availability = set_user_availability(user_id, slots, is_recurring)
        if set_availability:
            return (
                jsonify({"message": "User availability updated successfully!", "user_id": user_id}),
                201,
            )
        return set_availability, 409
    except Exception as e:
        db_session.rollback()
        print("DB error:", e)
        return jsonify({"message": "Failed to update user availability", "error": str(e)}), 500


@availability_bp.route("/", methods=["DELETE"])
def delete_time_slots():
    user_id = get_user_id_from_token()
    try:
        delete_all_time_slots(user_id)
        return (
            jsonify(
                {"message": "All user availability slots deleted successfully!", "user_id": user_id}
            ),
            201,
        )
    except Exception as e:
        print("DB error:", e)
        return jsonify({"message": "Failed to delete availability slots!", "error": str(e)}), 500
