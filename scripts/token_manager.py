#!/usr/bin/env python3
import os
import sys
import getpass
import configparser

# Get base directory
script_dir = os.path.dirname(os.path.abspath(__file__))
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Path to the credentials file
credentials_path = os.path.join(base_dir, "config", "credentials.ini")

print("=== Nuki API Token Manager ===")
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
    masked_token = f"{current_token[:5]}...{current_token[-5:]}" if len(current_token) > 10 else "***"
    print(f"Current API token: {masked_token}")
else:
    print("No API token currently set")

# Ask the user for a new token
print("\nTo generate a new API token, please follow these steps:")
print("1. Login to Nuki Web at https://web.nuki.io/")
print("2. Go to your account menu and select 'API'")
print("3. Click 'Generate API token' and ensure ALL permissions are checked:")
print("   - Especially 'View activity logs and get log notifications'")
print("4. Copy the token and paste it below\n")

new_token = input("Enter your new Nuki API token (press Enter to keep current): ").strip()

if new_token:
    # Save the new token
    config.set('Nuki', 'api_token', new_token)
    with open(credentials_path, 'w') as f:
        config.write(f)
    
    # Set secure permissions for the file
    try:
        os.chmod(credentials_path, 0o600)
        print(f"Set secure permissions for {credentials_path}")
    except Exception as e:
        print(f"Warning: Could not set permissions for credentials file: {e}")
    
    print("\nAPI token saved successfully!")
else:
    print("\nNo changes made to API token")

# Now check config.ini for smartlock_id setting
config_path = os.path.join(base_dir, "config", "config.ini")
if os.path.exists(config_path):
    config = configparser.ConfigParser()
    config.read(config_path)
    
    # Check for explicit smartlock ID
    use_explicit_id = config.getboolean('Nuki', 'use_explicit_id', fallback=False)
    smartlock_id = config.get('Nuki', 'smartlock_id', fallback='')
    
    print("\n=== Smartlock Configuration ===")
    if use_explicit_id:
        print(f"Using explicit smartlock ID: {smartlock_id}")
        
        # Offer to update it
        update_id = input("Enter a new smartlock ID (or press Enter to keep current): ").strip()
        if update_id:
            if 'Nuki' not in config:
                config.add_section('Nuki')
            
            config.set('Nuki', 'smartlock_id', update_id)
            config.set('Nuki', 'use_explicit_id', 'true')
            
            with open(config_path, 'w') as f:
                config.write(f)
            
            print(f"Updated smartlock ID to: {update_id}")
    else:
        print("Currently using dynamic smartlock discovery (through API)")
        set_explicit = input("Would you like to set an explicit smartlock ID? (y/n): ").strip().lower()
        
        if set_explicit == 'y':
            new_id = input("Enter the smartlock ID: ").strip()
            
            if new_id:
                if 'Nuki' not in config:
                    config.add_section('Nuki')
                
                config.set('Nuki', 'smartlock_id', new_id)
                config.set('Nuki', 'use_explicit_id', 'true')
                
                with open(config_path, 'w') as f:
                    config.write(f)
                
                print(f"Set explicit smartlock ID to: {new_id}")
else:
    print("\nConfig file not found. Run the main application first to generate it.")

print("\nSetup complete! Please restart the application for changes to take effect.")
