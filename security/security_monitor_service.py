#!/usr/bin/env python3
"""
Security Monitoring Service for Nuki Smart Lock

This script runs the security monitoring as a standalone service
or can be integrated with the main Nuki notification system.
"""

import os
import sys
import logging
import time
import json
from datetime import datetime, timedelta

# Add parent directory to path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# Import security modules
from security.security_monitor import SecurityMonitor
from security.security_alerter import SecurityAlerter
from security.security_config import SecurityConfigManager

# Import from main Nuki modules
from nuki.config import ConfigManager
from nuki.api import NukiAPI
from nuki.utils import ActivityTracker

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.expanduser("~/nukiweb/logs/nuki_security_service.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('nuki_security_service')

class SecurityMonitorService:
    """
    Service to run security monitoring and alerting.
    """
    
    def __init__(self):
        """Initialize the security monitoring service."""
        # Get base directory
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Load configuration
        self.config = ConfigManager(self.base_dir)
        self.security_config = SecurityConfigManager(self.base_dir)
        
        # Initialize components
        self.api = NukiAPI(self.config)
        self.tracker = ActivityTracker(self.base_dir)
        
        # Create security components
        self.alerter = SecurityAlerter(self.config)
        self.monitor = SecurityMonitor(self.config, self.handle_security_alert)
        
        # Track last checked time
        self.last_check_time = datetime.now() - timedelta(minutes=5)
        
        logger.info("Security Monitor Service initialized")
    
    def handle_security_alert(self, alert_data):
        """
        Handle a security alert from the monitor.
        
        Args:
            alert_data: Alert data dictionary
        """
        # Log alert
        alert_type = alert_data.get('type', 'unknown')
        logger.warning(f"Security alert triggered: {alert_type}")
        
        # Send alert via alerter
        self.alerter.send_alert(alert_data)
    
    def check_activity(self):
        """Check for new activity and process through security monitor."""
        logger.info("Checking for new activity...")
        
        try:
            # Get all lock IDs
            locks = self.api.get_smartlocks()
            if not locks:
                logger.error("No smartlocks found")
                return
            
            # Process events for each lock
            for lock in locks:
                lock_id = lock.get('smartlockId')
                lock_name = lock.get('name', 'Unknown Lock')
                
                # Get activity since last check
                activity = self.api.get_smartlock_logs(lock_id, limit=10)
                
                # Process each event through security monitor
                for event in activity:
                    # Parse date
                    date_str = event.get('date')
                    date = self.api.parse_date(date_str)
                    
                    # Skip events before last check
                    if date and date <= self.last_check_time:
                        continue
                    
                    # Process event data
                    event_id = event.get('id')
                    action = event.get('action')
                    trigger = event.get('trigger')
                    auth_id = event.get('authId')
                    
                    # Get action description
                    action_description = "Unknown"
                    if hasattr(self.api, 'get_action_description'):
                        action_description = self.api.get_action_description(event)
                    
                    # Get user name if available
                    user_name = "Auto Lock" if trigger == 6 else self.api.get_user_name(auth_id) if auth_id else "Unknown User"
                    
                    # Create event record for security monitor
                    event_record = {
                        'id': event_id,
                        'lock_name': lock_name,
                        'lock_id': lock_id,
                        'event_type': action_description,
                        'action': action,
                        'trigger': trigger,
                        'user_name': user_name,
                        'date': date.strftime('%Y-%m-%d %H:%M:%S') if date else datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'auth_id': auth_id
                    }
                    
                    # Process through security monitor
                    self.monitor.process_event(event_record)
            
            # Update last check time
            self.last_check_time = datetime.now()
        
        except Exception as e:
            logger.error(f"Error checking activity: {e}")
    
    def run(self):
        """Run the security monitoring service."""
        logger.info("Starting Security Monitor Service")
        
        # Check if security monitoring is enabled
        if not self.security_config.enabled:
            logger.warning("Security monitoring is disabled in configuration")
            return
        
        try:
            # Main service loop
            while True:
                # Check for new activity
                self.check_activity()
                
                # Sleep until next check
                time.sleep(self.config.polling_interval)
        except KeyboardInterrupt:
            logger.info("Security Monitor Service stopped by user")
        except Exception as e:
            logger.error(f"Error in Security Monitor Service: {e}")
            raise

# Main function
def main():
    """Main function to run the security monitor service."""
    service = SecurityMonitorService()
    service.run()

# Run when executed directly
if __name__ == "__main__":
    main()
