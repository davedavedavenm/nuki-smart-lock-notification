#!/usr/bin/env python3
import os
import shutil
import sys

def ensure_config_files():
    """
    Ensure configuration files exist by copying example files if needed.
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_dir = os.path.join(base_dir, 'config')
    
    # Create config directory if it doesn't exist
    if not os.path.exists(config_dir):
        os.makedirs(config_dir)
        print(f"Created config directory: {config_dir}")
    
    # Check and copy config.ini if needed
    config_file = os.path.join(config_dir, 'config.ini')
    config_example = os.path.join(config_dir, 'config.ini.example')
    
    if not os.path.exists(config_file) and os.path.exists(config_example):
        shutil.copy(config_example, config_file)
        print(f"Created config.ini from example")
    
    # Check and copy credentials.ini if needed
    cred_file = os.path.join(config_dir, 'credentials.ini')
    cred_example = os.path.join(config_dir, 'credentials.ini.example')
    
    if not os.path.exists(cred_file) and os.path.exists(cred_example):
        shutil.copy(cred_example, cred_file)
        print(f"Created credentials.ini from example")
        # Set secure permissions for credentials file
        try:
            os.chmod(cred_file, 0o600)  # Read/write for owner only
        except Exception as e:
            print(f"Warning: Could not set secure permissions on credentials file: {e}")
    
    # Check if config files exist now
    if os.path.exists(config_file) and os.path.exists(cred_file):
        print("Configuration files are ready")
        return True
    else:
        missing = []
        if not os.path.exists(config_file):
            missing.append("config.ini")
        if not os.path.exists(cred_file):
            missing.append("credentials.ini")
        print(f"Missing configuration files: {', '.join(missing)}")
        return False

if __name__ == "__main__":
    if ensure_config_files():
        sys.exit(0)
    else:
        sys.exit(1)
