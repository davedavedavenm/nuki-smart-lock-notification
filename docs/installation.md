# Installation Guide

This guide provides detailed instructions for installing the Nuki Smart Lock Notification System on a Raspberry Pi.

## Prerequisites

- Raspberry Pi 4 (or compatible) with Raspberry Pi OS or DietPi installed
- Internet connection
- Nuki Smart Lock 4th Generation
- Nuki Web API token
- Basic knowledge of Linux commands

## Installation Methods

Choose one of the following installation methods:

### Method 1: Automated Installation Script

This is the recommended method for most users.

1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/nuki-smart-lock-notification.git
   cd nuki-smart-lock-notification
   ```

2. Run the installation script:
   ```bash
   chmod +x install/install.sh
   ./install/install.sh
   ```

3. Follow the on-screen prompts to complete the installation.

4. The script will automatically:
   - Create necessary directories
   - Copy files to the appropriate locations
   - Set up a Python virtual environment
   - Install required dependencies
   - Set proper file permissions
   - Install and enable systemd services
   - Run initial configuration

### Method 2: Manual Installation

For advanced users who want more control over the installation process.

1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/nuki-smart-lock-notification.git
   cd nuki-smart-lock-notification
   ```

2. Create the directory structure:
   ```bash
   sudo mkdir -p /root/nukiweb/{scripts,config,logs,web,security}
   sudo mkdir -p /root/nukiweb/scripts/nuki
   ```

3. Copy the files:
   ```bash
   sudo cp -r scripts/* /root/nukiweb/scripts/
   sudo cp -r scripts/nuki/* /root/nukiweb/scripts/nuki/
   sudo cp -r web/* /root/nukiweb/web/
   sudo cp -r security/* /root/nukiweb/security/
   sudo cp config/config.ini.example /root/nukiweb/config/config.ini
   sudo cp config/credentials.ini.example /root/nukiweb/config/credentials.ini
   ```

4. Create a Python virtual environment:
   ```bash
   cd /root/nukiweb
   sudo python3 -m venv venv
   sudo venv/bin/pip install --upgrade pip
   sudo venv/bin/pip install -r /path/to/repository/requirements.txt
   sudo venv/bin/pip install -r /path/to/repository/requirements-web.txt
   ```

5. Set file permissions:
   ```bash
   sudo chmod +x /root/nukiweb/scripts/nuki_monitor.py
   sudo chmod +x /root/nukiweb/web/app.py
   sudo chmod +x /root/nukiweb/scripts/configure.py
   sudo chmod 600 /root/nukiweb/config/credentials.ini
   ```

6. Install the systemd services:
   ```bash
   sudo cp install/nuki-monitor.service /etc/systemd/system/
   sudo cp install/nuki-web.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable nuki-monitor.service
   sudo systemctl enable nuki-web.service
   ```

7. Configure the system:
   ```bash
   cd /root/nukiweb/scripts
   sudo ../venv/bin/python configure.py
   ```

8. Start the services:
   ```bash
   sudo systemctl start nuki-monitor.service
   sudo systemctl start nuki-web.service
   ```

### Method 3: Docker Installation

For users who prefer containerization:

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

4. Access the web interface at `http://your-pi-ip:5000`

## Post-Installation Configuration

After installing the system, you need to configure it:

1. Edit the configuration files:
   ```bash
   sudo nano /root/nukiweb/config/config.ini
   sudo nano /root/nukiweb/config/credentials.ini
   ```

2. Add your Nuki API token to `credentials.ini`:
   ```ini
   [Nuki]
   api_token = YOUR_NUKI_API_TOKEN
   ```

3. Configure notification methods in `config.ini`:
   ```ini
   [General]
   notification_type = both  # Options: email, telegram, both
   ```

4. For email notifications, configure the email settings in `credentials.ini`:
   ```ini
   [Email]
   username = your-email@example.com
   password = your-email-password
   ```

5. For Telegram notifications, configure the Telegram settings:
   ```ini
   [Telegram]
   bot_token = YOUR_TELEGRAM_BOT_TOKEN
   ```
   Then set your chat ID in `config.ini`:
   ```ini
   [Telegram]
   chat_id = YOUR_CHAT_ID
   ```

6. Restart the services:
   ```bash
   sudo systemctl restart nuki-monitor.service
   sudo systemctl restart nuki-web.service
   ```

## Verifying Installation

To verify that the installation was successful:

1. Check the status of the services:
   ```bash
   sudo systemctl status nuki-monitor.service
   sudo systemctl status nuki-web.service
   ```

2. Check the logs:
   ```bash
   tail -f /root/nukiweb/logs/nuki_monitor.log
   tail -f /root/nukiweb/logs/nuki_web.log
   ```

3. Access the web interface:
   ```
   http://your-pi-ip:5000
   ```

## Troubleshooting

If you encounter issues during installation:

1. **Python errors**: Ensure you have Python 3.6+ installed:
   ```bash
   python3 --version
   ```

2. **Permission errors**: Make sure you're running commands with sudo:
   ```bash
   sudo chmod 600 /root/nukiweb/config/credentials.ini
   ```

3. **Service won't start**: Check the logs for errors:
   ```bash
   sudo journalctl -u nuki-monitor.service
   ```

4. **Web interface not accessible**: Check that the web service is running and listening on port 5000:
   ```bash
   sudo systemctl status nuki-web.service
   ss -tuln | grep 5000
   ```

5. **No notifications**: Verify your API token and notification settings:
   ```bash
   tail -f /root/nukiweb/logs/nuki_monitor.log
   ```

## Next Steps

After installation:

1. [Configure notifications](configuration.md) to your preferences
2. Set up [user accounts](user-management.md) for the web interface
3. Learn about [security features](security.md)
4. Explore [advanced features](advanced-features.md)
