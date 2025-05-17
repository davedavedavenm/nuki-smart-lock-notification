# Troubleshooting Guide for Nuki Smart Lock Notification System

This guide addresses common issues you might encounter when setting up and running the Nuki Smart Lock Notification System, particularly with Docker deployments.

## Docker Bind Mount Permission Issues

### Problem Description

The most common issue with the Docker setup is permission errors when using bind mounts. The application runs as a non-root user (`nuki`) inside the containers, but this user needs write access to the host directories mounted at:
- `/app/logs` - For storing application logs
- `/app/data` - For storing application data

### Symptoms

When permission issues occur, you might see:
- Containers crashing or in a restart loop
- Error messages like `PermissionError: [Errno 13] Permission denied` in logs
- API health checks failing
- No logs being written

### Solutions

#### Solution 1: Set Appropriate Directory Permissions (Recommended)

Before starting the containers, ensure the host directories have the correct permissions:

```bash
# Create directories if they don't exist
mkdir -p config logs data

# Set permissions to allow the non-root container user to write
chmod -R 777 logs data
```

For a more secure approach with specific user permissions:

```bash
# Find the UID/GID used by the nuki user in the container
docker run --rm davedavedavenm/nuki-monitor id nuki
# Example output: uid=999(nuki) gid=999(nuki) groups=999(nuki)

# Create directories if they don't exist
mkdir -p config logs data

# Set ownership using the UID/GID from above (replace 999:999 with actual values)
sudo chown -R 999:999 logs data

# Set minimum required permissions
chmod -R 755 logs data
```

#### Solution 2: Use Named Volumes Instead of Bind Mounts

If setting permissions is problematic, you can modify your docker-compose.yml to use named volumes instead:

```yaml
services:
  nuki-monitor:
    # ... other settings ...
    volumes:
      - nuki-config:/app/config
      - nuki-logs:/app/logs
      - nuki-data:/app/data
  
  nuki-web:
    # ... other settings ...
    volumes:
      - nuki-config:/app/config
      - nuki-logs:/app/logs
      - nuki-data:/app/data

volumes:
  nuki-config:
  nuki-logs:
  nuki-data:
```

With this approach, Docker manages the volumes and their permissions internally.

#### Solution 3: Run the Container as Root (Not Recommended for Production)

If you're still having issues and just need a quick solution for testing, you can modify the Dockerfiles to run as root by removing or commenting out these lines:

```dockerfile
# Comment out or remove these lines in both Dockerfile.monitor and Dockerfile.web
#RUN groupadd -r nuki && useradd -r -g nuki nuki
#RUN chown -R nuki:nuki /app
#USER nuki
```

Then rebuild your containers:

```bash
docker compose down
docker compose build --no-cache
docker compose up -d
```

⚠️ **Security Warning**: This approach decreases container security and is not recommended for production deployments.

## Web Interface Issues

### Can't Access Web Interface

#### Problem
The web interface is not accessible at `http://localhost:5000` or `http://your-pi-ip:5000`.

#### Solutions
1. Check if containers are running:
   ```bash
   docker compose ps
   ```

2. Check logs for errors:
   ```bash
   docker compose logs nuki-web
   ```

3. Verify port mapping:
   ```bash
   docker compose port nuki-web 5000
   ```

4. Ensure no other service is using port 5000:
   ```bash
   sudo lsof -i :5000
   ```

### Login Issues

#### Problem
Can't log in with default credentials.

#### Solutions
1. Reset the admin password:
   ```bash
   docker compose exec nuki-web python -c "from web.app import reset_admin_password; reset_admin_password()"
   ```

2. Check user database:
   ```bash
   docker compose exec nuki-web python -c "from web.app import list_users; list_users()"
   ```

## Notification Issues

### No Notifications Being Sent

#### Problem
System is running but no notifications are being sent when lock events occur.

#### Solutions
1. Check API connectivity:
   ```bash
   docker compose logs nuki-monitor | grep "API"
   ```

2. Verify credentials:
   ```bash
   docker compose exec nuki-monitor python -c "from scripts.nuki.config import verify_credentials; verify_credentials()"
   ```

3. Test notification sending:
   ```bash
   docker compose exec nuki-monitor python -c "from scripts.nuki.notification import send_test_notification; send_test_notification()"
   ```

### Email Notifications Not Working

#### Problem
Email notifications specifically are not being received.

#### Solutions
1. Check email configuration:
   ```bash
   docker compose exec nuki-monitor python -c "from scripts.nuki.config import check_email_config; check_email_config()"
   ```

2. Verify SMTP settings in `credentials.ini`:
   ```bash
   docker compose exec nuki-monitor cat /app/config/credentials.ini | grep -A 6 '\[email\]'
   ```

3. Check if your email provider requires app-specific passwords or less secure app access.

## API Health Issues

### Health Check Failures

#### Problem
API health checks are failing or showing errors.

#### Solutions
1. Check health monitor logs:
   ```bash
   docker compose logs nuki-monitor | grep "health"
   ```

2. Verify Nuki API credentials:
   ```bash
   docker compose exec nuki-monitor cat /app/config/credentials.ini | grep -A 3 '\[nuki\]'
   ```

3. Test API connection manually:
   ```bash
   docker compose exec nuki-monitor python -c "from scripts.nuki.api import test_api_connection; test_api_connection()"
   ```

## Docker Performance Issues

### High CPU or Memory Usage

#### Problem
Containers are using excessive CPU or memory resources.

#### Solutions
1. Check container stats:
   ```bash
   docker stats
   ```

2. Adjust polling interval for API requests (in `config.ini`):
   ```ini
   [api]
   polling_interval = 120  # Increase to reduce API calls (in seconds)
   ```

3. Limit container resources in docker-compose.yml:
   ```yaml
   services:
     nuki-monitor:
       # ... other settings ...
       deploy:
         resources:
           limits:
             cpus: '0.50'
             memory: 512M
   ```

## Raspberry Pi Specific Issues

### Container won't start on Raspberry Pi

#### Problem
Services start on your development machine but not on the Raspberry Pi.

#### Solutions
1. Check if you're using the correct architecture in your Dockerfiles:
   ```dockerfile
   FROM python:3.9-slim
   ```

2. Verify Docker and docker-compose versions:
   ```bash
   docker --version
   docker compose version
   ```

3. Check filesystem space:
   ```bash
   df -h
   ```

### System Freezes on Raspberry Pi

#### Problem
The Raspberry Pi becomes unresponsive after running the Docker containers.

#### Solutions
1. Reduce container resource usage (see High CPU/Memory Usage section)
2. Add swap space to your Raspberry Pi:
   ```bash
   sudo dphys-swapfile swapoff
   sudo nano /etc/dphys-swapfile
   # Set CONF_SWAPSIZE=1024
   sudo dphys-swapfile setup
   sudo dphys-swapfile swapon
   ```

## Getting More Help

If you continue to experience issues after trying these troubleshooting steps, please:

1. Generate a diagnostic report:
   ```bash
   ./scripts/generate_diagnostics.sh
   ```

2. Open an issue on our GitHub repository with:
   - The diagnostic report
   - Description of the issue
   - Steps to reproduce
   - Your environment details (OS, Docker version, etc.)

GitHub: https://github.com/davedavedavenm/nuki-smart-lock-notification/issues