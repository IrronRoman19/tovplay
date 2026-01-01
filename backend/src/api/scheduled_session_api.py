import asyncio
from datetime import datetime, timedelta, timezone

from flask import json

from bot import create_private_channel, bot, create_discord_event
from src.app.models import Game, ScheduledSession, User, db


def find_duplicate_session(game_id, organizer_user_id, scheduled_date, start_time):
    return ScheduledSession.query.filter_by(
        game_id=game_id,
        organizer_user_id=organizer_user_id,
        scheduled_date=scheduled_date,
        start_time=start_time,
    ).first()


def get_info_from_data_names(data):
    organizer_username = data["organizer_username"]
    second_player_username = data["second_player_username"]
    if organizer_username == second_player_username:
        raise ValueError(f"You ('{organizer_username}') cannot invite yourself to a game")
    organizer_user = User.query.filter_by(username=organizer_username).first()
    if not organizer_user:
        raise ValueError(f"username {organizer_username} not found.")
    organizer_user_id = organizer_user.id
    second_player = User.query.filter_by(username=second_player_username).first()
    if not second_player:
        raise ValueError(f"username {second_player_username} not found.")
    second_player_id = second_player.id
    scheduled_date = datetime.strptime(data.get("scheduled_date"), "%Y-%m-%d").date()
    game = Game.query.filter_by(game_name=data.get("game_name").title()).first()
    if not game:
        raise ValueError("Game not found.")
    game_id = game.id
    start_time = datetime.strptime(data.get("start_time"), "%H:%M").time()
    duplicate_session = find_duplicate_session(
        game_id=game_id,
        organizer_user_id=organizer_user_id,
        scheduled_date=scheduled_date,
        start_time=start_time,
    )
    if duplicate_session:
        raise ValueError(
            f"A session of '{game.game_name}' with '{organizer_username}' as organizer and '{second_player_username}' as a participant at {scheduled_date} {start_time} has already been scheduled"
        )
    return organizer_user_id, second_player_id, scheduled_date, game_id, start_time


def create_meeting_link(discord_username_1, discord_username_2):
    try:
        future = asyncio.run_coroutine_threadsafe(
            create_private_channel(discord_username_1, discord_username_2),
            bot.loop
        )
        link = future.result()
        print(link)
        return link
    except Exception as e:
        return { "UnknownError": [discord_username_1, discord_username_2] , "message":e.message }

def create_event(game_name, meeting_link, game_site_url, user1_discord, user2_discord, start_time, end_time):
    description = (f'Have fun playing {game_name}! \n'
                   f'In order to chat go to {meeting_link}, in order to play the game go to {game_site_url}.\n'
                   f'Enjoy!')
    title = f"{game_name}: {user1_discord} Vs {user2_discord}"
    try:
        future = asyncio.run_coroutine_threadsafe(
            create_discord_event(title=title, description=description, meeting_link=meeting_link, start_time=start_time,
                                 end_time=end_time),
            bot.loop
        )
        event_link = future.result()
        print("meeting_link: ", meeting_link, "event_link: ", event_link)

    except Exception as e:
        raise e

def create_session(data):
    user1_id = data["organizer_id"]
    user1_discord = User.query.get_or_404(user1_id).discord_username
    user2_id = data["second_player_id"]
    user2_discord = User.query.get_or_404(user2_id).discord_username
    game_id = data["game_id"]
    game = Game.query.get_or_404(game_id)
    game_name = game.game_name
    game_site_url = game.game_site_url

    scheduled_date = data["scheduled_date"]
    ISRAEL_TZ = timezone(timedelta(hours=2))  # או +3 בקיץ TODO make global variable!
    scheduled_date = data["scheduled_date"]
    start_time = data["start_time"]
    if type(scheduled_date) == str:
        start_time = datetime.strptime(
            scheduled_date + data["start_time"],
            "%Y-%m-%d%H:%M"
        ).replace(tzinfo=ISRAEL_TZ)
    else:
        start_time = datetime.combine(scheduled_date, start_time).replace(tzinfo=ISRAEL_TZ)
    end_time = start_time + timedelta(hours=1)
    meeting_link = create_meeting_link(user1_discord, user2_discord)

    # If meeting_link is not a string, it indicates an error occurred during its creation
    # So we stringify the error and skip creating the event in that case
    if type(meeting_link) != str:
        meeting_link = json.dumps(meeting_link)
    else:
        create_event(game_name, meeting_link, game_site_url, user1_discord, user2_discord, start_time, end_time)


    new_session = ScheduledSession(
        game_id=game_id,
        organizer_user_id=user1_id,
        second_player_id=user2_id,
        scheduled_date=scheduled_date,
        start_time=start_time.time(),
        end_time=end_time.time(),
        game_site_url=game_site_url,
        session_id=data.get("session_id"),
        description=data.get("description"),
        meeting_link=meeting_link,
    )

    db.session.add(new_session)
    db.session.commit()
    print("Session saved successfully!")
    return new_session
