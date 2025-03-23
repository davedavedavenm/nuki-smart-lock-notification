# Docker Environment Fixes

This document outlines the fixes made to ensure the application runs smoothly in a Docker environment.

## Issues Fixed

1. **Password Hashing Method**
   - Changed the password hashing method from `scrypt` to `pbkdf2:sha256` to ensure compatibility with the Python environment in Docker.
   - Updated the `generate_password_hash()` function calls in `web/models.py`.

2. **Logging Path**
   - Updated logging path in `scripts/nuki_monitor.py` to use Docker volumes instead of home directory.
   - Changed from `~/nukiweb/logs/nuki_monitor.log` to environment variable `$LOGS_DIR`.

3. **Configuration Files**
   - Added `ensure_config.py` script to automatically create config files from examples if they don't exist.
   - Updated Docker entry points to run this script before starting the main application.

4. **Entry Point Scripts**
   - Added `docker-entrypoint.sh` and `docker-entrypoint-web.sh` scripts to set up the environment before running the main applications.
   
## How to Apply These Fixes

1. Pull the latest changes from GitHub:
   ```
   git pull origin main
   ```

2. Rebuild and restart the Docker containers:
   ```
   docker-compose down
   docker-compose build
   docker-compose up -d
   ```

3. If needed, reset the admin user's password:
   ```
   docker exec -it nuki-web python scripts/reset_users.py
   ```

## Configuration

The containers now automatically create default configuration files on startup if they don't exist.

To customize your configuration:

1. Edit the configuration files in the `config` directory:
   ```
   nano config/config.ini
   nano config/credentials.ini
   ```

2. Restart the containers to apply changes:
   ```
   docker-compose restart
   ```
