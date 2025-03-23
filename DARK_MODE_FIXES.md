# Nuki Smart Lock Dashboard - Dark Mode & API Fixes

This document explains the changes made to fix the dark mode feature and API connection issues in the Nuki Smart Lock Dashboard.

## Issues Fixed

1. **Dark Mode Toggle**
   - Fixed the dark mode toggle in the navigation bar
   - Added proper theme persistence in user settings
   - Ensured dark theme is correctly applied to all UI elements

2. **Missing Routes**
   - Added missing route for user management page (`/users/manage`)
   - Added corresponding API endpoints to support user management
   - Fixed template references to ensure all navigation links work

3. **API Connection**
   - Improved error handling in the API client
   - Added retry logic for failed API requests
   - Added connection timeout handling
   - Enhanced error messages for easier troubleshooting

4. **Docker Configuration**
   - Switched from Docker volumes to bind mounts for easier configuration
   - Added a fix-template.sh script to ensure templates work correctly in containers
   - Updated Docker healthchecks for better monitoring
   - Added psutil for improved health status reporting

## Files Changed

1. **Web Interface Files**:
   - `web/app.py`: Added missing routes and improved error handling
   - `web/templates/base.html`: Fixed theme toggle and navigation links
   - `web/static/js/main.js`: Added better error handling and retry functions
   - `web/static/css/dark-mode.css`: Enhanced dark mode styling

2. **API Files**:
   - `scripts/nuki/api.py`: Added retry logic and better error handling
   - `scripts/nuki/config.py`: Improved configuration loading and validation

3. **Docker Files**:
   - `Dockerfile.web`: Added fix-template.sh script and healthcheck
   - `docker-compose.yml` / `docker-compose-bind.yml`: Switched to bind mounts
   - `fix-template.sh`: Created to fix template paths within containers

## Deployment Instructions

### Method 1: Upgrade in Place

1. On your Raspberry Pi, navigate to the project directory:
   ```bash
   cd /root/nukiweb
   ```

2. Pull the latest changes from GitHub:
   ```bash
   git pull
   ```

3. Run the deployment script:
   ```bash
   chmod +x deploy-fix.sh
   ./deploy-fix.sh
   ```

### Method 2: Manual Deployment

1. Stop the current containers:
   ```bash
   docker compose down
   ```

2. Remove the old volumes:
   ```bash
   docker volume rm nukiweb_config-volume nukiweb_logs-volume
   ```

3. Create bind mount directories:
   ```bash
   mkdir -p config_bind logs_bind
   cp -r config/* config_bind/
   ```

4. Update to the new docker-compose file:
   ```bash
   cp docker-compose-bind.yml docker-compose.yml
   ```

5. Rebuild and start the containers:
   ```bash
   docker compose build --no-cache
   docker compose up -d
   ```

## Important Notes

- The bind mount setup ensures your configuration files are directly accessible on the host
- Any changes to your API token or other settings should be made in the `config_bind` directory
- The dark mode state is stored per user in the users.json file
- If you encounter any issues, check the logs with `docker compose logs`

## Future Improvements

- Add comprehensive health monitoring dashboard
- Improve mobile responsiveness for dark mode
- Add user preferences for notification settings
- Implement automatic API token refresh mechanism
