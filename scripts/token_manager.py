#!/usr/bin/env python3
"""
Nuki API Token Management Utility
This script helps you generate, validate, and update your Nuki API token.
"""

import os
import sys
import requests
import configparser
import logging
import webbrowser
import time
import json
from getpass import getpass

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('token_manager')

class NukiTokenManager:
    def __init__(self):
        self.config_dir = os.environ.get('CONFIG_DIR', os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config'))
        self.credentials_path = os.path.join(self.config_dir, 'credentials.ini')
        self.nuki_api_url = "https://api.nuki.io"
        self.nuki_web_url = "https://web.nuki.io"
        
    def load_credentials(self):
        """Load credentials file"""
        if not os.path.exists(self.credentials_path):
            logger.warning(f"Credentials file not found at {self.credentials_path}")
            return None
        
        try:
            credentials = configparser.ConfigParser()
            credentials.read(self.credentials_path)
            return credentials
        except Exception as e:
            logger.error(f"Error loading credentials: {e}")
            return None
            
    def save_credentials(self, credentials):
        """Save credentials to file"""
        try:
            os.makedirs(os.path.dirname(self.credentials_path), exist_ok=True)
            
            with open(self.credentials_path, 'w') as f:
                credentials.write(f)
                
            # Set secure permissions
            try:
                os.chmod(self.credentials_path, 0o600)
            except:
                pass  # May fail on Windows
                
            logger.info(f"Credentials saved to {self.credentials_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving credentials: {e}")
            return False
            
    def get_current_token(self):
        """Get current API token from credentials"""
        credentials = self.load_credentials()
        if not credentials:
            return None
            
        try:
            return credentials.get('Nuki', 'api_token', fallback='')
        except:
            return None
            
    def update_token(self, new_token):
        """Update the API token in credentials file"""
        credentials = self.load_credentials()
        if not credentials:
            credentials = configparser.ConfigParser()
            
        if 'Nuki' not in credentials:
            credentials.add_section('Nuki')
            
        credentials.set('Nuki', 'api_token', new_token)
        return self.save_credentials(credentials)
        
    def validate_token(self, token):
        """Validate if a token is working"""
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json"
        }
        
        try:
            response = requests.get(
                f"{self.nuki_api_url}/smartlock",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                locks = response.json()
                return True, f"Token valid - found {len(locks)} smartlocks"
            else:
                return False, f"Token invalid - Status code: {response.status_code}, Response: {response.text}"
        except Exception as e:
            return False, f"Error validating token: {e}"
            
    def open_token_generation_page(self):
        """Open the Nuki API token generation page in browser"""
        url = f"{self.nuki_web_url}/#/account/api"
        print(f"\nOpening {url} in your browser...\n")
        print("1. Log in to your Nuki account (if not already logged in)")
        print("2. On the API page, generate a new API token")
        print("3. Copy the token and paste it when prompted\n")
        
        try:
            webbrowser.open(url)
        except:
            print(f"Could not open the browser automatically. Please manually visit: {url}")
            
        time.sleep(2)  # Give time for browser to open

def main():
    """Main function"""
    print("\n====================================")
    print("   Nuki API Token Management Tool   ")
    print("====================================\n")
    
    manager = NukiTokenManager()
    current_token = manager.get_current_token()
    
    # Check if we have a current token
    if current_token:
        print(f"Current token found: {current_token[:4]}...{current_token[-4:]}")
        valid, message = manager.validate_token(current_token)
        
        if valid:
            print(f"✅ {message}")
            print("\nOptions:")
            print("1. Keep existing token")
            print("2. Generate new token")
            
            choice = input("\nEnter your choice (1-2): ")
            if choice != "2":
                print("Keeping existing token. No changes made.")
                return
        else:
            print(f"❌ {message}")
            print("The current token is not working. You need to generate a new one.")
    else:
        print("No existing token found. You need to generate a new one.")
    
    # Generate new token flow
    manager.open_token_generation_page()
    
    # Get new token from user
    print("\nEnter the new API token from the Nuki Web interface:")
    new_token = getpass("Token (input will be hidden): ")
    
    if not new_token.strip():
        print("No token provided. Exiting without changes.")
        return
        
    # Validate new token
    print("\nValidating new token...")
    valid, message = manager.validate_token(new_token)
    
    if valid:
        print(f"✅ {message}")
        # Save the new token
        if manager.update_token(new_token):
            print("\n✅ Token updated successfully!")
            print("You need to restart the Nuki monitoring system for changes to take effect.")
        else:
            print("\n❌ Failed to update token configuration.")
    else:
        print(f"❌ {message}")
        print("The provided token is not valid. Please check and try again.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"\n❌ An error occurred: {e}")
