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
        # Set when events were queued specifically because of quiet hours,
        # so they flush as soon as the quiet window ends
        self.quiet_flush_pending = False

    def in_quiet_hours(self, now=None):
        """Whether the current time falls inside the configured quiet window.

        Handles windows that span midnight (e.g. 22:00 -> 07:00).
        """
        if not self.config.quiet_hours_enabled:
            return False
        try:
            start = datetime.strptime(self.config.quiet_start, '%H:%M').time()
            end = datetime.strptime(self.config.quiet_end, '%H:%M').time()
        except (ValueError, TypeError):
            logger.warning(f"Invalid quiet hours window: {self.config.quiet_start}-{self.config.quiet_end}")
            return False
        current = (now or datetime.now()).time()
        if start <= end:
            return start <= current < end
        return current >= start or current < end

    def flush_digest_if_due(self):
        """Flush queued digest events when due or when quiet hours ended.

        Called by the monitor once per loop so digest/quiet-hour events are
        delivered even when no new events arrive to trigger a send.
        """
        if not self.digest_events:
            self.quiet_flush_pending = False
            return False

        if self.in_quiet_hours():
            return False

        quiet_ended = self.quiet_flush_pending
        interval_elapsed = (datetime.now() - self.last_digest_time).total_seconds() >= self.config.digest_interval

        if quiet_ended or interval_elapsed:
            logger.info("Flushing digest queue (%s)", "quiet hours ended" if quiet_ended else "digest interval elapsed")
            return self.send_digest_notification()
        return False

    def send_alert(self, message, subject="System Alert"):
        """Send a system/self-monitoring alert, bypassing event filters.

        Alerts are delivered via Telegram when configured, otherwise via
        email when configured — they intentionally still work when
        notification_type is 'none' (event notifications disabled), because
        their purpose is to surface that the monitor itself is failing.
        """
        logger.info(f"Sending system alert: {subject}")
        sent = False
        if self.config.telegram_bot_token and self.config.telegram_chat_id:
            sent = self.send_telegram(f"⚠️ *Nuki Monitor Alert*\n{message}") or sent
        elif self.config.smtp_server and self.config.email_recipient:
            sent = self.send_email(f"{self.config.email_subject_prefix}: {subject}", message) or sent
        else:
            logger.warning("System alert could not be delivered: no Telegram or email channel configured")
        return sent

    def send_notification(self, event):
        """Send an immediate notification for a single event"""
        logger.info(f"Sending notification for {event['event_type']} by {event['user_name']}")
        
        # Check if we should filter this event
        if self._should_filter_event(event):
            logger.info(f"Event filtered: {event['event_type']} by {event['user_name']}")
            return False

        # Inside quiet hours: defer to the digest queue instead of sending now
        if self.in_quiet_hours():
            logger.info(f"Quiet hours active - deferring event to digest: {event['event_type']} by {event['user_name']}")
            self.digest_events.append(event)
            self.quiet_flush_pending = True
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
        
        # Check if it's time to send digest (never during quiet hours —
        # the queued events flush when the quiet window ends)
        time_since_digest = datetime.now() - self.last_digest_time
        if time_since_digest.total_seconds() >= self.config.digest_interval and not self.in_quiet_hours():
            self.send_digest_notification()
    
    def _should_filter_event(self, event):
        """Check if an event should be filtered based on config settings.

        filter_mode:
          'all'     — everything notifies (subject to the auto-lock/system
                      toggles below)
          'include' — a non-empty select acts as an ALLOW-list: the event
                      must match it to notify. Empty selects don't restrict.
          'exclude' — a non-empty select acts as a BLOCK-list (legacy).
        """
        # Auto-lock filtering (trigger 6) — applies in every mode
        if event['user_name'] == "Auto Lock" and not self.config.notify_auto_lock:
            return True

        # System events (trigger 0 = System, e.g. "Nuki Bridge") — applies
        # in every mode
        event_name = str(event.get('event_type', ''))
        if ((event.get('trigger') == 0 or event_name.startswith("Nuki "))
                and not self.config.notify_system_events):
            return True

        mode = getattr(self.config, 'filter_mode', None) or 'all'
        if mode == 'all':
            return False

        selected_users = self.config.excluded_users
        selected_actions = self.config.excluded_actions
        selected_triggers = self.config.excluded_triggers

        def dimension_allows(selected, value):
            """Empty selection = no restriction; otherwise value must match"""
            return not selected or str(value) in selected

        if mode == 'include':
            if not dimension_allows(selected_users, event['user_name']):
                return True
            if 'action' in event and not dimension_allows(selected_actions, event.get('action')):
                return True
            if 'trigger' in event and not dimension_allows(selected_triggers, event.get('trigger')):
                return True
            return False

        # Legacy exclude mode: any match mutes the event
        if event['user_name'] in selected_users:
            return True
        if 'action' in event and str(event['action']) in selected_actions:
            return True
        if 'trigger' in event and str(event['trigger']) in selected_triggers:
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
        self.quiet_flush_pending = False

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
