#!/usr/bin/env python3
"""
Health monitoring for Nuki Smart Lock Notification System.
Used by Docker healthcheck to verify service status.
"""
import os
import sys
import time
import socket
import logging
import argparse
import requests
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('health_monitor')

def check_file_system():
    """Verify critical directories are accessible and writable."""
    required_dirs = [
        os.environ.get('CONFIG_DIR', '/app/config'),
        os.environ.get('LOGS_DIR', '/app/logs'),
        '/app/data'
    ]
    
    for directory in required_dirs:
        if not os.path.exists(directory):
            logger.error(f"Required directory not found: {directory}")
            return False
        
        # Check write permissions by attempting to create a temp file
        test_file = os.path.join(directory, '.health_check_temp')
        try:
            with open(test_file, 'w') as f:
                f.write('health check')
            os.remove(test_file)
        except Exception as e:
            logger.error(f"Write permission error for {directory}: {e}")
            return False
    
    return True

def check_config_files():
    """Verify required configuration files exist."""
    config_dir = os.environ.get('CONFIG_DIR', '/app/config')
    required_files = [
        os.path.join(config_dir, 'config.ini'),
        os.path.join(config_dir, 'credentials.ini')
    ]
    
    for file_path in required_files:
        if not os.path.exists(file_path):
            logger.error(f"Required configuration file not found: {file_path}")
            return False
    
    return True

def check_monitor_service():
    """Check if the Nuki monitor service is running properly."""
    # Look for PID file
    pid_file = Path('/app/data/nuki_monitor.pid')
    
    if not pid_file.exists():
        logger.error("Monitor service PID file not found")
        return False
    
    # Check process is running
    try:
        pid = int(pid_file.read_text().strip())
        os.kill(pid, 0)  # This will raise an exception if process doesn't exist
        logger.info(f"Monitor service running with PID {pid}")
        return True
    except (ProcessLookupError, ValueError, OSError):
        logger.error("Monitor service not running properly")
        return False

def check_web_service():
    """Check if the web service is accessible."""
    try:
        response = requests.get('http://localhost:5000/health', timeout=5)
        if response.status_code == 200:
            logger.info("Web service is healthy")
            return True
        else:
            logger.error(f"Web service health check failed: {response.status_code}")
            return False
    except requests.RequestException as e:
        logger.error(f"Failed to connect to web service: {e}")
        return False

def check_nuki_api_connection():
    """Verify connectivity to the Nuki API."""
    # We don't actually connect to the API here, just check internet connectivity
    # to avoid unnecessary API calls that might be rate-limited
    try:
        # Try to connect to Nuki's domain to check internet connectivity
        socket.create_connection(("api.nuki.io", 443), timeout=5)
        logger.info("Internet connectivity available for Nuki API access")
        return True
    except OSError as e:
        logger.error(f"Network connectivity issue: {e}")
        return False

def run_health_check(check_service=False, check_web=False):
    """
    Run a comprehensive health check.
    
    Args:
        check_service: Whether to check the monitor service (used by container)
        check_web: Whether to check the web service
    
    Returns:
        bool: True if all checks pass, False otherwise
    """
    checks = [
        ("File system", check_file_system()),
        ("Configuration files", check_config_files()),
        ("Network connectivity", check_nuki_api_connection())
    ]
    
    if check_service:
        checks.append(("Monitor service", check_monitor_service()))
    
    if check_web:
        checks.append(("Web service", check_web_service()))
    
    # Log results
    logger.info("Health check results:")
    all_passed = True
    
    for name, result in checks:
        status = "PASS" if result else "FAIL"
        logger.info(f"  {name}: {status}")
        if not result:
            all_passed = False
    
    return all_passed

def main():
    parser = argparse.ArgumentParser(description='Nuki Smart Lock Notification System Health Monitor')
    parser.add_argument('--check-service', action='store_true', help='Check if the monitor service is running')
    parser.add_argument('--check-web', action='store_true', help='Check if the web service is accessible')
    args = parser.parse_args()
    
    logger.info("Starting health check")
    result = run_health_check(check_service=args.check_service, check_web=args.check_web)
    
    if result:
        logger.info("Health check passed")
        return 0
    else:
        logger.error("Health check failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
