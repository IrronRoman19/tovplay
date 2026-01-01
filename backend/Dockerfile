# Multi-stage Dockerfile for TovPlay Backend
# Supports development, staging, and production environments
# Optimized for build caching and efficiency

# Base stage with common dependencies
FROM python:3.11-slim AS base

# Set Python environment variables for better performance
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=100

# Set working directory
WORKDIR /app

# Install system dependencies including PostgreSQL client and curl for health checks
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy and install Python dependencies first for better layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn psycopg2-binary

# Copy application code (this layer will change most frequently)
COPY . .

# Make scripts executable
RUN chmod +x scripts/docker-entrypoint.sh && \
    find scripts -type f -name "*.py" -exec chmod +x {} +

# Create directories for logs and data
RUN mkdir -p logs data

# Development stage
FROM base AS development

# Install development dependencies
RUN pip install --no-cache-dir \
    flask[dotenv] \
    pytest \
    pytest-cov \
    black \
    flake8 \
    mypy \
    bandit

# Expose port
EXPOSE 5001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:5001/health || exit 1

# Use entrypoint script for initialization
ENTRYPOINT ["./scripts/docker-entrypoint.sh"]

# Development uses Flask development server
CMD ["flask", "run", "--host=0.0.0.0", "--port=5001", "--debug"]

# Staging stage
FROM base AS staging

# Create non-root user for security
RUN groupadd -r tovplay && useradd -r -g tovplay -d /app tovplay
RUN chown -R tovplay:tovplay /app
USER tovplay

# Expose port
EXPOSE 5001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:5001/health || exit 1

# Use entrypoint script for initialization
ENTRYPOINT ["./scripts/docker-entrypoint.sh"]

# Staging uses Gunicorn with fewer workers
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:5001", "wsgi:app"]

# Production stage
FROM base AS production

# Remove unnecessary packages for production
RUN apt-get purge -y build-essential && apt-get autoremove -y

# Create non-root user for security
RUN groupadd -r tovplay && useradd -r -g tovplay -d /app tovplay
RUN chown -R tovplay:tovplay /app
USER tovplay

# Expose port
EXPOSE 5001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:5001/health || exit 1

# Use entrypoint script for initialization
ENTRYPOINT ["./scripts/docker-entrypoint.sh"]

# Production uses Gunicorn with optimized settings
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5001", "wsgi:app"]