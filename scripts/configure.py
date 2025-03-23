#!/usr/bin/env python3
import os
import sys
import argparse
import configparser
import getpass

def main():
    parser = argparse.ArgumentParser(description='Configure Nuki Smart Lock Notification System')
    
    # Command groups
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Show configuration
    show_parser = subparsers.add_parser('show', help='Show current configuration')
    
    # Update configuration
    update_parser = subparsers.add_parser('update', help='Update configuration settings')
    update_parser.add_argument('--section', required=True, help='Configuration section to update')
    update_parser.add_argument('--option', required=True, help='Configuration option to update')
    update_parser.add_argument('--value', required=True, help='New value for the configuration option')
    
    # Set API token
    token_parser = subparsers.add_parser('set-token', help='Set Nuki API token')
    
    # Set email credentials
    email_parser = subparsers.add_parser('set-email', help='Set email credentials')
    
    # Set Telegram credentials
    telegram_parser = subparsers.add_parser('set-telegram', help='Set Telegram credentials')
    
    # Reset configuration
    reset_parser = subparsers.add_parser('reset', help='Reset configuration to defaults')
    
    # Parse arguments
    args = parser.parse_args()
    
    # Determine base directory
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_dir = os.path.join(base_dir, "config")
    config_path = os.path.join(config_dir, "config.ini")
    credentials_path = os.path.join(config_dir, "credentials.ini")
    
    # Ensure config directory exists
    os.makedirs(config_dir, exist_ok=True)
    
    # Handle commands
    if args.command == 'show':
        show_config(config_path, credentials_path)
    elif args.command == 'update':
        update_config(config_path, args.section, args.option, args.value)
    elif args.command == 'set-token':
        set_api_token(credentials_path)
    elif args.command == 'set-email':
        set_email_credentials(credentials_path)
    elif args.command == 'set-telegram':
        set_telegram_credentials(credentials_path)
    elif args.command == 'reset':
        reset_config(config_path)
    else:
        # No command provided, show interactive menu
        interactive_menu(base_dir, config_path, credentials_path)

def show_config(config_path, credentials_path):
    """Display current configuration settings"""
    # Load configuration
    config = configparser.ConfigParser()
    if os.path.exists(config_path):
        config.read(config_path)
    
    credentials = configparser.ConfigParser()
    if os.path.exists(credentials_path):
        credentials.read(credentials_path)
    
    print("\nCurrent Configuration:")
    print("=====================")
    
    if not config.sections():
        print("No configuration set yet.\n")
    else:
        for section in config.sections():
            print(f"\n[{section}]")
            for option in config.options(section):
                print(f"{option} = {config.get(section, option)}")
    
    print("\nCredentials Status:")
    print("=================")
    
    if not credentials.sections():
        print("No credentials set yet.\n")
    else:
        if 'Nuki' in credentials.sections():
            if credentials.get('Nuki', 'api_token', fallback=''):
                print("Nuki API Token: Set")
            else:
                print("Nuki API Token: Not Set")
        else:
            print("Nuki API Token: Not Set")
        
        if 'Email' in credentials.sections():
            has_email = (credentials.get('Email', 'username', fallback='') and 
                        credentials.get('Email', 'password', fallback=''))
            print(f"Email Credentials: {'Set' if has_email else 'Not Set'}")
        else:
            print("Email Credentials: Not Set")
        
        if 'Telegram' in credentials.sections():
            has_telegram = credentials.get('Telegram', 'bot_token', fallback='')
            print(f"Telegram Bot Token: {'Set' if has_telegram else 'Not Set'}")
        else:
            print("Telegram Bot Token: Not Set")

def update_config(config_path, section, option, value):
    """Update a specific configuration setting"""
    # Load configuration
    config = configparser.ConfigParser()
    if os.path.exists(config_path):
        config.read(config_path)
    
    # Ensure section exists
    if not config.has_section(section):
        config.add_section(section)
    
    # Update option
    config.set(section, option, value)
    
    # Save configuration
    with open(config_path, 'w') as f:
        config.write(f)
    
    print(f"Updated {section}.{option} to {value}")

