#!/usr/bin/env python3
"""
Nuki API Token Verification Tool
This script verifies that your Nuki API token is valid and working correctly.
"""

import os
import sys
import requests
import configparser
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('token_verify')

def load_token_from_config():
    """Load API token from config file"""
    config_dir = os.environ.get('CONFIG_DIR', os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config'))
    credentials_path = os.path.join(config_dir, 'credentials.ini')
    
    if not os.path.exists(credentials_path):
        logger.error(f"Credentials file not found at {credentials_path}")
        return None
    
    try:
        credentials = configparser.ConfigParser()
        credentials.read(credentials_path)
        api_token = credentials.get('Nuki', 'api_token', fallback='')
        
        if not api_token:
            logger.error("API token not found in credentials.ini")
            return None
            
        # Mask the token for logging except first 4 and last 4 chars
        if len(api_token) > 8:
            masked_token = api_token[:4] + '*' * (len(api_token) - 8) + api_token[-4:]
        else:
            masked_token = '****'
            
        logger.info(f"Found API token: {masked_token}")
        return api_token
    except Exception as e:
        logger.error(f"Error loading credentials: {e}")
        return None

def verify_token(api_token):
    """Verify the API token by making a test request"""
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Accept": "application/json"
    }
    
    try:
        # First, try to get account info
        response = requests.get(
            "https://api.nuki.io/account",
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            logger.info("✅ API token is valid! Successfully retrieved account information.")
            account_data = response.json()
            logger.info(f"Account name: {account_data.get('name', 'Not available')}")
            return True
            
        elif response.status_code == 401:
            logger.error("❌ API token is invalid: Unauthorized (401)")
            logger.error(f"Response: {response.text}")
            return False
            
        else:
            logger.warning(f"⚠️ Unexpected status code: {response.status_code}")
            logger.warning(f"Response: {response.text}")
            
            # Try smartlock endpoint as fallback
            logger.info("Trying smartlock endpoint as fallback...")
            response = requests.get(
                "https://api.nuki.io/smartlock",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info("✅ API token is valid! Successfully retrieved smartlock information.")
                return True
            else:
                logger.error(f"❌ Smartlock endpoint failed with status code: {response.status_code}")
                logger.error(f"Response: {response.text}")
                return False
                
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Request error: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        return False

def main():
    """Main function"""
    logger.info("Nuki API Token Verification Tool")
    logger.info("-------------------------------")
    
    # Load token from config
    api_token = load_token_from_config()
    if not api_token:
        logger.info("\nTo fix this issue:")
        logger.info("1. Check that credentials.ini exists in the config directory")
        logger.info("2. Ensure the [Nuki] section contains api_token=YOUR_TOKEN")
        sys.exit(1)
    
    # Verify token
    if verify_token(api_token):
        logger.info("\n✅ Your Nuki API token is valid and working correctly.")
    else:
        logger.info("\n❌ Your Nuki API token appears to be invalid or expired.")
        logger.info("\nTo fix this issue:")
        logger.info("1. Go to https://web.nuki.io/")
        logger.info("2. Login to your Nuki account")
        logger.info("3. Go to 'Account' → 'API' and generate a new token")
        logger.info("4. Update your credentials.ini file with the new token")
        logger.info("5. Restart the system")
        
if __name__ == "__main__":
    main()
