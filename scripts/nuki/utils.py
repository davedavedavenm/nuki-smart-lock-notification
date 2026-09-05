import os
import json
import logging
from datetime import datetime

logger = logging.getLogger('nuki_monitor')

class ActivityTracker:
    def __init__(self, data_dir):
        self.data_dir = data_dir
        self.last_activity_path = os.path.join(self.data_dir, "last_activity.json")
        self.processed_event_ids = set()
        self.last_activity = self._load_last_activity()
    
    def _load_last_activity(self):
        """Load the last activity log from file"""
        try:
            if os.path.exists(self.last_activity_path):
                with open(self.last_activity_path, 'r') as f:
                    activity = json.load(f)
                    
                    # Populate processed event IDs set
                    for event in activity:
                        if 'id' in event:
                            self.processed_event_ids.add(event['id'])
                            
                    return activity
            return []
        except Exception as e:
            logger.error(f"Error loading last activity: {e}")
            return []
    
    def save_activity(self, activity):
        """Save the current activity log to file"""
        try:
            os.makedirs(os.path.dirname(self.last_activity_path), exist_ok=True)
            with open(self.last_activity_path, 'w') as f:
                json.dump(activity, f, indent=2)
                
            # Update our last activity reference
            self.last_activity = activity
            
            # Update processed event IDs set
            for event in activity:
                if 'id' in event:
                    self.processed_event_ids.add(event['id'])
                    
            return True
        except Exception as e:
            logger.error(f"Error saving last activity: {e}")
            return False
    
    def is_event_processed(self, event):
        """Check if an event is already processed"""
        event_id = event.get('id')
        if not event_id:
            return False

        # Check the processed event IDs set for faster lookup
        return event_id in self.processed_event_ids


class WakeSignal:
    """File-based wake signal shared between the web process and the monitor.

    The webhook endpoint (web process) touches the signal file; the monitor
    loop checks it once per second and polls the Nuki API immediately when
    it appears, instead of waiting out the full polling interval.
    """

    def __init__(self, data_dir, filename="webhook_wake.signal"):
        self.path = os.path.join(data_dir, filename)

    def trigger(self):
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(self.path, 'w') as f:
                f.write(str(datetime.now().isoformat()))
            return True
        except Exception as e:
            logger.error(f"Failed to write wake signal: {e}")
            return False

    def consume(self):
        """Return True (and remove the signal) if a wake was pending"""
        try:
            if os.path.exists(self.path):
                os.remove(self.path)
                return True
        except Exception as e:
            logger.error(f"Failed to consume wake signal: {e}")
        return False


class DoorStateStore:
    """Persists the last seen doorState per lock for transition detection"""

    # Nuki Web API doorState values
    DOOR_STATES = {
        0: "Untrained",
        1: "Online",
        2: "Offline",
        3: "Closed",
        4: "Opened",
        5: "Unknown",
        6: "Calibrating",
    }

    def __init__(self, data_dir, filename="door_state.json"):
        self.path = os.path.join(data_dir, filename)
        self.states = self._load()

    def _load(self):
        try:
            if os.path.exists(self.path):
                with open(self.path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading door state store: {e}")
        return {}

    def get(self, lock_id):
        return self.states.get(str(lock_id))

    def update(self, lock_id, door_state):
        """Record a door state; returns (previous, current) tuple"""
        key = str(lock_id)
        previous = self.states.get(key)
        if previous != door_state:
            self.states[key] = door_state
            try:
                os.makedirs(os.path.dirname(self.path), exist_ok=True)
                with open(self.path, 'w') as f:
                    json.dump(self.states, f, indent=2)
            except Exception as e:
                logger.error(f"Error saving door state store: {e}")
        return previous, door_state

    @classmethod
    def describe(cls, door_state):
        return cls.DOOR_STATES.get(door_state, f"Unknown ({door_state})")
