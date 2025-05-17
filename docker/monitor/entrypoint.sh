#!/bin/bash
set -e

echo "Starting Nuki Monitor..."

# Directly check critical permissions before running comprehensive checks
echo "Performing initial permission checks..."

# Test if credentials.ini is readable
if [ -f "/app/config/credentials.ini" ] && ! [ -r "/app/config/credentials.ini" ]; then
    echo "❌ CRITICAL ERROR: Cannot read /app/config/credentials.ini"
    echo "The container user 'nuki' doesn't have read permissions for this file."
    echo "Run: chmod 644 config/credentials.ini on your host system."
    echo "See DOCKER_SETUP.md for detailed instructions on setting the correct permissions."
    exit 1
fi

# Test if logs directory is writable
if ! [ -w "/app/logs" ]; then
    echo "❌ CRITICAL ERROR: Cannot write to /app/logs directory"
    echo "The container user 'nuki' doesn't have write permissions for this directory."
    echo "Run: chmod -R 777 logs on your host system."
    echo "See DOCKER_SETUP.md for detailed instructions on setting the correct permissions."
    exit 1
fi

# Test if config directory is writable (for users.json)
if ! [ -w "/app/config" ]; then
    echo "❌ CRITICAL ERROR: Cannot write to /app/config directory"
    echo "The container user 'nuki' doesn't have write permissions for this directory."
    echo "Run: chmod 777 config on your host system."
    echo "See DOCKER_SETUP.md for detailed instructions on setting the correct permissions."
    exit 1
fi

# Run comprehensive permission checks
echo "Checking filesystem permissions..."
python -m app.utils.check_permissions
if [ $? -ne 0 ]; then
    echo "❌ ERROR: Permission checks failed. Please fix the permissions and try again."
    echo "See DOCKER_SETUP.md for detailed instructions on setting the correct permissions."
    exit 1
fi
echo "✅ Permission checks passed"

# Ensure configuration files exist
python -m app.config.ensure_config
echo "✅ Configuration files verified"

# Check API health before starting, but don't fail if it doesn't work yet
echo "Checking Nuki API connection health..."
python -m app.monitoring.health_monitor || true
API_STATUS=$?

if [ $API_STATUS -eq 0 ]; then
    echo "✅ API connection is healthy"
elif [ $API_STATUS -eq 1 ]; then
    echo "⚠️ API connection has warnings but will continue"
else
    echo "⚠️ API connection status check did not succeed, but we'll continue anyway"
    echo "This could be due to missing or invalid credentials."
    echo "Please check config/credentials.ini and make sure it has valid API tokens."
    echo "The system will still start up, but won't function correctly until credentials are fixed."
fi

# Start the main application
echo "Starting Nuki Monitor application..."
exec "$@"