"""
Telegram notification service for Nuki Smart Lock Notification System.
Handles Telegram message formatting and delivery.
"""
import logging
import requests
from datetime import datetime

logger = logging.getLogger('nuki_monitor')

class TelegramService:
    """
    Telegram notification service that handles formatting and sending Telegram messages.
    """
    
    def __init__(self, config):
        """
        Initialize the Telegram notification service.
        
        Args:
            config: Configuration object with Telegram settings
        """
        self.config = config
        
        # Validate required Telegram configuration
        self._validate_config()
    
    def _validate_config(self):
        """Validate that all required Telegram configuration is present."""
        required_fields = ['telegram_bot_token', 'telegram_chat_id']
        
        missing_fields = []
        for field in required_fields:
            if not hasattr(self.config, field) or not getattr(self.config, field):
                missing_fields.append(field)
        
        if missing_fields:
            logger.warning(f"Missing Telegram configuration: {', '.join(missing_fields)}")
    
    def send_notification(self, subject, event):
        """
        Send a Telegram notification for a single event.
        
        Args:
            subject: Message subject (not used in Telegram, included for interface consistency)
            event: Event data dictionary
            
        Returns:
            bool: True if message was sent successfully, False otherwise
        """
        # Build message for single event
        message = self._build_single_telegram(event)
        
        # Send the message
        return self._send_telegram(message)
    
    def send_digest(self, subject, events):
        """
        Send a digest Telegram message with multiple events.
        
        Args:
            subject: Message subject (not used in Telegram, included for interface consistency)
            events: List of event data dictionaries
            
        Returns:
            bool: True if message was sent successfully, False otherwise
        """
        # Build digest message
        message = self._build_digest_telegram(events)
        
        # Send the message
        return self._send_telegram(message)
    
    def _send_telegram(self, message):
        """
        Send a Telegram message.
        
        Args:
            message: Formatted Telegram message
            
        Returns:
            bool: True if message was sent successfully, False otherwise
        """
        try:
            # Check if we have the necessary credentials
            if not self.config.telegram_bot_token or not self.config.telegram_chat_id:
                logger.error("Telegram credentials not configured")
                return False
                
            # Send message
            url = f"https://api.telegram.org/bot{self.config.telegram_bot_token}/sendMessage"
            payload = {
                'chat_id': self.config.telegram_chat_id,
                'text': message,
                'parse_mode': 'Markdown'
            }
            
            response = requests.post(url, data=payload)
            
            if response.status_code == 200:
                logger.info("Telegram notification sent successfully")
                return True
            else:
                logger.error(f"Failed to send Telegram notification. Status code: {response.status_code}, Response: {response.text}")
                return False
        except Exception as e:
            logger.error(f"Error sending Telegram notification: {e}")
            return False
    
    def _build_single_telegram(self, event):
        """
        Build Telegram message for a single event.
        
        Args:
            event: Event data dictionary
            
        Returns:
            str: Formatted Telegram message
        """
        trigger_desc = self._get_trigger_description(event)
        
        if not self.config.telegram_use_emoji:
            if self.config.telegram_format == 'compact':
                return f"Nuki Lock Alert: {event['event_type']} by {event['user_name']} on {event['lock_name']} at {event['date']} ({trigger_desc})"
            else:
                return f"Nuki Lock Alert\n{event['event_type']} on {event['lock_name']}\nUser: {event['user_name']}\nTime: {event['date']}\nTrigger: {trigger_desc}"
        
        # With emoji
        if self.config.telegram_format == 'compact':
            return f"🔔 Nuki Alert: {event['event_type']} by {event['user_name']} on {event['lock_name']} at {event['date']}"
        else:
            return f"""🔔 *Nuki Lock Alert*
🔒 *{event['event_type']}* on *{event['lock_name']}*
👤 User: {event['user_name']}
🕒 Time: {event['date']}
📱 Trigger: {trigger_desc}
"""
    
    def _build_digest_telegram(self, events):
        """
        Build Telegram message for digest with multiple events.
        
        Args:
            events: List of event data dictionaries
            
        Returns:
            str: Formatted Telegram message
        """
        emoji_prefix = "🔔 " if self.config.telegram_use_emoji else ""
        msg = f"{emoji_prefix}*Nuki Lock Activity Digest*\n\n"
        
        for event in events:
            trigger_desc = self._get_trigger_description(event)
            
            if self.config.telegram_use_emoji:
                lock_emoji = "🔒 " 
                user_emoji = "👤 " 
                time_emoji = "🕒 "
                trigger_emoji = "📱 "
                
                msg += f"• {time_emoji}{event['date']} - {event['lock_name']}\n"
                msg += f"  {lock_emoji}{event['event_type']} by {user_emoji}{event['user_name']}\n"
                msg += f"  {trigger_emoji}Trigger: {trigger_desc}\n\n"
            else:
                msg += f"• {event['date']} - {event['lock_name']}\n"
                msg += f"  {event['event_type']} by {event['user_name']}\n"
                msg += f"  Trigger: {trigger_desc}\n\n"
            
        return msg
    
    def _get_trigger_description(self, event):
        """
        Get human-readable trigger description.
        
        Args:
            event: Event data dictionary
            
        Returns:
            str: Human-readable trigger description
        """
        trigger_map = {
            0: "System",
            1: "Manual",
            2: "Button",
            3: "Automatic",
            4: "App",
            5: "Website",
            6: "Auto Lock",
            7: "Time Control"
        }
        
        trigger = event.get('trigger')
        if trigger in trigger_map:
            return trigger_map[trigger]
        return f"Unknown ({trigger})"
