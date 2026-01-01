#!/bin/bash
set -e

# TovPlay Backend Deployment Script
echo "🚀 Starting TovPlay Backend deployment..."

# Configuration
APP_NAME="tovplay-backend"
IMAGE_NAME="ghcr.io/8gsean/tovplay-backend/backend"
CONTAINER_NAME="tovplay-backend-container"
PORT="5001"
ENV_FILE=".env"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    log_error "Docker is not running. Please start Docker first."
    exit 1
fi

# Check if environment file exists
if [ ! -f "$ENV_FILE" ]; then
    log_warn "Environment file $ENV_FILE not found. Creating from example..."
    cp .env.example "$ENV_FILE"
    log_warn "Please edit $ENV_FILE with your actual values before continuing."
    exit 1
fi

# Get the latest tag or use 'latest'
TAG=${1:-latest}
FULL_IMAGE_NAME="$IMAGE_NAME:$TAG"

log_info "Pulling image: $FULL_IMAGE_NAME"
docker pull "$FULL_IMAGE_NAME" || {
    log_error "Failed to pull image. Trying to build locally..."
    docker build -t "$FULL_IMAGE_NAME" .
}

# Stop existing container if running
log_info "Stopping existing container (if any)..."
docker stop "$CONTAINER_NAME" 2>/dev/null || true
docker rm "$CONTAINER_NAME" 2>/dev/null || true

# Create network if it doesn't exist
docker network create tovplay-network 2>/dev/null || true

# Run new container
log_info "Starting new container..."
docker run -d \
    --name "$CONTAINER_NAME" \
    --network tovplay-network \
    -p "$PORT:5001" \
    --env-file "$ENV_FILE" \
    --restart unless-stopped \
    --health-cmd="curl -f http://localhost:5001/api/health || exit 1" \
    --health-interval=30s \
    --health-timeout=10s \
    --health-retries=3 \
    "$FULL_IMAGE_NAME"

# Wait for container to be healthy
log_info "Waiting for container to become healthy..."
timeout=60
while [ $timeout -gt 0 ]; do
    if [ "$(docker inspect --format='{{.State.Health.Status}}' $CONTAINER_NAME 2>/dev/null)" == "healthy" ]; then
        log_info "✅ Container is healthy!"
        break
    fi
    sleep 2
    timeout=$((timeout - 2))
done

if [ $timeout -le 0 ]; then
    log_error "Container failed to become healthy within 60 seconds"
    docker logs "$CONTAINER_NAME"
    exit 1
fi

# Show logs
log_info "📋 Recent logs:"
docker logs --tail 10 "$CONTAINER_NAME"

log_info "🎉 Deployment completed successfully!"
log_info "Backend is running on port $PORT"
log_info "Health check: http://localhost:$PORT/api/health"