def set_api_token(credentials_path):
    """Set Nuki API token"""
    # Load credentials
    credentials = configparser.ConfigParser()
    if os.path.exists(credentials_path):
        credentials.read(credentials_path)
    
    # Ensure section exists
    if not credentials.has_section('Nuki'):
        credentials.add_section('Nuki')
    
    # Get token
    token = getpass.getpass("Enter Nuki API token: ")
    
    # Update token
    credentials.set('Nuki', 'api_token', token)
    
    # Save credentials
    with open(credentials_path, 'w') as f:
        credentials.write(f)
    
    # Set secure permissions
    os.chmod(credentials_path, 0o600)
    
    print("Nuki API token updated successfully.")

def set_email_credentials(credentials_path):
    """Set email credentials"""
    # Load credentials
    credentials = configparser.ConfigParser()
    if os.path.exists(credentials_path):
        credentials.read(credentials_path)
    
    # Ensure section exists
    if not credentials.has_section('Email'):
        credentials.add_section('Email')
    
    # Get credentials
    username = input("Enter email username: ")
    password = getpass.getpass("Enter email password: ")
    
    # Update credentials
    credentials.set('Email', 'username', username)
    credentials.set('Email', 'password', password)
    
    # Save credentials
    with open(credentials_path, 'w') as f:
        credentials.write(f)
    
    # Set secure permissions
    os.chmod(credentials_path, 0o600)
    
    print("Email credentials updated successfully.")

def set_telegram_credentials(credentials_path):
    """Set Telegram credentials"""
    # Load credentials
    credentials = configparser.ConfigParser()
    if os.path.exists(credentials_path):
        credentials.read(credentials_path)
    
    # Ensure section exists
    if not credentials.has_section('Telegram'):
        credentials.add_section('Telegram')
    
    # Get token
    token = getpass.getpass("Enter Telegram bot token: ")
    
    # Update token
    credentials.set('Telegram', 'bot_token', token)
    
    # Save credentials
    with open(credentials_path, 'w') as f:
        credentials.write(f)
    
    # Set secure permissions
    os.chmod(credentials_path, 0o600)
    
    print("Telegram bot token updated successfully.")
    print("NOTE: Don't forget to update the chat_id in config.ini")

def reset_config(config_path):
    """Reset configuration to defaults"""
    # Confirm reset
    confirm = input("Are you sure you want to reset the configuration to defaults? [y/N] ")
    if confirm.lower() != 'y':
        print("Reset cancelled.")
        return
    
    # Create default configuration
    config = configparser.ConfigParser()
    
    # General section
    config.add_section('General')
    config.set('General', 'notification_type', 'both')
    config.set('General', 'polling_interval', '60')
    
    # Notification section
    config.add_section('Notification')
    config.set('Notification', 'digest_mode', 'false')
    config.set('Notification', 'digest_interval', '3600')
    config.set('Notification', 'track_all_users', 'true')
    config.set('Notification', 'notify_auto_lock', 'true')
    config.set('Notification', 'notify_system_events', 'true')
    
    # Filter section
    config.add_section('Filter')
    config.set('Filter', 'excluded_users', '')
    config.set('Filter', 'excluded_actions', '')
    config.set('Filter', 'excluded_triggers', '')
    
    # Email section
    config.add_section('Email')
    config.set('Email', 'smtp_server', '')
    config.set('Email', 'smtp_port', '587')
    config.set('Email', 'sender', '')
    config.set('Email', 'recipient', '')
    config.set('Email', 'use_html', 'true')
    config.set('Email', 'include_lock_image', 'false')
    config.set('Email', 'subject_prefix', 'Nuki Alert')
    
    # Telegram section
    config.add_section('Telegram')
    config.set('Telegram', 'chat_id', '')
    config.set('Telegram', 'use_emoji', 'true')
    config.set('Telegram', 'format', 'detailed')
    
    # Advanced section
    config.add_section('Advanced')
    config.set('Advanced', 'max_events_per_check', '5')
    config.set('Advanced', 'max_historical_events', '20')
    config.set('Advanced', 'debug_mode', 'false')
    config.set('Advanced', 'user_cache_timeout', '3600')
    config.set('Advanced', 'retry_on_failure', 'true')
    config.set('Advanced', 'max_retries', '3')
    config.set('Advanced', 'retry_delay', '5')
    
    # Save configuration
    with open(config_path, 'w') as f:
        config.write(f)
    
    print("Configuration reset to defaults.")

