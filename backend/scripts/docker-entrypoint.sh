#!/bin/bash
set -e
# Build: 20251224-1 - CRITICAL SAFEGUARD DEPLOYED

echo "🚀 Starting TovPlay Backend..."

# Debug: Show environment variables being used
echo "📋 Environment Configuration:"
echo "  DATABASE_URL: ${DATABASE_URL:0:50}..." || echo "  DATABASE_URL: NOT SET"
echo "  POSTGRES_HOST: $POSTGRES_HOST"
echo "  POSTGRES_USER: $POSTGRES_USER"
echo "  POSTGRES_DB: $POSTGRES_DB"

# Wait for database to be ready
echo "⏳ Waiting for database to be ready..."
while ! python -c "
import os
import sys
import psycopg2

# Verify DATABASE_URL is set
db_url = os.getenv('DATABASE_URL')
if not db_url:
    print('❌ ERROR: DATABASE_URL environment variable is not set!')
    print(f'Available env vars: {list(os.environ.keys())}')
    sys.exit(1)

print(f'Attempting connection with DATABASE_URL={db_url[:50]}...')
try:
    conn = psycopg2.connect(db_url)
    conn.close()
    print('✅ Database is ready!')
except Exception as e:
    print(f'⏳ Database not ready: {e}')
    exit(1)
"; do
  sleep 2
done

# Initialize database if needed
echo "📋 Checking database initialization..."
if [ "${INITIALIZE_DB:-false}" = "true" ]; then
    # CRITICAL SAFEGUARD: Block INITIALIZE_DB in production to prevent accidental data wipes
    if [ "$FLASK_ENV" = "production" ] || [ "$ENVIRONMENT" = "production" ]; then
        echo "🛑 CRITICAL ERROR: INITIALIZE_DB=true is BLOCKED in production environment!"
        echo "🛑 This safeguard prevents accidental database wipes."
        echo "🛑 If you need to reinitialize, connect directly and do it manually."
        exit 1
    fi
    echo "🏗️ Running database initialization..."
    python scripts/db/init_db.py || echo "⚠️ Database initialization had issues, continuing..."
else
    echo "ℹ️ Skipping database initialization (set INITIALIZE_DB=true to enable)"
fi

# Run database health check
echo "🔍 Running database health check..."
python -c "
import sys
sys.path.insert(0, '/src/app')
from app.db import check_db_connection
check_db_connection()
" || echo "⚠️ Database health check failed, but continuing..."

# Start the application
echo "🌟 Starting Gunicorn server..."
exec "$@"
