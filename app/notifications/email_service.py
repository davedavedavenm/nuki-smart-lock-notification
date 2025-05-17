"""
Email notification service for Nuki Smart Lock Notification System.
Handles email formatting, generation and delivery.
"""
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

logger = logging.getLogger('nuki_monitor')

class EmailService:
    """
    Email notification service that handles formatting and sending email notifications.
    """
    
    def __init__(self, config):
        """
        Initialize the email notification service.
        
        Args:
            config: Configuration object with email settings
        """
        self.config = config
        
        # Validate required email configuration
        self._validate_config()
    
    def _validate_config(self):
        """Validate that all required email configuration is present."""
        required_fields = [
            'smtp_server', 'smtp_port', 'email_sender', 
            'email_recipient', 'email_username', 'email_password'
        ]
        
        missing_fields = []
        for field in required_fields:
            if not hasattr(self.config, field) or not getattr(self.config, field):
                missing_fields.append(field)
        
        if missing_fields:
            logger.warning(f"Missing email configuration: {', '.join(missing_fields)}")
    
    def send_notification(self, subject, event):
        """
        Send an email notification for a single event.
        
        Args:
            subject: Email subject line
            event: Event data dictionary
            
        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        # Build email body based on configuration
        body = self._build_single_email(event)
        
        # Send the email
        return self._send_email(subject, body)
    
    def send_digest(self, subject, events):
        """
        Send a digest email with multiple events.
        
        Args:
            subject: Email subject line
            events: List of event data dictionaries
            
        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        # Build digest email body
        body = self._build_digest_email(events)
        
        # Send the email
        return self._send_email(subject, body)
    
    def _send_email(self, subject, body):
        """
        Send an email with the given subject and body.
        
        Args:
            subject: Email subject line
            body: Email body content
            
        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        try:
            # Check if we have the necessary credentials
            if not all([
                self.config.smtp_server, 
                self.config.smtp_port, 
                self.config.email_sender,
                self.config.email_recipient,
                self.config.email_username,
                self.config.email_password
            ]):
                logger.error("Email credentials not fully configured")
                return False
            
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
    
    def _build_single_email(self, event):
        """
        Build email body for a single event.
        
        Args:
            event: Event data dictionary
            
        Returns:
            str: Formatted email body
        """
        if not self.config.use_html_email:
            return self._build_single_plain_email(event)
        
        # Build HTML email
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
        """
        Build plain text email for a single event.
        
        Args:
            event: Event data dictionary
            
        Returns:
            str: Plain text email body
        """
        trigger_desc = self._get_trigger_description(event)
        
        text = "Nuki Lock Alert\n"
        text += "==============\n\n"
        text += f"Action: {event['event_type']}\n"
        text += f"Lock: {event['lock_name']}\n"
        text += f"User: {event['user_name']}\n"
        text += f"Time: {event['date']}\n"
        text += f"Trigger: {trigger_desc}\n"
        
        return text
    
    def _build_digest_email(self, events):
        """
        Build email body for digest with multiple events.
        
        Args:
            events: List of event data dictionaries
            
        Returns:
            str: Formatted email body
        """
        if not self.config.use_html_email:
            return self._build_digest_plain_email(events)
        
        # Build HTML digest
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
        """
        Build plain text email body for digest.
        
        Args:
            events: List of event data dictionaries
            
        Returns:
            str: Plain text email body
        """
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
