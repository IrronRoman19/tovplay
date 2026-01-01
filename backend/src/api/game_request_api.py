from datetime import datetime, timedelta

from dotenv.main import rewrite
from flask import request, jsonify
from sqlalchemy import or_, and_

from src.api.friend_request_api import get_blocked_players_for_player
from src.app.db import db
from src.app.error_handlers import AuthorizationError
from src.app.models import ScheduledSession, User, Game, UserGamePreference, UserAvailability, GameRequest, UserProfile, \
    UserNotifications, UserFriends, FriendStatus


def get_day_of_week_mapping():
    """Returns a mapping from Hebrew day names to their numeric representation (0=Sunday)."""
    return {
        "Sunday": 6, "Monday": 0, "Tuesday": 1, "Wednesday": 2,
        "Thursday": 3, "Friday": 4, "Saturday": 5
    }


def calculate_user_free_slots(availabilities, sessions, days_ahead=7):
    """
    Calculates hourly free slots for a user given their availability rules and scheduled sessions.
    """
    hourly_slots = set()
    today = datetime.now().date()
    # today = datetime.today().date()
    day_mapping_rev = {v: k for k, v in get_day_of_week_mapping().items()}

    # 1. Expand Availability Rules into Concrete Slots
    for i in range(days_ahead):
        current_date = today + timedelta(days=i)
        day_of_week_name = day_mapping_rev.get(current_date.weekday()) # e.g. "Monday"

        # Find matching rules for this day name
        # Optimization: Pre-group availabilities by day if list is huge,
        # but for per-user usage, simple iteration is fine.
        day_avails = [a for a in availabilities if a.day_of_week == day_of_week_name]

        for avail in day_avails:
            start = datetime.combine(current_date, avail.start_time)
            end = datetime.combine(current_date, avail.end_time)
            
            # Add hourly slots
            current_slot = start
            while current_slot < end:
                hourly_slots.add(current_slot)
                current_slot += timedelta(hours=1)

    # 2. Subtract Scheduled Sessions
    for session in sessions:
        # We only care if the session overlaps with our generated range, 
        # but simple subtraction is safe enough.
        start = datetime.combine(session.scheduled_date, session.start_time)
        end = datetime.combine(session.scheduled_date, session.end_time)
        
        current_slot = start
        while current_slot < end:
            if current_slot in hourly_slots:
                hourly_slots.remove(current_slot)
                # print(f"Removed busy slot: {current_slot}")
            current_slot += timedelta(hours=1)
            
    return hourly_slots


def get_user_free_slots(user_id):
    """
    Retrieves availability and sessions for a user and calculates their free slots.
    """
    availabilities = UserAvailability.query.filter_by(user_id=user_id).all()
    sessions = ScheduledSession.query.filter(
        or_(ScheduledSession.organizer_user_id == user_id,
            ScheduledSession.second_player_id == user_id)
    ).all()
    
    return calculate_user_free_slots(availabilities, sessions)


