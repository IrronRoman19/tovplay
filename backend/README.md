# Backend

[![Docker Hub](https://img.shields.io/badge/Docker-Hub-blue?logo=docker)](https://hub.docker.com/r/tovtech/tovplaybackend)

Modern backend API for the TovPlay gaming platform built with Flask, PostgreSQL, and Socket.IO.

## 🚀 Quick Start

### Local Development (Recommended)

```bash
python -m venv .venv
.\.venv\Scripts\activate  # Windows PowerShell
# or on Unix/macOS:
# source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env    # Configure with your credentials
```

then either run (choose one):

```shell
# Recommended while developing with Flask CLI
flask run --host=0.0.0.0 --port=5001 --debug

# Or run the project entrypoint (useful from an IDE)
python run.py
# On Windows PowerShell: python .\run.py
```

Access (local): http://localhost:5001/health

### Docker Development

```bash
# Using external database (default)
docker-compose up backend

# Using local PostgreSQL container
docker-compose --profile local-db up
```

Notes:
- The Compose file maps the container port 5001 to a host port controlled by `BACKEND_PORT` (default host port: 8000). Example: `BACKEND_PORT=8000` -> `http://localhost:8000` forwards to container:5001.
- Provide a `.env` file next to `docker-compose.yml` (copy from `.env.example`).
- The Docker image uses `BUILD_TARGET` to select `development|staging|production` build stages.

## 🛠️ Tech Stack

- **Framework**: Flask 3.1+, Python 3.11
- **Database**: PostgreSQL 17.4 with SQLAlchemy 2.0+
- **Real-time**: flask-socketio
- **Authentication**: JWT tokens with Flask-JWT-Extended
- **Containerization**: Docker multi-stage builds
- **CI/CD**: GitHub Actions → Docker Hub → Servers

## 📋 Configuration

1. **Copy environment example**:
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env`** with your configuration. Minimal required values for development (keys present in `.env.example`):

- `DATABASE_URL` (e.g. `postgresql://user:pass@localhost:5432/tovplay`)
- `SECRET_KEY` (Flask secret key)
- `JWT_SECRET_KEY`
- `FLASK_ENV` (development|production|staging)

Optional but commonly used:
- `REDIS_URL` (for rate limiting)
- `WEBSITE_URL` / `APP_URL`
- `EMAIL_SENDER`, `EMAIL_PASSWORD`, `SMTP_SERVER`, `SMTP_PORT`
- `DISCORD_CLIENT_ID`, `CLIENT_SECRET`, `DISCORD_BOT_TOKEN` (if using Discord features)

Security note: never commit real secrets into the repository. Use `.env` locally or secrets manager in CI/production.

3. **Database**: The repository previously referenced an external PostgreSQL at `45.148.28.196`; do not use that host unless you control it. For local development, run with local-db profile or point `DATABASE_URL` to your local Postgres instance.

## 🗄️ Migrations & Database

- Initialize/migrate the database (local dev):

```bash
# Using alembic directly
alembic upgrade head

# Or using Flask-Migrate (if configured in your environment)
flask db upgrade
```

- To create a new migration:

```bash
alembic revision --autogenerate -m "describe change"
```

- The project also includes `scripts/db/init_db.py` and Docker entrypoint logic. The Docker entrypoint uses `INITIALIZE_DB=true` to run the init script (blocked in production by safeguard).

## 📚 API Endpoints (high level)

- **Health**: `GET /health` (lightweight)
- **Health (detailed)**: `GET /health/detailed` (diagnostic)
- **Health (ready)**: `GET /health/ready` (readiness)
- **Health (live)**: `GET /health/live` (liveness)
- **Metrics**: `/metrics`
- **Auth**: `/api/auth`
- **Users**: `/api/users`
- **Availability**: `/api/availability`
- **Games**: `/api/games`
- and others (see source under `src/app/routes`)

Add sample curl (quick):

```bash
curl -s http://localhost:5001/health | jq .
```

## 🔄 CI/CD

The README documents GitHub Actions-based deployment. I did not find `.github/workflows` files in the repository snapshot; if you rely on CI automation, add workflow files and repository secrets as described below.

### Required GitHub Secrets (example)
- `DOCKERHUB_TOKEN`
- `SSH_PRIVATE_KEY`
- `SERVER_IP`
- `SERVER_USER`

## 🧪 Testing

Run tests locally:

```bash
# Shell (Unix/macOS)
./scripts/run_tests.sh

# Windows (PowerShell)
.\scripts\run_tests.bat

# Or run pytest directly
pytest
pytest --cov=src tests/
```

Notes:
- Some integration/functional tests may expect the server to be running at `http://localhost:5001` or a test database. Check `scripts/test_api_endpoints.py` and the `tests/` folder for details.

## 🧭 Logs & Troubleshooting

- Local logs directory: `logs/` (check `backend/logs/` in the project root).
- Docker logs: `docker-compose logs backend` or `docker logs <container>`.
- If DB connection fails on startup, verify `DATABASE_URL` and Postgres readiness. The Docker entrypoint waits for DB availability and will refuse `INITIALIZE_DB=true` in `production` to prevent accidental wipes.

Common quick checks:
- Ensure `.env` exists and required vars are set
- Confirm Postgres is reachable from the environment (port, user, password)
- Check `backend/logs` for application-level errors

## 🤖 Discord Bot Setup

To enable Discord integration features, you need to create a Discord Application and Bot:

1.  **Go to the Developer Portal**: Visit [Discord Developer Portal](https://discord.com/developers/applications).
2.  **Create Application**: Click "New Application", give it a name (e.g., "TovPlay Bot"), and create it.
3.  **Create Bot**:
    *   Navigate to the **Bot** tab in the left sidebar.
    *   Click "Add Bot" and confirm.
    *   **Important**: Under the "Token" section, click "Reset Token" to generate your bot token. Copy this immediately; you won't see it again.
    *   Set this token as `DISCORD_BOT_TOKEN` in your `.env` file.
4.  **Configure Intents**:
    *   Scroll down to "Privileged Gateway Intents".
    *   Enable **Server Members Intent**, **Message Content Intent**, and **Presence Intent** (depending on what features you need).
    *   Save changes.
5.  **OAuth2 Setup (Client ID & Secret)**:
    *   Navigate to the **OAuth2** tab.
    *   Copy the **Client ID** and **Client Secret**.
    *   Add these to your `.env` file as `DISCORD_CLIENT_ID` and `DISCORD_CLIENT_SECRET`.
    *   Add Redirects: Under "Redirects", add your callback URL (e.g., `http://localhost:5001/api/discord/callback` for local dev).

## Contributing & License

Contributions welcome — please open issues / pull requests and include tests for new behavior.

This repository is covered by the top-level `LICENSE` file. See `../LICENSE` (or the repository root) for details.

---

If you'd like, I can also:
- add a short `CONTRIBUTING.md` and a sample GitHub Actions workflow,
- add a one-line curl example for a protected endpoint (requires creating test credentials),
- or make the README changes more compact (strip verbose sections).
