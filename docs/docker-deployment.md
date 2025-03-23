# Docker Deployment Guide

This guide covers deployment of the Nuki Smart Lock Notification System using Docker and Docker Compose.

## Prerequisites

- Host system with Docker installed
- Docker Compose installed
- Nuki Smart Lock 4th Generation
- Nuki Web API token
- Basic knowledge of Docker concepts

## Architecture Overview

The Docker deployment uses a multi-container approach:

1. **nuki-monitor**: Core notification system
   - Connects to the Nuki API
   - Processes lock events
   - Sends notifications

2. **nuki-web**: Web interface
   - Provides user-friendly dashboard
   - Handles configuration
   - Manages user accounts

3. **Shared volumes**:
   - `config-volume`: Configuration files
   - `logs-volume`: Log files

## Quick Start

1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/nuki-smart-lock-notification.git
   cd nuki-smart-lock-notification
   ```

2. Create and configure the configuration files:
   ```bash
   mkdir -p config
   cp config/config.ini.example config/config.ini
   cp config/credentials.ini.example config/credentials.ini
   nano config/config.ini
   nano config/credentials.ini
   ```

3. Start the Docker containers:
   ```bash
   docker-compose up -d
   ```

4. Access the web interface at `http://your-host-ip:5000`

## Detailed Docker Configuration

### Docker Compose File

The `docker-compose.yml` file defines the container setup:

```yaml
version: '3.8'

services:
  nuki-monitor:
    build:
      context: .
      dockerfile: Dockerfile.monitor
    container_name: nuki-monitor
    restart: unless-stopped
    volumes:
      - config-volume:/app/config
      - logs-volume:/app/logs
    networks:
      - nuki-network

  nuki-web:
    build:
      context: .
      dockerfile: Dockerfile.web
    container_name: nuki-web
    restart: unless-stopped
    ports:
      - "5000:5000"
    volumes:
      - config-volume:/app/config
      - logs-volume:/app/logs
    networks:
      - nuki-network
    depends_on:
      - nuki-monitor

volumes:
  config-volume:
  logs-volume:

networks:
  nuki-network:
    driver: bridge
```

### Dockerfiles

**Dockerfile.monitor**:
```dockerfile
FROM python:3.9-slim-bullseye

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY scripts /app/scripts
COPY config /app/config

# Create necessary directories
RUN mkdir -p /app/logs

# Set environment variables
ENV CONFIG_DIR=/app/config
ENV LOGS_DIR=/app/logs

# Run as non-root user for security
RUN groupadd -r nuki && useradd -r -g nuki nuki
RUN chown -R nuki:nuki /app
USER nuki

# Run the monitor script
CMD ["python", "scripts/nuki_monitor.py"]
```

**Dockerfile.web**:
```dockerfile
FROM python:3.9-slim-bullseye

WORKDIR /app

# Install dependencies
COPY requirements-web.txt .
RUN pip install --no-cache-dir -r requirements-web.txt

# Copy application code
COPY web /app/web
COPY scripts /app/scripts
COPY config /app/config

# Create necessary directories
RUN mkdir -p /app/logs

# Set environment variables
ENV CONFIG_DIR=/app/config
ENV LOGS_DIR=/app/logs
ENV FLASK_APP=web/app.py

# Run as non-root user for security
RUN groupadd -r nuki && useradd -r -g nuki nuki
RUN chown -R nuki:nuki /app
USER nuki

# Expose the web port
EXPOSE 5000

# Run the Flask application
CMD ["python", "web/app.py"]
```

## Configuration with Docker

1. **Initial Setup**:
   Create the config files before starting the containers:
   ```bash
   mkdir -p config
   cp config/config.ini.example config/config.ini
   cp config/credentials.ini.example config/credentials.ini
   ```

2. **Edit Configuration Files**:
   ```bash
   nano config/config.ini
   nano config/credentials.ini
   ```

3. **Apply Configuration**:
   The containers will automatically use the configuration files from the shared volume.

4. **Reload After Changes**:
   After changing configuration, restart the containers:
   ```bash
   docker-compose restart
   ```

## Container Management

### Starting Containers

```bash
# Start all containers
docker-compose up -d

# Start individual container
docker-compose up -d nuki-web
```

### Stopping Containers

```bash
# Stop all containers
docker-compose down

# Stop individual container
docker-compose stop nuki-monitor
```

