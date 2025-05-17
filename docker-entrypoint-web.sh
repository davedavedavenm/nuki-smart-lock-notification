#!/bin/bash
set -e

echo "Starting Nuki Web Interface..."

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
python /app/scripts/check_permissions.py
if [ $? -ne 0 ]; then
    echo "❌ ERROR: Permission checks failed. Please fix the permissions and try again."
    echo "See DOCKER_SETUP.md for detailed instructions on setting the correct permissions."
    exit 1
fi
echo "✅ Permission checks passed"

# Ensure configuration files exist
python /app/scripts/ensure_config.py
echo "✅ Configuration files verified"

# Start the main application
echo "Starting Nuki Web application..."
exec "$@"