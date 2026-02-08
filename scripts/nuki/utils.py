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
