#!/bin/bash
#
# Docker Volume Permission Setup Script
# Sets up directories and permissions for Docker bind mounts
#
# This script creates the necessary directories for Docker bind mounts
# and sets appropriate permissions to prevent permission issues
# when running the Nuki Smart Lock Notification System.
#

set -e

# ANSI color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Print script header
echo -e "${BOLD}=========================================================${NC}"
echo -e "${BOLD}  Nuki Smart Lock Docker Volume Permission Setup Script  ${NC}"
echo -e "${BOLD}=========================================================${NC}"
echo

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

# Check if script is running as root on Linux
if [ "$(uname)" = "Linux" ] && [ "$EUID" -ne 0 ]; then
    print_warning "You are not running as root. Some operations might fail."
    print_warning "If you encounter permission errors, run this script with sudo."
    echo
fi

echo "Setting up directories and permissions for Docker bind mounts..."

# Create directories if they don't exist
echo "Creating directories..."
mkdir -p config logs data
print_status "Directories created"

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

# On Windows with WSL or MinGW (Git Bash), chmod works differently
if [ "$OSTYPE" = "msys" ] || [ "$OSTYPE" = "cygwin" ] || [[ "$(uname -r)" == *Microsoft* ]] || [[ "$(uname -r)" == *WSL* ]]; then
    print_warning "Running on Windows environment - permission model is different"
    print_warning "Make sure your Windows user has full access to these directories"
    
    # Try to set permissions anyway, but warn it might not work as expected
    chmod -R 777 logs data 2>/dev/null || true
    chmod 777 config 2>/dev/null || true
    if [ "$CONFIG_FILES_EXIST" = true ]; then
        chmod 644 config/*.ini 2>/dev/null || true
    fi
    
    print_status "Attempted to set permissions (Windows environment)"
else
    # Linux or macOS
    chmod -R 777 logs data
    chmod 777 config
    
    # Set permissions on config files if they exist
    if [ "$CONFIG_FILES_EXIST" = true ]; then
        chmod 644 config/*.ini
    fi
    
    print_status "Permissions set successfully"
fi

echo
echo -e "${GREEN}✓ Setup complete!${NC}"
echo
echo "You can now run the Docker containers with:"
echo "  docker compose up -d"
echo
echo "If you still encounter permission issues, see DOCKER_SETUP.md"
echo "for more information and advanced permission handling options."
echo
