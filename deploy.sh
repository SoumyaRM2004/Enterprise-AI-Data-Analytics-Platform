#!/bin/bash
# Enterprise AI Analytics Platform - Deployment Script
set -e

echo "============================================="
echo "  Enterprise AI Analytics Platform"
echo "  Deployment Script"
echo "============================================="

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "Docker Compose is not installed. Please install it first."
    exit 1
fi

# Detect compose command
COMPOSE_CMD="docker compose"
if ! docker compose version &> /dev/null; then
    COMPOSE_CMD="docker-compose"
fi

# Build images
echo "Building Docker images..."
$COMPOSE_CMD build

# Run migrations
echo "Running database migrations..."
$COMPOSE_CMD run --rm backend python manage.py migrate

# Collect static files
echo "Collecting static files..."
$COMPOSE_CMD run --rm backend python manage.py collectstatic --noinput 2>/dev/null || true

# Create superuser (optional)
echo "Creating superuser (skip if already exists)..."
$COMPOSE_CMD run --rm backend python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print('Superuser created: admin / admin123')
else:
    print('Superuser already exists')
" 2>/dev/null || true

# Start services
echo "Starting all services..."
$COMPOSE_CMD up -d

echo "============================================="
echo "  Deployment Complete!"
echo "============================================="
echo ""
echo "  Services:"
echo "    Frontend:  http://localhost:3000"
echo "    API:       http://localhost:8000/api"
echo "    Admin:     http://localhost:8000/admin"
echo "    Nginx:     http://localhost:80"
echo ""
echo "  Default credentials:"
echo "    Username: admin"
echo "    Password: admin123"
echo ""
echo "  Useful commands:"
echo "    View logs:  $COMPOSE_CMD logs -f"
echo "    Stop:       $COMPOSE_CMD down"
echo "    Restart:    $COMPOSE_CMD restart"
echo "    Status:     $COMPOSE_CMD ps"
echo "============================================="