def interactive_menu(base_dir, config_path, credentials_path):
    """Display interactive configuration menu"""
    while True:
        print("\nNuki Smart Lock Notification System - Configuration Utility")
        print("==========================================================")
        print("1. Show current configuration")
        print("2. Update settings")
        print("3. Configure notifications")
        print("4. Configure filters")
        print("5. Set up credentials")
        print("6. Configure advanced settings")
        print("7. Reset configuration to defaults")
        print("8. Exit")
        
        choice = input("\nEnter your choice (1-8): ")
        
        if choice == '1':
            show_config(config_path, credentials_path)
        elif choice == '2':
            update_settings_menu(config_path)
        elif choice == '3':
            notification_menu(config_path)
        elif choice == '4':
            filter_menu(config_path)
        elif choice == '5':
            credentials_menu(credentials_path, config_path)
        elif choice == '6':
            advanced_menu(config_path)
        elif choice == '7':
            reset_config(config_path)
        elif choice == '8':
            print("Exiting configuration utility.")
            sys.exit(0)
        else:
            print("Invalid choice. Please try again.")

def update_settings_menu(config_path):
    """Menu for updating general settings"""
    print("\nUpdate General Settings")
    print("=====================")
    print("1. Notification type (email, telegram, both)")
    print("2. Polling interval")
    print("3. Back to main menu")
    
    choice = input("\nEnter your choice (1-3): ")
    
    if choice == '1':
        value = input("Enter notification type (email, telegram, both): ")
        if value in ['email', 'telegram', 'both']:
            update_config(config_path, 'General', 'notification_type', value)
        else:
            print("Invalid value. Must be 'email', 'telegram', or 'both'.")
    elif choice == '2':
        value = input("Enter polling interval in seconds: ")
        try:
            int_value = int(value)
            if int_value > 0:
                update_config(config_path, 'General', 'polling_interval', value)
            else:
                print("Invalid value. Must be a positive integer.")
        except ValueError:
            print("Invalid value. Must be a number.")
    elif choice == '3':
        return
    else:
        print("Invalid choice. Please try again.")

def notification_menu(config_path):
    """Menu for configuring notification settings"""
    print("\nConfigure Notifications")
    print("=====================")
    print("1. Enable/disable digest mode")
    print("2. Set digest interval")
    print("3. Enable/disable notifications for auto lock")
    print("4. Enable/disable notifications for system events")
    print("5. Back to main menu")
    
    choice = input("\nEnter your choice (1-5): ")
    
    if choice == '1':
        value = input("Enable digest mode? (true/false): ")
        if value.lower() in ['true', 'false']:
            update_config(config_path, 'Notification', 'digest_mode', value.lower())
        else:
            print("Invalid value. Must be 'true' or 'false'.")
    elif choice == '2':
        value = input("Enter digest interval in seconds: ")
        try:
            int_value = int(value)
            if int_value > 0:
                update_config(config_path, 'Notification', 'digest_interval', value)
            else:
                print("Invalid value. Must be a positive integer.")
        except ValueError:
            print("Invalid value. Must be a number.")
    elif choice == '3':
        value = input("Enable notifications for auto lock? (true/false): ")
        if value.lower() in ['true', 'false']:
            update_config(config_path, 'Notification', 'notify_auto_lock', value.lower())
        else:
            print("Invalid value. Must be 'true' or 'false'.")
    elif choice == '4':
        value = input("Enable notifications for system events? (true/false): ")
        if value.lower() in ['true', 'false']:
            update_config(config_path, 'Notification', 'notify_system_events', value.lower())
        else:
            print("Invalid value. Must be 'true' or 'false'.")
    elif choice == '5':
        return
    else:
        print("Invalid choice. Please try again.")

