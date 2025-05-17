#!/bin/bash
set -e

echo "Starting Nuki Web Interface..."

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

# Start the main application
echo "Starting Nuki Web application..."
exec "$@"
