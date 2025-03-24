#!/bin/bash
# This script fixes template route issues in Docker containers

# Find all template files and ensure consistent routes
find /app -name "base.html" -type f -exec sed -i 's/users\/manage/users_manage/g' {} \;

echo "Fixed base.html templates"

# Print confirmation
echo "Template fixes applied successfully!"

# Continue with original command
exec "$@"
