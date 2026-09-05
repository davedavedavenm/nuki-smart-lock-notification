#!/usr/bin/env python3
import os
import time
import logging
import sys
from datetime import datetime

# Set up logging with fallback to console if file logging fails
log_handlers = []
try:
    # Ensure logs directory exists
    logs_dir = os.path.join(os.environ.get('LOGS_DIR', '/app/logs'))
    os.makedirs(logs_dir, exist_ok=True)
    
    # Try to set up file handler
    log_file = os.path.join(logs_dir, 'nuki_monitor.log')
    file_handler = logging.FileHandler(log_file)
    log_handlers.append(file_handler)
except (PermissionError, IOError) as e:
    print(f"WARNING: Could not set up file logging: {e}")
    print("File logging will be disabled. Check directory permissions.")
    print("See TROUBLESHOOTING.md for information on fixing permission issues.")

# Always add console handler as fallback
log_handlers.append(logging.StreamHandler())

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=log_handlers
)
logger = logging.getLogger('nuki_monitor')

# basicConfig attaches handlers to the ROOT logger — check there, not on the
# named logger (which only propagates), or this warning always fires
if not any(isinstance(h, logging.FileHandler) for h in logging.getLogger().handlers):
    logger.warning("File logging is disabled due to permission issues. Using console logging only.")
    logger.warning("To fix this, ensure the container has write access to the logs directory.")
    logger.warning("See TROUBLESHOOTING.md for more information.")

# Add the scripts directory to the Python path
scripts_dir = os.path.dirname(os.path.abspath(__file__))
if scripts_dir not in sys.path:
    sys.path.append(scripts_dir)

# Keep running (and alert) even if the API token goes missing at runtime —
# a dead monitor loop notifies nobody, an alive one sends failure alerts.
os.environ.setdefault("ALLOW_MISSING_TOKEN", "true")

# Import the modules
from nuki.config import ConfigManager
from nuki.api import NukiAPI
from nuki.utils import ActivityTracker, WakeSignal, DoorStateStore
from nuki.notification import Notifier

