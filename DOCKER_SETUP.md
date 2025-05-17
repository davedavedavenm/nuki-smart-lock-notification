# Docker Setup for Nuki Smart Lock Notification System

This document provides instructions for setting up and deploying the Nuki Smart Lock Notification System using Docker.

## Prerequisites

- Docker and Docker Compose installed on your system
- Git for cloning the repository
- Basic knowledge of Docker concepts

## Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/davedavedavenm/nuki-smart-lock-notification.git nukiweb
cd nukiweb
```

### 2. Prepare Configuration Files

```bash
# Create required directories
mkdir -p config logs data

# Copy and edit configuration files
cp config/config.ini.example config/config.ini
cp config/credentials.ini.example config/credentials.ini

# Edit the configuration files
nano config/config.ini
nano config/credentials.ini
```

### 3. Set Correct Permissions

Docker containers run with a specific user (`nuki` with UID 999) that needs appropriate permissions to access mounted volumes:

```bash
# Set permissions for directories
chmod -R 777 logs
chmod -R 777 data
chmod 777 config

# Set permissions for config files
chmod 644 config/*.ini
```

### 4. Build and Start Docker Containers

```bash
# Build and start the containers
docker compose up -d

# Check container status
docker compose ps

# View logs
docker compose logs -f
```

## Container Management

### Stopping Containers

```bash
docker compose down
```

### Restarting Containers

```bash
docker compose restart
```

### Rebuilding Containers After Changes

```bash
docker compose build --no-cache
docker compose up -d
```

## Troubleshooting

### Permission Issues

If you encounter permission errors in the logs, ensure the directories have the correct permissions:

```bash
chmod -R 777 logs data
chmod 777 config
chmod 644 config/*.ini
```

### Network Issues

If containers cannot communicate:

1. Check that both containers are on the same network:
   ```bash
   docker network inspect nukiweb_nuki-network
   ```

2. Ensure the network is properly configured in `docker-compose.yml`.

### Container Logs

View logs to diagnose issues:

```bash
docker logs nuki-monitor
docker logs nuki-web
```

## Security Recommendations

1. Do not expose the web interface directly to the internet without proper security measures
2. Use HTTPS by setting up a reverse proxy with SSL/TLS (e.g., Nginx or Traefik)
3. Change default credentials immediately after setup
4. Use strong passwords for the web interface
5. Regularly update the Docker images and host system

## Backup and Restore

### Backup

Backup your data by copying the mounted volumes:

```bash
tar -czvf nuki-backup-$(date +%Y%m%d).tar.gz config data
```

### Restore

Restore from a backup:

```bash
# Stop containers
docker compose down

# Extract backup
tar -xzvf nuki-backup-20240517.tar.gz

# Ensure correct permissions
chmod -R 777 logs data
chmod 777 config
chmod 644 config/*.ini

# Restart containers
docker compose up -d
```

## Production Deployment Recommendations

1. Set resource limits in docker-compose.yml (already configured)
2. Enable logging rotation
3. Implement a proper backup strategy
4. Monitor container health
5. Set up automatic restart for Docker service
6. Configure system monitoring for the host machine
