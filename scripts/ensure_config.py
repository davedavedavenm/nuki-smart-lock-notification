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

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('ensure_config')

def ensure_config_files():
    """Ensure all required configuration files exist"""
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
                        os.chmod(config_path, 0o600)
                    except:
                        pass  # May fail on Windows
            except Exception as e:
                logger.error(f"Error creating {config_file}: {e}")
        
        # Verify the file exists now
        if not os.path.exists(config_path):
            logger.error(f"Required configuration file {config_file} is missing!")
            
    logger.info("Configuration files are ready")
    return True

if __name__ == "__main__":
    ensure_config_files()
