import requests
import logging
import time
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
        
        # Initialize user cache
        self.user_cache = {}
        self.user_cache_timestamp = 0
        self.user_cache_timeout = config.user_cache_timeout  # In seconds
    
    def _make_request(self, method, url, params=None, json=None, retry=True):
        """Make an API request with retry logic"""
        max_retries = self.config.max_retries if retry else 1
        retry_delay = self.config.retry_delay
        
        for attempt in range(max_retries):
            try:
                response = requests.request(
                    method=method,
                    url=url,
                    headers=self.config.headers,
                    params=params,
                    json=json,
                    timeout=30  # Set a reasonable timeout
                )
                
                # Check for rate limiting
                if response.status_code == 429:
                    wait_time = int(response.headers.get('Retry-After', retry_delay))
                    logger.warning(f"Rate limited. Waiting {wait_time} seconds before retry.")
                    time.sleep(wait_time)
                    continue
                
                # Handle other error codes
                response.raise_for_status()
                return response.json()
                
            except requests.exceptions.RequestException as e:
                error_msg = f"API request failed: {str(e)}"
                if hasattr(e.response, 'text'):
                    error_msg += f", Response: {e.response.text}"
                
                logger.error(error_msg)
                
                if attempt < max_retries - 1 and retry and self.config.retry_on_failure:
                    logger.info(f"Retrying in {retry_delay} seconds (attempt {attempt+1}/{max_retries})...")
                    time.sleep(retry_delay)
                else:
                    logger.error(f"Request failed after {attempt+1} attempts: {url}")
                    return None
            except Exception as e:
                logger.error(f"Unexpected error during API request: {str(e)}")
                if attempt < max_retries - 1 and retry and self.config.retry_on_failure:
                    logger.info(f"Retrying in {retry_delay} seconds (attempt {attempt+1}/{max_retries})...")
                    time.sleep(retry_delay)
                else:
                    return None
    
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
            result = self._make_request('GET', f"{self.config.base_url}/smartlock")
            if result is None:
                # Return an empty list instead of None to prevent errors
                return []
            return result
        except Exception as e:
            logger.error(f"Error fetching smartlocks: {e}")
            return []
    
    def get_smartlock_logs(self, smartlock_id, limit=10):
        """Get recent activity logs for a specific smartlock"""
        try:
            # Ensure limit is within reasonable bounds
            if limit <= 0 or limit > 100:
                limit = 10
                
            result = self._make_request(
                'GET', 
                f"{self.config.base_url}/smartlock/{smartlock_id}/log",
                params={"limit": limit}
            )
            
            if result is None:
                return []
            
            # Debug log for the first event
            if result and len(result) > 0:
                sample_event = result[0]
                auth_id = sample_event.get('authId')
                action = sample_event.get('action')
                trigger = sample_event.get('trigger')
                
                logger.debug(f"Sample event structure: {sample_event}")
                logger.debug(f"Action info - Name: {sample_event.get('name')}, Type: {action}, Trigger: {trigger}, AuthID: {auth_id}")
                
            return result
        except Exception as e:
            logger.error(f"Error fetching logs for smartlock {smartlock_id}: {e}")
            return []
    
    def get_users(self, force_refresh=False):
        """Get all users associated with the account with caching"""
        current_time = time.time()
        
        # Check if we can use cached data
        if (not force_refresh and 
            self.user_cache and 
            (current_time - self.user_cache_timestamp) < self.user_cache_timeout):
            logger.debug("Using cached user data")
            return self.user_cache
        
        try:
            # First try the regular auth endpoint
            result = self._make_request('GET', f"{self.config.base_url}/smartlock/auth")
            
            if result is not None:
                # Update cache
                self.user_cache = result
                self.user_cache_timestamp = current_time
                
                # Debug logging to see the structure of the user data
                logger.debug(f"Retrieved {len(result)} users from the API")
                if result:
                    sample_user = result[0].copy()
                    if 'id' in sample_user:
                        sample_user['id'] = f"ID-{type(sample_user['id']).__name__}"  # Mask actual ID but show type
                    logger.debug(f"Sample user structure: {sample_user}")
                
                return result
            
            # Try alternative endpoint if the first one fails
            logger.info("Trying alternative user API endpoint...")
            result = self._make_request('GET', f"{self.config.base_url}/smartlock/auth/user")
            
            if result is not None:
                # Update cache
                self.user_cache = result
                self.user_cache_timestamp = current_time
                return result
            
            # If both endpoints fail, return empty list or cached data if available
            return self.user_cache if self.user_cache else []
            
        except Exception as e:
            logger.error(f"Error fetching users: {e}")
            # Return cached data if available, otherwise empty list
            return self.user_cache if self.user_cache else []
    
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
        try:
            if isinstance(auth_id, int):
                for user in users:
                    if user.get('id') == str(auth_id):
                        return user.get('name', 'Unknown User')
            elif isinstance(auth_id, str) and auth_id.isdigit():
                for user in users:
                    if user.get('id') == int(auth_id):
                        return user.get('name', 'Unknown User')
        except Exception as e:
            logger.warning(f"Error during user ID type conversion: {e}")
        
        return "Unknown User"
    
    def parse_date(self, date_str):
        """Parse the date from the API"""
        if not date_str:
            return None
            
        try:
            if isinstance(date_str, str) and 'T' in date_str:
                # Handle ISO format
                date_str = date_str.split('.')[0].replace('T', ' ')
                return datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
            elif isinstance(date_str, (int, float)) or (isinstance(date_str, str) and date_str.isdigit()):
                # Handle unix timestamp (milliseconds)
                timestamp = int(date_str)
                # Check if timestamp needs conversion (from milliseconds to seconds)
                if timestamp > 100000000000:  # Timestamp is in milliseconds
                    timestamp = timestamp / 1000
                return datetime.fromtimestamp(timestamp)
            else:
                logger.warning(f"Unrecognized date format: {date_str}")
                return None
        except Exception as e:
            logger.error(f"Error parsing date {date_str}: {e}")
            return None
