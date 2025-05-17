#!/usr/bin/env python3
import os
import time
import logging
import sys
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(os.environ.get('LOGS_DIR', '/app/logs'), 'nuki_monitor.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('nuki_monitor')

# Add the scripts directory to the Python path
scripts_dir = os.path.dirname(os.path.abspath(__file__))
if scripts_dir not in sys.path:
    sys.path.append(scripts_dir)

# Import the modules
from nuki.config import ConfigManager
from nuki.api import NukiAPI
from nuki.utils import ActivityTracker
from nuki.notification import Notifier

class NukiMonitor:
    def __init__(self):
        # Get base directory
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Initialize components
        self.config = ConfigManager(self.base_dir)
        self.api = NukiAPI(self.config)
        self.tracker = ActivityTracker(self.base_dir)
        self.notifier = Notifier(self.config)
        
        # Flag to indicate first run
        self.first_run = True
        
        logger.info("Nuki Monitor initialized")
    
    def initialize_history(self):
        """Initialize event history without sending notifications"""
        logger.info("Initializing event history...")
        
        # Check for explicit smartlock ID configuration
        if self.config.use_explicit_id and self.config.smartlock_id:
            logger.debug(f"Using explicit smartlock ID: {self.config.smartlock_id}")
            # Create a single-lock array to simulate the API response structure
            locks = [{
                'smartlockId': self.config.smartlock_id,
                'name': 'Configured Lock'  # Default name when using explicit ID
            }]
        else:
            # Get locks dynamically from API
            locks = self.api.get_smartlocks()
            if not locks:
                logger.error("No smartlocks found")
                return False
        
        for lock in locks:
            lock_id = lock.get('smartlockId')
            lock_name = lock.get('name', 'Unknown Lock')
            
            # Get current activity - use larger limit for initial history
            current_activity = self.api.get_smartlock_logs(lock_id, limit=20)
            if not current_activity:
                logger.warning(f"No activity logs found for lock {lock_name}")
                continue
            
            # Just save the activity without processing notifications
            self.tracker.save_activity(current_activity)
            logger.info(f"Initialized history for lock {lock_name} with {len(current_activity)} events")
        
        return True
    
    def check_new_activity(self):
        """Check for new activity and generate notifications if needed"""
        # Special handling for first run
        if self.first_run:
            logger.info("First run detected, initializing event history without sending notifications")
            self.initialize_history()
            self.first_run = False
            return True
        
        logger.info("Checking for new activity...")
        
        # Check for explicit smartlock ID configuration
        if self.config.use_explicit_id and self.config.smartlock_id:
            logger.debug(f"Using explicit smartlock ID: {self.config.smartlock_id}")
            # Create a single-lock array to simulate the API response structure
            locks = [{
                'smartlockId': self.config.smartlock_id,
                'name': 'Configured Lock'  # Default name when using explicit ID
            }]
        else:
            # Get locks dynamically from API
            locks = self.api.get_smartlocks()
            if not locks:
                logger.error("No smartlocks found")
                return False
        
        new_events = []
        
        for lock in locks:
            lock_id = lock.get('smartlockId')
            lock_name = lock.get('name', 'Unknown Lock')
            
            # Get current activity
            current_activity = self.api.get_smartlock_logs(lock_id, limit=5)
            if not current_activity:
                logger.warning(f"No activity logs found for lock {lock_name}")
                continue
            
            # Process new events
            for event in current_activity:
                # Skip if we've seen this event before
                if self.tracker.is_event_processed(event):
                    continue
                    
                # Extract event details
                event_id = event.get('id')
                event_type = event.get('name', 'Unknown Action')
                action = event.get('action')
                trigger = event.get('trigger')
                auth_id = event.get('authId')
                date = self.api.parse_date(event.get('date'))
                
                if not date:
                    continue
                
                # Get action description
                action_description = self.api.get_action_description(event)
                
                # Get user name if available
                user_name = "Auto Lock"  # Default for auto lock events
                
                # Special handling for trigger 6 (auto lock)
                if trigger == 6:
                    user_name = "Auto Lock"
                else:
                    user_name = self.api.get_user_name(auth_id) if auth_id else "Unknown User"
                
                # Create event record
                event_record = {
                    'lock_name': lock_name,
                    'lock_id': lock_id,
                    'event_type': action_description,  # Use improved action description
                    'action': action,
                    'trigger': trigger,
                    'user_name': user_name,
                    'date': date.strftime('%Y-%m-%d %H:%M:%S'),
                    'event_id': event_id
                }
                
                new_events.append(event_record)
                logger.info(f"New event: {action_description} by {user_name} at {event_record['date']}")
            
            # Save the current activity as last activity
            self.tracker.save_activity(current_activity)
        
        # Send notifications for new events
        if new_events:
            if self.config.digest_mode:
                # Add to digest queue
                for event in new_events:
                    self.notifier.add_to_digest(event)
            else:
                # Send immediate notifications
                for event in new_events:
                    self.notifier.send_notification(event)
        
        return True
    
    def run(self):
        """Run the monitor in a continuous loop"""
        logger.info("Starting Nuki Monitor")
        
        try:
            while True:
                self.check_new_activity()
                time.sleep(self.config.polling_interval)
        except KeyboardInterrupt:
            logger.info("Monitor stopped by user")
        except Exception as e:
            logger.error(f"Error in monitor: {e}")
            raise

if __name__ == "__main__":
    monitor = NukiMonitor()
    monitor.run()
