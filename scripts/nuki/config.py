import os
import configparser
import logging
import sys

logger = logging.getLogger('nuki_monitor')

class ConfigManager:
    def __init__(self, base_dir):
        self.base_dir = base_dir
        self.config_path = os.path.join(self.base_dir, "config", "config.ini")
        self.credentials_path = os.path.join(self.base_dir, "config", "credentials.ini")
        
        # Check CONFIG_DIR environment variable
        config_dir_env = os.environ.get('CONFIG_DIR')
        if config_dir_env:
            self.config_path = os.path.join(config_dir_env, "config.ini")
            self.credentials_path = os.path.join(config_dir_env, "credentials.ini")
            logger.info(f"Using config directory from environment: {config_dir_env}")
        
        # Check if config directory exists
        config_dir = os.path.dirname(self.config_path)
        if not os.path.exists(config_dir):
            try:
                os.makedirs(config_dir, exist_ok=True)
                logger.info(f"Created config directory: {config_dir}")
            except Exception as e:
                logger.error(f"Failed to create config directory {config_dir}: {e}")
                
        # Load configuration files
        self.config = self._load_config()
        self.credentials = self._load_credentials()
        
        # Configuration settings
        self.notification_type = self.config.get('General', 'notification_type', fallback='both')
        self.polling_interval = self.config.getint('General', 'polling_interval', fallback=60)
        self.digest_mode = self.config.getboolean('Notification', 'digest_mode', fallback=False)
        self.digest_interval = self.config.getint('Notification', 'digest_interval', fallback=3600)
        self.track_all_users = self.config.getboolean('Notification', 'track_all_users', fallback=True)
        self.notify_auto_lock = self.config.getboolean('Notification', 'notify_auto_lock', fallback=True)
        self.notify_system_events = self.config.getboolean('Notification', 'notify_system_events', fallback=True)
        
        # Filter settings
        self.excluded_users = self._parse_list(self.config.get('Filter', 'excluded_users', fallback=''))
        self.excluded_actions = self._parse_list(self.config.get('Filter', 'excluded_actions', fallback=''))
        self.excluded_triggers = self._parse_list(self.config.get('Filter', 'excluded_triggers', fallback=''))
        
        # API settings
        self.api_token = self.credentials.get('Nuki', 'api_token', fallback='')
        self.base_url = "https://api.nuki.io"
        
        # Smartlock settings
        self.smartlock_id = self.config.get('Nuki', 'smartlock_id', fallback='')
        self.use_explicit_id = self.config.getboolean('Nuki', 'use_explicit_id', fallback=False)
        
        if self.use_explicit_id and self.smartlock_id:
            logger.info(f"Using explicit smartlock ID: {self.smartlock_id}")
        elif self.use_explicit_id and not self.smartlock_id:
            logger.warning("'use_explicit_id' is enabled but no 'smartlock_id' is configured in config.ini!")
            logger.warning("Please add 'smartlock_id = YOUR_LOCK_ID' to the [Nuki] section in config.ini")
        else:
            logger.info("Using dynamic smartlock ID discovery from API")
        
        
        # Check if API token is set
        if not self.api_token:
            logger.warning("API token not set in credentials.ini! API requests will fail.")
            logger.info("DIAGNOSTIC: No API token found in credentials.ini")
        else:
            # Mask token for security while providing useful debugging info
            token_len = len(self.api_token)
            if token_len >= 10:
                masked_token = f"{self.api_token[:5]}...{self.api_token[-5:]}"
            else:
                masked_token = f"{self.api_token[:2]}...{self.api_token[-2:]}" if token_len >= 4 else "***"
            logger.info(f"DIAGNOSTIC: API token loaded successfully - {masked_token} (length: {token_len})")
        
        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Accept": "application/json"
        }
        
        # Log the prepared Authorization header
        auth_header = self.headers.get("Authorization", "")
        if auth_header:
            # Extract and mask just the token portion of the header
            if auth_header.startswith("Bearer ") and len(auth_header) > 7:
                token_part = auth_header[7:]  # Skip "Bearer "
                if len(token_part) >= 5:
                    logger.info(f"DIAGNOSTIC: Authorization header prepared: Bearer {token_part[:5]}...")
                else:
                    logger.info(f"DIAGNOSTIC: Authorization header prepared: Bearer ***")
            else:
                logger.info(f"DIAGNOSTIC: Authorization header prepared but in unexpected format")
        
        # Email settings
        self.smtp_server = self.config.get('Email', 'smtp_server', fallback='')
        self.smtp_port = self.config.getint('Email', 'smtp_port', fallback=587)
        self.email_username = self.credentials.get('Email', 'username', fallback='')
        self.email_password = self.credentials.get('Email', 'password', fallback='')
        self.email_sender = self.config.get('Email', 'sender', fallback='')
        self.email_recipient = self.config.get('Email', 'recipient', fallback='')
        self.use_html_email = self.config.getboolean('Email', 'use_html', fallback=True)
        self.email_subject_prefix = self.config.get('Email', 'subject_prefix', fallback='Nuki Alert')
        
        # Telegram settings
        self.telegram_bot_token = self.credentials.get('Telegram', 'bot_token', fallback='')
        self.telegram_chat_id = self.config.get('Telegram', 'chat_id', fallback='')
        self.telegram_use_emoji = self.config.getboolean('Telegram', 'use_emoji', fallback=True)
        self.telegram_format = self.config.get('Telegram', 'format', fallback='detailed')
        
        # Advanced settings
        self.max_events_per_check = self.config.getint('Advanced', 'max_events_per_check', fallback=5)
        self.max_historical_events = self.config.getint('Advanced', 'max_historical_events', fallback=20)
        self.debug_mode = self.config.getboolean('Advanced', 'debug_mode', fallback=False)
        self.user_cache_timeout = self.config.getint('Advanced', 'user_cache_timeout', fallback=3600)
        self.retry_on_failure = self.config.getboolean('Advanced', 'retry_on_failure', fallback=True)
        self.max_retries = self.config.getint('Advanced', 'max_retries', fallback=3)
        self.retry_delay = self.config.getint('Advanced', 'retry_delay', fallback=5)
        
        # Set debug logging if enabled
        if self.debug_mode:
            logger.setLevel(logging.DEBUG)
            for handler in logger.handlers:
                handler.setLevel(logging.DEBUG)
            logger.debug("Debug logging enabled")
    
    def _parse_list(self, value_str):
        """Parse a comma-separated string into a list of values"""
        if not value_str:
            return []
        return [item.strip() for item in value_str.split(',') if item.strip()]
    
    def _load_config(self):
        """Load the main configuration file"""
        config = configparser.ConfigParser()
        
        try:
            if os.path.exists(self.config_path):
                config.read(self.config_path)
                logger.info(f"Loaded configuration from {self.config_path}")
            else:
                logger.warning(f"Config file not found at {self.config_path}, creating default")
                self._create_default_config(config)
                self._save_config(config, self.config_path)
        except Exception as e:
            logger.error(f"Error loading config file: {e}")
            self._create_default_config(config)
            
        return config
        
    def _load_credentials(self):
        """Load the credentials file"""
        credentials = configparser.ConfigParser()
        
        try:
            if os.path.exists(self.credentials_path):
                credentials.read(self.credentials_path)
                logger.info(f"Loaded credentials from {self.credentials_path}")
            else:
                logger.warning(f"Credentials file not found at {self.credentials_path}, creating empty template")
                self._create_empty_credentials(credentials)
                self._save_config(credentials, self.credentials_path)
                
                # Set secure permissions for the credentials file
                try:
                    os.chmod(self.credentials_path, 0o600)
                    logger.info(f"Set secure permissions for {self.credentials_path}")
                except Exception as perm_e:
                    logger.warning(f"Could not set permissions for credentials file: {perm_e}")
        except Exception as e:
            logger.error(f"Error loading credentials file: {e}")
            self._create_empty_credentials(credentials)
            
        return credentials
    
    def _save_config(self, config_obj, file_path):
        """Save a configuration object to file"""
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, 'w') as f:
                config_obj.write(f)
                
            logger.info(f"Saved configuration to {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving configuration to {file_path}: {e}")
            return False
        
    def _create_default_config(self, config):
        """Create a default configuration if none exists"""
        config.add_section('General')
        config.set('General', 'notification_type', 'both')
        config.set('General', 'polling_interval', '60')
        
        config.add_section('Notification')
        config.set('Notification', 'digest_mode', 'false')
        config.set('Notification', 'digest_interval', '3600')
        config.set('Notification', 'track_all_users', 'true')
        config.set('Notification', 'notify_auto_lock', 'true')
        config.set('Notification', 'notify_system_events', 'true')
        
        config.add_section('Filter')
        config.set('Filter', 'excluded_users', '')
        config.set('Filter', 'excluded_actions', '')
        config.set('Filter', 'excluded_triggers', '')
        
        config.add_section('Email')
        config.set('Email', 'smtp_server', '')
        config.set('Email', 'smtp_port', '587')
        config.set('Email', 'sender', '')
        config.set('Email', 'recipient', '')
        config.set('Email', 'use_html', 'true')
        config.set('Email', 'subject_prefix', 'Nuki Alert')
        
        config.add_section('Telegram')
        config.set('Telegram', 'chat_id', '')
        config.set('Telegram', 'use_emoji', 'true')
        config.set('Telegram', 'format', 'detailed')
        
        config.add_section('Advanced')
        config.set('Advanced', 'max_events_per_check', '5')
        config.set('Advanced', 'max_historical_events', '20')
        config.set('Advanced', 'debug_mode', 'false')
        config.set('Advanced', 'user_cache_timeout', '3600')
        config.set('Advanced', 'retry_on_failure', 'true')
        config.set('Advanced', 'max_retries', '3')
        config.set('Advanced', 'retry_delay', '5')
    
    def _create_empty_credentials(self, credentials):
        """Create an empty credentials file structure"""
        credentials.add_section('Nuki')
        credentials.set('Nuki', 'api_token', '')
        
        credentials.add_section('Email')
        credentials.set('Email', 'username', '')
        credentials.set('Email', 'password', '')
        
        credentials.add_section('Telegram')
        credentials.set('Telegram', 'bot_token', '')
    
    def reload(self):
        """Reload configuration and credentials from disk"""
        logger.info("Reloading configuration files")
        self.config = self._load_config()
        self.credentials = self._load_credentials()
        # Re-initialize settings (simplified version, you may want to re-add all settings)
        self.api_token = self.credentials.get('Nuki', 'api_token', fallback='')
        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Accept": "application/json"
        }
