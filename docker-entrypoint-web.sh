#!/bin/bash
set -e

echo "Starting Nuki Web Interface..."

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