def filter_menu(config_path):
    """Menu for configuring notification filters"""
    print("\nConfigure Filters")
    print("===============")
    print("1. Set excluded users")
    print("2. Set excluded actions")
    print("3. Set excluded triggers")
    print("4. Back to main menu")
    
    choice = input("\nEnter your choice (1-4): ")
    
    if choice == '1':
        value = input("Enter comma-separated list of user IDs to exclude: ")
        update_config(config_path, 'Filter', 'excluded_users', value)
    elif choice == '2':
        print("\nAction types:")
        print("1 = Unlock")
        print("2 = Lock")
        print("3 = Unlatch")
        print("4 = Lock'n'Go")
        print("5 = Lock'n'Go with unlatch")
        value = input("\nEnter comma-separated list of action types to exclude: ")
        update_config(config_path, 'Filter', 'excluded_actions', value)
    elif choice == '3':
        print("\nTrigger types:")
        print("0 = System")
        print("1 = Manual")
        print("2 = Button")
        print("3 = Automatic")
        print("4 = App")
        print("5 = Website")
        print("6 = Auto Lock")
        print("7 = TimeControl")
        value = input("\nEnter comma-separated list of trigger types to exclude: ")
        update_config(config_path, 'Filter', 'excluded_triggers', value)
    elif choice == '4':
        return
    else:
        print("Invalid choice. Please try again.")

def credentials_menu(credentials_path, config_path):
    """Menu for configuring credentials"""
    print("\nConfigure Credentials")
    print("==================")
    print("1. Set Nuki API token")
    print("2. Set email credentials")
    print("3. Configure email settings")
    print("4. Set Telegram bot token")
    print("5. Configure Telegram settings")
    print("6. Back to main menu")
    
    choice = input("\nEnter your choice (1-6): ")
    
    if choice == '1':
        set_api_token(credentials_path)
    elif choice == '2':
        set_email_credentials(credentials_path)
    elif choice == '3':
        email_settings_menu(config_path)
    elif choice == '4':
        set_telegram_credentials(credentials_path)
    elif choice == '5':
        telegram_settings_menu(config_path)
    elif choice == '6':
        return
    else:
        print("Invalid choice. Please try again.")

def email_settings_menu(config_path):
    """Menu for configuring email settings"""
    print("\nConfigure Email Settings")
    print("=====================")
    print("1. Set SMTP server")
    print("2. Set SMTP port")
    print("3. Set sender email")
    print("4. Set recipient email")
    print("5. Enable/disable HTML formatting")
    print("6. Set email subject prefix")
    print("7. Back to credentials menu")
    
    choice = input("\nEnter your choice (1-7): ")
    
    if choice == '1':
        value = input("Enter SMTP server address: ")
        update_config(config_path, 'Email', 'smtp_server', value)
    elif choice == '2':
        value = input("Enter SMTP server port: ")
        try:
            int_value = int(value)
            if 0 < int_value < 65536:
                update_config(config_path, 'Email', 'smtp_port', value)
            else:
                print("Invalid port number. Must be between 1 and 65535.")
        except ValueError:
            print("Invalid value. Must be a number.")
    elif choice == '3':
        value = input("Enter sender email address: ")
        update_config(config_path, 'Email', 'sender', value)
    elif choice == '4':
        value = input("Enter recipient email address: ")
        update_config(config_path, 'Email', 'recipient', value)
    elif choice == '5':
        value = input("Enable HTML formatting? (true/false): ")
        if value.lower() in ['true', 'false']:
            update_config(config_path, 'Email', 'use_html', value.lower())
        else:
            print("Invalid value. Must be 'true' or 'false'.")
    elif choice == '6':
        value = input("Enter email subject prefix: ")
        update_config(config_path, 'Email', 'subject_prefix', value)
    elif choice == '7':
        return
    else:
        print("Invalid choice. Please try again.")

