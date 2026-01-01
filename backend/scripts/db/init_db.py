#!/usr/bin/env python3
"""
Database initialization script for TovPlay backend.
This script creates tables, indexes, and seeds initial data.
"""

import os
import sys
import logging
from pathlib import Path
from sqlalchemy import text, create_engine
from sqlalchemy.exc import OperationalError, ProgrammingError

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from src.app import create_app
from src.app.db import db
from src.app.models import (
    User, UserProfile, Game, UserGamePreference, UserAvailability,
    EmailVerification, ScheduledSession, GameRequest, UserSession
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def check_database_connection(database_url):
    """Check if we can connect to the database."""
    try:
        engine = create_engine(database_url)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("✅ Database connection successful!")
        return True
    except OperationalError as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False


def create_database_if_not_exists(database_url):
    """Create the database if it doesn't exist (PostgreSQL)."""
    try:
        # Extract database name from URL
        db_name = database_url.split('/')[-1]
        base_url = database_url.rsplit('/', 1)[0]
        
        # Connect to postgres database to create our database
        postgres_url = f"{base_url}/postgres"
        engine = create_engine(postgres_url)
        
        with engine.connect() as conn:
            # Check if database exists
            result = conn.execute(text(
                "SELECT 1 FROM pg_database WHERE datname = :db_name"
            ), {"db_name": db_name})
            
            if not result.fetchone():
                logger.info(f"📦 Creating database: {db_name}")
                conn.execute(text("COMMIT"))  # End current transaction
                conn.execute(text(f'CREATE DATABASE "{db_name}"'))
                logger.info(f"✅ Database {db_name} created successfully!")
            else:
                logger.info(f"✅ Database {db_name} already exists")
                
    except Exception as e:
        logger.warning(f"⚠️ Could not create database (may need manual creation): {e}")


def run_sql_file(database_url, sql_file_path):
    """Execute SQL commands from a file."""
    try:
        engine = create_engine(database_url)
        with open(sql_file_path, 'r', encoding='utf-8') as file:
            sql_content = file.read()
        
        with engine.connect() as conn:
            # Split by semicolon and execute each statement
            statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
            for statement in statements:
                if statement:
                    conn.execute(text(statement))
                    conn.commit()
        
        logger.info(f"✅ Successfully executed {sql_file_path}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error executing {sql_file_path}: {e}")
        return False


def create_tables(app):
    """Create all database tables using SQLAlchemy models."""
    try:
        with app.app_context():
            logger.info("📋 Creating database tables...")
            db.create_all()
            logger.info("✅ All tables created successfully!")
            return True
    except Exception as e:
        logger.error(f"❌ Error creating tables: {e}")
        return False


def seed_initial_data(app):
    """Seed the database with initial data."""
    try:
        with app.app_context():
            logger.info("🌱 Seeding initial data...")
            
            # Check if we already have games
            existing_games = Game.query.count()
            if existing_games > 0:
                logger.info(f"✅ Database already has {existing_games} games, skipping seed")
                return True
            
            # Run the seed SQL file
            db_scripts_dir = Path(__file__).parent
            seed_file = db_scripts_dir / "seed.sql"
            
            if seed_file.exists():
                return run_sql_file(app.config['SQLALCHEMY_DATABASE_URI'], seed_file)
            else:
                logger.warning("⚠️ Seed file not found, skipping initial data")
                return True
                
    except Exception as e:
        logger.error(f"❌ Error seeding data: {e}")
        return False


def create_indexes(app):
    """Create database indexes for performance."""
    try:
        with app.app_context():
            logger.info("🔍 Creating database indexes...")
            
            db_scripts_dir = Path(__file__).parent
            indexes_file = db_scripts_dir / "indexes.sql"
            
            if indexes_file.exists():
                return run_sql_file(app.config['SQLALCHEMY_DATABASE_URI'], indexes_file)
            else:
                logger.warning("⚠️ Indexes file not found, skipping index creation")
                return True
                
    except Exception as e:
        logger.error(f"❌ Error creating indexes: {e}")
        return False


def verify_setup(app):
    """Verify that the database setup is working correctly."""
    try:
        with app.app_context():
            logger.info("🔍 Verifying database setup...")
            
            # Check if tables exist and have expected structure
            tables_to_check = [
                'User', 'UserProfile', 'Game', 'UserGamePreference',
                'UserAvailability', 'EmailVerification', 'ScheduledSession',
                'GameRequest', 'UserSession'
            ]
            
            for table_name in tables_to_check:
                result = db.session.execute(text(
                    "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = :table_name"
                ), {"table_name": table_name})
                
                if result.scalar() == 0:
                    logger.error(f"❌ Table {table_name} not found!")
                    return False
            
            # Check if we have some games
            game_count = Game.query.count()
            logger.info(f"✅ Database verification passed! Found {game_count} games")
            return True
            
    except Exception as e:
        logger.error(f"❌ Error verifying setup: {e}")
        return False


def main():
    """Main initialization function."""
    logger.info("🚀 Starting TovPlay database initialization...")
    
    # Create Flask app
    try:
        app = create_app()
    except Exception as e:
        logger.error(f"❌ Failed to create Flask app: {e}")
        return False
    
    database_url = app.config.get('SQLALCHEMY_DATABASE_URI')
    if not database_url:
        logger.error("❌ DATABASE_URL not configured!")
        return False
    
    logger.info(f"🔗 Using database: {database_url.split('@')[-1]}")  # Hide credentials in log
    
    # Step 1: Create database if needed
    create_database_if_not_exists(database_url)
    
    # Step 2: Check connection
    if not check_database_connection(database_url):
        logger.error("❌ Cannot connect to database. Please check your configuration.")
        return False
    
    # Step 3: Run initialization SQL (extensions, roles, etc.)
    db_scripts_dir = Path(__file__).parent
    init_sql_file = db_scripts_dir / "init.sql"
    if init_sql_file.exists():
        if not run_sql_file(database_url, init_sql_file):
            logger.warning("⚠️ Initial SQL setup had issues, but continuing...")
    
    # Step 4: Create tables
    if not create_tables(app):
        logger.error("❌ Failed to create tables!")
        return False
    
    # Step 5: Create indexes
    if not create_indexes(app):
        logger.warning("⚠️ Index creation had issues, but continuing...")
    
    # Step 6: Seed initial data
    if not seed_initial_data(app):
        logger.warning("⚠️ Data seeding had issues, but continuing...")
    
    # Step 7: Verify setup
    if not verify_setup(app):
        logger.error("❌ Database verification failed!")
        return False
    
    logger.info("🎉 Database initialization completed successfully!")
    logger.info("💡 Next steps:")
    logger.info("   1. Update your environment secrets for production")
    logger.info("   2. Remove or secure the demo user account")
    logger.info("   3. Configure backup strategy")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)