def find_availability_matches(current_user_id, candidate_users=None, candidate_username=None, game_name=None):
    """
    Finds overlapping free time slots between the current user and a target set of users.
    
    Args:
        current_user_id: ID of the user searching.
        candidate_users: Optional list of User objects to check against.
        candidate_username: Optional username to find a specific user to check against.
        game_name: Optional game name to find all players of this game.
        
    Returns:
        List of match dictionaries (compatible with frontend expectation).
    """
    day_mapping_rev = {v: k for k, v in get_day_of_week_mapping().items()}
    
    # 1. Resolve Target Users
    targets = []
    
    if candidate_users:
        targets = candidate_users
    elif candidate_username:
        user = User.query.filter_by(username=candidate_username).first()
        if user:
            targets = [user]
    elif game_name:
        game = Game.query.filter_by(game_name=game_name).first()
        if game:
             targets = db.session.query(User).join(UserGamePreference).filter(
                UserGamePreference.game_id == game.id,
                User.id != current_user_id
            ).all()

    if not targets:
        return []

    # Filter out blocked users (bi-directional)
    blocked_connections = get_blocked_players_for_player(current_user_id)

    blocked_user_ids = set()
    for conn in blocked_connections:
        if str(conn.sender_user_id) == str(current_user_id):
            blocked_user_ids.add(str(conn.recipient_user_id))
        else:
            blocked_user_ids.add(str(conn.sender_user_id))

    targets = [t for t in targets if str(t.id) not in blocked_user_ids]

    if not targets:
        return []

    # 2. Get Current User Data
    current_free_slots = get_user_free_slots(current_user_id)

    # 3. Process Targets
    matches = []

    current_user_friends = UserFriends.query.filter(
        (UserFriends.sender_user_id == current_user_id) | (UserFriends.recipient_user_id == current_user_id),
        UserFriends.status == FriendStatus.ACCEPTED
    ).all()
    # יצירת סט של IDs
    friend_ids_set = set()
    for f in current_user_friends:
        ids = [str(f.sender_user_id), str(f.recipient_user_id)]
        ids.remove(str(current_user_id))
        friend_ids_set.add(ids[0])
    
    for other_user in targets:
        # Skip self if it somehow got in
        if str(other_user.id) == str(current_user_id):
            continue

        other_free_slots = get_user_free_slots(other_user.id)
        
        # Intersection
        common = current_free_slots.intersection(other_free_slots)
        
        if common:
             profile = UserProfile.query.filter_by(user_id=other_user.id).first()
             # Fetch games for this user (N+1, but usually small list)
             games = [Game.query.get(g.game_id).game_name for g in UserGamePreference.query.filter_by(user_id=other_user.id).all()]
             
             match_details = {
                "id": str(other_user.id),
                "username": other_user.username,
                "discord_username": other_user.discord_username,
                "user_profile_pic": profile.avatar_url if profile else None,
                "languages": profile.language if profile else None,
                "communication_preferences": profile.communication_preferences if profile else None,
                "games": games,
                 "is_friend": str(other_user.id) in friend_ids_set,
                "available_slots": []
            }
             
             sorted_slots = sorted(list(common))
             for slot in sorted_slots:
                 match_details["available_slots"].append({
                     "day": day_mapping_rev.get(slot.weekday()),
                     "hour": slot.strftime("%H:%M")
                 })
             
             matches.append(match_details)

    return matches


# Deprecated alias to maintain backward compatibility if needed temporarily (though we will fix callers)
def match_user_availability(current_user_id, relevant_users):
    return find_availability_matches(current_user_id, candidate_users=relevant_users)

def find_players_by_name_and_player_api(current_user_id,game_name ):
    recipient_username = request.args.get('recipient_username')
    recipient_user_id = User.query.filter_by(username=recipient_username).first().id
    game_id = Game.query.filter_by(game_name=game_name).first().id
    all_requests = []
    for req in db.session.query(GameRequest).filter(and_(
            or_(GameRequest.sender_user_id == current_user_id, GameRequest.recipient_user_id == current_user_id),
            or_(GameRequest.sender_user_id == recipient_user_id,
                GameRequest.recipient_user_id == recipient_user_id),
            GameRequest.game_id == game_id)
    ):
        all_values = req.to_dict()
        time = all_values.pop("suggested_time")
        datetime_obj = datetime.strptime(time, "%Y-%m-%d %H:%M:%S")
        weekday = datetime_obj.strftime("%A")
        time_part = datetime_obj.strftime("%H:%M")
        all_requests.append({'day': weekday, 'hour': time_part})

    return all_requests


def find_duplicate_requests(game_id, sender_user_id, recipient_user_id, suggested_time):
    return GameRequest.query.filter_by(
        game_id=game_id,
        sender_user_id=sender_user_id,
        recipient_user_id=recipient_user_id,
        suggested_time=suggested_time,
    ).first()


