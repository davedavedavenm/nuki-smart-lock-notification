#!/usr/bin/env python3
"""
Command-line entry point for Nuki Smart Lock Notification System.
Provides a simplified interface for starting and managing the monitor service.
"""
import os
import sys
import argparse
import logging
import signal
import time
from pathlib import Path

# Add the parent directory to sys.path to allow importing app packages
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

# Import application modules
from app.monitoring.nuki_monitor import NukiMonitor
from app.config.config_manager import ConfigManager
from app.utils.check_permissions import check_file_permissions

# Configure logging
def setup_logging(log_level, log_file=None):
    """Set up logging configuration."""
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Configure root logger
    level = getattr(logging, log_level.upper())
    
    # Create logs directory if it doesn't exist
    if log_file:
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
    
    logging.basicConfig(
        level=level,
        format=log_format,
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_file) if log_file else logging.NullHandler()
        ]
    )
    
    # Suppress verbose logging from external libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    
    return logging.getLogger('nuki_monitor')

# Daemon and process management
def create_pid_file(pid_file):
    """Create a PID file for the running process."""
    try:
        with open(pid_file, 'w') as f:
            f.write(str(os.getpid()))
        return True
    except Exception as e:
        logging.error(f"Failed to create PID file: {e}")
        return False

def remove_pid_file(pid_file):
    """Remove the PID file when the process exits."""
    try:
        if os.path.exists(pid_file):
            os.remove(pid_file)
    except Exception as e:
        logging.error(f"Failed to remove PID file: {e}")

def signal_handler(signum, frame):
    """Handle termination signals."""
    logging.info(f"Received signal {signum}, shutting down...")
    sys.exit(0)

# Main CLI entry point
def main():
    """Main entry point for the CLI application."""
    parser = argparse.ArgumentParser(description='Nuki Smart Lock Notification System')
    
    # Core command line options
    parser.add_argument('--config-dir', help='Configuration directory')
    parser.add_argument('--logs-dir', help='Logs directory')
    parser.add_argument('--data-dir', help='Data directory')
    parser.add_argument('--pid-file', help='PID file location')
    parser.add_argument('--log-level', default='INFO', 
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                       help='Logging level')
    parser.add_argument('--mode', choices=['foreground', 'daemon'], default='foreground',
                       help='Run mode')
    
    # Subcommands
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Run command
    run_parser = subparsers.add_parser('run', help='Run the monitor service')
    
    # Config command
    config_parser = subparsers.add_parser('config', help='Configure the system')
    config_parser.add_argument('--show', action='store_true', help='Show current configuration')
    config_parser.add_argument('--reset', action='store_true', help='Reset configuration to defaults')
    config_parser.add_argument('--update', nargs=3, metavar=('SECTION', 'OPTION', 'VALUE'),
                              help='Update a configuration value')
    
    # Check command
    check_parser = subparsers.add_parser('check', help='Check system status')
    check_parser.add_argument('--permissions', action='store_true', 
                             help='Check file permissions')
    check_parser.add_argument('--dependencies', action='store_true', 
                             help='Check dependencies')
    check_parser.add_argument('--all', action='store_true', 
                             help='Run all checks')
    
    # Parse arguments
    args = parser.parse_args()
    
    # Determine directories and files
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_dir = args.config_dir or os.environ.get('CONFIG_DIR') or os.path.join(base_dir, 'config')
    logs_dir = args.logs_dir or os.environ.get('LOGS_DIR') or os.path.join(base_dir, 'logs')
    data_dir = args.data_dir or os.environ.get('DATA_DIR') or os.path.join(base_dir, 'data')
    
    # Create directories if they don't exist
    os.makedirs(config_dir, exist_ok=True)
    os.makedirs(logs_dir, exist_ok=True)
    os.makedirs(data_dir, exist_ok=True)
    
    # Set up file paths
    config_file = os.path.join(config_dir, 'config.ini')
    credentials_file = os.path.join(config_dir, 'credentials.ini')
    log_file = os.path.join(logs_dir, 'nuki_monitor.log')
    pid_file = args.pid_file or os.path.join(data_dir, 'nuki_monitor.pid')
    
    # Set up logging
    logger = setup_logging(args.log_level, log_file)
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Handle commands
    if args.command == 'run':
        run_monitor(config_dir, config_file, credentials_file, pid_file, data_dir, logger)
    elif args.command == 'config':
        handle_config(args, config_file, credentials_file, logger)
    elif args.command == 'check':
        run_checks(args, config_dir, logger)
    else:
        # Default to showing help
        parser.print_help()
        return 1
    
    return 0

