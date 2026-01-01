"""
Migration 002: Add Indexes
Created: 2024-09-08
Description: Add database indexes for performance optimization
"""

def up(cursor):
    """
    Apply migration changes - Add performance indexes.
    
    Args:
        cursor: Database cursor for executing SQL
    """
    # Index on users table
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active) WHERE is_active = true;")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at);")
    
    # Index on user_sessions table
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON user_sessions(user_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_sessions_token ON user_sessions(session_token);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_sessions_expires_at ON user_sessions(expires_at);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_sessions_active ON user_sessions(expires_at) WHERE expires_at > CURRENT_TIMESTAMP;")
    
    # Index on api_keys table
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON api_keys(user_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_api_keys_hash ON api_keys(key_hash);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_api_keys_active ON api_keys(is_active) WHERE is_active = true;")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_api_keys_expires_at ON api_keys(expires_at);")
    
    # Index on audit_logs table
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs(user_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_resource ON audit_logs(resource_type, resource_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at);")
    
    # Index on system_settings table
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_system_settings_key ON system_settings(key);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_system_settings_public ON system_settings(is_public) WHERE is_public = true;")
    
    # Composite indexes for common queries
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_sessions_user_expires ON user_sessions(user_id, expires_at) WHERE expires_at > CURRENT_TIMESTAMP;")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_api_keys_user_active ON api_keys(user_id, is_active) WHERE is_active = true;")

def down(cursor):
    """
    Rollback migration changes - Remove indexes.
    
    Args:
        cursor: Database cursor for executing SQL
    """
    # Drop composite indexes first
    cursor.execute("DROP INDEX IF EXISTS idx_user_sessions_user_expires;")
    cursor.execute("DROP INDEX IF EXISTS idx_api_keys_user_active;")
    
    # Drop system_settings indexes
    cursor.execute("DROP INDEX IF EXISTS idx_system_settings_key;")
    cursor.execute("DROP INDEX IF EXISTS idx_system_settings_public;")
    
    # Drop audit_logs indexes
    cursor.execute("DROP INDEX IF EXISTS idx_audit_logs_user_id;")
    cursor.execute("DROP INDEX IF EXISTS idx_audit_logs_action;")
    cursor.execute("DROP INDEX IF EXISTS idx_audit_logs_resource;")
    cursor.execute("DROP INDEX IF EXISTS idx_audit_logs_created_at;")
    
    # Drop api_keys indexes
    cursor.execute("DROP INDEX IF EXISTS idx_api_keys_user_id;")
    cursor.execute("DROP INDEX IF EXISTS idx_api_keys_hash;")
    cursor.execute("DROP INDEX IF EXISTS idx_api_keys_active;")
    cursor.execute("DROP INDEX IF EXISTS idx_api_keys_expires_at;")
    
    # Drop user_sessions indexes
    cursor.execute("DROP INDEX IF EXISTS idx_user_sessions_user_id;")
    cursor.execute("DROP INDEX IF EXISTS idx_user_sessions_token;")
    cursor.execute("DROP INDEX IF EXISTS idx_user_sessions_expires_at;")
    cursor.execute("DROP INDEX IF EXISTS idx_user_sessions_active;")
    
    # Drop users indexes
    cursor.execute("DROP INDEX IF EXISTS idx_users_email;")
    cursor.execute("DROP INDEX IF EXISTS idx_users_username;")
    cursor.execute("DROP INDEX IF EXISTS idx_users_active;")
    cursor.execute("DROP INDEX IF EXISTS idx_users_created_at;")