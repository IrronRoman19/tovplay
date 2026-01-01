#!/usr/bin/env python3
"""
Database Migration Manager for TovPlay
Handles versioned database migrations with up/down capabilities and rollback support.
"""

import os
import sys
import importlib.util
import psycopg2
from psycopg2.extras import DictCursor
from datetime import datetime
import logging
from pathlib import Path
from typing import List, Dict, Optional
import traceback

# Add the parent directory to Python path to import app modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

class MigrationManager:
    def __init__(self, database_url: str, migrations_dir: str = None):
        """
        Initialize migration manager.
        
        Args:
            database_url: PostgreSQL connection URL
            migrations_dir: Path to migrations directory
        """
        self.database_url = database_url
        self.migrations_dir = migrations_dir or os.path.join(os.path.dirname(__file__), 'migrations')
        self.conn = None
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('migration.log')
            ]
        )
        self.logger = logging.getLogger(__name__)

    def connect(self):
        """Establish database connection."""
        try:
            self.conn = psycopg2.connect(self.database_url)
            self.conn.autocommit = False
            self.logger.info("Connected to database successfully")
        except Exception as e:
            self.logger.error(f"Failed to connect to database: {e}")
            raise

    def disconnect(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.logger.info("Disconnected from database")

    def ensure_migration_table(self):
        """Create migration tracking table if it doesn't exist."""
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS schema_migrations (
                        version VARCHAR(255) PRIMARY KEY,
                        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        description TEXT,
                        checksum VARCHAR(64)
                    )
                """)
                self.conn.commit()
                self.logger.info("Migration table ensured")
        except Exception as e:
            self.conn.rollback()
            self.logger.error(f"Failed to create migration table: {e}")
            raise

    def get_applied_migrations(self) -> List[str]:
        """Get list of applied migration versions."""
        try:
            with self.conn.cursor() as cur:
                cur.execute("SELECT version FROM schema_migrations ORDER BY version")
                return [row[0] for row in cur.fetchall()]
        except Exception as e:
            self.logger.error(f"Failed to get applied migrations: {e}")
            return []

    def get_pending_migrations(self) -> List[Dict]:
        """Get list of pending migrations."""
        applied = set(self.get_applied_migrations())
        all_migrations = self.discover_migrations()
        
        pending = []
        for migration in all_migrations:
            if migration['version'] not in applied:
                pending.append(migration)
        
        return pending

    def discover_migrations(self) -> List[Dict]:
        """Discover all migration files."""
        migrations = []
        
        if not os.path.exists(self.migrations_dir):
            self.logger.warning(f"Migrations directory not found: {self.migrations_dir}")
            return migrations

        for filename in os.listdir(self.migrations_dir):
            if filename.endswith('.py') and not filename.startswith('__'):
                # Extract version from filename (format: 001_description.py)
                parts = filename[:-3].split('_', 1)
                if len(parts) == 2:
                    version, description = parts
                    migrations.append({
                        'version': version,
                        'filename': filename,
                        'description': description.replace('_', ' '),
                        'path': os.path.join(self.migrations_dir, filename)
                    })

        # Sort by version
        migrations.sort(key=lambda x: x['version'])
        return migrations

    def load_migration_module(self, migration_path: str):
        """Load migration module from file."""
        spec = importlib.util.spec_from_file_location("migration", migration_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def validate_migration(self, migration_path: str) -> bool:
        """Validate migration file has required functions."""
        try:
            module = self.load_migration_module(migration_path)
            return hasattr(module, 'up') and hasattr(module, 'down')
        except Exception as e:
            self.logger.error(f"Invalid migration file {migration_path}: {e}")
            return False

    def calculate_checksum(self, migration_path: str) -> str:
        """Calculate checksum of migration file."""
        import hashlib
        with open(migration_path, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()[:16]

    def apply_migration(self, migration: Dict) -> bool:
        """Apply a single migration."""
        try:
            if not self.validate_migration(migration['path']):
                raise Exception("Invalid migration file")

            module = self.load_migration_module(migration['path'])
            checksum = self.calculate_checksum(migration['path'])

            self.logger.info(f"Applying migration {migration['version']}: {migration['description']}")

            # Start transaction
            with self.conn.cursor() as cur:
                # Execute migration
                module.up(cur)
                
                # Record migration
                cur.execute("""
                    INSERT INTO schema_migrations (version, description, checksum)
                    VALUES (%s, %s, %s)
                """, (migration['version'], migration['description'], checksum))
                
                self.conn.commit()
                self.logger.info(f"Successfully applied migration {migration['version']}")
                return True

        except Exception as e:
            self.conn.rollback()
            self.logger.error(f"Failed to apply migration {migration['version']}: {e}")
            self.logger.error(traceback.format_exc())
            return False

    def rollback_migration(self, migration: Dict) -> bool:
        """Rollback a single migration."""
        try:
            if not self.validate_migration(migration['path']):
                raise Exception("Invalid migration file")

            module = self.load_migration_module(migration['path'])

            self.logger.info(f"Rolling back migration {migration['version']}: {migration['description']}")

            # Start transaction
            with self.conn.cursor() as cur:
                # Execute rollback
                if hasattr(module, 'down'):
                    module.down(cur)
                else:
                    raise Exception("Migration has no 'down' function")
                
                # Remove migration record
                cur.execute("DELETE FROM schema_migrations WHERE version = %s", (migration['version'],))
                
                self.conn.commit()
                self.logger.info(f"Successfully rolled back migration {migration['version']}")
                return True

        except Exception as e:
            self.conn.rollback()
            self.logger.error(f"Failed to rollback migration {migration['version']}: {e}")
            self.logger.error(traceback.format_exc())
            return False

    def migrate_up(self, target_version: str = None) -> bool:
        """Apply pending migrations up to target version."""
        try:
            self.ensure_migration_table()
            pending = self.get_pending_migrations()

            if not pending:
                self.logger.info("No pending migrations")
                return True

            if target_version:
                # Filter to only migrations up to target
                pending = [m for m in pending if m['version'] <= target_version]

            success = True
            for migration in pending:
                if not self.apply_migration(migration):
                    success = False
                    break

            return success

        except Exception as e:
            self.logger.error(f"Migration up failed: {e}")
            return False

    def migrate_down(self, target_version: str = None, steps: int = 1) -> bool:
        """Rollback migrations to target version or by number of steps."""
        try:
            applied = self.get_applied_migrations()
            applied.reverse()  # Start with most recent

            if target_version:
                # Rollback to specific version
                to_rollback = []
                for version in applied:
                    if version > target_version:
                        # Find migration info
                        all_migrations = self.discover_migrations()
                        migration_info = next((m for m in all_migrations if m['version'] == version), None)
                        if migration_info:
                            to_rollback.append(migration_info)
            else:
                # Rollback by steps
                to_rollback = []
                all_migrations = self.discover_migrations()
                for i, version in enumerate(applied[:steps]):
                    migration_info = next((m for m in all_migrations if m['version'] == version), None)
                    if migration_info:
                        to_rollback.append(migration_info)

            if not to_rollback:
                self.logger.info("No migrations to rollback")
                return True

            success = True
            for migration in to_rollback:
                if not self.rollback_migration(migration):
                    success = False
                    break

            return success

        except Exception as e:
            self.logger.error(f"Migration down failed: {e}")
            return False

    def status(self):
        """Show migration status."""
        try:
            self.ensure_migration_table()
            applied = set(self.get_applied_migrations())
            all_migrations = self.discover_migrations()

            print("\n" + "="*80)
            print("MIGRATION STATUS")
            print("="*80)
            
            if not all_migrations:
                print("No migrations found")
                return

            for migration in all_migrations:
                status = "APPLIED" if migration['version'] in applied else "PENDING"
                status_marker = "✓" if status == "APPLIED" else "⏳"
                print(f"{status_marker} {migration['version']} - {migration['description']} [{status}]")

            pending_count = len([m for m in all_migrations if m['version'] not in applied])
            applied_count = len(applied)

            print("-" * 80)
            print(f"Total migrations: {len(all_migrations)}")
            print(f"Applied: {applied_count}")
            print(f"Pending: {pending_count}")
            print("="*80)

        except Exception as e:
            self.logger.error(f"Failed to get status: {e}")

def main():
    """Main CLI interface."""
    import argparse
    
    # Get database URL from environment
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("Error: DATABASE_URL environment variable not set")
        sys.exit(1)

    parser = argparse.ArgumentParser(description='TovPlay Database Migration Manager')
    parser.add_argument('command', choices=['up', 'down', 'status', 'create'], 
                       help='Migration command')
    parser.add_argument('--target', help='Target migration version')
    parser.add_argument('--steps', type=int, default=1, 
                       help='Number of steps for down migration')
    parser.add_argument('--name', help='Name for new migration (create command)')

    args = parser.parse_args()

    # Initialize migration manager
    manager = MigrationManager(database_url)
    
    try:
        manager.connect()

        if args.command == 'up':
            success = manager.migrate_up(args.target)
            sys.exit(0 if success else 1)

        elif args.command == 'down':
            success = manager.migrate_down(args.target, args.steps)
            sys.exit(0 if success else 1)

        elif args.command == 'status':
            manager.status()

        elif args.command == 'create':
            if not args.name:
                print("Error: --name required for create command")
                sys.exit(1)
            
            # Generate next version number
            existing_migrations = manager.discover_migrations()
            next_version = f"{len(existing_migrations) + 1:03d}"
            
            filename = f"{next_version}_{args.name.lower().replace(' ', '_')}.py"
            filepath = os.path.join(manager.migrations_dir, filename)
            
            # Create migration template
            template = f'''"""
Migration {next_version}: {args.name}
Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

def up(cursor):
    """
    Apply migration changes.
    
    Args:
        cursor: Database cursor for executing SQL
    """
    # Add your migration SQL here
    cursor.execute("""
        -- Example: CREATE TABLE example (id SERIAL PRIMARY KEY, name VARCHAR(255));
    """)

def down(cursor):
    """
    Rollback migration changes.
    
    Args:
        cursor: Database cursor for executing SQL
    """
    # Add your rollback SQL here
    cursor.execute("""
        -- Example: DROP TABLE IF EXISTS example;
    """)
'''
            
            with open(filepath, 'w') as f:
                f.write(template)
            
            print(f"Created migration: {filepath}")

    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
    finally:
        manager.disconnect()

if __name__ == '__main__':
    main()