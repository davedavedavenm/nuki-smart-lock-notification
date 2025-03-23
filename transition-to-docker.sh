#!/bin/bash

# Transition script to move from systemd services to Docker containers
# This preserves your existing configuration

# Define colors for better readability
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=======================================${NC}"
echo -e "${BLUE}   Nuki Project - Transition to Docker   ${NC}"
echo -e "${BLUE}=======================================${NC}"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
  echo -e "${RED}Please run as root (sudo)${NC}"
  exit 1
fi

# First, run the backup script
echo -e "${YELLOW}Step 1: Creating a backup using the existing backup script...${NC}"
if [ -f "./nuki_backup_restore.sh" ]; then
  chmod +x ./nuki_backup_restore.sh
  
  # Create an automatic backup
  TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
  BACKUP_DIR="/root/nukiweb/backups"
  mkdir -p "$BACKUP_DIR"
  BACKUP_FILE="$BACKUP_DIR/nukiweb_pre_docker_${TIMESTAMP}.tar.gz"
  
  echo -e "${YELLOW}Stopping Nuki services for consistent backup...${NC}"
  systemctl stop nuki-web.service
  systemctl stop nuki-monitor.service
  
  echo -e "${YELLOW}Creating backup at: ${NC}${BACKUP_FILE}"
  # Create tar excluding the backups directory and venv directory to save space
  tar --exclude="./backups" --exclude="./venv" -czf "$BACKUP_FILE" -C /root nukiweb
  
  # Check if backup was successful
  if [ -f "$BACKUP_FILE" ]; then
    size=$(du -h "$BACKUP_FILE" | cut -f1)
    echo -e "${GREEN}Backup completed successfully!${NC}"
    echo -e "Backup file: $BACKUP_FILE"
    echo -e "Size: $size"
  else
    echo -e "${RED}Backup failed! Aborting transition.${NC}"
    
    # Restart services since we stopped them
    systemctl start nuki-monitor.service
    systemctl start nuki-web.service
    exit 1
  fi
else
  echo -e "${RED}Backup script not found. Would you like to continue without a backup? (y/n)${NC}"
  read -p "Continue without backup? " confirm
  if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
    echo -e "${YELLOW}Transition canceled.${NC}"
    exit 0
  fi
fi

# Check if Docker is installed
echo -e "${YELLOW}Step 2: Checking if Docker is installed...${NC}"
if ! command -v docker &> /dev/null; then
    echo -e "${YELLOW}Docker is not installed. Installing Docker...${NC}"
    curl -sSL https://get.docker.com | sh
    usermod -aG docker $USER
    echo -e "${GREEN}Docker installed.${NC}"
fi

# Check if docker compose is available
if ! docker compose version &> /dev/null; then
    echo -e "${YELLOW}Docker Compose plugin not found. Installing...${NC}"
    apt-get update
    apt-get install -y docker-compose-plugin
    echo -e "${GREEN}Docker Compose plugin installed.${NC}"
fi

# Disable systemd services if they're already stopped
echo -e "${YELLOW}Step 3: Disabling systemd services...${NC}"
systemctl disable nuki-monitor.service 2>/dev/null || echo "nuki-monitor service not enabled or not found."
systemctl disable nuki-web.service 2>/dev/null || echo "nuki-web service not enabled or not found."

# Create directories needed for Docker volumes
echo -e "${YELLOW}Step 4: Preparing Docker environment...${NC}"
mkdir -p config
mkdir -p logs

# Ensure configuration files exist
if [ ! -d "/root/nukiweb/config" ]; then
    echo -e "${RED}Configuration directory not found. Cannot proceed.${NC}"
    exit 1
fi

# Copy current config to Docker volume location if not already done by backup
echo -e "${YELLOW}Step 5: Setting up configuration for Docker...${NC}"
cp -r /root/nukiweb/config/* ./config/

# Build and start Docker containers
echo -e "${YELLOW}Step 6: Building and starting Docker containers...${NC}"
docker compose build
docker compose up -d

# Create a systemd service for Docker
echo -e "${YELLOW}Step 7: Creating systemd service for Docker deployment...${NC}"
cat > /etc/systemd/system/nuki-docker.service << EOF
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
User=root

[Install]
WantedBy=multi-user.target
EOF

# Enable and start the Docker systemd service
echo -e "${YELLOW}Step 8: Enabling Docker systemd service...${NC}"
systemctl enable nuki-docker.service
systemctl start nuki-docker.service

echo ""
echo -e "${GREEN}Transition completed successfully!${NC}"
echo -e "${GREEN}Your Nuki Smart Lock system is now running in Docker containers.${NC}"
echo ""
echo -e "${YELLOW}You can manage the system with these commands:${NC}"
echo -e "- Check status: ${BLUE}docker compose ps${NC}"
echo -e "- View logs: ${BLUE}docker compose logs${NC}"
echo -e "- Follow logs: ${BLUE}docker compose logs -f${NC}"
echo -e "- Stop system: ${BLUE}docker compose down${NC}"
echo -e "- Start system: ${BLUE}docker compose up -d${NC}"
echo ""
echo -e "${YELLOW}Web interface is available at: ${BLUE}http://localhost:5000${NC}"
echo ""
echo -e "${YELLOW}If you need to revert back to the previous setup:${NC}"
echo -e "1. Stop Docker containers: ${BLUE}docker compose down${NC}"
echo -e "2. Disable Docker service: ${BLUE}systemctl disable nuki-docker.service${NC}"
echo -e "3. Restore from backup: ${BLUE}./nuki_backup_restore.sh${NC} and select the pre-docker backup"
echo ""
