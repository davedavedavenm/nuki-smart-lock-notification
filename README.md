# Nuki Smart Lock 4th Gen Notification System

A comprehensive notification system for Nuki Smart Lock 4th Generation using a Raspberry Pi 4. The system monitors lock activity via the Nuki Web API and sends customizable notifications via email and/or Telegram.

![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## Features

- 🔒 **Secure Monitoring**: Connect to Nuki Web API with proper authentication
- 🔔 **Instant Notifications**: Receive alerts via email and/or Telegram when the lock is used
- 👤 **User Identification**: Track which user operated the lock
- 🌐 **Web Interface**: User-friendly web dashboard for configuration and monitoring
- 🕒 **Activity Logging**: Keep a detailed history of lock activity
- 🔄 **Digest Mode**: Get summaries of activities rather than individual notifications
- 🔍 **Smart Filtering**: Filter notifications by user, action type, or trigger type
- 🌙 **Dark Mode**: Toggle between light and dark themes in the web interface
- 👥 **User Management**: Manage multiple user accounts with different permission levels
- 🔑 **Agent Access**: Allow agents to create temporary access codes
- 🔐 **Security Pattern Detection**: Detect unusual lock behaviors with security monitoring
- 🐳 **Docker Support**: Deploy using Docker for simplified setup

## Screenshots

*(Screenshots will be added in future version)*

## System Requirements

- Raspberry Pi 4 (or compatible single-board computer)
- Python 3.6+
- Network connection
- Nuki Smart Lock 4th Generation
- Nuki Web account with API token

## Installation Options

### Method 1: Standard Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/davedavedavenm/nuki-smart-lock-notification.git
   cd nuki-smart-lock-notification
   ```

2. Run the installation script:
   ```bash
   ./install/install.sh
   ```

3. Configure the application:
   ```bash
   python scripts/configure.py
   ```

4. Start the services:
   ```bash
   sudo systemctl start nuki-monitor.service
   sudo systemctl start nuki-web.service
   ```

### Method 2: Docker Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/davedavedavenm/nuki-smart-lock-notification.git
   cd nuki-smart-lock-notification
   ```

2. (Optional) Configure via Environment Variables:
   ```bash
   cp .env.example .env
   nano .env
   ```

3. Set up proper directory permissions:
   ```bash
   mkdir -p config logs data flask_session
   chmod -R 775 logs data config flask_session
   ```

4. Build and start Docker containers:
   ```bash
   docker compose up -d
   ```

5. Access the web interface at `http://your-pi-ip:5000`. If it's a first-time installation, you will be automatically redirected to the **Setup Wizard**.

## Directory Structure

```
/
├── scripts/                     # Core notification system
│   ├── nuki_monitor.py          # Main monitoring script
│   ├── configure.py             # Configuration utility
│   ├── nuki/                    # Python package
│   │   ├── api.py               # API interaction
│   │   ├── config.py            # Configuration management
│   │   ├── notification.py      # Notification handling
│   │   └── utils.py             # Utility functions
├── security/                    # Security module
│   ├── security_monitor.py      # Security monitoring
│   ├── security_alerter.py      # Security alerting
│   └── security_config.py       # Security configuration
├── web/                         # Web interface
│   ├── app.py                   # Flask application
│   ├── models.py                # User models
│   ├── static/                  # Static assets
│   │   ├── css/
│   │   └── js/
│   └── templates/               # HTML templates
├── config/                      # Configuration files
│   ├── config.ini.example       # Example configuration
│   └── credentials.ini.example  # Example credentials
├── install/                     # Installation scripts
│   ├── install.sh               # Main installation script
│   ├── nuki-monitor.service     # systemd service file
│   └── nuki-web.service         # systemd service file
├── docs/                        # Documentation
├── docker-compose.yml           # Docker Compose configuration
├── Dockerfile.monitor           # Dockerfile for monitor service
├── Dockerfile.web               # Dockerfile for web service
├── LICENSE                      # MIT License
└── README.md                    # This readme file
```

## Configuration

Configuration is done through two main files:

1. `config/config.ini` - General configuration options
2. `config/credentials.ini` - API tokens and passwords

You can use the built-in configuration utility:
```bash
python scripts/configure.py
```

Or edit the files directly (see the example files for available options).

### Getting a Nuki API Token

1. Log in to the [Nuki Web Dashboard](https://web.nuki.io/)
2. Go to "Account" > "API"
3. Generate a new API token
4. Copy the token into your `credentials.ini` file

### Setting up Telegram Notifications

1. Create a new Telegram bot using [BotFather](https://t.me/botfather)
2. Get your bot token and add it to `credentials.ini`
3. Run the utility to get your chat ID:
   ```bash
   python scripts/get_telegram_chat_id.py
   ```
4. Add the chat ID to your `config.ini` file

## Web Interface

The web interface provides a user-friendly way to manage your Nuki lock notifications:

- **Dashboard**: View current lock status and recent activity
- **Activity**: Browse complete activity history
- **Status**: Check the current status of all your locks
- **Temporary Codes**: Create and manage temporary access codes (admin and agent roles)
- **Configuration**: Adjust notification settings (admin only)
- **User Management**: Add and manage users (admin only)
- **Notification Settings**: Configure notification preferences (admin only)

Access the web interface at `http://your-pi-ip:5000`

### User Roles

The system supports two types of user roles:

1. **Admin**: Full access to all features and settings
2. **Agent**: Restricted access for managing temporary codes and viewing basic lock information

#### Creating Agent Users

To create an agent user with the ability to manage temporary access codes:

1. Log in as an admin user
2. Go to Admin → Create Agent User
3. Fill in the required information
4. Click "Create Agent User"

The agent role provides limited dashboard access focused primarily on temporary code management.

#### Managing Temporary Codes

To create a temporary access code:

1. Log in as an admin or agent user
2. Go to the "Temporary Codes" page
3. Fill in the code, name/purpose, and expiry date/time
4. Click "Create Temporary Code"

Temporary codes will automatically expire at the set time.

## Security Features

- Secure storage of API credentials
- HTTPS support for the web interface
- Role-based access control
- Proper password hashing
- Security event detection
- Activity anomaly monitoring

For more details, see the [SECURITY.md](SECURITY.md) file.

## Docker Deployment Guidelines

For detailed information about Docker deployment, including important information about container permissions and bind mounts, please refer to the [DOCKER_SETUP.md](DOCKER_SETUP.md) document.

### Important: Host Directory Permissions for Docker

When using Docker, the containers run as a non-root user (`nuki` with UID 999). This means the host directories mounted into the container must have appropriate permissions:

```bash
# Create directories if they don't exist
mkdir -p config logs data

# Set directory permissions (Linux/macOS only)
chmod 777 config
chmod -R 777 logs data

# Set config file permissions (if they exist)
chmod 644 config/*.ini
```

These permissions are critical for the application to function correctly. If the container cannot access the config files or write to logs, it will fail to start or operate correctly.

## Troubleshooting

Common issues and solutions:

### API Authentication Failed (401 Unauthorized)

If you're seeing "401 Unauthorized" errors in the logs:

- Your Nuki API token has likely expired or been revoked
- Generate a new API token using the token manager:
  ```bash
  # If running traditionally:
  python scripts/token_manager.py
  
  # If running in Docker:
  docker exec -it nuki-monitor python scripts/token_manager.py
  ```
- Alternatively, you can edit `config/credentials.ini` directly with your new token
- After updating the token, restart the service or container:
  ```bash
  # For traditional installation:
  sudo systemctl restart nuki-monitor.service
  
  # For Docker installation:
  docker compose restart nuki-monitor
  ```

### Docker Bind Mount Permission Issues

If you're using Docker and see errors like:
- `Permission denied: '/app/config/credentials.ini'`
- `Permission denied: '/app/config/users.json'`
- No notifications despite correct configuration
- Containers crash or restart repeatedly

This indicates a permission issue with the Docker bind mounts. Follow the steps in [DOCKER_SETUP.md](DOCKER_SETUP.md) to fix these issues.

### Web interface not working

- Ensure the web service is running:
  ```bash
  # For traditional installation:
  sudo systemctl status nuki-web.service
  
  # For Docker installation:
  docker ps | grep nuki-web
  ```
- Check for errors in the web logs:
  ```bash
  # For traditional installation:
  tail -f ~/nukiweb/logs/nuki_web.log
  
  # For Docker installation:
  docker logs nuki-web
  ```
- Verify the health status with:
  ```bash
  curl http://your-pi-ip:5000/health
  ```

## Repository

This project is hosted on GitHub at: [https://github.com/davedavedavenm/nuki-smart-lock-notification](https://github.com/davedavedavenm/nuki-smart-lock-notification)

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [Nuki](https://nuki.io/) for providing the Smart Lock and API
- The Python and Flask communities for excellent tools
- All contributors to this project