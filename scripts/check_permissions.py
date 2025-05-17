#!/usr/bin/env python3
"""
Permission Check Script
Checks if the application has the necessary file system permissions
before startup to provide clear error messages and prevent repeated crashes.

Should be called at the beginning of the entrypoint scripts.
"""

import os
import sys
import logging

def setup_logging():
    """Configure logging to console"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s: %(message)s',
        handlers=[logging.StreamHandler()]
    )
    return logging.getLogger('permission_check')

def check_directory_writable(directory, logger, critical=True):
    """Check if a directory exists and is writable"""
    if not os.path.exists(directory):
        try:
            os.makedirs(directory, exist_ok=True)
            logger.info(f"Created directory: {directory}")
        except (PermissionError, IOError) as e:
            logger.error(f"❌ Cannot create directory {directory}: {e}")
            if critical:
                return False
    
    # Check write permissions with a more reliable method by attempting to create a test file
    test_file = os.path.join(directory, ".permission_test")
    try:
        with open(test_file, 'w') as f:
            f.write("test")
        os.remove(test_file)
        logger.info(f"✅ Directory is writable: {directory}")
        return True
    except (PermissionError, IOError) as e:
        logger.error(f"❌ Directory is not writable: {directory}")
        logger.error(f"  Error: {e}")
        if critical:
            return False
        return False

def check_file_readable(file_path, logger, critical=True):
    """Check if a file exists and is readable"""
    if not os.path.exists(file_path):
        logger.warning(f"⚠️ File does not exist: {file_path}")
        return True  # File doesn't exist yet, but that might be OK
    
    try:
        with open(file_path, 'r') as f:
            # Just try to read a byte to verify access
            f.read(1)
        logger.info(f"✅ File is readable: {file_path}")
        return True
    except (PermissionError, IOError) as e:
        logger.error(f"❌ File is not readable: {file_path}")
        logger.error(f"  Error: {e}")
        if critical:
            return False
        return False

def print_permission_fix_instructions():
    """Print instructions for fixing permission issues"""
    print("\n" + "=" * 80)
    print("PERMISSION ERROR: The application cannot access required files or directories.")
    print("=" * 80)
    print("\nTo fix this issue, run these commands on your host system:\n")
    print("# Create directories if they don't exist")
    print("mkdir -p config logs data")
    print("")
    print("# Set directory permissions to allow the Docker container user to write")
    print("chmod -R 777 logs data")
    print("chmod 777 config")
    print("")
    print("# If config files exist, ensure they're readable")
    print("chmod 644 config/config.ini config/credentials.ini")
    print("\nSee DOCKER_SETUP.md and TROUBLESHOOTING.md for more information.")
    print("=" * 80 + "\n")

def check_all_permissions():
    """Check all required permissions and exit if critical checks fail"""
    logger = setup_logging()
    logger.info("Checking permissions for Nuki Smart Lock Notification System...")
    
    # Determine directories based on environment or defaults
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_dir = os.environ.get('CONFIG_DIR', os.path.join(base_dir, 'config'))
    logs_dir = os.environ.get('LOGS_DIR', os.path.join(base_dir, 'logs'))
    data_dir = os.path.join(base_dir, 'data')
    
    # Check critical writable directories
    directories_ok = True
    if not check_directory_writable(config_dir, logger, critical=True):
        directories_ok = False
    if not check_directory_writable(logs_dir, logger, critical=True):
        directories_ok = False
    if not check_directory_writable(data_dir, logger, critical=True):
        directories_ok = False
        
    # Check important readable files
    files_ok = True
    config_file = os.path.join(config_dir, 'config.ini')
    credentials_file = os.path.join(config_dir, 'credentials.ini')
    
    if os.path.exists(credentials_file) and not check_file_readable(credentials_file, logger, critical=True):
        files_ok = False
    if os.path.exists(config_file) and not check_file_readable(config_file, logger, critical=True):
        files_ok = False
    
    # If any critical checks failed, print instructions and exit
    if not directories_ok or not files_ok:
        print_permission_fix_instructions()
        return False
    
    logger.info("✅ All permission checks passed!")
    return True

if __name__ == "__main__":
    success = check_all_permissions()
    sys.exit(0 if success else 1)
