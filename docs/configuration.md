# Configuration Guide

This guide covers the configuration options for the Nuki Smart Lock Notification System.

## Configuration Files

The system uses two main configuration files:

1. `config.ini` - General configuration settings
2. `credentials.ini` - Sensitive credentials and API tokens

Both files are located in the `config` directory.

## Configuration Tool

The system includes a configuration utility that makes it easy to set up:

```bash
cd /root/nukiweb/scripts
sudo ../venv/bin/python configure.py
```

This interactive tool will guide you through the configuration process.

## Manual Configuration

You can also edit the configuration files directly.

### config.ini

This file contains general configuration settings:

```ini
[General]
notification_type = both         ; Options: email, telegram, both
polling_interval = 60            ; Check interval in seconds

[Notification]
digest_mode = false              ; Send digest instead of immediate notifications
digest_interval = 3600           ; Digest interval in seconds
track_all_users = true           ; Track all users or only specified ones
notify_auto_lock = true          ; Send notifications for auto-lock events
notify_system_events = true      ; Send notifications for system events

[Filter]
excluded_users =                 ; Comma-separated list of users to exclude
excluded_actions =               ; Comma-separated list of actions to exclude
excluded_triggers =              ; Comma-separated list of triggers to exclude

[Email]
smtp_server = smtp.example.com   ; SMTP server address
smtp_port = 587                  ; SMTP port
sender = nuki-alerts@example.com ; Sender email address
recipient = your-email@example.com ; Recipient email address
use_html = true                  ; Use HTML formatting for emails
subject_prefix = Nuki Alert      ; Email subject prefix

[Telegram]
chat_id =                        ; Your Telegram chat ID
use_emoji = true                 ; Use emoji in Telegram messages
format = detailed                ; Options: detailed, simple

[Advanced]
max_events_per_check = 5         ; Maximum events to process per check
max_historical_events = 20       ; Maximum historical events to track
debug_mode = false               ; Enable debug logging
user_cache_timeout = 3600        ; User cache timeout in seconds
retry_on_failure = true          ; Retry on API failure
max_retries = 3                  ; Maximum retry attempts
retry_delay = 5                  ; Delay between retries in seconds
```

### credentials.ini

This file contains sensitive credentials:

```ini
[Nuki]
api_token = YOUR_NUKI_API_TOKEN

[Email]
username = your-email@example.com
password = your-email-password

[Telegram]
bot_token = YOUR_TELEGRAM_BOT_TOKEN
```

## Obtaining Required Credentials

### Nuki API Token

1. Log in to the [Nuki Web Dashboard](https://web.nuki.io/)
2. Go to "Account" > "API"
3. Generate a new API token
4. Add the token to your `credentials.ini` file

### Email Configuration

For Gmail:
```ini
[Email]
smtp_server = smtp.gmail.com
smtp_port = 587
username = your-gmail@gmail.com
password = your-app-password
```

Note: For Gmail, you need to use an [App Password](https://support.google.com/accounts/answer/185833) rather than your regular password.

For Outlook/Office 365:
```ini
[Email]
smtp_server = smtp.office365.com
smtp_port = 587
username = your-email@outlook.com
password = your-password
```

### Telegram Bot Token

1. Open Telegram and start a chat with [@BotFather](https://t.me/botfather)
2. Send the command `/newbot`
3. Follow the prompts to create a new bot
4. Copy the bot token provided by BotFather
5. Add the token to your `credentials.ini` file

### Telegram Chat ID

After creating your bot:

1. Run the helper script:
   ```bash
   cd /root/nukiweb/scripts
   sudo ../venv/bin/python get_telegram_chat_id.py
   ```
2. Enter your bot token when prompted
3. Follow the instructions to start a chat with your bot
4. The script will display your chat ID
5. Add the chat ID to your `config.ini` file

## Web Interface Configuration

The web interface has additional configuration options:

1. Access the web interface at `http://your-pi-ip:5000`
2. Log in with the default admin account or create a new account
3. Go to the "Configuration" page
4. Adjust settings as needed
5. Save changes

### User Management

To configure user accounts:

1. Log in as an administrator
2. Go to the "Users" page
3. Add new users or modify existing ones
4. Assign appropriate roles (admin or user)

### Notification Preferences

To set notification preferences:

1. Log in to your account
2. Go to the "Notifications" page
3. Configure your personal notification preferences
4. Save changes

## Security Configuration

For enhanced security:

1. Secure the `credentials.ini` file:
   ```bash
   sudo chmod 600 /root/nukiweb/config/credentials.ini
   ```

2. Use HTTPS for the web interface (recommended for internet-facing installations):
   - Set up a reverse proxy (e.g., Nginx, Apache)
   - Configure SSL certificates
   - Forward requests to the internal web service

3. Adjust firewall settings to restrict access:
   ```bash
   sudo ufw allow ssh
   sudo ufw allow 5000/tcp  # Only if web interface needs to be accessible
   sudo ufw enable
   ```

## Advanced Configuration

### Filtering Options

You can filter notifications by:

- **Users**: Exclude specific users
  ```ini
  [Filter]
  excluded_users = User1, User2
  ```

- **Actions**: Exclude specific actions
  ```ini
  [Filter]
  excluded_actions = Lock, Unlock
  ```

- **Triggers**: Exclude specific triggers
  ```ini
  [Filter]
  excluded_triggers = Auto Lock, Button
  ```

### Digest Mode

Instead of individual notifications, you can receive digests:

```ini
[Notification]
digest_mode = true
digest_interval = 3600  # Send digest every hour
```

### Debug Mode

For troubleshooting, enable debug mode:

```ini
[Advanced]
debug_mode = true
```

This will produce more detailed log output.

## Applying Configuration Changes

After changing configuration:

1. Restart the services:
   ```bash
   sudo systemctl restart nuki-monitor.service
   sudo systemctl restart nuki-web.service
   ```

2. Check the logs to verify the changes took effect:
   ```bash
   tail -f /root/nukiweb/logs/nuki_monitor.log
   ```
