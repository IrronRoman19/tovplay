"""
Migration 001: Initial Schema
Created: 2024-09-08
Description: Create initial database schema for TovPlay application
"""

def up(cursor):
    """
    Apply migration changes - Create initial schema.
    
    Args:
        cursor: Database cursor for executing SQL
    """
    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(255) UNIQUE NOT NULL,
            email VARCHAR(255) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            first_name VARCHAR(255),
            last_name VARCHAR(255),
            is_active BOOLEAN DEFAULT true,
            is_verified BOOLEAN DEFAULT false,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    
    # Sessions table for user sessions
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_sessions (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            session_token VARCHAR(255) UNIQUE NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ip_address INET,
            user_agent TEXT
        );
    """)
    
    # API keys table for authentication
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS api_keys (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            key_hash VARCHAR(255) UNIQUE NOT NULL,
            name VARCHAR(255) NOT NULL,
            permissions JSONB DEFAULT '{}',
            is_active BOOLEAN DEFAULT true,
            expires_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_used TIMESTAMP
        );
    """)
    
    # Audit log table for tracking changes
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
            action VARCHAR(255) NOT NULL,
            resource_type VARCHAR(255),
            resource_id VARCHAR(255),
            old_values JSONB,
            new_values JSONB,
            ip_address INET,
            user_agent TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    
    # System settings table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS system_settings (
            id SERIAL PRIMARY KEY,
            key VARCHAR(255) UNIQUE NOT NULL,
            value JSONB,
            description TEXT,
            is_public BOOLEAN DEFAULT false,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

def down(cursor):
    """
    Rollback migration changes - Drop initial schema.
    
    Args:
        cursor: Database cursor for executing SQL
    """
    # Drop tables in reverse order of creation (handle foreign key constraints)
    cursor.execute("DROP TABLE IF EXISTS system_settings;")
    cursor.execute("DROP TABLE IF EXISTS audit_logs;")
    cursor.execute("DROP TABLE IF EXISTS api_keys;")
    cursor.execute("DROP TABLE IF EXISTS user_sessions;")
    cursor.execute("DROP TABLE IF EXISTS users;")