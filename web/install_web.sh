#!/bin/bash
# Installation script for Nuki Web Dashboard

# Exit on error
set -e

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root"
    exit 1
fi

# Base directory
BASE_DIR="/root/nukiweb"
WEB_DIR="$BASE_DIR/web"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}====================================================${NC}"
echo -e "${GREEN}      Nuki Smart Lock Web Dashboard Installer       ${NC}"
echo -e "${GREEN}====================================================${NC}"

# Check if base directory exists
if [ ! -d "$BASE_DIR" ]; then
    echo -e "${RED}Error: Base directory $BASE_DIR not found${NC}"
    echo "Please install the Nuki notification system first"
    exit 1
fi

# Check if Python virtual environment exists
if [ ! -d "$BASE_DIR/venv" ]; then
    echo -e "${RED}Error: Python virtual environment not found${NC}"
    echo "Please install the Nuki notification system first"
    exit 1
fi

# Activate virtual environment
source "$BASE_DIR/venv/bin/activate"

echo -e "${YELLOW}Installing required packages...${NC}"
pip install flask flask-login werkzeug

# Create web directory
echo -e "${YELLOW}Creating web directory...${NC}"
mkdir -p "$WEB_DIR"
mkdir -p "$WEB_DIR/templates"
mkdir -p "$WEB_DIR/static/css"
mkdir -p "$WEB_DIR/static/js"

# Copy web files
echo -e "${YELLOW}Copying web files...${NC}"
# This would be done by your deployment process
# For development, you can manually copy files

# Setup systemd service for web dashboard
echo -e "${YELLOW}Setting up systemd service...${NC}"
cat > /etc/systemd/system/nuki-web.service << EOL
[Unit]
Description=Nuki Smart Lock Web Dashboard
After=network.target nuki-monitor.service

[Service]
Type=simple
User=root
WorkingDirectory=$WEB_DIR
ExecStart=$BASE_DIR/venv/bin/python $WEB_DIR/app.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOL

# Reload systemd
systemctl daemon-reload

# Enable and start service
echo -e "${YELLOW}Enabling and starting service...${NC}"
systemctl enable nuki-web.service
systemctl start nuki-web.service

# Display status
echo -e "${GREEN}====================================================${NC}"
echo -e "${GREEN}      Nuki Web Dashboard Installation Complete      ${NC}"
echo -e "${GREEN}====================================================${NC}"
echo ""
echo -e "You can access the dashboard at: ${YELLOW}http://$(hostname -I | awk '{print $1}'):5000${NC}"
echo -e "Default login: ${YELLOW}admin / nukiadmin${NC}"
echo ""
echo -e "${YELLOW}IMPORTANT:${NC} Change the default password by editing $WEB_DIR/app.py"
echo ""
echo -e "To check the service status: ${GREEN}systemctl status nuki-web.service${NC}"
echo -e "To view logs: ${GREEN}journalctl -u nuki-web.service${NC}"
echo ""
