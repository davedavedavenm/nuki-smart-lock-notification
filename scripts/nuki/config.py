import os
import configparser
import logging

logger = logging.getLogger('nuki_monitor')

class ConfigManager:
    def __init__(self, base_dir):
        self.base_dir = base_dir
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
        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Accept": "application/json"
        }
        
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
    
    def _parse_list(self, value_str):
        """Parse a comma-separated string into a list of values"""
        if not value_str:
            return []
        return [item.strip() for item in value_str.split(',')]
    
    def _load_config(self):
        config = configparser.ConfigParser()
        config_path = os.path.join(self.base_dir, "config", "config.ini")
        if os.path.exists(config_path):
            config.read(config_path)
        else:
            logger.warning(f"Config file not found at {config_path}, using defaults")
            self._create_default_config(config)
        return config
        
    def _load_credentials(self):
        credentials = configparser.ConfigParser()
        credentials_path = os.path.join(self.base_dir, "config", "credentials.ini")
        if os.path.exists(credentials_path):
            credentials.read(credentials_path)
        else:
            logger.warning(f"Credentials file not found at {credentials_path}")
            self._create_empty_credentials(credentials)
        return credentials
        
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