### Viewing Logs

```bash
# View monitor logs
docker logs nuki-monitor

# View web interface logs
docker logs nuki-web

# Follow logs in real-time
docker logs -f nuki-monitor
```

### Updating the Application

To update to a new version:

```bash
# Pull the latest code
git pull

# Rebuild and restart containers
docker-compose down
docker-compose build
docker-compose up -d
```

## Persistent Data

Data is persisted using named volumes:

- **config-volume**: Stores configuration files
- **logs-volume**: Stores log files

To manage volumes:

```bash
# List volumes
docker volume ls

# Inspect a volume
docker volume inspect nuki-smart-lock-notification_config-volume

# Backup a volume
docker run --rm -v nuki-smart-lock-notification_config-volume:/source -v $(pwd):/backup alpine tar -czf /backup/config-backup.tar.gz -C /source .

# Restore a volume
docker run --rm -v nuki-smart-lock-notification_config-volume:/target -v $(pwd):/backup alpine sh -c "rm -rf /target/* && tar -xzf /backup/config-backup.tar.gz -C /target"
```

## Security Considerations

### Securing Configuration

1. Secure file permissions:
   ```bash
   sudo chmod 600 config/credentials.ini
   ```

2. Use Docker secrets for production:
   ```yaml
   services:
     nuki-monitor:
       secrets:
         - nuki_api_token
         - email_password
         - telegram_bot_token
   
   secrets:
     nuki_api_token:
       file: ./secrets/nuki_api_token.txt
     email_password:
       file: ./secrets/email_password.txt
     telegram_bot_token:
       file: ./secrets/telegram_bot_token.txt
   ```

### Network Security

1. Use a reverse proxy with HTTPS:
   ```yaml
   services:
     nuki-web:
       networks:
         - internal
       labels:
         - "traefik.enable=true"
         - "traefik.http.routers.nuki.rule=Host(`nuki.example.com`)"
         - "traefik.http.routers.nuki.tls=true"
   
     traefik:
       image: traefik:v2.5
       ports:
         - "80:80"
         - "443:443"
       volumes:
         - /var/run/docker.sock:/var/run/docker.sock
         - ./traefik:/etc/traefik
       networks:
         - internal
   ```

2. Use network isolation:
   ```yaml
   services:
     nuki-monitor:
       networks:
         - backend
     
     nuki-web:
       networks:
         - frontend
         - backend
   
   networks:
     frontend:
       driver: bridge
     backend:
       driver: bridge
       internal: true
   ```

## Troubleshooting

### Common Issues

1. **Container fails to start**:
   ```bash
   docker logs nuki-monitor
   ```

2. **Web interface not accessible**:
   ```bash
   docker ps  # Check if container is running
   docker logs nuki-web  # Check for errors
   ```

3. **Configuration not applied**:
   ```bash
   docker-compose down
   docker-compose up -d
   ```

4. **Permission issues**:
   ```bash
   # Check volume permissions
   docker run --rm -v nuki-smart-lock-notification_config-volume:/config alpine ls -la /config
   
   # Fix permissions
   docker run --rm -v nuki-smart-lock-notification_config-volume:/config alpine chmod 600 /config/credentials.ini
   ```

## Advanced Docker Configurations

### Using Environment Variables

You can use environment variables to override configuration:

```yaml
services:
  nuki-monitor:
    environment:
      - NUKI_API_TOKEN=your_api_token
      - NOTIFICATION_TYPE=telegram
      - POLLING_INTERVAL=60
```

### Custom Health Checks

Add health checks to monitor container health:

```yaml
services:
  nuki-web:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
      interval: 1m
      timeout: 10s
      retries: 3
      start_period: 30s
```

### Resource Limits

Set resource limits to prevent container overuse:

```yaml
services:
  nuki-monitor:
    deploy:
      resources:
        limits:
          cpus: "0.5"
          memory: 256M
```

## Production Recommendations

For production deployments:

1. Use a proper reverse proxy (Nginx, Traefik)
2. Enable HTTPS with valid certificates
3. Set up monitoring (e.g., with Prometheus/Grafana)
4. Implement automated backups for volumes
5. Use Docker secrets for sensitive data
6. Set appropriate resource limits
7. Enable automatic container restarts
8. Set up log rotation
