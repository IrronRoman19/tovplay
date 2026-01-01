"""
API endpoints that work with real PostgreSQL data
"""
from flask import Blueprint, jsonify, request
from datetime import datetime
import psycopg2
import os
from src.api.game_request_api import match_user_availability
from src.app.services import get_user_id_from_token, check_admin
from src.app.security import rate_limit

# Create API blueprint for database endpoints
db_api_bp = Blueprint('db_api', __name__, url_prefix='/api/v1')

def get_db_connection():
    """Get database connection using environment variables"""
    database_url = os.getenv('DATABASE_URL', 'postgresql://tovplay_user:tovplay_dev_password@localhost:5432/tovplay_dev')
    try:
        conn = psycopg2.connect(database_url)
        return conn
    except Exception as e:
        # Don't log the full database URL (contains credentials)
        return None

@db_api_bp.route('/users', methods=['GET'])
@rate_limit(requests_per_hour=60, burst_limit=20)
def get_users():
    """Get all users from database - Admin only"""
    user_id = get_user_id_from_token()
    if not user_id:
        return jsonify({"error": "Authentication required"}), 401
    
    try:
        check_admin()
    except:
        return jsonify({"error": "Admin access required"}), 403
    
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500
    
    try:
        cur = conn.cursor()
        # Use parameterized queries to prevent SQL injection
        cur.execute("""
            SELECT id, username, email, created_at, updated_at, verified
            FROM "User" 
            ORDER BY created_at DESC
        """)
        
        users = []
        for row in cur.fetchall():
            users.append({
                "id": str(row[0]),
                "username": row[1],
                "email": row[2],
                "created_at": row[3].isoformat() if row[3] else None,
                "updated_at": row[4].isoformat() if row[4] else None,
                "verified": row[5]
            })
        
        cur.close()
        conn.close()
        
        return jsonify({
            "users": users,
            "count": len(users),
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        if conn:
            conn.close()
        return jsonify({"error": "Database query failed"}), 500

@db_api_bp.route('/games', methods=['GET'])
@rate_limit(requests_per_hour=100, burst_limit=30)
def get_games():
    """Get all games from database - Public endpoint but rate limited"""
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500
    
    try:
        cur = conn.cursor()
        # Use parameterized queries
        cur.execute("""
            SELECT id, game_name, created_at
            FROM "Game"
            ORDER BY game_name
        """)
        
        games = []
        for row in cur.fetchall():
            games.append({
                "id": str(row[0]),
                "name": row[1],
                "created_at": row[2].isoformat() if row[2] else None
            })
        
        cur.close()
        conn.close()
        
        return jsonify({
            "games": games,
            "count": len(games),
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        if conn:
            conn.close()
        return jsonify({"error": str(e)}), 500

@db_api_bp.route('/game-requests', methods=['GET'])
def get_game_requests():
    """Get game requests with user and game details"""
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500
    
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT 
                gr.id, gr.status, gr.preferred_date, gr.preferred_time,
                gr.max_players, gr.description, gr.created_at,
                u.username, u.first_name, u.last_name,
                g.name AS game_name, g.category
            FROM game_requests gr
            JOIN users u ON gr.user_id = u.id
            JOIN games g ON gr.game_id = g.id
            ORDER BY gr.created_at DESC
        """)
        
        requests = []
        for row in cur.fetchall():
            requests.append({
                "id": row[0],
                "status": row[1],
                "preferred_date": row[2].isoformat() if row[2] else None,
                "preferred_time": str(row[3]) if row[3] else None,
                "max_players": row[4],
                "description": row[5],
                "created_at": row[6].isoformat() if row[6] else None,
                "user": {
                    "username": row[7],
                    "first_name": row[8],
                    "last_name": row[9]
                },
                "game": {
                    "name": row[10],
                    "category": row[11]
                }
            })
        
        cur.close()
        conn.close()
        
        return jsonify({
            "game_requests": requests,
            "count": len(requests),
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        if conn:
            conn.close()
        return jsonify({"error": str(e)}), 500

@db_api_bp.route('/stats', methods=['GET'])
def get_stats():
    """Get platform statistics"""
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500
    
    try:
        cur = conn.cursor()
        
        # Get counts
        cur.execute("SELECT COUNT(*) FROM users WHERE is_active = true")
        active_users = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM games WHERE is_active = true")
        active_games = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM game_requests WHERE status = 'pending'")
        pending_requests = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM game_requests WHERE status = 'accepted'")
        accepted_requests = cur.fetchone()[0]
        
        # Get popular games
        cur.execute("""
            SELECT g.name, COUNT(gr.id) as request_count
            FROM games g
            LEFT JOIN game_requests gr ON g.id = gr.game_id
            GROUP BY g.id, g.name
            ORDER BY request_count DESC
            LIMIT 5
        """)
        
        popular_games = []
        for row in cur.fetchall():
            popular_games.append({
                "game": row[0],
                "requests": row[1]
            })
        
        cur.close()
        conn.close()
        
        return jsonify({
            "stats": {
                "active_users": active_users,
                "active_games": active_games,
                "pending_requests": pending_requests,
                "accepted_requests": accepted_requests,
                "popular_games": popular_games
            },
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        if conn:
            conn.close()
        return jsonify({"error": str(e)}), 500

@db_api_bp.route('/health/database', methods=['GET'])
def database_health():
    """Check database health with real connection test"""
    conn = get_db_connection()
    if not conn:
        return jsonify({
            "status": "unhealthy", 
            "error": "Database connection failed",
            "timestamp": datetime.utcnow().isoformat()
        }), 503
    
    try:
        cur = conn.cursor()
        cur.execute("SELECT version(), current_database(), current_user, now()")
        result = cur.fetchone()
        
        cur.close()
        conn.close()
        
        return jsonify({
            "status": "healthy",
            "database_info": {
                "version": result[0],
                "database": result[1],
                "user": result[2],
                "server_time": result[3].isoformat()
            },
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        if conn:
            conn.close()
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }), 503

@db_api_bp.route('/players', methods=['GET'])
def get_players_api():
    game_name = request.args.get('gameName')
    current_user_id = request.args.get('currentUserId')

    if not game_name or not current_user_id:
        return jsonify({"error": "gameName and currentUserId are required"}), 400

    # Use match_user_availability to get all potential players
    all_potential_players = match_user_availability(current_user_id, game_name)

    # Filter out the current user and return the rest as offline players
    offline_players = [player for player in all_potential_players if str(player['id']) != str(current_user_id)]

    return jsonify({
        "onlinePlayers": [], # Always empty for the REST API fallback
        "offlinePlayers": offline_players
    })