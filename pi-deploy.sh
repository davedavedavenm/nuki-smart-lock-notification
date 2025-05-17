#!/bin/bash
# Nuki Smart Lock Notification System - Pi Deployment Script
# Deploys the application on a Raspberry Pi with Docker

echo "Nuki Smart Lock Notification System - Docker Deployment"
echo "-----------------------------------------------------------"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Docker is not installed. Installing Docker..."
    curl -sSL https://get.docker.com | sh
else
    echo "Docker is already installed."
fi

# Create necessary directories
echo "Creating necessary directories..."
mkdir -p config logs data

# Copy example config files if they don't exist
echo "Checking configuration files..."
if [ ! -f "config/config.ini" ] && [ -f "config/config.ini.example" ]; then
    echo "Creating config.ini from example..."
    cp config/config.ini.example config/config.ini
    echo "Don't forget to edit config/config.ini with your settings!"
fi

if [ ! -f "config/credentials.ini" ] && [ -f "config/credentials.ini.example" ]; then
    echo "Creating credentials.ini from example..."
    cp config/credentials.ini.example config/credentials.ini
    echo "Don't forget to edit config/credentials.ini with your API keys!"
fi

# Set proper permissions - THIS IS CRITICAL
echo "Setting proper permissions..."
chmod -R 777 logs data
chmod 777 config
chmod 666 config/config.ini config/credentials.ini 2>/dev/null || true

# Build and start containers with modern docker compose syntax
echo "Building and starting Docker containers..."
echo "This might take a few minutes on the Raspberry Pi..."

# First, stop any running containers
docker compose down

# Build containers from scratch to ensure all changes are applied
docker compose build --no-cache

# Start containers in detached mode
docker compose up -d

# Check if containers started successfully
sleep 5
if [ "$(docker compose ps | grep -c "running")" -eq 2 ]; then
    echo "-----------------------------------------------------------"
    echo "✓ Nuki Smart Lock Notification System deployed successfully!"
    echo "-----------------------------------------------------------"
    echo "Web interface available at: http://$(hostname -I | awk '{print $1}'):5000"
    echo ""
    echo "To view logs:"
    echo "docker compose logs -f"
    echo ""
    echo "To restart services:"
    echo "docker compose restart"
else
    echo "-----------------------------------------------------------"
    echo "❌ Deployment incomplete - some containers failed to start"
    echo "-----------------------------------------------------------"
    echo "Checking container status..."
    docker compose ps
    echo ""
    echo "Checking logs for nuki-monitor:"
    docker compose logs nuki-monitor
    echo ""
    echo "Running troubleshooting script..."
    ./troubleshoot.sh
fi