class NukiMonitor:
    def __init__(self):
        # Get base directory
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Check directory permissions
        self._check_directory_permissions()
        
        # Initialize components
        self.config = ConfigManager(self.base_dir)
        self.api = NukiAPI(self.config)
        self.tracker = ActivityTracker(self.config.data_dir)
        self.notifier = Notifier(self.config)
        self.wake = WakeSignal(self.config.data_dir)
        self.door_states = DoorStateStore(self.config.data_dir)

        # Flag to indicate first run
        self.first_run = True

        # Last full lock objects fetched from the API (reused for door state)
        self.last_locks = None

        # Self-monitoring state
        self.consecutive_failures = 0
        self.failure_alert_sent = False
        self.auth_alert_sent = False

        # Config hot-reload: only re-read when the files actually change
        self._config_mtimes = self._get_config_mtimes()

        logger.info("Nuki Monitor initialized")

    def _get_config_mtimes(self):
        mtimes = {}
        for path in (self.config.config_path, self.config.credentials_path):
            try:
                mtimes[path] = os.path.getmtime(path)
            except OSError:
                mtimes[path] = None
        return mtimes

    def _reload_config_if_changed(self):
        """Pick up web-UI config changes without a restart (mtime-gated to
        avoid log spam and needless re-reads)"""
        current = self._get_config_mtimes()
        if current == self._config_mtimes:
            return
        self._config_mtimes = current
        try:
            self.config.reload()
            logger.info("Configuration reloaded after change detected")
        except Exception as e:
            logger.error(f"Failed to reload configuration: {e}")
    
    def _check_directory_permissions(self):
        """Check directory permissions and log warnings if issues are found"""
        logs_dir = os.path.join(self.base_dir, 'logs')
        data_dir = os.path.join(self.base_dir, 'data')
        
        # Check logs directory
        if not os.path.exists(logs_dir):
            try:
                os.makedirs(logs_dir, exist_ok=True)
                logger.info(f"Created logs directory: {logs_dir}")
            except (PermissionError, IOError) as e:
                logger.warning(f"Cannot create logs directory: {e}")
        
        # Check data directory
        if not os.path.exists(data_dir):
            try:
                os.makedirs(data_dir, exist_ok=True)
                logger.info(f"Created data directory: {data_dir}")
            except (PermissionError, IOError) as e:
                logger.warning(f"Cannot create data directory: {e}")
                
        # Check write permissions
        if not os.access(logs_dir, os.W_OK):
            logger.warning(f"Cannot write to logs directory: {logs_dir}")
            logger.warning("See TROUBLESHOOTING.md for information on fixing permission issues.")
            
        if not os.access(data_dir, os.W_OK):
            logger.warning(f"Cannot write to data directory: {data_dir}")
            logger.warning("See TROUBLESHOOTING.md for information on fixing permission issues.")
    
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
            try:
                self.tracker.save_activity(current_activity)
                logger.info(f"Initialized history for lock {lock_name} with {len(current_activity)} events")
            except (PermissionError, IOError) as e:
                logger.error(f"Failed to save activity history due to permission error: {e}")
                logger.error("Check that the data directory is writable by the container.")
                return False
        
        return True
    
    def check_new_activity(self):
        """Check for new activity and generate notifications if needed"""
        # Special handling for first run
        if self.first_run:
            logger.info("First run detected, initializing event history without sending notifications")
            success = self.initialize_history()
            self.first_run = False
            if not success:
                logger.warning("Failed to initialize history, will retry on next check")
                return False
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
            self.last_locks = None
        else:
            # Get locks dynamically from API
            locks = self.api.get_smartlocks()
            if not locks:
                logger.error("No smartlocks found")
                return False
            # Full lock objects (with state) reused for the door-state check
            self.last_locks = locks
        
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
                try:
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
                except Exception as e:
                    logger.error(f"Error processing event: {e}")
                    continue
            
            # Save the current activity as last activity
            try:
                self.tracker.save_activity(current_activity)
            except (PermissionError, IOError) as e:
                logger.error(f"Failed to save activity history due to permission error: {e}")
                logger.error("Check that the data directory is writable by the container.")
                return False
        
        # Send notifications for new events
        if new_events:
            if self.config.digest_mode:
                # Add to digest queue
                for event in new_events:
                    try:
                        self.notifier.add_to_digest(event)
                    except Exception as e:
                        logger.error(f"Error adding event to digest: {e}")
            else:
                # Send immediate notifications
                for event in new_events:
                    try:
                        self.notifier.send_notification(event)
                    except Exception as e:
                        logger.error(f"Error sending notification: {e}")
        
        return True
    
    def check_door_states(self):
        """Detect door sensor transitions and alert when the door opens.

        Only the closed->opened transition notifies; the first observed state
        per lock just seeds the store (no alert after restarts).
        """
        if not self.config.notify_door_open:
            return

        locks = getattr(self, 'last_locks', None)
        if not locks:
            locks = self.api.get_smartlocks()

        for lock in locks or []:
            lock_id = lock.get('smartlockId')
            lock_name = lock.get('name', 'Unknown Lock')
            state = lock.get('state') or {}
            door_state = state.get('doorState')
            if door_state is None:
                continue

            previous, current = self.door_states.update(lock_id, door_state)
            if previous is not None and previous != current:
                logger.info(f"Door state for {lock_name}: {self.door_states.describe(previous)} -> {self.door_states.describe(current)}")
            if previous is not None and previous != 4 and current == 4:
                event = {
                    'lock_name': lock_name,
                    'lock_id': lock_id,
                    'event_type': 'Door Opened',
                    'action': None,
                    'trigger': None,
                    'user_name': 'Door Sensor',
                    'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'event_id': None
                }
                try:
                    self.notifier.send_notification(event)
                except Exception as e:
                    logger.error(f"Error sending door-open notification: {e}")

    def _handle_health(self, check_ok):
        """Track consecutive failures and send one-shot Telegram/email alerts"""
        error_status = self.api.last_error_status

        if check_ok and error_status is None:
            if self.failure_alert_sent or self.auth_alert_sent:
                self.notifier.send_alert(
                    "Monitoring resumed — the Nuki API is responding normally again."
                )
            self.consecutive_failures = 0
            self.failure_alert_sent = False
            self.auth_alert_sent = False
            return

        self.consecutive_failures += 1

        if error_status == 401 and not self.auth_alert_sent:
            self.notifier.send_alert(
                "Nuki API authentication failed (HTTP 401). The API token is "
                "invalid, expired or lacks scopes — notifications are paused "
                "until this is fixed in Admin > System Config."
            )
            self.auth_alert_sent = True
        elif (self.consecutive_failures >= self.config.alert_failure_threshold
              and not self.failure_alert_sent
              and not self.auth_alert_sent):
            detail = f" (last API status: {error_status})" if error_status else ""
            self.notifier.send_alert(
                f"The Nuki monitor has failed {self.consecutive_failures} "
                f"consecutive activity checks{detail}. Lock events may not be "
                "delivered until this recovers."
            )
            self.failure_alert_sent = True

    def _sleep_with_wake(self):
        """Sleep for the polling interval, waking early on a webhook signal"""
        interval = max(1, self.config.polling_interval)
        for _ in range(interval):
            time.sleep(1)
            if self.wake.consume():
                logger.info("Wake signal received - polling immediately")
                return

    def run(self):
        """Run the monitor in a continuous loop"""
        logger.info("Starting Nuki Monitor")
        
        try:
            while True:
                # Pick up config changes made through the web UI without
                # needing a container restart
                self._reload_config_if_changed()

                check_ok = False
                try:
                    check_ok = bool(self.check_new_activity())
                except Exception as e:
                    logger.error(f"Error checking for new activity: {e}")

                try:
                    self.check_door_states()
                except Exception as e:
                    logger.error(f"Error checking door states: {e}")

                try:
                    self._handle_health(check_ok)
                except Exception as e:
                    logger.error(f"Error in health handling: {e}")

                try:
                    self.notifier.flush_digest_if_due()
                except Exception as e:
                    logger.error(f"Error flushing digest: {e}")

                self._sleep_with_wake()
        except KeyboardInterrupt:
            logger.info("Monitor stopped by user")
        except Exception as e:
            logger.error(f"Error in monitor: {e}")
            raise

if __name__ == "__main__":
    monitor = NukiMonitor()
    monitor.run()
