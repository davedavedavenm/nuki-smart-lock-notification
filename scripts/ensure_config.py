#!/usr/bin/env python3
"""
Configuration Validation Script
Ensures that all required configuration files exist with the correct structure.
"""

import os
import sys
import configparser
import logging
import shutil

# Set up logging with fallback to console if file logging fails
log_handlers = []
try:
    # Ensure logs directory exists
    logs_dir = os.environ.get('LOGS_DIR', os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs'))
    os.makedirs(logs_dir, exist_ok=True)
    
    # Try to set up file handler
    log_file = os.path.join(logs_dir, 'ensure_config.log')
    file_handler = logging.FileHandler(log_file)
    log_handlers.append(file_handler)
except (PermissionError, IOError) as e:
    print(f"WARNING: Could not set up file logging: {e}")
    print("File logging will be disabled. Check directory permissions.")
    print("See TROUBLESHOOTING.md for information on fixing permission issues.")

# Always add console handler as fallback
log_handlers.append(logging.StreamHandler())

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=log_handlers
)
logger = logging.getLogger('ensure_config')

def check_directory_permissions():
    """Check if directories are writable and log warnings"""
    config_dir = os.environ.get('CONFIG_DIR', os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config'))
    logs_dir = os.environ.get('LOGS_DIR', os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs'))
    data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
    
    # Check directories exist
    for directory in [config_dir, logs_dir, data_dir]:
        if not os.path.exists(directory):
            try:
                os.makedirs(directory, exist_ok=True)
                logger.info(f"Created directory: {directory}")
            except (PermissionError, IOError) as e:
                logger.warning(f"Cannot create directory {directory}: {e}")
                logger.warning("See TROUBLESHOOTING.md for information on fixing permission issues.")
    
    # Check write permissions
    permission_issues = []
    
    if not os.access(config_dir, os.W_OK):
        permission_issues.append(f"Config directory is not writable: {config_dir}")
        
    if not os.access(logs_dir, os.W_OK):
        permission_issues.append(f"Logs directory is not writable: {logs_dir}")
        
    if not os.access(data_dir, os.W_OK):
        permission_issues.append(f"Data directory is not writable: {data_dir}")
    
    if permission_issues:
        logger.warning("Permission issues detected:")
        for issue in permission_issues:
            logger.warning(f"- {issue}")
        logger.warning("See TROUBLESHOOTING.md for information on fixing permission issues.")
        return False
    
    logger.info("All directories are writable")
    return True

def ensure_config_files():
    """Ensure all required configuration files exist"""
    # Check directory permissions first
    check_directory_permissions()
    
    # Determine config directory
    config_dir = os.environ.get('CONFIG_DIR', os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config'))
    
    # Ensure config directory exists
    os.makedirs(config_dir, exist_ok=True)
    
    # List of required configuration files and their example templates
    required_files = {
        'config.ini': 'config.ini.example',
        'credentials.ini': 'credentials.ini.example'
    }
    
    for config_file, example_file in required_files.items():
        config_path = os.path.join(config_dir, config_file)
        example_path = os.path.join(config_dir, example_file)
        
        # If the config file doesn't exist but the example does, copy it
        if not os.path.exists(config_path) and os.path.exists(example_path):
            try:
                shutil.copy(example_path, config_path)
                logger.info(f"Created {config_file} from example template")
                
                # Set secure permissions for credentials file
                if config_file == 'credentials.ini':
                    try:
                        os.chmod(config_path, 0o640)
                        logger.info(f"Set secure permissions for {config_file}")
                    except Exception as e:
                        logger.warning(f"Could not set permissions for {config_file}: {e}")
            except (PermissionError, IOError) as e:
                logger.error(f"Error creating {config_file} due to permission issue: {e}")
                logger.error("This may be due to the container user not having write permissions to the config directory.")
                logger.error("See TROUBLESHOOTING.md for information on fixing permission issues.")
            except Exception as e:
                logger.error(f"Error creating {config_file}: {e}")
        
        # Verify the file exists now
        if not os.path.exists(config_path):
            logger.error(f"Required configuration file {config_file} is missing!")
            
    logger.info("Configuration files are ready")
    return True

if __name__ == "__main__":
    ensure_config_files()
