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
            
        # Check DATA_DIR environment variable
        self.data_dir = os.environ.get('DATA_DIR', os.path.join(self.base_dir, "data"))
        logger.info(f"Using data directory: {self.data_dir}")
        
        # Check if data directory exists
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir, exist_ok=True)
            logger.info(f"Created data directory: {self.data_dir}")
        
        # Check if config directory exists and is writable
        config_dir = os.path.dirname(self.config_path)
        if not os.path.exists(config_dir):
            try:
                os.makedirs(config_dir, exist_ok=True)
                logger.info(f"Created config directory: {config_dir}")
            except PermissionError as e:
                logger.critical(f"❌ CRITICAL: Permission denied creating config directory {config_dir}")
                logger.critical(f"The application does not have write permissions to create the directory.")
                logger.critical(f"See DOCKER_SETUP.md for details on setting correct permissions.")
                sys.exit(1)
            except Exception as e:
                logger.critical(f"❌ CRITICAL: Failed to create config directory {config_dir}: {e}")
                logger.critical(f"See DOCKER_SETUP.md for details on setting correct permissions.")
                sys.exit(1)
        elif not os.access(config_dir, os.W_OK):
            logger.critical(f"❌ CRITICAL: Config directory {config_dir} is not writable")
            logger.critical(f"The application needs write access to this directory for users.json")
            logger.critical(f"See DOCKER_SETUP.md for details on setting correct permissions.")
            sys.exit(1)
                
        # Load configuration files
        try:
            self.config = self._load_config()
            self.credentials = self._load_credentials()
        except (PermissionError, IOError) as e:
            logger.critical(f"❌ CRITICAL: Permission error accessing configuration files: {e}")
            logger.critical(f"The application cannot read/write to configuration files.")
            logger.critical(f"See DOCKER_SETUP.md for details on setting correct permissions.")
            sys.exit(1)
        
        # Configuration settings
        self.notification_type = self._get_val('General', 'notification_type', env_name='NUKI_NOTIFICATION_TYPE', fallback='both')
        self.polling_interval = self._get_val_int('General', 'polling_interval', env_name='NUKI_POLLING_INTERVAL', fallback=60)
        self.digest_mode = self._get_val_bool('Notification', 'digest_mode', env_name='NUKI_DIGEST_MODE', fallback=False)
        self.digest_interval = self._get_val_int('Notification', 'digest_interval', env_name='NUKI_DIGEST_INTERVAL', fallback=3600)
        self.track_all_users = self._get_val_bool('Notification', 'track_all_users', env_name='NUKI_TRACK_ALL_USERS', fallback=True)
        self.notify_auto_lock = self._get_val_bool('Notification', 'notify_auto_lock', env_name='NUKI_NOTIFY_AUTO_LOCK', fallback=True)
        self.notify_system_events = self._get_val_bool('Notification', 'notify_system_events', env_name='NUKI_NOTIFY_SYSTEM_EVENTS', fallback=True)
        
        # Filter settings
        self.excluded_users = self._parse_list(self._get_val('Filter', 'excluded_users', env_name='NUKI_EXCLUDED_USERS', fallback=''))
        self.excluded_actions = self._parse_list(self._get_val('Filter', 'excluded_actions', env_name='NUKI_EXCLUDED_ACTIONS', fallback=''))
        self.excluded_triggers = self._parse_list(self._get_val('Filter', 'excluded_triggers', env_name='NUKI_EXCLUDED_TRIGGERS', fallback=''))
        
        # API settings
        self.api_token = self._get_val('Nuki', 'api_token', env_name='NUKI_API_TOKEN', is_credential=True, fallback='')
        self.base_url = "https://api.nuki.io"
        
        # Smartlock settings
        self.smartlock_id = self._get_val('Nuki', 'smartlock_id', env_name='NUKI_SMARTLOCK_ID', fallback='')
        self.use_explicit_id = self._get_val_bool('Nuki', 'use_explicit_id', env_name='NUKI_USE_EXPLICIT_ID', fallback=False)
        
        if self.use_explicit_id and self.smartlock_id:
            logger.info(f"Using explicit smartlock ID: {self.smartlock_id}")
        elif self.use_explicit_id and not self.smartlock_id:
            logger.warning("'use_explicit_id' is enabled but no 'smartlock_id' is configured in config.ini!")
            logger.warning("Please add 'smartlock_id = YOUR_LOCK_ID' to the [Nuki] section in config.ini")
        else:
            logger.info("Using dynamic smartlock ID discovery from API")
        
        
        # Check if API token is set
        if not self.api_token:
            logger.critical("❌ CRITICAL: API token not set or credentials.ini is not readable!")
            logger.critical("This may be due to a permission issue with the config directory.")
            logger.critical("DIAGNOSTIC: No API token found in credentials.ini")
            logger.critical("Make sure credentials.ini exists with proper permissions (chmod 644)")
            logger.critical("See DOCKER_SETUP.md for details on setting correct permissions.")
            
            # Check if credentials file exists to provide more helpful error messages
            if not os.path.exists(self.credentials_path):
                logger.critical(f"File does not exist: {self.credentials_path}")
                logger.critical("You need to create this file with your API token.")
            elif not os.access(self.credentials_path, os.R_OK):
                logger.critical(f"File exists but is not readable: {self.credentials_path}")
                logger.critical(f"Fix with: chmod 644 {os.path.basename(self.credentials_path)}")
            
            # Exit with error code to prevent starting with invalid configuration
            sys.exit(1)
        else:
            # Mask token for security while providing useful debugging info
            token_len = len(self.api_token)
            if token_len >= 10:
                masked_token = f"{self.api_token[:5]}...{self.api_token[-5:]}"
            else:
                masked_token = f"{self.api_token[:2]}...{self.api_token[-2:]}" if token_len >= 4 else "***"
            logger.info(f"✅ DIAGNOSTIC: API token loaded successfully - {masked_token} (length: {token_len})")
        
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
        self.smtp_server = self._get_val('Email', 'smtp_server', env_name='NUKI_SMTP_SERVER', fallback='')
        self.smtp_port = self._get_val_int('Email', 'smtp_port', env_name='NUKI_SMTP_PORT', fallback=587)
        self.email_username = self._get_val('Email', 'username', env_name='NUKI_EMAIL_USERNAME', is_credential=True, fallback='')
        self.email_password = self._get_val('Email', 'password', env_name='NUKI_EMAIL_PASSWORD', is_credential=True, fallback='')
        self.email_sender = self._get_val('Email', 'sender', env_name='NUKI_EMAIL_SENDER', fallback='')
        self.email_recipient = self._get_val('Email', 'recipient', env_name='NUKI_EMAIL_RECIPIENT', fallback='')
        self.use_html_email = self._get_val_bool('Email', 'use_html', env_name='NUKI_EMAIL_USE_HTML', fallback=True)
        self.email_subject_prefix = self._get_val('Email', 'subject_prefix', env_name='NUKI_EMAIL_SUBJECT_PREFIX', fallback='Nuki Alert')
        
        # Telegram settings
        self.telegram_bot_token = self._get_val('Telegram', 'bot_token', env_name='NUKI_TELEGRAM_BOT_TOKEN', is_credential=True, fallback='')
        self.telegram_chat_id = self._get_val('Telegram', 'chat_id', env_name='NUKI_TELEGRAM_CHAT_ID', fallback='')
        self.telegram_use_emoji = self._get_val_bool('Telegram', 'use_emoji', env_name='NUKI_TELEGRAM_USE_EMOJI', fallback=True)
        self.telegram_format = self._get_val('Telegram', 'format', env_name='NUKI_TELEGRAM_FORMAT', fallback='detailed')
        
        # Advanced settings
        self.max_events_per_check = self._get_val_int('Advanced', 'max_events_per_check', env_name='NUKI_MAX_EVENTS_PER_CHECK', fallback=5)
        self.max_historical_events = self._get_val_int('Advanced', 'max_historical_events', env_name='NUKI_MAX_HISTORICAL_EVENTS', fallback=20)
        self.debug_mode = self._get_val_bool('Advanced', 'debug_mode', env_name='NUKI_DEBUG_MODE', fallback=False)
        self.user_cache_timeout = self._get_val_int('Advanced', 'user_cache_timeout', env_name='NUKI_USER_CACHE_TIMEOUT', fallback=3600)
        self.retry_on_failure = self._get_val_bool('Advanced', 'retry_on_failure', env_name='NUKI_RETRY_ON_FAILURE', fallback=True)
        self.max_retries = self._get_val_int('Advanced', 'max_retries', env_name='NUKI_MAX_RETRIES', fallback=3)
        self.retry_delay = self._get_val_int('Advanced', 'retry_delay', env_name='NUKI_RETRY_DELAY', fallback=5)
        
        # Set debug logging if enabled
        if self.debug_mode:
            logger.setLevel(logging.DEBUG)
            for handler in logger.handlers:
                handler.setLevel(logging.DEBUG)
            logger.debug("Debug logging enabled")
    
    def _get_val(self, section, key, env_name=None, is_credential=False, fallback=None):
        """Get a value with environment variable prioritization"""
        if env_name and os.environ.get(env_name):
            return os.environ.get(env_name)
        
        target_config = self.credentials if is_credential else self.config
        return target_config.get(section, key, fallback=fallback)

    def _get_val_int(self, section, key, env_name=None, is_credential=False, fallback=None):
        """Get an integer value with environment variable prioritization"""
        if env_name and os.environ.get(env_name):
            try:
                return int(os.environ.get(env_name))
            except (ValueError, TypeError):
                pass
        
        target_config = self.credentials if is_credential else self.config
        try:
            return target_config.getint(section, key, fallback=fallback)
        except (ValueError, TypeError):
            return fallback

    def _get_val_bool(self, section, key, env_name=None, is_credential=False, fallback=None):
        """Get a boolean value with environment variable prioritization"""
        if env_name and os.environ.get(env_name):
            val = os.environ.get(env_name).lower()
            if val in ('true', '1', 'yes', 'on'):
                return True
            if val in ('false', '0', 'no', 'off'):
                return False
        
        target_config = self.credentials if is_credential else self.config
        try:
            return target_config.getboolean(section, key, fallback=fallback)
        except (ValueError, TypeError):
            return fallback

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
                if not os.access(self.config_path, os.R_OK):
                    raise PermissionError(f"Cannot read configuration file: {self.config_path}")
                config.read(self.config_path)
                logger.info(f"Loaded configuration from {self.config_path}")
            else:
                logger.warning(f"Config file not found at {self.config_path}, creating default")
                self._create_default_config(config)
                self._save_config(config, self.config_path)
        except PermissionError as e:
            logger.critical(f"❌ CRITICAL: Permission error with config file: {e}")
            logger.critical(f"Make sure {os.path.basename(self.config_path)} has the correct permissions (chmod 644)")
            logger.critical(f"See DOCKER_SETUP.md for details on setting correct permissions.")
            raise
        except Exception as e:
            logger.error(f"Error loading config file: {e}")
            self._create_default_config(config)
            
        return config
        
    def _load_credentials(self):
        """Load the credentials file"""
        credentials = configparser.ConfigParser()
        
        try:
            if os.path.exists(self.credentials_path):
                if not os.access(self.credentials_path, os.R_OK):
                    raise PermissionError(f"Cannot read credentials file: {self.credentials_path}")
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
        except PermissionError as e:
            logger.critical(f"❌ CRITICAL: Permission error with credentials file: {e}")
            logger.critical(f"Make sure {os.path.basename(self.credentials_path)} has the correct permissions (chmod 644)")
            logger.critical(f"See DOCKER_SETUP.md for details on setting correct permissions.")
            raise
        except Exception as e:
            logger.error(f"Error loading credentials file: {e}")
            self._create_empty_credentials(credentials)
            
        return credentials
    
    def _save_config(self, config_obj, file_path):
        """Save a configuration object to file"""
        try:
            # Create directory if it doesn't exist
            dir_path = os.path.dirname(file_path)
            if not os.path.exists(dir_path):
                os.makedirs(dir_path, exist_ok=True)
            
            if os.path.exists(file_path) and not os.access(file_path, os.W_OK):
                raise PermissionError(f"Cannot write to configuration file: {file_path}")
                
            with open(file_path, 'w') as f:
                config_obj.write(f)
                
            logger.info(f"Saved configuration to {file_path}")
            return True
        except PermissionError as e:
            logger.critical(f"❌ CRITICAL: Permission error saving configuration: {e}")
            logger.critical(f"Make sure the container has write access to the config directory.")
            logger.critical(f"See DOCKER_SETUP.md for details on setting correct permissions.")
            return False
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
        try:
            self.config = self._load_config()
            self.credentials = self._load_credentials()
            # Re-initialize settings (simplified version, you may want to re-add all settings)
            self.api_token = self.credentials.get('Nuki', 'api_token', fallback='')
            if not self.api_token:
                logger.error("❌ API token not found when reloading credentials!")
                logger.error("Please check your credentials.ini file.")
            self.headers = {
                "Authorization": f"Bearer {self.api_token}",
                "Accept": "application/json"
            }
            return True
        except (PermissionError, IOError) as e:
            logger.critical(f"❌ CRITICAL: Permission error reloading configuration: {e}")
            logger.critical(f"See DOCKER_SETUP.md for details on setting correct permissions.")
            return False