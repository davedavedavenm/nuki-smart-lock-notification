"""
Notification dispatcher module for Nuki Smart Lock Notification System.
Coordinates different notification services and handles notification routing.
"""
import logging
import importlib
from datetime import datetime
from pathlib import Path

logger = logging.getLogger('nuki_monitor')

class NotificationDispatcher:
    """
    Central notification dispatcher that coordinates between different notification services.
    Handles notification routing, filtering, and digest management.
    """
    
    def __init__(self, config):
        """
        Initialize the notification dispatcher.
        
        Args:
            config: Configuration object with notification settings
        """
        self.config = config
        self.digest_events = []
        self.last_digest_time = datetime.now()
        self.notification_services = {}
        
        # Initialize notification services based on configuration
        self._initialize_services()
    
    def _initialize_services(self):
        """Initialize enabled notification services based on configuration."""
        if self.config.notification_type in ['email', 'both']:
            try:
                from app.notifications.email_service import EmailService
                self.notification_services['email'] = EmailService(self.config)
                logger.info("Email notification service initialized")
            except Exception as e:
                logger.error(f"Failed to initialize email service: {e}")
        
        if self.config.notification_type in ['telegram', 'both']:
            try:
                from app.notifications.telegram_service import TelegramService
                self.notification_services['telegram'] = TelegramService(self.config)
                logger.info("Telegram notification service initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Telegram service: {e}")
    
    def send_notification(self, event):
        """
        Send an immediate notification for a single event.
        
        Args:
            event: Event data dictionary
            
        Returns:
            bool: True if notification was sent successfully, False otherwise
        """
        logger.info(f"Dispatching notification for {event['event_type']} by {event['user_name']}")
        
        # Check if we should filter this event
        if self._should_filter_event(event):
            logger.info(f"Event filtered: {event['event_type']} by {event['user_name']}")
            return False
        
        # Prepare notification content
        notification_data = {
            'subject': f"{self.config.email_subject_prefix}: {event['event_type']} by {event['user_name']}",
            'event': event,
            'is_digest': False
        }
        
        # Dispatch to enabled services
        return self._dispatch_to_services(notification_data)
    
    def add_to_digest(self, event):
        """
        Add an event to the digest queue.
        
        Args:
            event: Event data dictionary
        """
        # Check if we should filter this event
        if self._should_filter_event(event):
            logger.info(f"Event filtered from digest: {event['event_type']} by {event['user_name']}")
            return
            
        self.digest_events.append(event)
        
        # Check if it's time to send digest
        time_since_digest = datetime.now() - self.last_digest_time
        if time_since_digest.total_seconds() >= self.config.digest_interval:
            self.send_digest_notification()
    
    def send_digest_notification(self):
        """
        Send a digest notification with all events since last digest.
        
        Returns:
            bool: True if digest was sent successfully, False otherwise
        """
        if not self.digest_events:
            logger.info("No events to send in digest")
            return True
            
        logger.info(f"Sending digest notification with {len(self.digest_events)} events")
        
        # Sort events by date, newest first
        sorted_events = sorted(
            self.digest_events, 
            key=lambda x: datetime.strptime(x['date'], '%Y-%m-%d %H:%M:%S'),
            reverse=True
        )
        
        # Prepare notification content
        notification_data = {
            'subject': f"{self.config.email_subject_prefix}: Activity Digest - {len(sorted_events)} events",
            'events': sorted_events,
            'is_digest': True
        }
        
        # Dispatch to enabled services
        success = self._dispatch_to_services(notification_data)
        
        # Reset digest regardless of send success to prevent repeated failures
        self.digest_events = []
        self.last_digest_time = datetime.now()
        
        return success
    
    def _dispatch_to_services(self, notification_data):
        """
        Dispatch notification to all enabled services.
        
        Args:
            notification_data: Dictionary with notification content
            
        Returns:
            bool: True if all enabled services succeeded, False otherwise
        """
        if not self.notification_services:
            logger.error("No notification services configured")
            return False
        
        success = True
        for service_name, service in self.notification_services.items():
            try:
                if notification_data['is_digest']:
                    service_success = service.send_digest(
                        notification_data['subject'], 
                        notification_data['events']
                    )
                else:
                    service_success = service.send_notification(
                        notification_data['subject'], 
                        notification_data['event']
                    )
                
                if not service_success:
                    logger.error(f"{service_name.capitalize()} notification failed")
                    success = False
            except Exception as e:
                logger.error(f"Error in {service_name} service: {e}")
                success = False
                
        return success
    
    def _should_filter_event(self, event):
        """
        Check if an event should be filtered based on configuration settings.
        
        Args:
            event: Event data dictionary
            
        Returns:
            bool: True if event should be filtered out, False otherwise
        """
        # Auto-lock filtering
        if event['user_name'] == "Auto Lock" and not self.config.notify_auto_lock:
            return True
            
        # User filtering
        if event['user_name'] in self.config.excluded_users:
            return True
            
        # Action filtering
        if 'action' in event and str(event['action']) in self.config.excluded_actions:
            return True
            
        # Trigger filtering
        if 'trigger' in event and str(event['trigger']) in self.config.excluded_triggers:
            return True
            
        return False
