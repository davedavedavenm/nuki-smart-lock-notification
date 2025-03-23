#!/bin/bash
set -e

# Deploy script to update the Nuki Smart Lock Notification System
# This script applies the fixes for the dark mode and API errors

echo "=== Nuki Smart Lock Update Script ==="
echo "This script will apply fixes for dark mode and route issues"
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

# Make the template fixing script executable
echo "Preparing template fixing script..."
chmod +x fix-template.sh

# Copy the script to the Docker container
echo "Copying fix script to Docker container..."
docker cp fix-template.sh nukiweb-nuki-web-1:/app/ || \
docker cp fix-template.sh nuki-web:/app/ || \
echo "Warning: Could not copy script to container. Container may not be running."

# Execute the fix script inside the container
echo "Applying template fixes inside container..."
docker exec -it nukiweb-nuki-web-1 bash -c "/app/fix-template.sh" || \
docker exec -it nuki-web bash -c "/app/fix-template.sh" || \
echo "Warning: Could not execute fix script. Will rely on container rebuild."

# Update Docker Compose configuration to use bind mounts
echo "Updating Docker configuration for bind mounts..."
if grep -q "config-volume" docker-compose.yml; then
  echo "Updating volume configuration in docker-compose.yml..."
  
  # Create new config directories if they don't exist
  mkdir -p config_bind
  mkdir -p logs_bind
  
  # Copy existing config if available
  if [ -d "config" ]; then
    cp -r config/* config_bind/ 2>/dev/null
    chmod -R 755 config_bind
  fi
  
  # Modify docker-compose.yml to use bind mounts
  sed -i.bak 's#- config-volume:/app/config#- ./config_bind:/app/config#g' docker-compose.yml
  sed -i 's#- logs-volume:/app/logs#- ./logs_bind:/app/logs#g' docker-compose.yml
  
  echo "Docker Compose configuration updated to use bind mounts"
fi

# Add the fix script to the Dockerfile
echo "Updating web Dockerfile..."
if ! grep -q "fix-template.sh" Dockerfile.web; then
  cp Dockerfile.web Dockerfile.web.bak
  sed -i '/ENTRYPOINT/i COPY fix-template.sh /app/\nRUN chmod +x /app/fix-template.sh\n' Dockerfile.web
  sed -i 's#ENTRYPOINT \["/app/docker-entrypoint-web.sh"\]#ENTRYPOINT \["/app/fix-template.sh", "/app/docker-entrypoint-web.sh"\]#' Dockerfile.web
  echo "Dockerfile updated to include template fixes"
fi

# Stop running containers
echo "Stopping running containers..."
docker compose down || echo "No containers running"

# Remove old volumes if they exist
echo "Removing old volumes..."
docker volume rm nukiweb_config-volume nukiweb_logs-volume 2>/dev/null || echo "No volumes to remove"

# Rebuild the containers
echo "Rebuilding containers..."
docker compose build --no-cache

# Start the containers
echo "Starting containers..."
docker compose up -d

# Wait for containers to start
echo "Waiting for containers to start..."
sleep 10

# Check container status
echo "Checking container status..."
docker compose ps

# Check logs for errors
echo "Checking container logs for errors..."
docker compose logs --tail=20

echo
echo "=== Update Complete ==="
echo "Fixed issues:"
echo "1. Dark mode restored - look for the theme toggle in the top-right navigation"
echo "2. Route issues fixed - all menu links should work properly now"
echo "3. API error handling improved - data should load properly with valid API token"
echo
echo "If you still have issues:"
echo "- Check the logs: docker compose logs"
echo "- Verify your API token in config_bind/credentials.ini"
echo "- Make sure your Nuki API credentials are valid"
echo
echo "Backup of your previous configuration is at: $BACKUP_DIR"
