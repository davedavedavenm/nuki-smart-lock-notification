#!/bin/bash
set -e

# Ensure logs directory exists
mkdir -p $LOGS_DIR

# Ensure configuration files exist
python /app/scripts/ensure_config.py

# Start the main application
exec "$@"