def run_monitor(config_dir, config_file, credentials_file, pid_file, data_dir, logger):
    """Run the Nuki monitor service."""
    logger.info("Starting Nuki Smart Lock Notification System")
    
    # Create PID file
    if not create_pid_file(pid_file):
        logger.error("Failed to create PID file, exiting")
        return 1
    
    try:
        # Initialize configuration
        config_manager = ConfigManager(config_dir)
        
        # Check file permissions
        permission_issues = check_file_permissions([config_file, credentials_file])
        if permission_issues:
            for file, issue in permission_issues.items():
                logger.warning(f"Permission issue with {file}: {issue}")
        
        # Initialize and run monitor
        monitor = NukiMonitor(config_manager)
        
        # Start the monitoring loop
        logger.info("Monitor service started")
        monitor.run()
    except KeyboardInterrupt:
        logger.info("Interrupted by user, shutting down...")
    except Exception as e:
        logger.error(f"Error running monitor: {e}", exc_info=True)
    finally:
        # Clean up
        remove_pid_file(pid_file)
        logger.info("Monitor service stopped")
    
    return 0

def handle_config(args, config_file, credentials_file, logger):
    """Handle configuration-related commands."""
    # Import here to avoid circular imports
    from app.config.configure import get_config_value, update_config, reset_config
    
    if args.show:
        # Show configuration
        logger.info("Current configuration:")
        
        # Check if config files exist
        config_exists = os.path.exists(config_file)
        credentials_exist = os.path.exists(credentials_file)
        
        if not config_exists and not credentials_exist:
            logger.info("No configuration files found")
            return 0
        
        # Show general configuration (not credentials)
        if config_exists:
            with open(config_file, 'r') as f:
                for line in f:
                    print(line.rstrip())
        
        # Just show if credentials exist, not the actual values
        if credentials_exist:
            logger.info("\nCredentials file exists")
            
    elif args.reset:
        # Reset configuration
        if reset_config(config_file):
            logger.info("Configuration reset to defaults")
        else:
            logger.error("Failed to reset configuration")
            
    elif args.update:
        # Update configuration
        section, option, value = args.update
        if update_config(config_file, section, option, value):
            logger.info(f"Updated {section}.{option} to {value}")
        else:
            logger.error(f"Failed to update {section}.{option}")
    
    return 0

def run_checks(args, config_dir, logger):
    """Run system checks."""
    all_checks_passed = True
    
    # Check file permissions
    if args.permissions or args.all:
        logger.info("Checking file permissions...")
        
        # Get all configuration files
        config_files = [os.path.join(config_dir, f) for f in os.listdir(config_dir) 
                        if os.path.isfile(os.path.join(config_dir, f))]
        
        permission_issues = check_file_permissions(config_files)
        if permission_issues:
            for file, issue in permission_issues.items():
                logger.warning(f"Permission issue with {file}: {issue}")
            all_checks_passed = False
        else:
            logger.info("File permissions check passed")
    
    # Check dependencies
    if args.dependencies or args.all:
        logger.info("Checking dependencies...")
        
        try:
            # Get the scripts directory
            scripts_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'scripts')
            check_script = os.path.join(scripts_dir, 'check_dependencies.py')
            
            if os.path.exists(check_script):
                # Execute the dependency check script
                import subprocess
                result = subprocess.run([sys.executable, check_script], 
                                       capture_output=True, text=True)
                
                print(result.stdout)
                if result.returncode != 0:
                    logger.warning("Dependency check failed")
                    all_checks_passed = False
                else:
                    logger.info("Dependency check passed")
            else:
                logger.warning(f"Dependency check script not found at {check_script}")
                all_checks_passed = False
        except Exception as e:
            logger.error(f"Error checking dependencies: {e}")
            all_checks_passed = False
    
    # Report overall status
    if all_checks_passed:
        logger.info("All checks passed")
    else:
        logger.warning("Some checks failed")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
