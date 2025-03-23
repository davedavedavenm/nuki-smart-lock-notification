# Docker Setup for Nuki Smart Lock Notification System

This guide explains how to transition your Nuki Smart Lock notification system from systemd services to Docker containers.

## Workflow

1. Update files in the local OneDrive folder
2. Push changes to GitHub
3. Pull changes on the Raspberry Pi
4. Run the transition or update script

## Initial Setup

### On Your Development Machine

1. The Docker configuration files are already in the repository:
   - `docker-compose.yml`: Defines the container setup
   - `Dockerfile.monitor`: For the monitoring service
   - `Dockerfile.web`: For the web interface
   - `transition-to-docker.sh`: Script to help with the transition

2. After making any changes, push to GitHub:
   ```bash
   git add .
   git commit -m "Update Docker configuration"
   git push
   ```

### On Your Raspberry Pi (First-time Setup)

1. Pull the latest changes:
   ```bash
   cd /path/to/repository
   git pull
   ```

2. Make the transition script executable:
   ```bash
   chmod +x transition-to-docker.sh
   ```

3. Run the transition script (only once, for the initial setup):
   ```bash
   ./transition-to-docker.sh
   ```

   This script will:
   - Backup your current configuration
   - Stop and disable existing systemd services
   - Set up Docker volumes for your config and logs
   - Build and start the Docker containers
   - Create a new systemd service to manage the Docker containers

## Routine Updates

### Updating After Changes

1. On the Raspberry Pi, pull the latest changes:
   ```bash
   cd /path/to/repository
   git pull
   ```

2. Rebuild and restart the containers:
   ```bash
   docker compose down
   docker compose build
   docker compose up -d
   ```

   Or simply:
   ```bash
   docker compose up -d --build
   ```

## Managing the Docker Setup

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

### Accessing the Web Interface

The web interface remains available at:
```
http://your-pi-ip:5000
```

## Configuration

Your configuration files in the `config` directory will be used by the Docker containers. Any changes to these files will require a container restart:

```bash
docker compose restart
```

## Troubleshooting

### Check Container Logs

```bash
# For the monitor service
docker compose logs nuki-monitor

# For the web interface
docker compose logs nuki-web
```

### Access a Container Shell

```bash
docker compose exec nuki-monitor bash
docker compose exec nuki-web bash
```

### Check Container Health

```bash
docker inspect --format='{{json .State.Health}}' nuki-monitor
docker inspect --format='{{json .State.Health}}' nuki-web
```

### Return to Systemd Services

If you need to revert back to the original systemd services:

1. Stop the Docker containers:
   ```bash
   docker compose down
   ```

2. Disable the Docker systemd service:
   ```bash
   sudo systemctl disable nuki-docker.service
   sudo systemctl stop nuki-docker.service
   ```

3. Re-enable the original services:
   ```bash
   sudo systemctl enable nuki-monitor.service
   sudo systemctl enable nuki-web.service
   sudo systemctl start nuki-monitor.service
   sudo systemctl start nuki-web.service
   ```

## Advanced Options

### Customizing Port Mappings

Edit the `docker-compose.yml` file:
```yaml
nuki-web:
  # ...
  ports:
    - "8080:5000"  # Changes the external port to 8080
```

### Updating Environment Variables

Edit the `docker-compose.yml` file:
```yaml
nuki-monitor:
  # ...
  environment:
    - CONFIG_DIR=/app/config
    - LOGS_DIR=/app/logs
    - TZ=Europe/London  # Change to your timezone
```