def telegram_settings_menu(config_path):
    """Menu for configuring Telegram settings"""
    print("\nConfigure Telegram Settings")
    print("========================")
    print("1. Set chat ID")
    print("2. Enable/disable emoji")
    print("3. Set message format (compact/detailed)")
    print("4. Back to credentials menu")
    
    choice = input("\nEnter your choice (1-4): ")
    
    if choice == '1':
        value = input("Enter Telegram chat ID: ")
        update_config(config_path, 'Telegram', 'chat_id', value)
    elif choice == '2':
        value = input("Enable emoji in messages? (true/false): ")
        if value.lower() in ['true', 'false']:
            update_config(config_path, 'Telegram', 'use_emoji', value.lower())
        else:
            print("Invalid value. Must be 'true' or 'false'.")
    elif choice == '3':
        value = input("Enter message format (compact/detailed): ")
        if value.lower() in ['compact', 'detailed']:
            update_config(config_path, 'Telegram', 'format', value.lower())
        else:
            print("Invalid value. Must be 'compact' or 'detailed'.")
    elif choice == '4':
        return
    else:
        print("Invalid choice. Please try again.")

def advanced_menu(config_path):
    """Menu for configuring advanced settings"""
    print("\nConfigure Advanced Settings")
    print("========================")
    print("1. Set maximum events per check")
    print("2. Set maximum historical events")
    print("3. Enable/disable debug mode")
    print("4. Set user cache timeout")
    print("5. Enable/disable retry on API failure")
    print("6. Set maximum retry attempts")
    print("7. Set retry delay")
    print("8. Back to main menu")
    
    choice = input("\nEnter your choice (1-8): ")
    
    if choice == '1':
        value = input("Enter maximum events per check: ")
        try:
            int_value = int(value)
            if int_value > 0:
                update_config(config_path, 'Advanced', 'max_events_per_check', value)
            else:
                print("Invalid value. Must be a positive integer.")
        except ValueError:
            print("Invalid value. Must be a number.")
    elif choice == '2':
        value = input("Enter maximum historical events: ")
        try:
            int_value = int(value)
            if int_value > 0:
                update_config(config_path, 'Advanced', 'max_historical_events', value)
            else:
                print("Invalid value. Must be a positive integer.")
        except ValueError:
            print("Invalid value. Must be a number.")
    elif choice == '3':
        value = input("Enable debug mode? (true/false): ")
        if value.lower() in ['true', 'false']:
            update_config(config_path, 'Advanced', 'debug_mode', value.lower())
        else:
            print("Invalid value. Must be 'true' or 'false'.")
    elif choice == '4':
        value = input("Enter user cache timeout in seconds: ")
        try:
            int_value = int(value)
            if int_value > 0:
                update_config(config_path, 'Advanced', 'user_cache_timeout', value)
            else:
                print("Invalid value. Must be a positive integer.")
        except ValueError:
            print("Invalid value. Must be a number.")
    elif choice == '5':
        value = input("Enable retry on API failure? (true/false): ")
        if value.lower() in ['true', 'false']:
            update_config(config_path, 'Advanced', 'retry_on_failure', value.lower())
        else:
            print("Invalid value. Must be 'true' or 'false'.")
    elif choice == '6':
        value = input("Enter maximum retry attempts: ")
        try:
            int_value = int(value)
            if int_value > 0:
                update_config(config_path, 'Advanced', 'max_retries', value)
            else:
                print("Invalid value. Must be a positive integer.")
        except ValueError:
            print("Invalid value. Must be a number.")
    elif choice == '7':
        value = input("Enter retry delay in seconds: ")
        try:
            int_value = int(value)
            if int_value > 0:
                update_config(config_path, 'Advanced', 'retry_delay', value)
            else:
                print("Invalid value. Must be a positive integer.")
        except ValueError:
            print("Invalid value. Must be a number.")
    elif choice == '8':
        return
    else:
        print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()
