#!/usr/bin/env python3
"""
Security Monitoring Module for Nuki Smart Lock

This module monitors activity and detects suspicious patterns that could
indicate security issues. It works alongside the main notification system
to provide enhanced security alerting.
"""

import os
import sys
import logging
import json
import time
from datetime import datetime, timedelta
from collections import defaultdict, deque

# Add parent directory to path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# Import from main Nuki modules
from nuki.config import ConfigManager

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.expanduser("~/nukiweb/logs/nuki_security.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('nuki_security')

class SecurityMonitor:
    """
    Monitor for detecting suspicious activity patterns and generating security alerts.
    """
    
    def __init__(self, config_manager=None, alert_callback=None):
        """
        Initialize the security monitor.
        
        Args:
            config_manager: ConfigManager instance or None to create new one
            alert_callback: Function to call when an alert is triggered
        """
        # Get base directory
        self.base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        # Get config manager
        self.config = config_manager or ConfigManager(self.base_dir)
        
        # Set alert callback
        self.alert_callback = alert_callback
        
        # Initialize activity tracking
        self.recent_activity = deque(maxlen=100)  # Store recent activity
        self.failed_attempts = defaultdict(list)  # Store failed attempts per user/device
        self.access_events = defaultdict(list)    # Store access events per user/device
        
        # Load security settings
        self._load_security_settings()
        
        logger.info("Security Monitor initialized")
    
    def _load_security_settings(self):
        """Load security settings from configuration."""
        # Default thresholds
        self.failed_attempts_threshold = 3
        self.failed_attempts_window = 300  # 5 minutes
        self.unusual_hour_start = 23       # 11 PM
        self.unusual_hour_end = 6          # 6 AM
        self.rapid_access_threshold = 5
        self.rapid_access_window = 60      # 1 minute
        
        # Try to load from config
        if hasattr(self.config, 'config') and 'Security' in self.config.config:
            security_config = self.config.config['Security']
            self.failed_attempts_threshold = security_config.getint('failed_attempts_threshold', 3)
            self.failed_attempts_window = security_config.getint('failed_attempts_window', 300)
            self.unusual_hour_start = security_config.getint('unusual_hour_start', 23)
            self.unusual_hour_end = security_config.getint('unusual_hour_end', 6)
            self.rapid_access_threshold = security_config.getint('rapid_access_threshold', 5)
            self.rapid_access_window = security_config.getint('rapid_access_window', 60)
        
        logger.info(f"Security settings loaded: failed_threshold={self.failed_attempts_threshold}, "
                   f"unusual_hours={self.unusual_hour_start}-{self.unusual_hour_end}")
    
    def process_event(self, event):
        """
        Process a new event and check for security issues.
        
        Args:
            event: Event dictionary containing event details
        
        Returns:
            None, but may trigger security alerts via callback
        """
        # Add to recent activity
        self.recent_activity.append(event)
        
        # Extract event details
        event_id = event.get('id')
        event_type = event.get('event_type', '')
        action = event.get('action')
        user_name = event.get('user_name', 'Unknown User')
        date_str = event.get('date')
        
        # Parse date
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
        except (ValueError, TypeError):
            logger.warning(f"Invalid date format in event: {date_str}")
            date = datetime.now()
        
        # Check if this is a failed attempt
        if self._is_failed_attempt(event):
            self._handle_failed_attempt(event, user_name, date)
        
        # Check for access during unusual hours
        if self._is_unusual_hour(date):
            self._handle_unusual_hour_access(event, user_name, date)
        
        # Track access events for rapid access detection
        self._track_access_event(event, user_name, date)
        
        # Clean up old entries periodically
        self._cleanup_old_entries()
    
    def _is_failed_attempt(self, event):
        """
        Determine if an event represents a failed access attempt.
        
        Args:
            event: Event dictionary
            
        Returns:
            bool: True if this is a failed attempt
        """
        # Look for failed unlock attempts, denied access, etc.
        action = event.get('action')
        event_type = event.get('event_type', '').lower()
        
        # Check for specific failure indicators
        return ('failed' in event_type or 
                'denied' in event_type or 
                'rejected' in event_type or
                'invalid' in event_type)
    
    def _handle_failed_attempt(self, event, user_name, date):
        """
        Handle a failed access attempt and check for security issues.
        
        Args:
            event: Event dictionary
            user_name: Name of the user
            date: Datetime of the event
        """
        # Add to failed attempts list
        self.failed_attempts[user_name].append(date)
        
        # Check for multiple failed attempts
        recent_failures = [d for d in self.failed_attempts[user_name] 
                          if date - d < timedelta(seconds=self.failed_attempts_window)]
        
        if len(recent_failures) >= self.failed_attempts_threshold:
            # This is a security concern - multiple failed attempts
            alert_message = (f"Security Alert: Multiple failed access attempts detected for {user_name}. "
                            f"{len(recent_failures)} attempts in the last "
                            f"{self.failed_attempts_window // 60} minutes.")
            
            logger.warning(alert_message)
            self._trigger_alert(alert_message, "failed_attempts", event, user_name)
    
    def _is_unusual_hour(self, date):
        """
        Check if the time is within the unusual hours range.
        
        Args:
            date: Datetime to check
            
        Returns:
            bool: True if time is within unusual hours
        """
        hour = date.hour
        
        if self.unusual_hour_start > self.unusual_hour_end:
            # Range spans midnight (e.g., 23-6)
            return hour >= self.unusual_hour_start or hour < self.unusual_hour_end
        else:
            # Normal range (e.g., 1-5)
            return hour >= self.unusual_hour_start and hour < self.unusual_hour_end
    
    def _handle_unusual_hour_access(self, event, user_name, date):
        """
        Handle access during unusual hours.
        
        Args:
            event: Event dictionary
            user_name: Name of the user
            date: Datetime of the event
        """
        # Check if this is an actual access event (not just a status check)
        if event.get('event_type', '').lower() in ['unlock', 'unlatch']:
            alert_message = (f"Security Notice: Access during unusual hours by {user_name}. "
                           f"Time: {date.strftime('%H:%M:%S')}")
            
            logger.info(alert_message)
            self._trigger_alert(alert_message, "unusual_hours", event, user_name)
    
    def _track_access_event(self, event, user_name, date):
        """
        Track access events to detect rapid multiple accesses.
        
        Args:
            event: Event dictionary
            user_name: Name of the user
            date: Datetime of the event
        """
        # Only track actual access events
        if event.get('event_type', '').lower() in ['unlock', 'unlatch', 'lock']:
            # Add to access events list
            self.access_events[user_name].append(date)
            
            # Check for rapid access
            recent_access = [d for d in self.access_events[user_name] 
                            if date - d < timedelta(seconds=self.rapid_access_window)]
            
            if len(recent_access) >= self.rapid_access_threshold:
                # This is unusual - rapid multiple access
                alert_message = (f"Security Notice: Rapid multiple access events detected. "
                               f"{len(recent_access)} events in the last "
                               f"{self.rapid_access_window // 60} minutes by {user_name}.")
                
                logger.info(alert_message)
                self._trigger_alert(alert_message, "rapid_access", event, user_name)
    
    def _cleanup_old_entries(self):
        """Clean up old entries from tracking dictionaries."""
        now = datetime.now()
        
        # Clean up failed attempts
        for user in list(self.failed_attempts.keys()):
            self.failed_attempts[user] = [d for d in self.failed_attempts[user] 
                                        if now - d < timedelta(seconds=self.failed_attempts_window * 2)]
            
            # Remove empty lists
            if not self.failed_attempts[user]:
                del self.failed_attempts[user]
        
        # Clean up access events
        for user in list(self.access_events.keys()):
            self.access_events[user] = [d for d in self.access_events[user] 
                                      if now - d < timedelta(seconds=self.rapid_access_window * 2)]
            
            # Remove empty lists
            if not self.access_events[user]:
                del self.access_events[user]
    
    def _trigger_alert(self, message, alert_type, event, user_name):
        """
        Trigger a security alert.
        
        Args:
            message: Alert message
            alert_type: Type of alert
            event: Original event
            user_name: Name of the user
        """
        # Create alert data
        alert_data = {
            'message': message,
            'type': alert_type,
            'event': event,
            'user': user_name,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'priority': 'high'
        }
        
        # Save alert to log file
        self._save_alert(alert_data)
        
        # Call callback if available
        if self.alert_callback:
            self.alert_callback(alert_data)
    
    def _save_alert(self, alert_data):
        """
        Save alert to a log file.
        
        Args:
            alert_data: Alert data dictionary
        """
        alerts_log_path = os.path.join(self.base_dir, "logs", "security_alerts.json")
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(alerts_log_path), exist_ok=True)
        
        # Load existing alerts or create new list
        alerts = []
        if os.path.exists(alerts_log_path):
            try:
                with open(alerts_log_path, 'r') as f:
                    alerts = json.load(f)
            except json.JSONDecodeError:
                # File exists but is not valid JSON
                alerts = []
        
        # Add new alert
        alerts.append(alert_data)
        
        # Save to file
        with open(alerts_log_path, 'w') as f:
            json.dump(alerts, f, indent=2)

# Example usage when run directly
if __name__ == "__main__":
    # Create a test event
    test_event = {
        'id': '123456',
        'event_type': 'unlock',
        'action': 1,
        'user_name': 'Test User',
        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'lock_name': 'Front Door'
    }
    
    # Create security monitor
    monitor = SecurityMonitor()
    
    # Process event
    monitor.process_event(test_event)
    
    print("Security monitor test complete. Check logs for output.")
