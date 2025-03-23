# Docker Container Setup for Nuki Smart Lock Notification System

This document outlines how to containerize the Nuki Smart Lock Notification System using Docker. Containerization provides easier deployment, better isolation, and simplified management.

## Docker Architecture Overview

The Nuki Smart Lock Notification System will be containerized using a multi-container approach with Docker Compose. This separates the core monitoring system from the web interface, improving security and scalability.

### Container Structure

1. **nuki-monitor**: Core notification system container
   - Runs the monitoring script
   - Handles API interactions
   - Sends notifications

2. **nuki-web**: Web interface container
   - Runs the Flask web application
   - Provides user interface
   - Manages configuration

3. **shared volumes**: For configuration and data sharing
   - Configuration files
   - Log files
   - User database

## Prerequisites

- Docker installed on your host system
- Docker Compose installed
- Basic understanding of Docker concepts
- Internet connection for the containers to access the Nuki API

## Dockerfile for Nuki Monitor

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

## Dockerfile for Nuki Web Interface

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

## Docker Compose Configuration

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

## Dependencies Files

### requirements.txt (for nuki-monitor)

```
requests==2.28.1
python-dateutil==2.8.2
```

### requirements-web.txt (for nuki-web)

```
Flask==2.2.2
Werkzeug==2.2.2
requests==2.28.1
python-dateutil==2.8.2
```

## Installation and Setup

### 1. Create Project Structure

```
/docker-nuki/
├── config/
│   ├── config.ini
│   └── credentials.ini
├── Dockerfile.monitor
├── Dockerfile.web
├── docker-compose.yml
├── requirements.txt
└── requirements-web.txt
```

### 2. Configure the Application

1. Create configuration files in the `config` directory
2. Set up your Nuki API credentials in `credentials.ini`
3. Customize notification settings in `config.ini`

### 3. Build and Start Containers

```bash
cd docker-nuki
docker-compose up -d
```

### 4. Access the Web Interface

Open your browser and navigate to:
```
http://localhost:5000
```

### 5. View Container Logs

```bash
# View monitor logs
docker logs nuki-monitor

# View web interface logs
docker logs nuki-web

# Follow logs in real-time
docker logs -f nuki-monitor
```

## Data Persistence

The Docker setup uses named volumes to persist data:

- **config-volume**: Stores configuration files
- **logs-volume**: Stores log files

This ensures that your configuration and logs are preserved even if the containers are recreated.

## Security Considerations

1. **Credentials Protection**:
   - Store sensitive information in Docker secrets (for production)
   - Use environment variables for credentials instead of config files
   - Set proper permissions on config files

2. **Network Security**:
   - Restrict access to the web interface using a reverse proxy
   - Consider using HTTPS with Let's Encrypt certificates
   - Use network isolation for production deployments

3. **Container Hardening**:
   - Run containers as non-root users
   - Use minimal base images
   - Regularly update images for security patches

## Updating the Application

To update the application:

1. Pull the latest code changes
2. Rebuild the containers:
```bash
docker-compose down
docker-compose build
docker-compose up -d
```

## Troubleshooting

### Common Issues

1. **Container fails to start**:
   - Check logs with `docker logs nuki-monitor`
   - Verify configuration files exist and are valid
   - Ensure required environment variables are set

2. **Web interface not accessible**:
   - Check if container is running with `docker ps`
   - Verify port mapping with `docker-compose ps`
   - Check for errors in the web container logs

3. **Notifications not working**:
   - Verify Nuki API credentials
   - Check notification configuration
   - Inspect monitor container logs for API errors

## Advanced Configuration

### Using Environment Variables

You can use environment variables to override configuration settings:

```yaml
version: '3.8'

services:
  nuki-monitor:
    # ... other settings ...
    environment:
      - NUKI_API_TOKEN=your_token
      - NOTIFICATION_TYPE=telegram
      - POLLING_INTERVAL=60
```

### Custom Networks

For enhanced security, you can further isolate the containers:

```yaml
services:
  nuki-monitor:
    # ... other settings ...
    networks:
      - backend-network

  nuki-web:
    # ... other settings ...
    networks:
      - frontend-network
      - backend-network

networks:
  frontend-network:
    driver: bridge
  backend-network:
    driver: bridge
```

### Using a Reverse Proxy

For production deployments, use a reverse proxy like Traefik or Nginx:

```yaml
services:
  nuki-web:
    # ... other settings ...
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.nuki.rule=Host(`nuki.example.com`)"
      - "traefik.http.routers.nuki.tls=true"
      - "traefik.http.routers.nuki.tls.certresolver=letsencrypt"
```

## Conclusion

Containerizing the Nuki Smart Lock Notification System with Docker provides a consistent and isolated environment for running the application. This approach simplifies deployment, updates, and maintenance while improving security through isolation.
