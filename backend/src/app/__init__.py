from apscheduler.schedulers.background import BackgroundScheduler
from .services import expire_old_game_requests, update_scheduled_session_statuses
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask
from flask_migrate import Migrate
from flask_cors import CORS
from .extensions import limiter
from prometheus_flask_exporter import PrometheusMetrics

# Add config path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.secure_config import get_flask_config, validate_environment
from .db import check_db_connection, db, init_db
from .basic_routes import bp as basic_bp  # Basic routes (/, /health) from basic_routes.py
from .routes import bp as api_bp  # Main API blueprint (/api/*) from routes/__init__.py - includes auth, users, games
from .api_endpoints import db_api_bp
from .health import health_bp
from .error_handlers import setup_error_handlers
from .logging_config import setup_logging, get_logger
from .security import setup_security

migrate = Migrate()


def create_app(config_object=None, environment=None):
    # Prevent duplicate initialization in Flask's reloader
    werkzeug_reloader = os.getenv('WERKZEUG_RUN_MAIN') == 'true'

    if werkzeug_reloader and hasattr(create_app, '_app_instance'):
        return create_app._app_instance

    # For non-reloader environments, prevent multiple instances
    if hasattr(create_app, '_app_instance') and not werkzeug_reloader:
        return create_app._app_instance

    app = Flask(__name__)
    # CORS will be configured by security module


    load_dotenv()

    if config_object:
        app.config.from_object(config_object)
    else:
        # Use secure configuration management
        try:
            environment = environment or os.getenv('FLASK_ENV', 'development')

            # Validate configuration first
            validation_result = validate_environment(environment)

            if not validation_result['valid']:
                # Use ASCII characters for Windows compatibility
                if os.name == 'nt':  # Windows
                    print("Configuration validation failed:")
                else:
                    print("❌ Configuration validation failed:")
                for error in validation_result['errors']:
                    print(f"   - {error}")
                raise ValueError("Invalid configuration detected")

            # Load secure configuration
            secure_config = get_flask_config(environment)
            app.config.update(secure_config)

            # Additional Flask-specific configurations
            app.config["JSON_SORT_KEYS"] = False

        except Exception as e:
            if os.name == 'nt':  # Windows
                print(f"Failed to load secure configuration: {e}")
                print("Falling back to basic configuration...")
            else:
                print(f"❌ Failed to load secure configuration: {e}")
                print("🔄 Falling back to basic configuration...")

            # Fallback configuration (less secure)
            app.config["JSON_SORT_KEYS"] = False
            app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///tovplay.db")
            app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
            app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
            app.config['SQLALCHEMY_ECHO'] = True

    # Initialize Prometheus metrics AFTER config is loaded (skip in testing)
    # This will automatically create /metrics endpoint
    if not app.config.get('TESTING'):
        metrics = PrometheusMetrics(app)
        metrics.info('tovplay_backend', 'TovPlay Backend API', version='1.0.0')

    # Setup logging first (before other systems)
    loggers = setup_logging(app)
    logger = loggers['main']

    # Initialize extensions
    init_db(app)

    # Setup security (includes CORS)
    setup_security(app)

    migrate.init_app(app, db)


    # --- START LIMITER CONFIG ---
    app.config["RATELIMIT_STORAGE_URL"] = app.config.get("REDIS_URL")
    if not app.config["RATELIMIT_STORAGE_URL"]:
        # Add a fallback just in case
        app.config["RATELIMIT_STORAGE_URL"] = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # Initialize the Limiter
    limiter.init_app(app) 
    
    # Setup error handlers
    setup_error_handlers(app)
    

    # Register blueprints
    app.register_blueprint(basic_bp)  # Basic routes (/, /health) from basic_routes.py
    app.register_blueprint(api_bp)  # Main API routes (/api/auth, /api/users, /api/games, etc.)
    app.register_blueprint(db_api_bp)  # Database API endpoints with /api/v1 prefix
    app.register_blueprint(health_bp)  # Health monitoring endpoints

    # Optional: Check DB connection on startup
    with app.app_context():
        # Use ASCII characters for Windows compatibility
        if os.name == 'nt':  # Windows
            logger.info("Starting TovPlay backend application")
        else:
            logger.info("🚀 Starting TovPlay backend application")
        db_status = check_db_connection()
        if db_status:
            if os.name == 'nt':  # Windows
                logger.info("Database connection verified")
            else:
                logger.info("✅ Database connection verified")
        else:
            if os.name == 'nt':  # Windows
                logger.error("Database connection failed during startup")
            else:
                logger.error("❌ Database connection failed during startup")

    mark_old_requests_as_expired(app)

    # Cache the app instance to prevent duplicate initialization
    create_app._app_instance = app

    return app


def mark_old_requests_as_expired(app):
    # Skip scheduler in testing mode
    if os.environ.get("TESTING"):
        return
    scheduler = BackgroundScheduler()
    scheduler.add_job(expire_old_game_requests, 'cron', hour=0, minute=0, args=[app])
    scheduler.add_job(update_scheduled_session_statuses, 'interval', minutes=5, args=[app])
    scheduler.start()
