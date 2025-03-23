import logging
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

logger = logging.getLogger('nuki_monitor')

class Notifier:
    def __init__(self, config):
        self.config = config
        self.digest_events = []
        self.last_digest_time = datetime.now()
    
    def send_notification(self, event):
        """Send an immediate notification for a single event"""
        logger.info(f"Sending notification for {event['event_type']} by {event['user_name']}")
        
        # Check if we should filter this event
        if self._should_filter_event(event):
            logger.info(f"Event filtered: {event['event_type']} by {event['user_name']}")
            return False
        
        # Create subject and messages
        subject = f"{self.config.email_subject_prefix}: {event['event_type']} by {event['user_name']}"
        
        email_body = self._build_single_email(event)
        telegram_msg = self._build_single_telegram(event)
        
        # Send notifications based on settings
        success = True
        if self.config.notification_type in ['email', 'both']:
            email_success = self.send_email(subject, email_body)
            success = success and email_success
            
        if self.config.notification_type in ['telegram', 'both']:
            telegram_success = self.send_telegram(telegram_msg)
            success = success and telegram_success
            
        return success
    
    def add_to_digest(self, event):
        """Add an event to the digest queue"""
        # Check if we should filter this event
        if self._should_filter_event(event):
            logger.info(f"Event filtered from digest: {event['event_type']} by {event['user_name']}")
            return
            
        self.digest_events.append(event)
        
        # Check if it's time to send digest
        time_since_digest = datetime.now() - self.last_digest_time
        if time_since_digest.total_seconds() >= self.config.digest_interval:
            self.send_digest_notification()
    
    def _should_filter_event(self, event):
        """Check if an event should be filtered based on config settings"""
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
    
    def send_digest_notification(self):
        """Send a digest notification with all events since last digest"""
        if not self.digest_events:
            return
            
        logger.info(f"Sending digest notification with {len(self.digest_events)} events")
        
        # Build the message
        subject = f"{self.config.email_subject_prefix}: Activity Digest - {len(self.digest_events)} events"
        
        # Sort events by date, newest first
        sorted_events = sorted(
            self.digest_events, 
            key=lambda x: datetime.strptime(x['date'], '%Y-%m-%d %H:%M:%S'),
            reverse=True
        )
        
        # Build the email and telegram messages
        email_body = self._build_digest_email(sorted_events)
        telegram_msg = self._build_digest_telegram(sorted_events)
        
        # Send notifications based on settings
        success = True
        if self.config.notification_type in ['email', 'both']:
            email_success = self.send_email(subject, email_body)
            success = success and email_success
            
        if self.config.notification_type in ['telegram', 'both']:
            telegram_success = self.send_telegram(telegram_msg)
            success = success and telegram_success
        
        # Reset digest regardless of send success to prevent repeated failures
        self.digest_events = []
        self.last_digest_time = datetime.now()
        
        return success
    
    def _build_digest_email(self, events):
        """Build HTML email body for digest"""
        if not self.config.use_html_email:
            return self._build_digest_plain_email(events)
            
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .container {{ padding: 20px; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                tr:nth-child(even) {{ background-color: #f9f9f9; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h2>Nuki Lock Activity Digest</h2>
                <p>The following activity has been recorded:</p>
                
                <table>
                    <tr>
                        <th>Date & Time</th>
                        <th>Lock</th>
                        <th>Action</th>
                        <th>User</th>
                        <th>Trigger</th>
                    </tr>
        """
        
        for event in events:
            trigger_desc = self._get_trigger_description(event)
            html += f"""
                    <tr>
                        <td>{event['date']}</td>
                        <td>{event['lock_name']}</td>
                        <td>{event['event_type']}</td>
                        <td>{event['user_name']}</td>
                        <td>{trigger_desc}</td>
                    </tr>
            """
            
        html += """
                </table>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def _build_digest_plain_email(self, events):
        """Build plain text email body for digest"""
        text = "Nuki Lock Activity Digest\n"
        text += "========================\n\n"
        text += "The following activity has been recorded:\n\n"
        
        for event in events:
            trigger_desc = self._get_trigger_description(event)
            text += f"Date: {event['date']}\n"
            text += f"Lock: {event['lock_name']}\n"
            text += f"Action: {event['event_type']}\n"
            text += f"User: {event['user_name']}\n"
            text += f"Trigger: {trigger_desc}\n\n"
            text += "-----------------------\n\n"
            
        return text
    
    def _build_digest_telegram(self, events):
        """Build Telegram message for digest"""
        emoji_prefix = "🔔 " if self.config.telegram_use_emoji else ""
        msg = f"{emoji_prefix}*Nuki Lock Activity Digest*\n\n"
        
        for event in events:
            trigger_desc = self._get_trigger_description(event)
            lock_emoji = "🔒 " if self.config.telegram_use_emoji else ""
            user_emoji = "👤 " if self.config.telegram_use_emoji else ""
            time_emoji = "🕒 " if self.config.telegram_use_emoji else ""
            trigger_emoji = "📱 " if self.config.telegram_use_emoji else ""
            
            msg += f"• {event['date']} - {event['lock_name']}\n"
            msg += f"  {lock_emoji}{event['event_type']} by {user_emoji}{event['user_name']}\n"
            msg += f"  {trigger_emoji}Trigger: {trigger_desc}\n\n"
            
        return msg
    
    def _get_trigger_description(self, event):
        """Get human-readable trigger description"""
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
    
    def _build_single_email(self, event):
        """Build email for a single event"""
        if not self.config.use_html_email:
            return self._build_single_plain_email(event)
            
        trigger_desc = self._get_trigger_description(event)
        return f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .container {{ padding: 20px; }}
                .event {{ margin-bottom: 20px; }}
                .label {{ font-weight: bold; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h2>Nuki Lock Alert</h2>
                
                <div class="event">
                    <p><span class="label">Action:</span> {event['event_type']}</p>
                    <p><span class="label">Lock:</span> {event['lock_name']}</p>
                    <p><span class="label">User:</span> {event['user_name']}</p>
                    <p><span class="label">Time:</span> {event['date']}</p>
                    <p><span class="label">Trigger:</span> {trigger_desc}</p>
                </div>
            </div>
        </body>
        </html>
        """
    
    def _build_single_plain_email(self, event):
        """Build plain text email for a single event"""
        trigger_desc = self._get_trigger_description(event)
        text = "Nuki Lock Alert\n"
        text += "==============\n\n"
        text += f"Action: {event['event_type']}\n"
        text += f"Lock: {event['lock_name']}\n"
        text += f"User: {event['user_name']}\n"
        text += f"Time: {event['date']}\n"
        text += f"Trigger: {trigger_desc}\n"
        
        return text
    
    def _build_single_telegram(self, event):
        """Build Telegram message for a single event"""
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
    
    def send_email(self, subject, body):
        """Send an email notification"""
        try:
            # Create message
            msg = MIMEMultipart() if self.config.use_html_email else MIMEText(body)
            msg['From'] = self.config.email_sender
            msg['To'] = self.config.email_recipient
            msg['Subject'] = subject
            
            # Attach body for HTML emails
            if self.config.use_html_email:
                msg.attach(MIMEText(body, 'html'))
            
            # Connect to server and send
            server = smtplib.SMTP(self.config.smtp_server, self.config.smtp_port)
            server.starttls()
            server.login(self.config.email_username, self.config.email_password)
            server.sendmail(self.config.email_sender, self.config.email_recipient, msg.as_string())
            server.quit()
            
            logger.info("Email notification sent successfully")
            return True
        except Exception as e:
            logger.error(f"Error sending email notification: {e}")
            return False
    
    def send_telegram(self, message):
        """Send a Telegram notification"""
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
