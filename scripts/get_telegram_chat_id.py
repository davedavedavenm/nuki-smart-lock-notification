#!/usr/bin/env python3
import sys
import os
import logging
import requests
import configparser
import time

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('telegram_setup')

def get_bot_token():
    """Get the Telegram bot token from credentials file or prompt user"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    credentials_path = os.path.join(base_dir, "config", "credentials.ini")
    
    if os.path.exists(credentials_path):
        credentials = configparser.ConfigParser()
        credentials.read(credentials_path)
        
        if 'Telegram' in credentials and 'bot_token' in credentials['Telegram']:
            token = credentials['Telegram']['bot_token']
            if token:
                return token
    
    # Prompt user if token not found
    print("\nTelegram bot token not found in credentials.ini.")
    print("You need to create a Telegram bot using @BotFather on Telegram first.")
    token = input("Please enter your Telegram bot token: ")
    
    # Save token if provided
    if token:
        save_token = input("Do you want to save this token to credentials.ini? (y/n): ")
        if save_token.lower() == 'y':
            save_bot_token(token)
    
    return token

def save_bot_token(token):
    """Save the bot token to credentials.ini"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_dir = os.path.join(base_dir, "config")
    credentials_path = os.path.join(config_dir, "credentials.ini")
    
    # Ensure config directory exists
    os.makedirs(config_dir, exist_ok=True)
    
    # Read existing config or create new
    credentials = configparser.ConfigParser()
    if os.path.exists(credentials_path):
        credentials.read(credentials_path)
    
    # Ensure Telegram section exists
    if 'Telegram' not in credentials:
        credentials.add_section('Telegram')
    
    # Set token
    credentials['Telegram']['bot_token'] = token
    
    # Save to file
    with open(credentials_path, 'w') as f:
        credentials.write(f)
    
    # Set secure permissions
    os.chmod(credentials_path, 0o600)
    
    logger.info(f"Bot token saved to {credentials_path}")

def save_chat_id(chat_id):
    """Save the chat ID to config.ini"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_dir = os.path.join(base_dir, "config")
    config_path = os.path.join(config_dir, "config.ini")
    
    # Ensure config directory exists
    os.makedirs(config_dir, exist_ok=True)
    
    # Read existing config or create new
    config = configparser.ConfigParser()
    if os.path.exists(config_path):
        config.read(config_path)
    
    # Ensure Telegram section exists
    if 'Telegram' not in config:
        config.add_section('Telegram')
    
    # Set chat ID
    config['Telegram']['chat_id'] = str(chat_id)
    
    # Save to file
    with open(config_path, 'w') as f:
        config.write(f)
    
    logger.info(f"Chat ID saved to {config_path}")

def get_updates(token):
    """Get updates from Telegram API"""
    url = f"https://api.telegram.org/bot{token}/getUpdates"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Error getting updates: {e}")
        return None

def main():
    print("\nTelegram Chat ID Utility")
    print("======================")
    print("This utility helps you get your Telegram chat ID for notification setup.")
    print("You need to have already created a Telegram bot using @BotFather.")
    print("Follow these steps:")
    print("1. Find your bot on Telegram and send it a message containing the text '/start'")
    print("2. Run this utility to detect your chat ID")
    print("3. The chat ID will be saved to your configuration file")
    
    # Get bot token
    token = get_bot_token()
    if not token:
        logger.error("No bot token provided. Exiting.")
        return
    
    print("\nGetting updates from your bot...")
    print("Please make sure you've sent a message to your bot on Telegram.")
    
    # Try to get updates multiple times
    max_attempts = 5
    for attempt in range(max_attempts):
        updates = get_updates(token)
        
        if not updates or 'result' not in updates or not updates['result']:
            print(f"No updates found. Waiting and trying again... ({attempt+1}/{max_attempts})")
            time.sleep(3)
            continue
        
        # Process updates
        for update in updates['result']:
            if 'message' in update and 'chat' in update['message']:
                chat_id = update['message']['chat']['id']
                user = update['message']['chat'].get('username', 'Unknown')
                
                print(f"\nFound chat ID: {chat_id} for user: {user}")
                
                # Confirm and save
                save = input("Do you want to use this chat ID for notifications? (y/n): ")
                if save.lower() == 'y':
                    save_chat_id(chat_id)
                    print("\nChat ID saved. Sending test message...")
                    
                    # Send test message
                    test_url = f"https://api.telegram.org/bot{token}/sendMessage"
                    test_payload = {
                        'chat_id': chat_id,
                        'text': "🔔 Test notification from Nuki Monitor setup.\nYour notification system is now configured correctly!",
                        'parse_mode': 'Markdown'
                    }
                    
                    try:
                        test_response = requests.post(test_url, data=test_payload)
                        test_response.raise_for_status()
                        print("Test message sent successfully!")
                    except Exception as e:
                        print(f"Error sending test message: {e}")
                    
                    return
        
        print("No suitable chat found or user declined to save the ID.")
        break
    
    print("\nCould not find any messages from your bot.")
    print("Please make sure to send a message to your bot on Telegram and try again.")

if __name__ == "__main__":
    main()
