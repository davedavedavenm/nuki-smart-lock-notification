#!/usr/bin/env python3
"""
Security Alerter Module for Nuki Smart Lock

This module handles the generation and delivery of security alerts
through the notification system with special formatting and priority.
"""

import os
import sys
import logging
import json
from datetime import datetime

# Add parent directory to path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# Import from main Nuki modules
from nuki.config import ConfigManager
from nuki.notification import Notifier

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.expanduser("~/nukiweb/logs/nuki_security_alerts.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('nuki_security_alerts')

class SecurityAlerter:
    """
    Handles the generation and delivery of security alerts.
    """
    
    def __init__(self, config_manager=None):
        """
        Initialize the security alerter.
        
        Args:
            config_manager: ConfigManager instance or None to create new one
        """
        # Get base directory
        self.base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        # Get config manager
        self.config = config_manager or ConfigManager(self.base_dir)
        
        # Create notifier
        self.notifier = Notifier(self.config)
        
        # Load alert settings
        self._load_alert_settings()
        
        logger.info("Security Alerter initialized")
    
    def _load_alert_settings(self):
        """Load alert settings from configuration."""
        # Default settings
        self.alert_priority = "high"
        self.alert_sound = True
        self.notify_owner_only = True
        self.include_evidence = True
        
        # Try to load from config
        if hasattr(self.config, 'config') and 'Security' in self.config.config:
            security_config = self.config.config['Security']
            self.alert_priority = security_config.get('alert_priority', 'high')
            self.alert_sound = security_config.getboolean('alert_sound', True)
            self.notify_owner_only = security_config.getboolean('notify_owner_only', True)
            self.include_evidence = security_config.getboolean('include_evidence', True)
        
        logger.info(f"Alert settings loaded: priority={self.alert_priority}, "
                   f"sound={self.alert_sound}, owner_only={self.notify_owner_only}")
    
    def send_alert(self, alert_data):
        """
        Send a security alert notification.
        
        Args:
            alert_data: Dictionary containing alert information
        
        Returns:
            bool: True if alert was sent successfully
        """
        # Extract alert details
        message = alert_data.get('message', 'Security Alert')
        alert_type = alert_data.get('type', 'unknown')
        event = alert_data.get('event', {})
        user = alert_data.get('user', 'Unknown User')
        timestamp = alert_data.get('timestamp', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        
        # Log the alert
        logger.warning(f"Sending security alert: {message}")
        
        # Create notification subject
        subject = f"⚠️ SECURITY ALERT: {alert_type.replace('_', ' ').title()}"
        
        # Create notification data
        notification_data = {
            'lock_name': event.get('lock_name', 'Unknown Lock'),
            'lock_id': event.get('lock_id', ''),
            'event_type': f"SECURITY: {alert_type.replace('_', ' ').title()}",
            'user_name': user,
            'date': timestamp,
            'trigger': event.get('trigger', ''),
            'message': message,
            'priority': self.alert_priority,
            'security_alert': True
        }
        
        # Send notification
        return self.send_security_notification(subject, notification_data)
    
    def send_security_notification(self, subject, data):
        """
        Send a specially formatted security notification.
        
        Args:
            subject: Notification subject
            data: Notification data dictionary
            
        Returns:
            bool: True if notification was sent successfully
        """
        try:
            # Create email body with security formatting
            email_body = self._create_security_email(data)
            
            # Create Telegram message with security formatting
            telegram_msg = self._create_security_telegram(data)
            
            # Determine recipients
            recipients = self._get_security_recipients()
            
            # Send through normal notification channels with security formatting
            success = True
            
            # Send email
            if self.config.notification_type in ['email', 'both']:
                email_success = self.notifier.send_email(subject, email_body, recipients.get('email', None))
                success = success and email_success
            
            # Send Telegram
            if self.config.notification_type in ['telegram', 'both']:
                telegram_success = self.notifier.send_telegram(telegram_msg, recipients.get('telegram', None))
                success = success and telegram_success
            
            return success
        except Exception as e:
            logger.error(f"Error sending security notification: {e}")
            return False
    
    def _create_security_email(self, data):
        """
        Create HTML email body for security alert.
        
        Args:
            data: Notification data
            
        Returns:
            str: HTML email body
        """
        # Create security-themed HTML
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .container {{ padding: 20px; }}
                .security-alert {{ 
                    border-left: 5px solid #ff0000; 
                    background-color: #fff8f8;
                    padding: 15px;
                    margin-bottom: 20px;
                }}
                .label {{ font-weight: bold; color: #cc0000; }}
                .evidence {{ 
                    background-color: #f5f5f5; 
                    padding: 10px; 
                    border: 1px solid #ddd;
                    margin-top: 20px;
                }}
                .warning-icon {{
                    font-size: 48px;
                    color: #cc0000;
                    margin-bottom: 15px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="security-alert">
                    <div class="warning-icon">⚠️</div>
                    <h2>Security Alert</h2>
                    <p><strong>{data.get('message')}</strong></p>
                    
                    <div class="alert-details">
                        <p><span class="label">Alert Type:</span> {data.get('event_type')}</p>
                        <p><span class="label">Lock:</span> {data.get('lock_name')}</p>
                        <p><span class="label">User:</span> {data.get('user_name')}</p>
                        <p><span class="label">Time:</span> {data.get('date')}</p>
                    </div>
        """
        
        # Add evidence section if enabled
        if self.include_evidence:
            html += f"""
                    <div class="evidence">
                        <h3>Additional Details</h3>
                        <p><span class="label">Lock ID:</span> {data.get('lock_id')}</p>
                        <p><span class="label">Trigger:</span> {data.get('trigger')}</p>
                        <p><span class="label">Priority:</span> {data.get('priority', 'high')}</p>
                    </div>
            """
        
        # Complete HTML
        html += """
                </div>
                
                <p>This is an automated security alert from your Nuki Smart Lock system.</p>
                <p>Please investigate this activity promptly if it was not expected.</p>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def _create_security_telegram(self, data):
        """
        Create formatted Telegram message for security alert.
        
        Args:
            data: Notification data
            
        Returns:
            str: Formatted Telegram message
        """
        # Create security-themed message with emoji
        message = f"""🚨 *SECURITY ALERT* 🚨

*{data.get('message')}*

🔐 Lock: {data.get('lock_name')}
👤 User: {data.get('user_name')}
🕒 Time: {data.get('date')}
⚠️ Alert Type: {data.get('event_type').replace('SECURITY: ', '')}
"""
        
        # Add evidence if enabled
        if self.include_evidence:
            message += f"""
📋 Additional Details:
  • Trigger: {data.get('trigger')}
  • Priority: {data.get('priority', 'high')}
"""
            
        # Add footer
        message += """
⚠️ Please investigate this activity promptly if it was not expected.
"""
        
        return message
    
    def _get_security_recipients(self):
        """
        Get recipients for security notifications.
        
        Returns:
            dict: Dictionary with email and telegram recipients
        """
        # If notify_owner_only is True, only send to owner email/chat
        if self.notify_owner_only:
            # Try to get owner email from config
            owner_email = None
            owner_chat_id = None
            
            if hasattr(self.config, 'config') and 'Owner' in self.config.config:
                owner_config = self.config.config['Owner']
                owner_email = owner_config.get('email', None)
                owner_chat_id = owner_config.get('telegram_chat_id', None)
            
            # Fall back to normal recipients if owner not configured
            if not owner_email:
                owner_email = self.config.email_recipient
            
            if not owner_chat_id:
                owner_chat_id = self.config.telegram_chat_id
                
            return {
                'email': owner_email,
                'telegram': owner_chat_id
            }
        else:
            # Use normal notification recipients
            return {
                'email': None,  # None means use default recipient
                'telegram': None
            }

# Example usage when run directly
if __name__ == "__main__":
    # Create a test alert
    test_alert = {
        'message': 'Test security alert',
        'type': 'test_alert',
        'event': {
            'lock_name': 'Front Door',
            'lock_id': '123456',
            'trigger': 'Manual Test'
        },
        'user': 'Test User',
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    # Create security alerter
    alerter = SecurityAlerter()
    
    # Send test alert
    alerter.send_alert(test_alert)
    
    print("Security alert test complete. Check logs for output.")
