import requests
import logging
from datetime import datetime

logger = logging.getLogger('nuki_monitor')

class NukiAPI:
    def __init__(self, config):
        self.config = config
        self.action_map = {
            1: "Unlock",
            2: "Lock",
            3: "Unlatch",
            4: "Lock 'n' Go",
            5: "Lock 'n' Go with unlatch",
            6: "Full Lock"
        }
        
        self.trigger_map = {
            0: "System",
            1: "Manual",
            2: "Button",
            3: "Automatic",
            4: "App",
            5: "Website",
            6: "Auto Lock",
            7: "Time Control"
        }
    
    def get_action_description(self, event):
        """Get human-readable description of the action"""
        action = event.get('action')
        name = event.get('name', '')
        
        # If name is provided and not empty, use it
        if name and name.strip():
            return name
            
        # Otherwise use the action code mapping
        if action in self.action_map:
            return self.action_map[action]
            
        return "Unknown Action"
    
    def get_trigger_description(self, trigger):
        """Get human-readable description of the trigger"""
        if trigger in self.trigger_map:
            return self.trigger_map[trigger]
        return "Unknown Trigger"
    
    def get_smartlocks(self):
        """Get all smartlocks associated with the account"""
        try:
            response = requests.get(
                f"{self.config.base_url}/smartlock", 
                headers=self.config.headers
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching smartlocks: {e}")
            return []
    
    def get_smartlock_logs(self, smartlock_id, limit=10):
        """Get recent activity logs for a specific smartlock"""
        try:
            response = requests.get(
                f"{self.config.base_url}/smartlock/{smartlock_id}/log", 
                headers=self.config.headers,
                params={"limit": limit}
            )
            response.raise_for_status()
            logs = response.json()
            
            # Debug log for the first event
            if logs and len(logs) > 0:
                sample_event = logs[0]
                auth_id = sample_event.get('authId')
                action = sample_event.get('action')
                trigger = sample_event.get('trigger')
                
                logger.info(f"Sample event structure: {sample_event}")
                logger.info(f"Action info - Name: {sample_event.get('name')}, Type: {action}, Trigger: {trigger}, AuthID: {auth_id}")
                
            return logs
        except Exception as e:
            logger.error(f"Error fetching logs for smartlock {smartlock_id}: {e}")
            return []
    
    def get_users(self):
        """Get all users associated with the account"""
        try:
            # First try the regular auth endpoint
            response = requests.get(
                f"{self.config.base_url}/smartlock/auth", 
                headers=self.config.headers
            )
            response.raise_for_status()
            users = response.json()
            
            # Debug logging to see the structure of the user data
            logger.info(f"Retrieved {len(users)} users from the API")
            if users:
                sample_user = users[0].copy()
                if 'id' in sample_user:
                    sample_user['id'] = f"ID-{type(sample_user['id']).__name__}"  # Mask actual ID but show type
                logger.info(f"Sample user structure: {sample_user}")
            
            return users
        except Exception as e:
            logger.error(f"Error fetching users: {e}")
            
            # Try alternative endpoint if the first one fails
            try:
                logger.info("Trying alternative user API endpoint...")
                response = requests.get(
                    f"{self.config.base_url}/smartlock/auth/user", 
                    headers=self.config.headers
                )
                response.raise_for_status()
                return response.json()
            except Exception as alt_e:
                logger.error(f"Error fetching users from alternative endpoint: {alt_e}")
                return []
    
    def get_user_name(self, auth_id):
        """Get the name of a user based on their auth ID"""
        # Special case for auto-lock (no auth ID)
        if auth_id is None:
            return "Auto Lock"
            
        users = self.get_users()
        if not users:
            logger.warning(f"No users found when looking up auth_id: {auth_id}")
            return "Unknown User"
        
        # Try direct match first
        for user in users:
            if user.get('id') == auth_id:
                return user.get('name', 'Unknown User')
        
        # Try type conversion if direct match fails
        if isinstance(auth_id, int):
            for user in users:
                if user.get('id') == str(auth_id):
                    return user.get('name', 'Unknown User')
        elif isinstance(auth_id, str) and auth_id.isdigit():
            for user in users:
                if user.get('id') == int(auth_id):
                    return user.get('name', 'Unknown User')
        
        return "Unknown User"
    
    def parse_date(self, date_str):
        """Parse the date from the API"""
        if not date_str:
            return None
            
        try:
            if 'T' in date_str:
                # Handle ISO format
                date_str = date_str.split('.')[0].replace('T', ' ')
                return datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
            else:
                # Handle unix timestamp (milliseconds)
                return datetime.fromtimestamp(int(date_str)/1000)
        except Exception as e:
            logger.error(f"Error parsing date {date_str}: {e}")
            return None
