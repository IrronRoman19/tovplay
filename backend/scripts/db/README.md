# TovPlay Database Scripts

This directory contains database initialization and management scripts for the TovPlay backend.

## Files Overview

- **`init_db.py`** - Main database initialization script
- **`init.sql`** - PostgreSQL extensions and roles setup
- **`seed.sql`** - Initial data seeding (games, demo users)
- **`indexes.sql`** - Performance indexes
- **`README.md`** - This documentation

## Quick Start

### First-Time Setup

```bash
# Make sure you're in the backend directory
cd backend

# Set up environment variables
export DATABASE_URL="postgresql://username:password@localhost:5432/tovplay"
export FLASK_ENV="development"

# Run the initialization script
python scripts/db/init_db.py
```

### Development Reset

```bash
# Reinitialize after reset
python scripts/db/init_db.py
```

## Environment Setup

### Required Environment Variables

```bash
# Database connection
DATABASE_URL="postgresql://username:password@host:port/database"

# Flask environment
FLASK_ENV="development"  # or "staging" or "production"

# Other required variables (see .env.example)
SECRET_KEY="your-secret-key"
EMAIL_SENDER="your-email"
EMAIL_PASSWORD="your-email-password"
SMTP_SERVER="smtp.gmail.com"
SMTP_PORT="587"
WEBSITE_URL_DEVELOPMENT="http://localhost:3000"
```

### Database Requirements

- PostgreSQL 12+ (recommended 15+)
- Extensions: `uuid-ossp`, `pgcrypto`
- Sufficient permissions to create databases, tables, and indexes

## Script Details

### init_db.py

Main initialization script that:

1. **Creates database** if it doesn't exist
2. **Sets up extensions** (UUID, crypto functions)
3. **Creates tables** from SQLAlchemy models
4. **Adds indexes** for performance optimization
5. **Seeds initial data** (games, demo users)
6. **Verifies setup** to ensure everything works

**Usage:**
```bash
python scripts/db/init_db.py
```

**Safe to run multiple times** - won't duplicate data or break existing setup.

### SQL Files

#### init.sql
- Creates PostgreSQL extensions
- Sets up database roles and permissions
- Run automatically by `init_db.py`

#### seed.sql
- Inserts popular games (Chess, Scrabble, Among Us, etc.)
- Creates demo user account for testing
- Sets up sample user preferences and availability
- Uses `ON CONFLICT DO NOTHING` for safe re-runs

#### indexes.sql
- Creates performance indexes on commonly queried columns
- Includes composite indexes for complex queries
- Partial indexes for filtered queries
- Optimizes user lookups, game searches, session queries

## Production Deployment

### Security Checklist

- [ ] Remove or secure demo user account
- [ ] Use strong, unique passwords for database roles
- [ ] Configure proper database backup strategy
- [ ] Set up monitoring for database performance
- [ ] Review and adjust database connection limits
- [ ] Enable SSL for database connections

### Recommended Production Setup

```bash
# Set production environment
export FLASK_ENV="production"

# Use secure database URL with SSL
export DATABASE_URL="postgresql://user:pass@host:5432/tovplay?sslmode=require"

# Run initialization
python scripts/db/init_db.py

# Verify setup
python -c "from app import create_app; from app.db import check_db_connection; app = create_app(); check_db_connection()"
```

## Troubleshooting

### Common Issues

**Connection Refused**
- Check PostgreSQL service is running
- Verify host, port, username, password in DATABASE_URL
- Ensure database server accepts connections

**Permission Denied**
- User needs CREATE DATABASE permissions
- Check database role has necessary privileges
- For cloud databases, may need admin/superuser access

**Import Errors**
- Ensure you're running from the backend directory
- Check Python path includes the src directory
- Verify all dependencies are installed (`pip install -r requirements.txt`)

**Table Already Exists**
- Scripts are designed to handle existing tables
- Check logs for specific error messages

### Database Health Check

```bash
# Test database connection
python -c "
from app import create_app
from app.db import db, check_db_connection
app = create_app()
with app.app_context():
    check_db_connection()
    print(f'Tables: {len(db.metadata.tables)}')
"
```

### Manual Database Operations

```sql
-- Check table sizes
SELECT schemaname,tablename,attname,n_distinct,correlation FROM pg_stats WHERE tablename IN ('User', 'Game', 'GameRequest');

-- Check indexes
SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'User';

-- Check recent activity
SELECT * FROM "GameRequest" ORDER BY created_at DESC LIMIT 10;
```

## Migration Strategy

For future schema changes, consider implementing a proper migration system:

1. **Alembic** for SQLAlchemy migrations
2. **Versioned migration files**
3. **Rollback capabilities**
4. **Production-safe migration process**

Example future migration setup:
```bash
# Initialize Alembic (future enhancement)
alembic init migrations
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head
```

## Backup and Recovery

### Automated Backups

```bash
# Create backup
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d_%H%M%S).sql

# Restore from backup
psql $DATABASE_URL < backup_file.sql
```

### Data Export/Import

```bash
# Export specific tables
pg_dump -t "Game" -t "User" $DATABASE_URL > games_and_users.sql

# Import to new database
psql $NEW_DATABASE_URL < games_and_users.sql
```