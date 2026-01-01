"""
Health monitoring and diagnostic endpoints for TovPlay backend.
Provides comprehensive system health checks including database, services, and dependencies.
"""

import os
import time
import datetime
import psutil
from flask import Blueprint, jsonify, current_app
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from .db import db
from .models import User, Game, GameRequest

health_bp = Blueprint('health', __name__)


def check_database_health():
    """Check database connectivity and basic operations."""
    try:
        start_time = time.time()

        # Basic connection test
        db.session.execute(text("SELECT 1"))
        db.session.commit()

        response_time = (time.time() - start_time) * 1000  # Convert to milliseconds

        # Get connection pool information
        pool = db.engine.pool
        pool_info = {
            'active': pool.checkedout(),
            'idle': pool.size() - pool.checkedout(),
            'total': pool.size()
        }

        return {
            'status': 'up',
            'response_time_ms': round(response_time, 2),
            'connection_pool': pool_info
        }

    except SQLAlchemyError as e:
        return {
            'status': 'down',
            'error': str(e)
        }
    except Exception as e:
        return {
            'status': 'down',
            'error': f'Unexpected error: {str(e)}'
        }


def check_system_resources():
    """Check system resource usage."""
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            'status': 'healthy',
            'cpu_percent': cpu_percent,
            'memory': {
                'total_gb': round(memory.total / (1024**3), 2),
                'used_gb': round(memory.used / (1024**3), 2),
                'percent': memory.percent,
                'available_gb': round(memory.available / (1024**3), 2)
            },
            'disk': {
                'total_gb': round(disk.total / (1024**3), 2),
                'used_gb': round(disk.used / (1024**3), 2),
                'free_gb': round(disk.free / (1024**3), 2),
                'percent': round((disk.used / disk.total) * 100, 2)
            }
        }
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }


def check_environment_config():
    """Check critical environment variables and configuration."""
    required_vars = [
        'DATABASE_URL',
        'SECRET_KEY',
        'FLASK_ENV'
    ]
    
    optional_vars = [
        'EMAIL_SENDER',
        'EMAIL_PASSWORD', 
        'SMTP_SERVER',
        'SMTP_PORT',
        'WEBSITE_URL'
    ]
    
    config_status = {
        'status': 'healthy',
        'required_vars': {},
        'optional_vars': {},
        'flask_config': {}
    }
    
    # Check required variables
    missing_required = []
    for var in required_vars:
        value = os.getenv(var)
        if value:
            # Don't expose actual values, just confirm they exist
            config_status['required_vars'][var] = 'configured' if len(value) > 0 else 'empty'
        else:
            config_status['required_vars'][var] = 'missing'
            missing_required.append(var)
    
    # Check optional variables
    for var in optional_vars:
        value = os.getenv(var)
        config_status['optional_vars'][var] = 'configured' if value else 'not_set'
    
    # Check Flask configuration
    try:
        config_status['flask_config'] = {
            'debug': current_app.debug,
            'testing': current_app.testing,
            'secret_key_configured': bool(current_app.config.get('SECRET_KEY')),
            'database_configured': bool(current_app.config.get('SQLALCHEMY_DATABASE_URI'))
        }
    except Exception as e:
        config_status['flask_config']['error'] = str(e)
    
    if missing_required:
        config_status['status'] = 'unhealthy'
        config_status['missing_required'] = missing_required
    
    return config_status


@health_bp.route('/health')
def basic_health():
    """Basic health check endpoint - lightweight for load balancers."""
    try:
        # Quick database ping
        db.session.execute(text("SELECT 1"))
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.datetime.utcnow().isoformat(),
            'service': 'backend'
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.datetime.utcnow().isoformat(),
            'service': 'backend'
        }), 503


@health_bp.route('/health/detailed')
def detailed_health():
    """Comprehensive health check with all system components."""
    start_time = time.time()
    
    health_report = {
        'timestamp': datetime.datetime.utcnow().isoformat(),
        'service': 'backend',
        'version': os.getenv('APP_VERSION', 'unknown'),
        'environment': os.getenv('FLASK_ENV', 'unknown'),
        'uptime_seconds': time.time() - start_time,
        'overall_status': 'healthy',
        'checks': {}
    }
    
    # Database health
    health_report['checks']['database'] = check_database_health()
    
    # System resources  
    health_report['checks']['system'] = check_system_resources()
    
    # Environment configuration
    health_report['checks']['configuration'] = check_environment_config()
    
    # Determine overall status
    unhealthy_checks = [
        check for check_name, check in health_report['checks'].items()
        if check.get('status') != 'healthy'
    ]
    
    if unhealthy_checks:
        health_report['overall_status'] = 'degraded' if len(unhealthy_checks) == 1 else 'unhealthy'
    
    # Calculate total response time
    health_report['response_time_ms'] = round((time.time() - start_time) * 1000, 2)
    
    status_code = 200
    if health_report['overall_status'] == 'unhealthy':
        status_code = 503
    elif health_report['overall_status'] == 'degraded':
        status_code = 200  # Still functional, but with warnings
    
    return jsonify(health_report), status_code


@health_bp.route('/health/database')
def database_health():
    """Dedicated database health endpoint."""
    db_health = check_database_health()
    db_health['timestamp'] = datetime.datetime.utcnow().isoformat()
    
    status_code = 200 if db_health['status'] == 'healthy' else 503
    return jsonify(db_health), status_code


@health_bp.route('/health/ready')
def readiness_probe():
    """Kubernetes readiness probe - checks if app is ready to serve traffic."""
    try:
        # Check database connectivity
        db.session.execute(text("SELECT 1"))
        
        # Check if essential data exists
        game_count = Game.query.count()
        
        return jsonify({
            'status': 'ready',
            'timestamp': datetime.datetime.utcnow().isoformat(),
            'games_available': game_count > 0
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 'not_ready',
            'error': str(e),
            'timestamp': datetime.datetime.utcnow().isoformat()
        }), 503


@health_bp.route('/health/live')
def liveness_probe():
    """Kubernetes liveness probe - checks if app is alive."""
    return jsonify({
        'status': 'alive',
        'timestamp': datetime.datetime.utcnow().isoformat(),
        'pid': os.getpid()
    }), 200


@health_bp.route('/metrics')
def metrics():
    """Basic metrics endpoint for monitoring systems."""
    try:
        with db.session.begin():
            user_count = User.query.count()
            game_count = Game.query.count()
            
            # Recent activity metrics
            now = datetime.datetime.now()
            active_requests = GameRequest.query.filter(
                GameRequest.status == 'pending'
            ).count()
            
            requests_24h = GameRequest.query.filter(
                GameRequest.created_at >= now - datetime.timedelta(hours=24)
            ).count()
            
            requests_7d = GameRequest.query.filter(
                GameRequest.created_at >= now - datetime.timedelta(days=7)
            ).count()
        
        # System metrics
        cpu_percent = psutil.cpu_percent()
        memory = psutil.virtual_memory()
        
        return jsonify({
            'timestamp': datetime.datetime.utcnow().isoformat(),
            'application': {
                'total_users': user_count,
                'total_games': game_count,
                'active_game_requests': active_requests,
                'requests_last_24h': requests_24h,
                'requests_last_7d': requests_7d
            },
            'system': {
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_used_gb': round(memory.used / (1024**3), 2)
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'timestamp': datetime.datetime.utcnow().isoformat()
        }), 500