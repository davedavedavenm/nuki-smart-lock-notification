# Docker Setup for Nuki Smart Lock Notification System

This guide explains how to deploy and manage the Nuki Smart Lock notification system using Docker containers, making it portable across various platforms.

## Deployment Options

### Option 1: One-click Deployment (Coming Soon)
A simplified deployment script that handles all setup automatically.

### Option 2: Manual Deployment
Follow the workflow below for manual deployment and management.

1. Update files in the local OneDrive folder
2. Push changes to GitHub
3. Pull changes on the Raspberry Pi
4. Run the transition or update script

## Deployment on Different Platforms

### Linux (Raspberry Pi, Ubuntu, etc.)
1. Install Docker and Docker Compose:
   ```bash
   curl -sSL https://get.docker.com | sh
   sudo apt-get install -y docker-compose
   ```
2. Clone the repository and deploy:
   ```bash
   git clone https://github.com/davedavedavenm/nuki-smart-lock-notification.git
   cd nuki-smart-lock-notification
   docker compose up -d
   ```

### Windows
1. Install Docker Desktop from [Docker Hub](https://www.docker.com/products/docker-desktop/)
2. Clone the repository using Git or download as ZIP
3. Open Command Prompt in the repository folder:
   ```cmd
   docker compose up -d
   ```

### macOS
1. Install Docker Desktop from [Docker Hub](https://www.docker.com/products/docker-desktop/)
2. Clone the repository:
   ```bash
   git clone https://github.com/davedavedavenm/nuki-smart-lock-notification.git
   cd nuki-smart-lock-notification
   docker compose up -d
   ```

## First-time Setup

On first launch, the system will:
1. Create default configuration files if none exist
2. Set up necessary volumes for persistence
3. Initialize with default admin credentials (admin/nukiadmin)
4. Start all required services

After deploying, configure your system by accessing:
```
http://localhost:5000 (or http://your-device-ip:5000)
```

## Volume Management and Data Persistence

The Docker setup uses volumes to ensure your data persists between container restarts:

```yaml
volumes:
  nuki-config:    # Stores configuration files
  nuki-logs:      # Stores application logs
  nuki-data:      # Stores user data and history
```

### Backup and Restore

**Backup your data:**
```bash
# Create a backup of all volumes
docker run --rm -v nuki-config:/config -v nuki-logs:/logs -v nuki-data:/data \
  -v $(pwd):/backup alpine tar czf /backup/nuki-backup.tar.gz /config /logs /data
```

**Restore from backup:**
```bash
# Restore from backup file
docker run --rm -v nuki-config:/config -v nuki-logs:/logs -v nuki-data:/data \
  -v $(pwd):/backup alpine sh -c "cd / && tar xzf /backup/nuki-backup.tar.gz"
```

## Security Considerations

### HTTPS Setup

For production use, enable HTTPS:

1. **Using Nginx Reverse Proxy (Recommended)**
   - Install Nginx and Certbot
   - Configure a reverse proxy to your Docker container
   - Set up automatic SSL with Let's Encrypt

2. **Direct HTTPS Configuration**
   - Generate SSL certificates
   - Mount certificates into the container
   - Update environment variables:
     ```yaml
     environment:
       - ENABLE_HTTPS=true
       - SSL_CERT_PATH=/app/ssl/cert.pem
       - SSL_KEY_PATH=/app/ssl/key.pem
     ```

### Secure Password Management

On first login, immediately change the default admin password (admin/nukiadmin) to a strong, unique password.

### Network Isolation

Use Docker's network features to isolate your containers:

```yaml
networks:
  nuki-network:
    driver: bridge
    internal: false  # Set to true to prevent containers from accessing internet
```

## Advanced Configuration

### Environment Variables

All features can be customized through environment variables:

```yaml
environment:
  # General settings
  - TZ=Europe/London                     # Set your timezone
  - LOG_LEVEL=INFO                       # Logging level (DEBUG, INFO, WARNING, ERROR)
  
  # Web interface settings
  - WEB_PORT=5000                        # Web interface port
  - SESSION_TIMEOUT=3600                 # Session timeout in seconds
  - ENABLE_HTTPS=false                   # Enable HTTPS
  
  # Notification settings
  - NOTIFICATION_TYPE=both               # Email, telegram, or both
  - POLLING_INTERVAL=60                  # API polling interval
  - DIGEST_MODE=false                    # Enable digest mode
  
  # Security settings
  - FAILED_ATTEMPT_THRESHOLD=3           # Failed attempt threshold
  - SECURITY_ALERT_PRIORITY=high         # Security alert priority
```

### Docker Compose Extensions

For advanced setups, use Docker Compose profiles and extensions:

```bash
# Run with monitoring profile only
docker compose --profile monitoring up -d

# Run with web interface profile only
docker compose --profile web up -d
```

## Routine Management

### Common Commands

- **Check status**:
  ```bash
  docker compose ps
  ```

- **View logs**:
  ```bash
  docker compose logs
  # Follow logs in real-time
  docker compose logs -f
  ```

- **Stop the system**:
  ```bash
  docker compose down
  ```

- **Start the system**:
  ```bash
  docker compose up -d
  ```

- **Restart a specific service**:
  ```bash
  docker compose restart nuki-monitor
  docker compose restart nuki-web
  ```

### Updating the System

```bash
# Pull latest version
git pull

# Rebuild and restart
docker compose down
docker compose build --no-cache
docker compose up -d
```

## Troubleshooting

### Common Issues

1. **Web Interface Not Accessible**
   - Check if containers are running: `docker compose ps`
   - Verify port mapping: `docker compose port nuki-web 5000`
   - Check container logs: `docker compose logs nuki-web`

2. **Configuration Not Saving**
   - Check volume permissions: `docker volume inspect nuki-config`
   - Verify config file exists: `docker compose exec nuki-web ls -la /app/config`

3. **No Notifications Being Sent**
   - Check credentials: `docker compose exec nuki-monitor cat /app/config/credentials.ini`
   - Verify API connectivity: `docker compose logs nuki-monitor | grep "API"`

### Container Health Checks

```bash
docker inspect --format='{{json .State.Health}}' nuki-monitor
docker inspect --format='{{json .State.Health}}' nuki-web
```

## Contributing

Improvements to the Docker setup are welcome! Please submit pull requests to our GitHub repository.
