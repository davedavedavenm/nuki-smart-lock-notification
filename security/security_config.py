"""
Security Configuration Module for Nuki Smart Lock

This module manages security-specific configuration options for the
security monitoring and alerting system.
"""

import os
import sys
import logging
import configparser

# Add parent directory to path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.expanduser("~/nukiweb/logs/nuki_security_config.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('nuki_security_config')

class SecurityConfigManager:
    """
    Manages security-specific configuration options for the Nuki system.
    """
    
    def __init__(self, base_dir=None):
        """
        Initialize the security configuration manager.
        
        Args:
            base_dir: Base directory or None to determine automatically
        """
        # Determine base directory
        if base_dir is None:
            self.base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        else:
            self.base_dir = base_dir
        
        # Set config paths
        self.config_dir = os.path.join(self.base_dir, "config")
        self.config_path = os.path.join(self.config_dir, "config.ini")
        self.security_config_path = os.path.join(self.config_dir, "security.ini")
        
        # Load configuration
        self.config = self._load_main_config()
        self.security_config = self._load_security_config()
        
        # Load settings from config
        self._load_settings()
        
        logger.info("Security Configuration Manager initialized")
    
    def _load_main_config(self):
        """
        Load main configuration file.
        
        Returns:
            configparser.ConfigParser: Config object
        """
        config = configparser.ConfigParser()
        
        if os.path.exists(self.config_path):
            try:
                config.read(self.config_path)
                logger.info(f"Loaded main configuration from {self.config_path}")
            except Exception as e:
                logger.error(f"Error loading main configuration: {e}")
        else:
            logger.warning(f"Main configuration file not found at {self.config_path}")
        
        return config
    
    def _load_security_config(self):
        """
        Load security-specific configuration file.
        
        Returns:
            configparser.ConfigParser: Config object
        """
        config = configparser.ConfigParser()
        
        if os.path.exists(self.security_config_path):
            try:
                config.read(self.security_config_path)
                logger.info(f"Loaded security configuration from {self.security_config_path}")
            except Exception as e:
                logger.error(f"Error loading security configuration: {e}")
        else:
            logger.info(f"Security configuration file not found at {self.security_config_path}, creating default")
            self._create_default_security_config(config)
        
        return config
    
    def _create_default_security_config(self, config):
        """
        Create a default security configuration.
        
        Args:
            config: ConfigParser object to add defaults to
        """
        # Ensure directory exists
        os.makedirs(self.config_dir, exist_ok=True)
        
        # Add default sections and options
        if 'Security' not in config:
            config.add_section('Security')
        
        # Threshold settings
        config.set('Security', 'enabled', 'true')
        config.set('Security', 'failed_attempts_threshold', '3')
        config.set('Security', 'failed_attempts_window', '300')
        config.set('Security', 'unusual_hour_start', '23')
        config.set('Security', 'unusual_hour_end', '6')
        config.set('Security', 'rapid_access_threshold', '5')
        config.set('Security', 'rapid_access_window', '60')
        
        # Alert settings
        config.set('Security', 'alert_priority', 'high')
        config.set('Security', 'alert_sound', 'true')
        config.set('Security', 'notify_owner_only', 'true')
        config.set('Security', 'include_evidence', 'true')
        
        # Save default configuration
        try:
            with open(self.security_config_path, 'w') as f:
                config.write(f)
            logger.info(f"Created default security configuration at {self.security_config_path}")
        except Exception as e:
            logger.error(f"Error creating default security configuration: {e}")
    
    def _load_settings(self):
        """Load all security settings from config."""
        # First check if security is enabled
        if 'Security' not in self.config:
            self.config.add_section('Security')
        
        self.enabled = self.config.getboolean('Security', 'enabled', fallback=True)
        
        # Load threshold settings from main config
        self.failed_attempts_threshold = self.config.getint('Security', 'failed_attempts_threshold', fallback=3)
        self.failed_attempts_window = self.config.getint('Security', 'failed_attempts_window', fallback=300)
        self.unusual_hour_start = self.config.getint('Security', 'unusual_hour_start', fallback=23)
        self.unusual_hour_end = self.config.getint('Security', 'unusual_hour_end', fallback=6)
        self.rapid_access_threshold = self.config.getint('Security', 'rapid_access_threshold', fallback=5)
        self.rapid_access_window = self.config.getint('Security', 'rapid_access_window', fallback=60)
        
        # Load alert settings
        self.alert_priority = self.config.get('Security', 'alert_priority', fallback='high')
        self.alert_sound = self.config.getboolean('Security', 'alert_sound', fallback=True)
        self.notify_owner_only = self.config.getboolean('Security', 'notify_owner_only', fallback=True)
        self.include_evidence = self.config.getboolean('Security', 'include_evidence', fallback=True)
        
        # Override from security-specific config if exists
        if os.path.exists(self.security_config_path):
            # Load settings from security config
            if 'Security' in self.security_config:
                security_section = self.security_config['Security']
                
                # Only override settings that are actually in the security config
                if 'enabled' in security_section:
                    self.enabled = security_section.getboolean('enabled')
                
                if 'failed_attempts_threshold' in security_section:
                    self.failed_attempts_threshold = security_section.getint('failed_attempts_threshold')
                
                if 'failed_attempts_window' in security_section:
                    self.failed_attempts_window = security_section.getint('failed_attempts_window')
                
                if 'unusual_hour_start' in security_section:
                    self.unusual_hour_start = security_section.getint('unusual_hour_start')
                
                if 'unusual_hour_end' in security_section:
                    self.unusual_hour_end = security_section.getint('unusual_hour_end')
                
                if 'rapid_access_threshold' in security_section:
                    self.rapid_access_threshold = security_section.getint('rapid_access_threshold')
                
                if 'rapid_access_window' in security_section:
                    self.rapid_access_window = security_section.getint('rapid_access_window')
                
                if 'alert_priority' in security_section:
                    self.alert_priority = security_section.get('alert_priority')
                
                if 'alert_sound' in security_section:
                    self.alert_sound = security_section.getboolean('alert_sound')
                
                if 'notify_owner_only' in security_section:
                    self.notify_owner_only = security_section.getboolean('notify_owner_only')
                
                if 'include_evidence' in security_section:
                    self.include_evidence = security_section.getboolean('include_evidence')
        
        logger.info(f"Security settings loaded: enabled={self.enabled}, "
                   f"failed_threshold={self.failed_attempts_threshold}, "
                   f"unusual_hours={self.unusual_hour_start}-{self.unusual_hour_end}")
    
    def update_setting(self, name, value):
        """
        Update a security setting.
        
        Args:
            name: Setting name
            value: New value
            
        Returns:
            bool: True if setting was updated successfully
        """
        try:
            # Validate setting
            if name not in [
                'enabled', 'failed_attempts_threshold', 'failed_attempts_window',
                'unusual_hour_start', 'unusual_hour_end', 'rapid_access_threshold',
                'rapid_access_window', 'alert_priority', 'alert_sound',
                'notify_owner_only', 'include_evidence'
            ]:
                logger.error(f"Invalid security setting: {name}")
                return False
            
            # Update setting in security config
            if 'Security' not in self.security_config:
                self.security_config.add_section('Security')
            
            # Convert booleans
            if name in ['enabled', 'alert_sound', 'notify_owner_only', 'include_evidence']:
                if isinstance(value, str):
                    value = value.lower() in ['true', 'yes', '1', 'on']
                self.security_config.set('Security', name, str(value).lower())
            else:
                self.security_config.set('Security', name, str(value))
            
            # Save config
            with open(self.security_config_path, 'w') as f:
                self.security_config.write(f)
            
            # Update instance variable
            setattr(self, name, value)
            
            logger.info(f"Updated security setting {name} to {value}")
            return True
        except Exception as e:
            logger.error(f"Error updating security setting {name}: {e}")
            return False
    
    def get_all_settings(self):
        """
        Get all security settings as a dictionary.
        
        Returns:
            dict: Dictionary of all security settings
        """
        return {
            'enabled': self.enabled,
            'failed_attempts_threshold': self.failed_attempts_threshold,
            'failed_attempts_window': self.failed_attempts_window,
            'unusual_hour_start': self.unusual_hour_start,
            'unusual_hour_end': self.unusual_hour_end,
            'rapid_access_threshold': self.rapid_access_threshold,
            'rapid_access_window': self.rapid_access_window,
            'alert_priority': self.alert_priority,
            'alert_sound': self.alert_sound,
            'notify_owner_only': self.notify_owner_only,
            'include_evidence': self.include_evidence
        }

# Example usage when run directly
if __name__ == "__main__":
    # Create security config manager
    config_manager = SecurityConfigManager()
    
    # Print all settings
    settings = config_manager.get_all_settings()
    print("Current Security Settings:")
    for name, value in settings.items():
        print(f"  {name}: {value}")
    
    # Example: update a setting
    config_manager.update_setting('failed_attempts_threshold', 4)
    print(f"Updated threshold: {config_manager.failed_attempts_threshold}")
