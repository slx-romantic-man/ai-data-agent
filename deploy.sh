#!/bin/bash
set -e

echo "============================================"
echo "  AI Data Agent v4.3 - Production Deploy"
echo "============================================"
echo ""

# Check prerequisites
echo "[1/5] Checking prerequisites..."
if ! command -v docker &> /dev/null; then
    echo "ERROR: Docker is not installed. Please install Docker first."
    exit 1
fi
if ! command -v docker compose &> /dev/null && ! docker compose version &> /dev/null 2>&1; then
    echo "ERROR: Docker Compose is not installed."
    exit 1
fi
echo "  Docker: $(docker --version)"
echo "  Compose: $(docker compose version 2>/dev/null || docker-compose --version)"
echo ""

# Check .env.production
echo "[2/5] Checking configuration..."
if [ ! -f .env.production ]; then
    echo "ERROR: .env.production not found!"
    exit 1
fi
if grep -q "change-me" .env.production; then
    echo "WARNING: .env.production still contains placeholder values. Please configure:"
    grep "change-me" .env.production
    echo ""
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi
echo "  Configuration valid"
echo ""

# Start services
echo "[3/5] Starting services..."
docker compose up -d --build
echo ""

# Wait for MySQL and backend
echo "[4/5] Waiting for services to be ready..."
MAX_WAIT=60
for i in $(seq 1 $MAX_WAIT); do
    if docker compose exec -T backend curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "  Backend is ready!"
        break
    fi
    if [ $i -eq $MAX_WAIT ]; then
        echo "  WARNING: Backend health check timed out. Check logs with: docker compose logs backend"
        break
    fi
    sleep 2
    printf "."
done
echo ""

# Initialize database
echo "[5/5] Initializing database..."
docker compose exec -T backend python scripts/init_database.py || echo "  WARNING: DB init failed. May need manual setup."
echo ""

echo "============================================"
echo "  Deployment Complete!"
echo "============================================"
echo ""
echo "  Frontend:  http://your-server-ip/"
echo "  API Docs:  http://your-server-ip/docs"
echo "  Health:    http://your-server-ip/health"
echo ""
echo "  Useful commands:"
echo "    docker compose logs -f backend    # View backend logs"
echo "    docker compose logs -f mysql      # View MySQL logs"
echo "    docker compose restart backend    # Restart backend"
echo "    docker compose down               # Stop all services"
echo ""
