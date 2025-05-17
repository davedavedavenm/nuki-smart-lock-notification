#!/bin/bash
# Troubleshooting script for Nuki Smart Lock Notification System

echo "=== Nuki Smart Lock Notification System Troubleshooter ==="
echo "This script will help identify and fix common issues."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start the Docker service."
    echo "   Run: systemctl start docker"
    exit 1
fi

# Check container status
echo "Checking container status..."
MONITOR_RUNNING=$(docker compose ps nuki-monitor | grep -c "running")
WEB_RUNNING=$(docker compose ps nuki-web | grep -c "running")

if [ "$MONITOR_RUNNING" -eq 0 ]; then
    echo "❌ nuki-monitor container is not running."
    echo "Checking container logs for errors..."
    docker compose logs nuki-monitor | tail -n 20
    
    echo "Checking permission issues..."
    # First ensure directories exist with proper permissions
    mkdir -p config logs data
    chmod -R 777 logs data
    chmod 777 config
    chmod 666 config/config.ini config/credentials.ini 2>/dev/null || true
    
    echo "Attempting to fix permissions on mounted volumes..."
    docker run --rm -v "$(pwd)/config:/config" -v "$(pwd)/logs:/logs" -v "$(pwd)/data:/data" alpine sh -c "chmod -R 777 /logs /data && chmod 777 /config && find /config -type f -exec chmod 666 {} \;"
    
    echo "Checking if credentials.ini exists and has proper content..."
    if [ ! -f "config/credentials.ini" ]; then
        echo "❌ credentials.ini is missing! Creating from example..."
        cp config/credentials.ini.example config/credentials.ini
        echo "⚠️ You MUST edit config/credentials.ini with your actual API keys!"
    else
        # Check if the token contains placeholder text
        if grep -q "YOUR_NUKI_API_TOKEN" config/credentials.ini; then
            echo "❌ The Nuki API token in credentials.ini is still the placeholder value!"
            echo "   Please edit this file and add your actual Nuki API token."
        fi
    fi
    
    echo "Rebuilding and restarting nuki-monitor container..."
    docker compose build --no-cache nuki-monitor
    docker compose up -d nuki-monitor
    
    # Check if restarting helped
    sleep 5
    if [ "$(docker compose ps nuki-monitor | grep -c "running")" -eq 1 ]; then
        echo "✅ nuki-monitor container is now running!"
    else
        echo "❌ nuki-monitor container still failed to start."
        echo "   Try manually editing credentials.ini and config.ini with your settings."
        echo "   Then run: docker compose up -d"
    fi
else
    echo "✅ nuki-monitor container is running."
fi

if [ "$WEB_RUNNING" -eq 0 ]; then
    echo "❌ nuki-web container is not running."
    echo "This is likely because nuki-monitor failed its health check."
    echo "Fix nuki-monitor first, then restart nuki-web."
    echo "To restart web container after fixing monitor: docker compose up -d nuki-web"
else
    echo "✅ nuki-web container is running."
fi

# Print overall system health
echo ""
echo "=== SYSTEM HEALTH SUMMARY ==="
if [ "$MONITOR_RUNNING" -eq 1 ] && [ "$WEB_RUNNING" -eq 1 ]; then
    echo "✅ All services are running. System appears healthy!"
    echo "   Web interface available at: http://$(hostname -I | awk '{print $1}'):5000"
else
    echo "⚠️ Some services are not running. Follow the instructions above to fix the issues."
    echo "   For more detailed troubleshooting, check TROUBLESHOOTING.md"
fi

echo ""
echo "If you continue to have issues, you can manually run a permission check inside the container:"
echo "docker compose run nuki-monitor python /app/scripts/check_permissions.py"
echo ""
