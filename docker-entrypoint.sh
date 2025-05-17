#!/bin/bash
set -e

echo "Starting Nuki Monitor..."

# Check directory permissions
echo "Checking directory permissions..."

# Check logs directory
mkdir -p $LOGS_DIR
if [ ! -w "$LOGS_DIR" ]; then
    echo "❌ ERROR: The logs directory ($LOGS_DIR) is not writable by the nuki user!"
    echo "Please run the following commands on your host system:"
    echo "  mkdir -p logs data"
    echo "  chmod -R 777 logs data"
    echo ""
    echo "See TROUBLESHOOTING.md for more information on permission issues."
    exit 1
fi
echo "✅ Logs directory verified"

# Check data directory
mkdir -p /app/data
if [ ! -w "/app/data" ]; then
    echo "❌ ERROR: The data directory (/app/data) is not writable by the nuki user!"
    echo "Please run the following commands on your host system:"
    echo "  mkdir -p logs data"
    echo "  chmod -R 777 logs data"
    echo ""
    echo "See TROUBLESHOOTING.md for more information on permission issues."
    exit 1
fi
echo "✅ Data directory verified"

# Ensure configuration files exist
python /app/scripts/ensure_config.py
echo "✅ Configuration files verified"

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
