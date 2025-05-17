# Docker Setup Guide for Nuki Smart Lock Notification System

This guide provides detailed instructions for setting up and running the Nuki Smart Lock Notification System using Docker.

## Quick Start

```bash
# Clone the repository
git clone https://github.com/davedavedavenm/nuki-smart-lock-notification.git
cd nuki-smart-lock-notification

# Set up host directories and permissions
mkdir -p config logs data
chmod 777 config logs data

# Create configuration files (if not existing)
cp config/config.ini.example config/config.ini
cp config/credentials.ini.example config/credentials.ini

# Edit the configuration files
nano config/config.ini
nano config/credentials.ini

# Set proper permissions for config files
chmod 644 config/*.ini

# Start the containers
docker compose up -d
```

## Important: Host Directory Permissions for Docker Bind Mounts

### Understanding Container User Context

The application's Docker containers run as a non-root user (`nuki` with UID 999) for security reasons. This means the container process doesn't have root privileges within the container or on the host system.

When using bind mounts in `docker-compose.yml` (e.g., `./config:/app/config`), the container user (`nuki`) must have appropriate permissions to access the host directories that are mounted into the container.

### Required Permissions

The following directories require specific permissions:

1. **`./config` Directory**:
   - **Read access**: For loading `config.ini` and `credentials.ini`
   - **Write access**: For creating and updating `users.json` (user database)
   
2. **`./logs` Directory**:
   - **Write access**: For creating and writing log files

3. **`./data` Directory**:
   - **Write access**: For storing temporary data and cached information

### Symptoms of Incorrect Host Permissions

If permissions are not set correctly, you may encounter:

- Container crashes with messages like: `Permission denied: '/app/logs/nuki_monitor.log'`
- Web interface reporting: "No API token found" due to inability to read `credentials.ini`
- User management failures with messages about being unable to write to `users.json`
- Login failures because the application cannot read/write to the user database

### Setting Correct Permissions on Linux

Run these commands in the directory where the `docker-compose.yml` file is located:

```bash
# Create directories if they don't exist
mkdir -p config logs data

# Set directory permissions (allows reading/writing to directories)
chmod 777 config
chmod -R 777 logs data

# If you have configuration files, set appropriate permissions
# (readable by all, writable by owner)
chmod 644 config/config.ini config/credentials.ini
```

### Setting Correct Permissions on Raspberry Pi

The commands are the same as for Linux:

```bash
# Create directories if they don't exist
mkdir -p config logs data

# Set directory permissions
chmod 777 config
chmod -R 777 logs data

# Set config file permissions
chmod 644 config/config.ini config/credentials.ini
```

### Understanding Permission Numbers

- `777`: Full read/write/execute for everyone (directories)
- `644`: Read/write for owner, read-only for everyone else (config files)

### Alternative: User Mapping

For advanced users, you can alternatively use user mapping with Docker to map the container's `nuki` user to your host user:

```bash
# Find your user and group IDs
id

# Add the user mapping when running
docker compose up -d --user $(id -u):$(id -g)
```

## Troubleshooting Permission Issues

If permission issues persist:

1. **Check Container Logs**:
   ```bash
   docker logs nuki-monitor
   docker logs nuki-web
   ```

2. **Verify Permissions on Host**:
   ```bash
   ls -la config logs data
   ```

3. **Test Writing from Container**:
   ```bash
   docker exec -it nuki-monitor sh -c "touch /app/logs/test.txt"
   ```

4. **Ensure All Parent Directories Have Appropriate Permissions**:
   Sometimes, the issue might be with parent directory permissions, not just the immediate directories.

5. **Reset Permissions**:
   ```bash
   chmod -R 777 logs data
   chmod 777 config
   chmod 644 config/*.ini
   ```

## Users.json File Location and Permissions

The web application stores user account information in `/app/config/users.json`. This file:

- Is automatically created during first startup if it doesn't exist
- Requires write permissions for the container's `nuki` user
- Contains sensitive information (like password hashes)
- By default has permissions set to `600` (owner read/write only)

The host's `./config` directory must have write permissions for the container's `nuki` user to create and update this file.

## Further Configuration

For more details on configuring the application, see the [Configuration Guide](CONFIGURATION.md).
