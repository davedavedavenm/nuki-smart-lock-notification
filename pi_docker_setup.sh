#!/bin/bash
#
# Raspberry Pi Docker Volume Permission Setup Script
# For use on the Raspberry Pi deployment
#
# Sets up directories and permissions for Docker bind mounts
# with proper ownership for the nuki container user
#

set -e

# ANSI color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Print script header
echo -e "${BOLD}=================================================================${NC}"
echo -e "${BOLD}  Nuki Smart Lock Docker Volume Permission Setup (Raspberry Pi)  ${NC}"
echo -e "${BOLD}=================================================================${NC}"
echo

# Check if script is running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Error: This script must be run as root on the Raspberry Pi${NC}"
    echo "Please run again with sudo:"
    echo "  sudo $0"
    exit 1
fi

# Function to print status messages
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠️${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

echo "Setting up directories and permissions for Docker bind mounts..."

# Create directories if they don't exist
echo "Creating directories..."
mkdir -p /root/nukiweb/config /root/nukiweb/logs /root/nukiweb/data
print_status "Directories created"

# Get into the nukiweb directory
cd /root/nukiweb

# Check if config files already exist
CONFIG_FILES_EXIST=false
if [ -f "config/config.ini" ] || [ -f "config/credentials.ini" ]; then
    CONFIG_FILES_EXIST=true
    print_status "Configuration files found"
else
    print_warning "No configuration files found. They will be created when the container starts."
fi

# Set permissions
echo "Setting directory permissions..."

# Standard method - works for most cases
chmod -R 777 logs data
chmod 777 config
if [ "$CONFIG_FILES_EXIST" = true ]; then
    chmod 644 config/*.ini
fi

print_status "Standard permissions set"

# Using chown with nuki user UID
# The typical UID for nuki user in the container is 999
echo "Setting ownership for container user (UID 999)..."
chown -R 999:999 logs data
chown 999:999 config
if [ "$CONFIG_FILES_EXIST" = true ]; then
    # User 999 should be able to read but not write config.ini and credentials.ini
    chown 999:999 config/*.ini  
fi

print_status "Ownership set to UID 999 (container nuki user)"

echo
echo -e "${GREEN}✓ Setup complete!${NC}"
echo
echo "The Docker volumes are now properly configured for bind mounts."
echo "You can now run the Docker containers with:"
echo "  cd /root/nukiweb"
echo "  docker compose up -d"
echo
echo "If you still encounter permission issues, see DOCKER_SETUP.md"
echo "for more information and advanced permission handling options."
echo
