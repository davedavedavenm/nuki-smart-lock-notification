#!/bin/bash
# Docker Deploy Helper Script for Nuki Smart Lock Notification System
# This script helps set up the correct directory permissions for Docker deployment

# Print colored text
print_green() {
    echo -e "\e[32m$1\e[0m"
}

print_yellow() {
    echo -e "\e[33m$1\e[0m"
}

print_red() {
    echo -e "\e[31m$1\e[0m"
}

print_blue() {
    echo -e "\e[34m$1\e[0m"
}

# Header
print_blue "============================================================="
print_blue "   Nuki Smart Lock Notification System - Docker Setup Helper"
print_blue "============================================================="
echo ""
print_yellow "This script will help set up your Docker environment with the"
print_yellow "correct directory permissions for the Nuki notification system."
echo ""

# Check if running as root
if [ "$(id -u)" -ne 0 ]; then
    print_red "This script needs to be run as root to set permissions correctly."
    print_red "Please run with sudo:"
    print_red "    sudo ./docker_setup.sh"
    exit 1
fi

# Define directory variables
NUKI_DIR=$(pwd)
CONFIG_DIR="$NUKI_DIR/config"
LOGS_DIR="$NUKI_DIR/logs"
DATA_DIR="$NUKI_DIR/data"

# Create directories if they don't exist
print_blue "Creating required directories if they don't exist..."
mkdir -p "$CONFIG_DIR"
mkdir -p "$LOGS_DIR"
mkdir -p "$DATA_DIR"
echo ""

# Determine Docker's UID and GID
print_blue "Detecting Docker user information..."
CONTAINER_UID=""
CONTAINER_GID=""

# Try to get nuki user info from running container, or use default values
if docker ps | grep -q "nuki-"; then
    print_yellow "Detected running Nuki container, getting user information..."
    
    # Check which container is running
    if docker ps | grep -q "nuki-monitor"; then
        CONTAINER_UID=$(docker exec nuki-monitor id -u nuki)
        CONTAINER_GID=$(docker exec nuki-monitor id -g nuki)
    elif docker ps | grep -q "nuki-web"; then
        CONTAINER_UID=$(docker exec nuki-web id -u nuki)
        CONTAINER_GID=$(docker exec nuki-web id -g nuki)
    fi
    
    if [ -n "$CONTAINER_UID" ] && [ -n "$CONTAINER_GID" ]; then
        print_green "Found Docker nuki user UID:GID = $CONTAINER_UID:$CONTAINER_GID"
    else
        print_yellow "Could not determine Docker user info from running container."
        print_yellow "Using default Docker non-root UID:GID = 999:999"
        CONTAINER_UID=999
        CONTAINER_GID=999
    fi
else
    print_yellow "No running Nuki container found."
    print_yellow "Using default Docker non-root UID:GID = 999:999"
    CONTAINER_UID=999
    CONTAINER_GID=999
fi

echo ""

# Ask for permission strategy
print_blue "Choose permission strategy:"
echo "1) Secure (recommended): Set specific owner and permissions"
echo "   This sets the owner to the container's user and minimum necessary permissions"
echo ""
echo "2) Simple: Set world-writable permissions"
echo "   This makes directories writable by any user/process (less secure but simpler)"
echo ""

read -p "Enter your choice (1 or 2): " PERM_CHOICE
echo ""

if [ "$PERM_CHOICE" = "1" ]; then
    # Secure strategy
    print_blue "Setting secure permissions..."
    
    # Set ownership
    chown -R "$CONTAINER_UID:$CONTAINER_GID" "$LOGS_DIR" "$DATA_DIR"
    print_green "✓ Set ownership of logs and data directories to $CONTAINER_UID:$CONTAINER_GID"
    
    # Set permissions - more restrictive
    chmod -R 755 "$CONFIG_DIR"  # Read access is enough for config
    chmod -R 755 "$LOGS_DIR" "$DATA_DIR"  # Directories need execute permission
    chmod 644 "$CONFIG_DIR"/*  # Config files are readable
    
    # Make sure log and data dirs are writable by container user
    chmod -R u+w "$LOGS_DIR" "$DATA_DIR"
    
    print_green "✓ Set secure permissions for all directories"
elif [ "$PERM_CHOICE" = "2" ]; then
    # Simple strategy - world writable
    print_blue "Setting simple permissions (world-writable)..."
    
    chmod -R 777 "$LOGS_DIR" "$DATA_DIR"
    chmod -R 755 "$CONFIG_DIR"
    chmod 644 "$CONFIG_DIR"/*
    
    print_green "✓ Set directories to be world-writable"
else
    print_red "Invalid choice. Exiting without changing permissions."
    exit 1
fi

echo ""
print_blue "Setting up config files..."

# Check for example config files and copy if needed
if [ -f "$CONFIG_DIR/config.ini.example" ] && [ ! -f "$CONFIG_DIR/config.ini" ]; then
    cp "$CONFIG_DIR/config.ini.example" "$CONFIG_DIR/config.ini"
    print_green "✓ Created config.ini from example"
fi

if [ -f "$CONFIG_DIR/credentials.ini.example" ] && [ ! -f "$CONFIG_DIR/credentials.ini" ]; then
    cp "$CONFIG_DIR/credentials.ini.example" "$CONFIG_DIR/credentials.ini"
    chmod 640 "$CONFIG_DIR/credentials.ini"
    print_green "✓ Created credentials.ini from example with secure permissions"
fi

echo ""
print_green "✓ Setup complete!"
echo ""
print_blue "You can now start your containers with:"
print_blue "    docker compose up -d"
echo ""
print_yellow "If you still encounter permission issues, see TROUBLESHOOTING.md"
print_yellow "for more information and alternative solutions."
echo ""
