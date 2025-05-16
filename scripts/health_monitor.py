#!/usr/bin/env python3
"""
Nuki API Health Monitor
Monitors the Nuki API connection and reports on any issues.
"""

import os
import sys
import requests
import configparser
import logging
import json
import time
from datetime import datetime, timedelta

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('health_monitor')

class NukiHealthMonitor:
    def __init__(self):
        self.config_dir = os.environ.get('CONFIG_DIR', os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config'))
        self.credentials_path = os.path.join(self.config_dir, 'credentials.ini')
        self.health_file = os.path.join(os.environ.get('LOGS_DIR', os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')), 'api_health.json')
        self.nuki_api_url = "https://api.nuki.io"
        
    def load_token(self):
        """Load API token from credentials file"""
        if not os.path.exists(self.credentials_path):
            logger.error(f"Credentials file not found at {self.credentials_path}")
            return None
        
        try:
            credentials = configparser.ConfigParser()
            credentials.read(self.credentials_path)
            return credentials.get('Nuki', 'api_token', fallback='')
        except Exception as e:
            logger.error(f"Error loading token: {e}")
            return None
            
    def check_api_health(self):
        """Check the health of the Nuki API connection"""
        token = self.load_token()
        if not token:
            return {
                "status": "error",
                "message": "No API token found in credentials.ini",
                "timestamp": datetime.now().isoformat()
            }
            
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json"
        }
        
        try:
            # First try the account endpoint (less intrusive)
            response = requests.get(
                f"{self.nuki_api_url}/account",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                return {
                    "status": "healthy",
                    "message": "API connection is working properly",
                    "timestamp": datetime.now().isoformat()
                }
            
            # If account fails, try smartlock endpoint
            if response.status_code == 401:
                # Try smartlock endpoint as a backup
                response = requests.get(
                    f"{self.nuki_api_url}/smartlock",
                    headers=headers,
                    timeout=10
                )
                
                if response.status_code == 200:
                    return {
                        "status": "healthy",
                        "message": "API connection is working properly",
                        "timestamp": datetime.now().isoformat()
                    }
                    
            # Handle error cases
            if response.status_code == 401:
                return {
                    "status": "error",
                    "message": "API authentication failed: Invalid or expired token",
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {
                    "status": "warning",
                    "message": f"API response code: {response.status_code}",
                    "timestamp": datetime.now().isoformat()
                }
                
        except requests.exceptions.ConnectionError:
            return {
                "status": "warning",
                "message": "Connection error: Could not connect to Nuki API",
                "timestamp": datetime.now().isoformat()
            }
        except requests.exceptions.Timeout:
            return {
                "status": "warning",
                "message": "Timeout: API request timed out",
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error checking API health: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
    
    def save_health_status(self, status):
        """Save the health status to a file"""
        try:
            os.makedirs(os.path.dirname(self.health_file), exist_ok=True)
            
            with open(self.health_file, 'w') as f:
                json.dump(status, f, indent=2)
                
            logger.info(f"Health status saved to {self.health_file}")
            return True
        except Exception as e:
            logger.error(f"Error saving health status: {e}")
            return False
            
    def load_health_status(self):
        """Load the health status from file"""
        if not os.path.exists(self.health_file):
            return None
            
        try:
            with open(self.health_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading health status: {e}")
            return None
            
    def check_and_report(self):
        """Check API health and report/save status"""
        current_status = self.check_api_health()
        previous_status = self.load_health_status()
        
        # Compare with previous status
        status_changed = False
        if previous_status and previous_status.get("status") != current_status.get("status"):
            status_changed = True
            
        # Save the new status
        self.save_health_status(current_status)
        
        # Print status
        if status_changed:
            if current_status.get("status") == "healthy":
                logger.info(f"✅ API Status: {current_status.get('message')}")
            elif current_status.get("status") == "warning":
                logger.warning(f"⚠️ API Status: {current_status.get('message')}")
            else:
                logger.error(f"❌ API Status: {current_status.get('message')}")
                
            # Print help message if there's an error
            if current_status.get("status") == "error":
                logger.warning("\nTo fix API connection issues:")
                logger.warning("1. Run scripts/token_manager.py to generate a new API token")
                logger.warning("2. Restart the application after updating the token")
        else:
            # Just print a brief status update if nothing changed
            logger.info(f"API Status: {current_status.get('status')} - {current_status.get('message')}")
        
        return current_status

def main():
    """Main function"""
    monitor = NukiHealthMonitor()
    status = monitor.check_and_report()
    
    # Exit with appropriate code based on status
    if status.get("status") == "healthy":
        sys.exit(0)  # Success
    elif status.get("status") == "warning":
        sys.exit(1)  # Warning
    else:
        sys.exit(2)  # Error

if __name__ == "__main__":
    main()
