import json
import os
import eventlet
import eventlet.wsgi
import psycopg2
import select
import socketio
from dotenv import load_dotenv

from src.api.game_request_api import match_user_availability

# Load environment variables from .env file
load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")
NOTIFICATION_CHANNEL = os.environ.get("NOTIFICATION_CHANNEL", "notifications")
SOCKETIO_HOST = os.environ.get("SOCKETIO_HOST", "127.0.0.1")
SOCKETIO_PORT = int(os.environ.get("SOCKETIO_PORT", 8080))

# Get allowed origins from environment or use defaults
allowed_origins = os.getenv('ALLOWED_ORIGINS', 'http://localhost:3000,https://tovplay.vps.webdock.cloud').split(',')
allowed_origins = [origin.strip() for origin in allowed_origins if origin.strip()]

# Create a python-socketio Server using eventlet with restricted CORS
sio = socketio.Server(async_mode='eventlet', cors_allowed_origins=allowed_origins)

# Track user -> set of session ids
CONNECTIONS = {}

flask_app_instance = None


# --- Basic Socket.IO event handlers to maintain CONNECTIONS ---
@sio.event
def connect(sid, environ, auth):
    print(f"Client connected: sid={sid}")
    sio.emit('player_status_changed', {'sid': sid, 'status': 'connected'})


@sio.event
def disconnect(sid):
    # Remove sid from any CONNECTIONS entries
    removed_user = None
    for user_id, sids in list(CONNECTIONS.items()):
        if sid in sids:
            sids.remove(sid)
            if not sids:
                del CONNECTIONS[user_id]
            removed_user = user_id
            break
    print(f"Client disconnected: sid={sid} user={removed_user} total_users={len(CONNECTIONS)}")
    sio.emit('player_status_changed', {'sid': sid, 'status': 'disconnected', 'userId': removed_user})


@sio.on('register')
def handle_register(sid, data):
    """Client sends {'userId': '<id>'} to register their session with a user id."""
    try:
        user_id = str(data.get('userId') if isinstance(data, dict) else data)
    except Exception:
        user_id = None

    if not user_id:
        print(f"register event missing userId from sid={sid}")
        return

    room = f"user:{user_id}"
    # Add mapping
    CONNECTIONS.setdefault(user_id, set()).add(sid)
    # Put this session into a room named for the user so notify_user can target it
    sio.enter_room(sid, room)
    print(f"Registered sid={sid} as user={user_id}. Total users={len(CONNECTIONS)}")
    sio.emit('player_status_changed', {'sid': sid, 'status': 'registered', 'userId': user_id})


def get_all_players_for_game(game_name, current_user_id):
    # 1. Identify Online Players from CONNECTIONS
    online_player_ids = {uid for uid, sids in CONNECTIONS.items() if uid != str(current_user_id)}

    # 2. Fetch all potential players for the game from the database using match_user_availability
    with flask_app_instance.app_context():
        all_potential_players_db = match_user_availability(current_user_id, game_name) or []

    online_players = []
    offline_players = []

    # 3. Filter and populate online_players and offline_players lists
    for player_data in all_potential_players_db:
        player_id_str = str(player_data.get('id'))  # Ensure ID is string for comparison

        if player_id_str in online_player_ids:
            online_players.append(player_data)
        else:
            offline_players.append(player_data)
    return online_players, offline_players


# --- Application-specific event handlers ---
@sio.on('get_players')
def get_players(sid, data):
    print(f"SERVER: 'get_players' event received from sid={sid}. Data: {data}")

    if not isinstance(data, dict):
        data = {}

    game_name = data.get('game_name')
    current_user_id = data.get('current_user_id')

    if not game_name or not current_user_id:
        print(f"SERVER: Missing gameName or currentUserId in 'get_players' event from sid={sid}")
        # Reply directly to the requesting session
        sio.emit('player_list_update', {'onlinePlayers': [], 'offlinePlayers': []}, room=sid)
        return

    online_players, offline_players = get_all_players_for_game(game_name, current_user_id)

    print(
        f"SERVER: Logic complete. Found {len(online_players)} online, {len(offline_players)} offline for game {game_name}.")
    sio.emit('player_list_update', {'onlinePlayers': online_players, 'offlinePlayers': offline_players}, room=sid)
    print(f"SERVER: Emitting 'player_list_update' back to client sid={sid}.")

    # Broadcast player_joined_game to all other connected clients
    sio.emit('player_joined_game', {'userId': current_user_id, 'gameName': game_name}, skip_sid=sid)
    print(f"SERVER: Broadcasting 'player_joined_game' for user={current_user_id} in game={game_name}.")


# --- Notification sending ---

def notify_user(user_id, message):
    """Send a notification message to all connected clients for a given user_id.
    message should be a JSON-serializable object or a JSON string; we'll emit it as a string payload
    under the 'notification' event to maintain a simple contract with clients.
    """
    if not user_id:
        print("notify_user called without user_id")
        return
    room = f"user:{user_id}"
    try:
        if isinstance(message, (dict, list)):
            payload = json.dumps(message)
        else:
            payload = str(message)
        # Emit to the user's room
        sio.emit('notification', payload, room=room)
        print(f"Notification emitted to user={user_id} room={room} payload={payload}")
    except Exception as e:
        print(f"Error emitting notification to user={user_id}: {e}")


# --- PostgreSQL LISTEN loop ---

def listen_for_notifications():
    """Listen for PostgreSQL NOTIFY messages and forward them to the correct user room.
    This runs in an eventlet greenthread so it won't block the WSGI server.
    Expected payload: JSON containing a key 'recipient_user_id' or 'user_id' to route the message.
    """
    if not DATABASE_URL:
        print("DATABASE_URL not set; skipping DB notification listener")
        return

    conn = None
    try:
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute(f"LISTEN {NOTIFICATION_CHANNEL};")
        print(f"Listening for notifications on channel: {NOTIFICATION_CHANNEL}")

        while True:
            # Use select to wait for notifications
            if select.select([conn], [], [], 1)[0]:
                conn.poll()
                while conn.notifies:
                    notify = conn.notifies.pop(0)
                    print(f"Received DB notification: {notify.payload}")
                    try:
                        data = json.loads(notify.payload)
                        recipient_user_id = data.get('recipient_user_id') or data.get('user_id')
                        if recipient_user_id is None:
                            print("Notification payload missing recipient_user_id or user_id; skipping")
                            continue
                        notify_user(str(recipient_user_id), data)
                    except json.JSONDecodeError:
                        print(f"Invalid JSON in notification payload: {notify.payload}")
                    except Exception as e:
                        print(f"Error handling DB notification: {e}")
            # Sleep briefly to yield
            eventlet.sleep(0.01)

    except Exception as e:
        print(f"Postgres LISTEN error: {e}")
    finally:
        if conn:
            conn.close()
            print("Database connection closed.")


def start_servers(flask_app=None):
    global flask_app_instance
    flask_app_instance = flask_app
    # Wrap Socket.IO WSGI app
    sio_app = socketio.WSGIApp(sio)
    # Start DB listener in a greenthread
    eventlet.spawn_n(listen_for_notifications)

    print(f"Starting Socket.IO server on ws://{SOCKETIO_HOST}:{SOCKETIO_PORT}")
    # Serve the WSGI app with eventlet
    eventlet.wsgi.server(eventlet.listen((SOCKETIO_HOST, SOCKETIO_PORT)), sio_app)


if __name__ == '__main__':
    pass
