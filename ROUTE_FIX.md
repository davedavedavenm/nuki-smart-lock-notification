# Nuki Dashboard Route Fix

## Problem Identified

The web application is showing the following error:

```
BuildError: Could not build url for endpoint 'users/manage'. Did you mean 'users_manage' instead?
```

This error occurs because there's a mismatch between:
1. How the route is defined in `app.py` (as `/users_manage`)
2. How it's referenced in templates (as `users_manage`)
3. But the Docker container is modifying the templates during startup

## Root Cause

After investigating, I discovered that the issue is in the `fix-template.sh` script that runs when the Docker container starts. This script is actually *causing* the problem by deliberately replacing `users_manage` with `users/manage` in the templates:

```bash
# Find all template files and ensure consistent routes
find /app -name "base.html" -type f -exec sed -i 's/users_manage/users\/manage/g' {} \;
```

## Solution

The fix is to reverse the replacement in the `fix-template.sh` script:

```bash
# Find all template files and ensure consistent routes
find /app -name "base.html" -type f -exec sed -i 's/users\/manage/users_manage/g' {} \;
```

This will ensure that the templates use `users_manage`, which matches the route definition in the Flask application.

## Implementation Steps

1. Update the script locally:
   ```bash
   # Edit fix-template.sh
   cd C:\Users\Dave\OneDrive\Claude\NukiAppProject\consolidated_code
   git add fix-template.sh
   git commit -m "Fix route mismatch in template script"
   git push origin main
   ```

2. Deploy to Raspberry Pi:
   ```bash
   # SSH into Pi
   ssh root@[pi-ip]
   
   # Update code
   cd /root/nukiweb
   git pull
   
   # Rebuild and restart Docker
   docker compose down
   docker compose build --no-cache nuki-web
   docker compose up -d
   ```

## Verification

After implementing this fix, the error should be resolved and you should be able to access the user management page without issues.
