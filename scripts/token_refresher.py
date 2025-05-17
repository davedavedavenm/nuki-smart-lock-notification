#!/usr/bin/env python3
"""
Nuki Token Refresher Script
This script helps you refresh your Nuki API token with proper validation.
"""

import os
import sys
import configparser
import getpass
import re
import requests

def header():
    print("\n============================================")
    print("🔄 NUKI API TOKEN REFRESHER 🔄")
    print("============================================\n")
    print("This utility will help you set up a new Nuki API token")
    print("with validation before saving.")

def validate_token(token):
    """Validate the API token by testing it against the Nuki API"""
    print("\nValidating token with the Nuki API...")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json"
    }
    
    endpoints = [
        {"name": "Account", "url": "https://api.nuki.io/account"},
        {"name": "Smartlock", "url": "https://api.nuki.io/smartlock"}
    ]
    
    for endpoint in endpoints:
        try:
            print(f"Testing {endpoint['name']} endpoint...")
            response = requests.get(
                endpoint['url'],
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                print(f"✅ {endpoint['name']} endpoint: SUCCESS")
                
                # For smartlock endpoint, try to get logs if we have locks
                if endpoint['name'] == 'Smartlock':
                    try:
                        smartlocks = response.json()
                        
                        if smartlocks:
                            smartlock_id = smartlocks[0].get('smartlockId')
                            print(f"Testing logs endpoint for smartlock ID: {smartlock_id}...")
                            
                            log_response = requests.get(
                                f"https://api.nuki.io/smartlock/{smartlock_id}/log",
                                headers=headers,
                                timeout=10
                            )
                            
                            if log_response.status_code == 200:
                                print(f"✅ Logs endpoint: SUCCESS")
                                return True, "Token is valid and has all required permissions"
                            else:
                                print(f"❌ Logs endpoint: FAILED (Status {log_response.status_code})")
                                print(f"Response: {log_response.text}")
                                return False, "Token is valid for basic access but not for logs endpoint"
                    except Exception as e:
                        print(f"Error testing logs endpoint: {e}")
                        return False, "Token is valid for basic access but couldn't test logs endpoint"
                
                return True, "Token is valid for basic access"
            elif response.status_code == 401:
                print(f"❌ {endpoint['name']} endpoint: FAILED (Status 401 Unauthorized)")
                print(f"Response: {response.text}")
                return False, "Token is invalid or expired (401 Unauthorized)"
            else:
                print(f"⚠️ {endpoint['name']} endpoint: WARNING (Status {response.status_code})")
                print(f"Response: {response.text}")
                return False, f"Unexpected response from API (Status {response.status_code})"
        except Exception as e:
            print(f"❌ Error testing {endpoint['name']} endpoint: {e}")
            return False, f"Error testing API: {str(e)}"
    
    return False, "No valid endpoints could be tested"

def main():
    header()
    
    # Determine the credentials file path
    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Check if CONFIG_DIR environment variable is set (for Docker)
    config_dir = os.environ.get('CONFIG_DIR', os.path.join(base_dir, 'config'))
    credentials_path = os.path.join(config_dir, 'credentials.ini')
    
    print(f"Credentials file: {credentials_path}")
    
    # Check if the credentials directory exists
    if not os.path.isdir(os.path.dirname(credentials_path)):
        print(f"Creating directory: {os.path.dirname(credentials_path)}")
        os.makedirs(os.path.dirname(credentials_path), exist_ok=True)
    
    # Load the existing credentials if available
    config = configparser.ConfigParser()
    if os.path.exists(credentials_path):
        config.read(credentials_path)
        print("Loaded existing credentials file")
    else:
        print("No existing credentials file found, creating new one")
    
    # Ensure the Nuki section exists
    if 'Nuki' not in config:
        config.add_section('Nuki')
    
    # Get the current token if it exists
    current_token = config.get('Nuki', 'api_token', fallback='')
    if current_token:
        token_length = len(current_token)
        masked_token = f"{current_token[:5]}...{current_token[-5:]}" if token_length > 10 else "***"
        print(f"Current API token: {masked_token} (length: {token_length})")
    else:
        print("No API token currently set")
    
    # Display instructions for generating a new token
    print("\n🔑 TO GENERATE A NEW API TOKEN:")
    print("1. Login to Nuki Web at https://web.nuki.io/")
    print("2. Go to your account menu and select 'API'")
    print("3. Click 'Generate API token' and check ALL permissions:")
    print("   - 'View smartlocks'")
    print("   - 'View activity logs and get log notifications'")
    print("   (Check ALL other permissions too for comprehensive access)")
    print("4. Copy the token and paste it below\n")
    
    # Get the new token
    new_token = getpass.getpass("Enter your new Nuki API token: ").strip()
    
    if not new_token:
        print("No token entered. Operation cancelled.")
        return
    
    # Basic format check
    if not re.match(r'^[A-Za-z0-9\-_=\.]+$', new_token):
        print("⚠️ Warning: Token contains characters that may not be valid.")
        confirm = input("Continue anyway? (y/n): ").strip().lower()
        
        if confirm != 'y':
            print("Operation cancelled.")
            return
    
    # Validate the token
    is_valid, message = validate_token(new_token)
    
    if is_valid:
        print(f"\n✅ Token validation successful: {message}")
    else:
        print(f"\n⚠️ Token validation warning: {message}")
        
        confirm = input("Do you still want to save this token? (y/n): ").strip().lower()
        
        if confirm != 'y':
            print("Token not saved. Operation cancelled.")
            return
    
    # Save the token
    backup_token = current_token
    config.set('Nuki', 'api_token', new_token)
    
    try:
        with open(credentials_path, 'w') as f:
            config.write(f)
        
        # Set secure permissions for the file
        try:
            os.chmod(credentials_path, 0o600)
            print(f"Set secure permissions for {credentials_path}")
        except Exception as e:
            print(f"Warning: Could not set permissions for credentials file: {e}")
        
        print("\n✅ API token saved successfully!")
        
        # Suggest restarting services
        print("\n🔄 RECOMMENDED NEXT STEPS:")
        print("1. If running in Docker:")
        print("   - Run 'docker compose down && docker compose up -d'")
        print("2. If running as a service:")
        print("   - Run 'systemctl restart nuki-monitor.service'")
        
    except Exception as e:
        print(f"\n❌ Error saving token: {e}")
        
        # Offer to restore the backup token
        if backup_token:
            restore = input("Would you like to restore the previous token? (y/n): ").strip().lower()
            
            if restore == 'y':
                try:
                    config.set('Nuki', 'api_token', backup_token)
                    with open(credentials_path, 'w') as f:
                        config.write(f)
                    print("Previous token restored")
                except Exception as restore_e:
                    print(f"Error restoring previous token: {restore_e}")

if __name__ == "__main__":
    main()
