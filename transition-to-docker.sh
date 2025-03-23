#!/bin/bash

# Transition script to move from systemd services to Docker containers
# This preserves your existing configuration

echo "Nuki Smart Lock - Transition to Docker"
echo "====================================="
echo ""
echo "This script will help transition your current systemd setup to Docker"
echo "while preserving all your configurations and data."
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Docker is not installed. Installing Docker..."
    curl -sSL https://get.docker.com | sh
    sudo usermod -aG docker $USER
    echo "Docker installed. Please log out and log back in, then run this script again."
    exit 0
fi

# Check if docker compose is available
if ! docker compose version &> /dev/null; then
    echo "Docker Compose plugin not found. Please install the Docker Compose plugin:"
    echo "sudo apt-get install docker-compose-plugin"
    exit 1
fi

# Backup current configuration
echo "Step 1: Backing up current configuration..."
BACKUP_DIR="nuki_backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p $BACKUP_DIR
cp -r config $BACKUP_DIR/
cp -r logs $BACKUP_DIR/ 2>/dev/null || echo "No logs directory found to backup."
echo "Configuration backed up to $BACKUP_DIR"

# Stop current systemd services
echo "Step 2: Stopping current systemd services..."
sudo systemctl stop nuki-monitor.service 2>/dev/null || echo "nuki-monitor service not found or already stopped."
sudo systemctl stop nuki-web.service 2>/dev/null || echo "nuki-web service not found or already stopped."

# Disable systemd services
echo "Step 3: Disabling systemd services..."
sudo systemctl disable nuki-monitor.service 2>/dev/null || echo "nuki-monitor service not enabled or not found."
sudo systemctl disable nuki-web.service 2>/dev/null || echo "nuki-web service not enabled or not found."

# Create directories needed for Docker volumes
echo "Step 4: Preparing Docker environment..."
mkdir -p docker-volumes/config
mkdir -p docker-volumes/logs

# Copy current config to Docker volume location
echo "Step 5: Copying configuration to Docker volumes..."
cp -r config/* docker-volumes/config/

# Build and start Docker containers
echo "Step 6: Building and starting Docker containers..."
docker compose build
docker compose up -d

# Create a systemd service for Docker
echo "Step 7: Creating systemd service for Docker deployment..."
sudo bash -c 'cat > /etc/systemd/system/nuki-docker.service << EOF
[Unit]
Description=Nuki Smart Lock Notification Docker Service
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$(pwd)
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
User=$USER

[Install]
WantedBy=multi-user.target
EOF'

# Enable and start the Docker systemd service
echo "Step 8: Enabling Docker systemd service..."
sudo systemctl enable nuki-docker.service
sudo systemctl start nuki-docker.service

echo ""
echo "Transition completed successfully!"
echo "Your Nuki Smart Lock system is now running in Docker containers."
echo ""
echo "You can manage the system with these commands:"
echo "- Check status: docker compose ps"
echo "- View logs: docker compose logs"
echo "- Stop system: docker compose down"
echo "- Start system: docker compose up -d"
echo ""
echo "Web interface is available at: http://localhost:5000"
echo ""
echo "Note: Your original configuration was backed up to $BACKUP_DIR"
