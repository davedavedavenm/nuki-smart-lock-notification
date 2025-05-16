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
- 🔑 **Management Agency Access**: Allow management agencies to create temporary access codes
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

2. Copy example configuration files:
   ```bash
   cp config/config.ini.example config/config.ini
   cp config/credentials.ini.example config/credentials.ini
   ```

3. Edit configuration files with your settings:
   ```bash
   nano config/config.ini
   nano config/credentials.ini
   ```

4. Build and start Docker containers:
   ```bash
   docker-compose up -d
   ```

5. Access the web interface at `http://your-pi-ip:5000`

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
- **Configuration**: Adjust notification settings
- **User Management**: Add and manage users (admin only)
- **Notification Settings**: Configure notification preferences
- **Temporary Codes**: Create and manage temporary access codes (admin and agency roles)

Access the web interface at `http://your-pi-ip:5000`

### User Roles

The system supports three types of user roles:

1. **Admin**: Full access to all features and settings
2. **Agency**: Restricted access focused on temporary code management
3. **User**: Basic access for viewing lock status and activity

#### Creating Agency Users

To create a management agency user with the ability to manage temporary access codes:

1. Log in as an admin user
2. Go to Admin → Create Agency User
3. Fill in the required information
4. Click "Create Agency User"

#### Managing Temporary Codes

To create a temporary access code:

1. Log in as an admin or agency user
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

## Troubleshooting

Common issues and solutions:

### Password hashing error when using Docker

If you see an error like `ValueError: unsupported hash type scrypt:32768:8:1` after logging in:

- This happens because the Docker container's Python environment doesn't support the scrypt hashing algorithm
- Run the fix script to update the password hashing method:
  ```bash
  # Linux/Mac
  ./fix-password-hash.sh
  
  # Windows
  fix-password-hash.bat
  ```
- This will reset the admin user with default credentials (admin/nukiadmin)

### No notifications are being sent

- Check that your API token is valid
- Verify that notification settings are correct
- Check the logs for errors:
  ```bash
  tail -f ~/nukiweb/logs/nuki_monitor.log
  ```

### Web interface not working

- Ensure the web service is running:
  ```bash
  sudo systemctl status nuki-web.service
  ```
- Check for errors in the web logs:
  ```bash
  tail -f ~/nukiweb/logs/nuki_web.log
  ```

### Cannot determine user name for an action

- The API might return auth IDs differently
- Check that you're using the latest version
- Try to reset the user cache:
  ```bash
  rm ~/nukiweb/logs/user_cache.json
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
