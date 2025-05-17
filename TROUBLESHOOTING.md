# Troubleshooting Docker Deployment

This document addresses common issues with the Docker deployment of the Nuki Smart Lock Notification System.

## Common Issues and Solutions

### Docker Container Health Check Failures

If the nuki-monitor container fails to start with a health check issue:

1. **Check Permissions**:
   ```bash
   # Set proper permissions on host system
   chmod -R 777 logs data
   chmod 777 config
   chmod 666 config/config.ini config/credentials.ini
   ```

2. **Check API Credentials**:
   - Ensure the `config/credentials.ini` file has your actual Nuki API token
   - Make sure the token is valid (not expired)
   - If needed, generate a new token through the Nuki Web API

3. **Run the Troubleshooting Script**:
   ```bash
   ./troubleshoot.sh
   ```

### Missing Configuration Files

If necessary configuration files are missing:

1. **Copy Example Files**:
   ```bash
   cp config/config.ini.example config/config.ini
   cp config/credentials.ini.example config/credentials.ini
   ```

2. **Edit the Files**:
   ```bash
   nano config/config.ini       # Set general configuration
   nano config/credentials.ini  # Add your API tokens
   ```

### Deploying Changes

After making changes to configuration or code:

1. **Rebuild and Restart Containers**:
   ```bash
   docker compose down
   docker compose build --no-cache
   docker compose up -d
   ```

2. **Check Logs**:
   ```bash
   docker compose logs -f
   ```

## Testing API Connection

You can manually test the API connection:

```bash
docker compose exec nuki-monitor python /app/scripts/health_monitor.py
```

## Completely Resetting the System

If you need to start fresh:

```bash
# Stop all containers
docker compose down

# Remove all data (caution: this deletes all logs and cached data)
sudo rm -rf logs/* data/*

# Keep your configuration
# If you want to reset configuration too, run:
# sudo rm -rf config/*

# Rebuild from scratch
docker compose build --no-cache
docker compose up -d
```

## Getting Logs for Support

If you need to share logs for troubleshooting:

```bash
docker compose logs nuki-monitor > monitor_logs.txt
docker compose logs nuki-web > web_logs.txt
```

These files can be shared with support channels for assistance.
