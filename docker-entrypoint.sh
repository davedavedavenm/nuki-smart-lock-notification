#!/bin/bash
set -e

echo "Starting Nuki Monitor..."

# Ensure logs directory exists
mkdir -p $LOGS_DIR
echo "Logs directory verified"

# Ensure configuration files exist
python /app/scripts/ensure_config.py
echo "Configuration files verified"

# Check API health before starting
echo "Checking Nuki API connection health..."
python /app/scripts/health_monitor.py
API_STATUS=$?

if [ $API_STATUS -eq 0 ]; then
    echo "✅ API connection is healthy"
elif [ $API_STATUS -eq 1 ]; then
    echo "⚠️ API connection has warnings but will continue"
else
    echo "❌ API connection has errors"
    echo "The Nuki Monitor will start but may not function correctly."
    echo "Please check your API token and credentials."
    echo "You can use the token_manager.py script to refresh your token."
fi

# Start the main application
echo "Starting Nuki Monitor application..."
exec "$@"
