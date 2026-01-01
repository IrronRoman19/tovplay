from flask import Blueprint, jsonify
import os
import time
import datetime
import psutil
from sqlalchemy import text
from .db import db

bp = Blueprint('main', __name__)

@bp.route("/")
def home():
    return jsonify({
        "message": "Welcome to TovPlay Backend API",
        "status": "running",
        "version": "1.0"
    })

@bp.route("/health")
def health():
    return jsonify({"status": "healthy"})

@bp.route("/api/health")
def api_health():
    """Enhanced health check endpoint for monitoring systems."""
    health_data = {
        'status': 'healthy',
        'timestamp': datetime.datetime.utcnow().isoformat() + 'Z',
        'environment': os.getenv('FLASK_ENV', 'production'),
        'version': os.getenv('APP_VERSION', '1.0.0'),
        'checks': {}
    }

    # Database check with connection pool info
    try:
        start = time.time()
        db.session.execute(text('SELECT 1'))
        db.session.commit()
        response_time = round((time.time() - start) * 1000, 2)

        pool = db.engine.pool
        health_data['checks']['database'] = {
            'status': 'up',
            'response_time_ms': response_time,
            'connection_pool': {
                'active': pool.checkedout(),
                'idle': pool.size() - pool.checkedout(),
                'total': pool.size()
            }
        }
    except Exception as e:
        health_data['status'] = 'unhealthy'
        health_data['checks']['database'] = {
            'status': 'down',
            'error': str(e)
        }

    # Memory check
    try:
        memory = psutil.virtual_memory()
        health_data['checks']['memory'] = {
            'status': 'ok' if memory.percent < 90 else 'warning',
            'percent_used': round(memory.percent, 2),
            'available_mb': round(memory.available / 1024 / 1024, 2)
        }
    except Exception as e:
        health_data['checks']['memory'] = {'status': 'error', 'error': str(e)}

    # Disk check
    try:
        disk = psutil.disk_usage('/')
        health_data['checks']['disk'] = {
            'status': 'ok' if disk.percent < 90 else 'warning',
            'percent_used': round(disk.percent, 2),
            'available_gb': round(disk.free / 1024 / 1024 / 1024, 2)
        }
    except Exception as e:
        health_data['checks']['disk'] = {'status': 'error', 'error': str(e)}

    # WebSocket check (optional - if realtime_backend is available)
    try:
        from src.api.realtime_backend import get_active_connections
        health_data['checks']['websocket'] = {
            'status': 'up',
            'active_connections': get_active_connections()
        }
    except:
        health_data['checks']['websocket'] = {'status': 'not_available'}

    status_code = 200 if health_data['status'] == 'healthy' else 503
    return jsonify(health_data), status_code
