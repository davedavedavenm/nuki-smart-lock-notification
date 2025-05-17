#!/bin/bash

# Nuki Smart Lock Notification System - Docker Deployment Script
# This script handles the deployment process on a Raspberry Pi

set -e

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Nuki Smart Lock Notification System - Docker Deployment${NC}"
echo "-----------------------------------------------------------"

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Please run this script as root${NC}"
    exit 1
fi

# Check if Docker is installed
if ! command_exists docker; then
    echo -e "${YELLOW}Docker not found. Installing Docker...${NC}"
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    usermod -aG docker $USER
    echo -e "${GREEN}Docker installed successfully!${NC}"
else
    echo -e "${GREEN}Docker is already installed.${NC}"
fi

# Create necessary directories
echo -e "${BLUE}Creating necessary directories...${NC}"
mkdir -p /root/nukiweb/{config,logs,data}

# Clone or update the repo
echo -e "${BLUE}Cloning or updating the repository...${NC}"
if [ -d "/root/nukiweb/.git" ]; then
    echo "Repository exists, updating..."
    cd /root/nukiweb
    git pull
else
    echo "Cloning fresh repository..."
    rm -rf /root/nukiweb
    git clone https://github.com/davedavedavenm/nuki-smart-lock-notification.git /root/nukiweb
    cd /root/nukiweb
fi

# Check if config files exist, create if not
echo -e "${BLUE}Checking configuration files...${NC}"
if [ ! -f "config/config.ini" ]; then
    echo "Creating config.ini from example..."
    cp config/config.ini.example config/config.ini
    echo -e "${YELLOW}Don't forget to edit config/config.ini with your settings!${NC}"
fi

if [ ! -f "config/credentials.ini" ]; then
    echo "Creating credentials.ini from example..."
    cp config/credentials.ini.example config/credentials.ini
    echo -e "${YELLOW}Don't forget to edit config/credentials.ini with your API keys!${NC}"
fi

# Set proper permissions for Docker volumes
echo -e "${BLUE}Setting proper permissions...${NC}"
chmod -R 777 logs data
chmod 777 config
[ -f "config/config.ini" ] && chmod 644 config/config.ini
[ -f "config/credentials.ini" ] && chmod 644 config/credentials.ini

# Configure Docker to handle network timeouts better
echo -e "${BLUE}Configuring Docker settings...${NC}"
mkdir -p /etc/docker
cat > /etc/docker/daemon.json << 'EOF'
{
  "registry-mirrors": ["https://registry-1.docker.io"],
  "max-concurrent-downloads": 1,
  "max-concurrent-uploads": 1
}
EOF

# Restart Docker to apply changes
systemctl restart docker

# Build and start containers
echo -e "${BLUE}Building and starting Docker containers...${NC}"
echo "This might take a few minutes on the Raspberry Pi..."
DOCKER_BUILDKIT=0 docker compose build --no-cache

echo -e "${BLUE}Starting services...${NC}"
docker compose up -d

# Check if services are running
echo -e "${BLUE}Checking service status...${NC}"
if docker ps | grep -q "nuki-web" && docker ps | grep -q "nuki-monitor"; then
    echo -e "${GREEN}Services are running successfully!${NC}"
    echo "Web interface is available at: http://$(hostname -I | awk '{print $1}'):5000"
else
    echo -e "${RED}Services failed to start properly.${NC}"
    echo "Checking logs for issues..."
    docker logs nuki-web
    docker logs nuki-monitor
fi

echo -e "${BLUE}Deployment completed!${NC}"
echo "Run 'docker compose logs -f' to view service logs"
echo "Run 'docker compose down' to stop services"
echo "Run 'docker compose restart' to restart services"