def create_game_request_api(sender_user_id):
    user = User.query.get(sender_user_id)
    if not user:
        return jsonify({"error": "User doesn't exist"}), 409
    data = request.get_json()
    recipient_username = data.get("recipient_username")
    recipient_user = User.query.filter_by(username=recipient_username).first()
    if not recipient_user:
        return (
            jsonify({"error": f"There is no user with the username of '{recipient_username}'"}),
            409,
        )
    game_name = data.get("game_name").title()
    game = Game.query.filter_by(game_name=game_name).first()
    if not game:
        return jsonify({"error": f"There is no game '{game_name}'"}), 409
    suggested_time = data.get("suggested_time")
    duplicate_requests = find_duplicate_requests(
        game.id, sender_user_id, recipient_user.id, suggested_time
    )
    if duplicate_requests:
        raise ValueError(
            f"A game request of '{game.game_name}' with '{user.username}' as organizer and '{recipient_username}' as a participant at {suggested_time} has already been scheduled"
        )

    new_request = GameRequest(
        sender_user_id=sender_user_id,
        recipient_user_id=recipient_user.id,
        game_id=game.id,
        suggested_time=suggested_time,
        message=data.get("message"),
    )
    print(new_request)

    recipient_notification = UserNotifications(
        user_id=recipient_user.id,
        message=f"{user.username} has invited you to play"
                f" {game_name} "
                f" at {suggested_time}",
        title="New game request"

    )
    db.session.add(recipient_notification)

    db.session.add(new_request)
    db.session.commit()
    return jsonify(new_request.to_dict()), 201

def accept_invite_api(user_id, game_request, accept_invite_bool):
    from src.api.scheduled_session_api import create_session
    request_id = game_request.id
    if not game_request:
        raise ValueError("Game request not found.")

    if str(user_id) != str(game_request.recipient_user_id) and User.query.get_or_404(user_id).role != 'Admin':

        raise AuthorizationError( f"{user_id} != {game_request.recipient_user_id}")
    if accept_invite_bool:
        print(request_id)
        session = ScheduledSession.query.filter_by(session_id=request_id).first()
        if session:
            print("Session already exists")
            status_code = 304
        elif game_request.status == "pending":
            session = create_session(
                {
                    "organizer_id": game_request.sender_user_id,
                    "second_player_id": game_request.recipient_user_id,
                    "scheduled_date": game_request.suggested_time.date(),
                    "start_time": game_request.suggested_time.time(),
                    "end_time": (game_request.suggested_time + timedelta(hours=1)).time(),
                    "game_id": game_request.game_id,
                    "session_id": game_request.id
                }
            )
            game_name = Game.query.get_or_404(game_request.game_id).game_name
            recipient_username = User.query.get_or_404(game_request.recipient_user_id).username
            sender_username = User.query.get_or_404(game_request.sender_user_id).username
            suggested_time = f"{game_request.suggested_time.date()} {game_request.suggested_time.time()}"
            print(game_name, recipient_username, sender_username, suggested_time)
            sender_message = (f"Game {game_name} "
                              f"with {recipient_username} ("
                              f"scheduled at {suggested_time}) was accepted")
            print(sender_message)
            sender_notification = UserNotifications(
                user_id=game_request.sender_user_id,
                message=sender_message,
                title="Invitation accepted"
            )
            db.session.add(sender_notification)

            recipient_notification = UserNotifications(
                user_id = game_request.recipient_user_id,
                message = f"You accepted {sender_username}'s invitation to play"
                          f" {game_name} "
                          f" at {suggested_time}",
                title="You have accepted an invitation"

            )
            db.session.add(recipient_notification)

            status_code = 201
        else:
            return None
        setattr(game_request, "status", "accepted")
        pending_requests = db.session.query(GameRequest).filter(
            and_(GameRequest.suggested_time == game_request.suggested_time),
            GameRequest.status == "pending",
            or_(
                GameRequest.sender_user_id == game_request.sender_user_id,
                GameRequest.recipient_user_id == game_request.sender_user_id,
                GameRequest.sender_user_id == game_request.recipient_user_id,
                GameRequest.recipient_user_id == game_request.recipient_user_id,
            ),
        )
        for pending_request in pending_requests:
            # call accept_invite_api with (user_id, game_request, accept_invite_bool)
            # use the pending_request.recipient_user_id as the acting user for this call
            accept_invite_api(pending_request.recipient_user_id, pending_request, False)
        db.session.commit()
        return session, status_code
    else:
        setattr(game_request, "status", "rejected")
        db.session.commit()
