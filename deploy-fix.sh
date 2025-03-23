#!/bin/bash
set -e

# Deploy script to update the Nuki Smart Lock Notification System
# This script applies the fixes for the dark mode and API errors

echo "=== Nuki Smart Lock Update Script ==="
echo "This script will apply fixes for dark mode and API errors"
echo

# Check if running as root (required for Docker)
if [ "$(id -u)" -ne 0 ]; then
  echo "This script must be run as root or with sudo."
  exit 1
fi

# Navigate to the project directory
PROJECT_DIR="$(pwd)"
echo "Working directory: $PROJECT_DIR"

# Backup current configuration
echo "Creating backup of current config..."
BACKUP_DIR="$PROJECT_DIR/backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"
cp -r "$PROJECT_DIR/config" "$BACKUP_DIR/" 2>/dev/null || echo "No config directory to backup"
cp -r "$PROJECT_DIR/web" "$BACKUP_DIR/web" 2>/dev/null || echo "No web directory to backup"
cp -r "$PROJECT_DIR/scripts" "$BACKUP_DIR/scripts" 2>/dev/null || echo "No scripts directory to backup"
echo "Backup created at: $BACKUP_DIR"

# Stop running containers
echo "Stopping running containers..."
docker compose down || echo "No containers running"

# Rebuild the containers
echo "Rebuilding containers..."
docker compose build

# Start the containers
echo "Starting containers..."
docker compose up -d

# Check container status
echo "Checking container status..."
sleep 5
docker compose ps

echo
echo "=== Update Complete ==="
echo "Fixed issues:"
echo "1. Dark mode restored - look for the theme toggle in the top-right navigation"
echo "2. API error handling improved - data should load properly now"
echo
echo "If you still have issues:"
echo "- Check the logs: docker compose logs"
echo "- Verify your API token in config/credentials.ini"
echo "- Make sure your Nuki API credentials are valid"
echo
echo "Backup of your previous configuration is at: $BACKUP_DIR"
