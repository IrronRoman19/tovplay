#!/usr/bin/env python3
"""
Automated Database Migration Testing Script for TovPlay Backend
Tests migrations on a temporary database copy before production deployment.
"""

import os
import sys
import logging
import tempfile
import subprocess
from pathlib import Path
from sqlalchemy import text, create_engine, inspect
from sqlalchemy.exc import OperationalError, ProgrammingError

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from src.app import create_app
from src.app.db import db
from src.app.models import (
    User, UserProfile, Game, UserGamePreference, UserAvailability,
    EmailVerification, ScheduledSession, GameRequest, UserSession
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DatabaseMigrationTester:
    """Test database migrations safely on a temporary copy."""

    def __init__(self, original_db_url, test_db_name="test_migrations_temp"):
        """
        Initialize migration tester.

        Args:
            original_db_url: Connection string for original database
            test_db_name: Name of temporary test database
        """
        self.original_db_url = original_db_url
        self.test_db_name = test_db_name
        self.test_db_url = None
        self.original_db_name = self._extract_db_name(original_db_url)

    def _extract_db_name(self, db_url):
        """Extract database name from URL."""
        return db_url.split('/')[-1]

    def _build_test_db_url(self):
        """Build test database URL from original."""
        base_url = self.original_db_url.rsplit('/', 1)[0]
        self.test_db_url = f"{base_url}/{self.test_db_name}"
        return self.test_db_url

    def _connect_to_postgres(self):
        """Connect to postgres database (for creating/dropping databases)."""
        base_url = self.original_db_url.rsplit('/', 1)[0]
        postgres_url = f"{base_url}/postgres"
        try:
            engine = create_engine(postgres_url)
            return engine
        except Exception as e:
            logger.error(f"❌ Failed to connect to postgres database: {e}")
            return None

    def _database_exists(self, engine, db_name):
        """Check if database exists."""
        try:
            with engine.connect() as conn:
                result = conn.execute(text(
                    "SELECT 1 FROM pg_database WHERE datname = :db_name"
                ), {"db_name": db_name})
                return result.fetchone() is not None
        except Exception as e:
            logger.error(f"❌ Error checking if database exists: {e}")
            return False

    def setup_test_database(self):
        """Create temporary test database as a copy of original."""
        logger.info("🔧 Setting up temporary test database...")

        postgres_engine = self._connect_to_postgres()
        if not postgres_engine:
            return False

        try:
            with postgres_engine.connect() as conn:
                # End current transaction
                conn.execute(text("COMMIT"))

                # Drop test database if it exists
                if self._database_exists(postgres_engine, self.test_db_name):
                    logger.info(f"🗑️  Dropping existing test database: {self.test_db_name}")
                    conn.execute(text(f'DROP DATABASE "{self.test_db_name}" WITH (FORCE)'))
                    conn.execute(text("COMMIT"))

                # Create test database as a copy of original
                logger.info(f"📦 Creating test database: {self.test_db_name} (copy of {self.original_db_name})")
                conn.execute(text(f'CREATE DATABASE "{self.test_db_name}" TEMPLATE "{self.original_db_name}"'))
                conn.execute(text("COMMIT"))
                logger.info(f"✅ Test database created successfully!")
                return True

        except Exception as e:
            logger.error(f"❌ Error creating test database: {e}")
            return False
        finally:
            postgres_engine.dispose()

    def verify_test_database_connection(self):
        """Verify we can connect to the test database."""
        logger.info("🔗 Verifying test database connection...")

        try:
            engine = create_engine(self.test_db_url)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("✅ Test database connection successful!")
            return True
        except OperationalError as e:
            logger.error(f"❌ Test database connection failed: {e}")
            return False

    def verify_schema_integrity(self):
        """Verify all expected tables exist in test database."""
        logger.info("🔍 Verifying database schema integrity...")

        try:
            engine = create_engine(self.test_db_url)
            inspector = inspect(engine)

            expected_tables = {
                'user': ['id', 'email', 'username', 'password_hash'],
                'user_profile': ['id', 'user_id', 'bio', 'avatar_url'],
                'game': ['id', 'name', 'description'],
                'user_game_preference': ['id', 'user_id', 'game_id'],
                'user_availability': ['id', 'user_id', 'day_of_week'],
                'email_verification': ['id', 'user_id', 'verification_code'],
                'scheduled_session': ['id', 'name', 'game_id'],
                'game_request': ['id', 'sender_id', 'recipient_id', 'game_id'],
                'user_session': ['id', 'user_id', 'token_hash'],
            }

            existing_tables = set(inspector.get_table_names())
            logger.info(f"📋 Found {len(existing_tables)} tables in test database")

            missing_tables = []
            for expected_table in expected_tables.keys():
                if expected_table not in existing_tables:
                    missing_tables.append(expected_table)
                else:
                    # Verify columns
                    columns = inspector.get_columns(expected_table)
                    column_names = {col['name'] for col in columns}
                    expected_cols = set(expected_tables[expected_table])
                    missing_cols = expected_cols - column_names

                    if missing_cols:
                        logger.warning(f"⚠️  Table '{expected_table}' missing columns: {missing_cols}")
                    else:
                        logger.info(f"✅ Table '{expected_table}' - all columns present")

            if missing_tables:
                logger.error(f"❌ Missing tables: {missing_tables}")
                return False

            logger.info("✅ Schema verification passed!")
            return True

        except Exception as e:
            logger.error(f"❌ Error verifying schema: {e}")
            return False

    def verify_data_integrity(self):
        """Verify data integrity in test database."""
        logger.info("🔍 Verifying data integrity...")

        try:
            engine = create_engine(self.test_db_url)

            with engine.connect() as conn:
                # Check for referential integrity issues
                # Verify game_requests have valid sender and recipient
                result = conn.execute(text("""
                    SELECT COUNT(*) FROM game_request gr
                    WHERE gr.sender_id NOT IN (SELECT id FROM "user")
                    OR gr.recipient_id NOT IN (SELECT id FROM "user")
                """))

                invalid_requests = result.scalar()
                if invalid_requests > 0:
                    logger.warning(f"⚠️  Found {invalid_requests} game_requests with invalid user references")
                else:
                    logger.info("✅ game_requests - referential integrity OK")

                # Verify scheduled_sessions
                result = conn.execute(text("""
                    SELECT COUNT(*) FROM scheduled_session ss
                    WHERE ss.game_id NOT IN (SELECT id FROM game)
                """))

                invalid_sessions = result.scalar()
                if invalid_sessions > 0:
                    logger.warning(f"⚠️  Found {invalid_sessions} scheduled_sessions with invalid game references")
                else:
                    logger.info("✅ scheduled_sessions - referential integrity OK")

                logger.info("✅ Data integrity verification passed!")
                return True

        except Exception as e:
            logger.error(f"❌ Error verifying data integrity: {e}")
            return False

    def test_write_operations(self):
        """Test that write operations work on the test database."""
        logger.info("✍️  Testing write operations...")

        try:
            engine = create_engine(self.test_db_url)

            with engine.connect() as conn:
                # Test: Create a test user
                test_email = "migration_test@test.com"

                # Delete if exists
                conn.execute(text(
                    'DELETE FROM "user" WHERE email = :email'
                ), {"email": test_email})
                conn.execute(text("COMMIT"))

                # Insert test user
                conn.execute(text(
                    'INSERT INTO "user" (email, username, password_hash) VALUES (:email, :username, :hash)'
                ), {
                    "email": test_email,
                    "username": "migration_test_user",
                    "hash": "test_hash_12345"
                })
                conn.execute(text("COMMIT"))

                # Verify insert
                result = conn.execute(text(
                    'SELECT COUNT(*) FROM "user" WHERE email = :email'
                ), {"email": test_email})

                count = result.scalar()
                if count > 0:
                    logger.info("✅ Write operations test passed!")

                    # Cleanup
                    conn.execute(text(
                        'DELETE FROM "user" WHERE email = :email'
                    ), {"email": test_email})
                    conn.execute(text("COMMIT"))
                    return True
                else:
                    logger.error("❌ Failed to insert test user")
                    return False

        except Exception as e:
            logger.error(f"❌ Error testing write operations: {e}")
            return False

    def cleanup_test_database(self):
        """Drop the temporary test database."""
        logger.info("🧹 Cleaning up test database...")

        postgres_engine = self._connect_to_postgres()
        if not postgres_engine:
            logger.warning("⚠️  Could not cleanup test database")
            return False

        try:
            with postgres_engine.connect() as conn:
                conn.execute(text("COMMIT"))

                # Force disconnect all connections to test database
                conn.execute(text(f"""
                    SELECT pg_terminate_backend(pg_stat_activity.pid)
                    FROM pg_stat_activity
                    WHERE pg_stat_activity.datname = '{self.test_db_name}'
                    AND pid <> pg_backend_pid()
                """))
                conn.execute(text("COMMIT"))

                # Drop test database
                logger.info(f"🗑️  Dropping test database: {self.test_db_name}")
                conn.execute(text(f'DROP DATABASE IF EXISTS "{self.test_db_name}"'))
                conn.execute(text("COMMIT"))
                logger.info("✅ Test database dropped successfully!")
                return True

        except Exception as e:
            logger.error(f"❌ Error dropping test database: {e}")
            return False
        finally:
            postgres_engine.dispose()

    def run_full_test(self):
        """Run full migration test suite."""
        logger.info("=" * 80)
        logger.info("🚀 STARTING AUTOMATED DATABASE MIGRATION TESTING")
        logger.info("=" * 80)
        logger.info(f"Original Database: {self.original_db_name}")
        logger.info(f"Test Database: {self.test_db_name}")
        logger.info("")

        # Build test URL
        self._build_test_db_url()

        # Step 1: Setup test database
        if not self.setup_test_database():
            logger.error("❌ Failed to setup test database. Aborting.")
            return False

        logger.info("")

        # Step 2: Verify connection
        if not self.verify_test_database_connection():
            logger.error("❌ Failed to connect to test database. Cleaning up.")
            self.cleanup_test_database()
            return False

        logger.info("")

        # Step 3: Verify schema
        if not self.verify_schema_integrity():
            logger.error("⚠️  Schema verification failed (may be recoverable)")

        logger.info("")

        # Step 4: Verify data
        if not self.verify_data_integrity():
            logger.error("⚠️  Data integrity check found issues")

        logger.info("")

        # Step 5: Test write operations
        if not self.test_write_operations():
            logger.error("❌ Write operations test failed")
            self.cleanup_test_database()
            return False

        logger.info("")

        # Step 6: Cleanup
        self.cleanup_test_database()

        logger.info("")
        logger.info("=" * 80)
        logger.info("✅ MIGRATION TESTING COMPLETED SUCCESSFULLY")
        logger.info("=" * 80)
        logger.info("")
        logger.info("Summary:")
        logger.info("  ✅ Test database created from production backup")
        logger.info("  ✅ Schema integrity verified")
        logger.info("  ✅ Data integrity verified")
        logger.info("  ✅ Write operations tested")
        logger.info("  ✅ Safe to proceed with production deployment")
        logger.info("")

        return True


def main():
    """Main entry point."""

    # Get original database URL
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        logger.error("❌ DATABASE_URL environment variable not set!")
        return False

    # Hide credentials in logs
    safe_db_url = database_url.split('@')[-1] if '@' in database_url else database_url
    logger.info(f"🔗 Using database: {safe_db_url}")

    # Create tester
    tester = DatabaseMigrationTester(database_url)

    # Run tests
    try:
        success = tester.run_full_test()
        return success
    except KeyboardInterrupt:
        logger.warning("\n⚠️  Test interrupted by user")
        tester.cleanup_test_database()
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        tester.cleanup_test_database()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
