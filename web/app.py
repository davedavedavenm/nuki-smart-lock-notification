#!/usr/bin/env python3
import os
import sys
import json
import time
import logging
from datetime import datetime, timedelta

# Enable lenient mode for web interface to allow setup wizard
os.environ["ALLOW_MISSING_TOKEN"] = "true"

from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from flask_session import Session

# Add parent directory to path to import nuki modules
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

from scripts.nuki.config import ConfigManager
from scripts.nuki.api import NukiAPI
from scripts.nuki.utils import ActivityTracker
from web.models import UserDatabase, User
from web.temp_codes import TemporaryCodeDatabase
from web.dark_mode import init_app

# Configure logging with fallback to console if file logging fails
log_handlers = []
try:
    # Create logs directory if it doesn't exist
    logs_dir = os.path.join(parent_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    
    # Attempt to add file handler
    log_file = os.path.join(logs_dir, "nuki_web.log")
    file_handler = logging.FileHandler(log_file)
    log_handlers.append(file_handler)
except (PermissionError, IOError) as e:
    print(f"WARNING: Could not set up file logging: {e}")
    print("File logging will be disabled. Check directory permissions.")
    print("See TROUBLESHOOTING.md for information on fixing permission issues.")

# Always add console handler as fallback
log_handlers.append(logging.StreamHandler())

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=log_handlers
)
logger = logging.getLogger('nuki_web')

if not any(isinstance(h, logging.FileHandler) for h in logger.handlers):
    logger.warning("File logging is disabled due to permission issues. Using console logging only.")
    logger.warning("To fix this, ensure the container has write access to the logs directory.")
    logger.warning("See TROUBLESHOOTING.md for more information.")

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))  # Use persistent secret key if available
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_DIR'] = os.environ.get('SESSION_FILE_DIR', os.path.join(parent_dir, 'flask_session'))
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)  # Longer session lifetime
app.config['SESSION_COOKIE_SECURE'] = False  # Allow session on http for development
app.config['SESSION_COOKIE_HTTPONLY'] = True  # Security best practice

# Initialize Flask-Session
Session(app)

# Make sessions permanent by default
@app.before_request
def make_session_permanent():
    session.permanent = True

# Check if setup is needed
@app.before_request
def check_setup():
    # Allow access to setup page, setup API, and static files
    if request.endpoint in ['setup', 'api_setup', 'static', 'health']:
        return
    
    # If not configured, redirect to setup
    if not config.is_configured:
        return redirect(url_for('setup'))

# Initialize dark mode as default
init_app(app)

# Provide common template variables
@app.context_processor
def inject_now():
    return {'now': datetime.now()}

# Load configuration
config = ConfigManager(parent_dir)
api = NukiAPI(config)
tracker = ActivityTracker(config.data_dir)
user_db = UserDatabase(config.data_dir)
temp_code_db = TemporaryCodeDatabase(config.data_dir)

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            flash('Please log in to access this page')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# Admin required decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            flash('Please log in to access this page')
            return redirect(url_for('login', next=request.url))
        if session.get('role') != 'admin':
            flash('You need administrator privileges to access this page')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# Agent access required decorator (admin or agent role)
def agent_access_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            flash('Please log in to access this page')
            return redirect(url_for('login', next=request.url))
        if session.get('role') not in ['admin', 'agent']:
            flash('You need agent or administrator privileges to access this page')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# Routes
@app.route('/')
@login_required
def index():
    """Dashboard home page"""
    return render_template('index.html')

@app.route('/setup')
def setup():
    """First-time setup wizard page"""
    # If already configured, redirect to index
    if config.is_configured:
        return redirect(url_for('index'))
    return render_template('setup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if user_db.authenticate(username, password):
            user_data = user_db.get_user(username)
            session['logged_in'] = True
            session['username'] = username
            session['role'] = user_data.get('role', 'user')
            session['theme'] = user_data.get('theme', 'dark')
            
            flash('You were successfully logged in')
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('index'))
        else:
            error = 'Invalid credentials'
            
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    """Logout and clear session"""
    session.pop('logged_in', None)
    session.pop('username', None)
    session.pop('role', None)
    session.pop('theme', None)
    flash('You were logged out')
    return redirect(url_for('login'))

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """User profile page"""
    return render_template('profile.html')

@app.route('/api/profile', methods=['POST'])
@login_required
def update_profile():
    """API endpoint to update user profile"""
    try:
        # Get data from request
        data = request.json
        current_password = data.get('current_password')
        new_password = data.get('new_password')
        theme = data.get('theme')
        
        # Get current user
        username = session.get('username')
        
        # Verify current password
        if current_password and new_password:
            if not user_db.authenticate(username, current_password):
                return jsonify({"error": "Current password is incorrect"}), 401
            
            # Update password
            success = user_db.update_password(username, new_password)
            if not success:
                return jsonify({"error": "Failed to update password"}), 500
            
            logger.info(f"Password updated for user: {username}")
        
        # Update theme if provided
        if theme:
            user_db.update_theme(username, theme)
            session['theme'] = theme
            logger.info(f"Theme updated for user: {username} to {theme}")
        
        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Error updating profile: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/theme', methods=['POST'])
@login_required
def update_theme():
    """API endpoint to update user theme preference"""
    try:
        data = request.json
        username = session.get('username')
        theme = data.get('theme')
        
        # Update theme
        if theme and username:
            user_db.update_theme(username, theme)
            session['theme'] = theme
            return jsonify({"success": True})
        else:
            return jsonify({"error": "Invalid theme or username"}), 400
    except Exception as e:
        logger.error(f"Error updating theme: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/users_manage')
@admin_required
def users_manage():
    """User management page"""
    return render_template('users_manage.html')

@app.route('/api/users/manage', methods=['GET'])
@admin_required
def get_users_manage():
    """API endpoint to get all users for management"""
    try:
        users = user_db.get_all_users()
        return jsonify(users)
    except Exception as e:
        logger.error(f"Error getting users: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/users/manage', methods=['POST'])
@admin_required
def add_user():
    """API endpoint to add a new user"""
    try:
        data = request.json
        username = data.get('username')
        password = data.get('password')
        role = data.get('role', 'user')
        active = data.get('active', True)
        
        if not username or not password:
            return jsonify({"error": "Username and password are required"}), 400
        
        if user_db.user_exists(username):
            return jsonify({"error": "User already exists"}), 409
        
        success = user_db.add_user(username, password, role, active)
        if success:
            return jsonify({"success": True})
        else:
            return jsonify({"error": "Failed to add user"}), 500
    except Exception as e:
        logger.error(f"Error adding user: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/users/manage/<username>', methods=['PUT'])
@admin_required
def update_user(username):
    """API endpoint to update a user"""
    try:
        data = request.json
        password = data.get('password')
        role = data.get('role')
        active = data.get('active')
        theme = data.get('theme')
        
        if not user_db.user_exists(username):
            return jsonify({"error": "User not found"}), 404
        
        # Update password if provided
        if password:
            user_db.update_password(username, password)
        
        # Update role if provided
        if role:
            user_db.update_role(username, role)
        
        # Update active status if provided
        if active is not None:
            user_db.update_active(username, active)
        
        # Update theme if provided
        if theme:
            user_db.update_theme(username, theme)
        
        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Error updating user: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/users/manage/<username>', methods=['DELETE'])
@admin_required
def delete_user(username):
    """API endpoint to delete a user"""
    try:
        if username == 'admin' or username == session.get('username'):
            return jsonify({"error": "Cannot delete admin user or currently logged in user"}), 400
        
        if not user_db.user_exists(username):
            return jsonify({"error": "User not found"}), 404
        
        success = user_db.delete_user(username)
        if success:
            return jsonify({"success": True})
        else:
            return jsonify({"error": "Failed to delete user"}), 500
    except Exception as e:
        logger.error(f"Error deleting user: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/activity')
@login_required
def activity():
    """Activity log page"""
    return render_template('activity.html')

@app.route('/api/activity', methods=['GET'])
@login_required
def get_activity():
    """API endpoint to get activity logs"""
    try:
        # Get parameters
        days = int(request.args.get('days', 7))
        limit = int(request.args.get('limit', 50))
        
        # Get locks
        locks = api.get_smartlocks()
        if not locks:
            return jsonify({"error": "No smartlocks found"}), 404
        
        all_activity = []
        
        # Get activity for each lock
        for lock in locks:
            lock_id = lock.get('smartlockId')
            lock_name = lock.get('name', 'Unknown Lock')
            
            # Get activity logs
            activity = api.get_smartlock_logs(lock_id, limit=limit)
            
            # Filter by date if needed
            if days > 0:
                cutoff_date = datetime.now() - timedelta(days=days)
                filtered_activity = []
                
                for event in activity:
                    event_date = api.parse_date(event.get('date'))
                    if event_date and event_date >= cutoff_date:
                        # Add lock name to event
                        event['lockName'] = lock_name
                        filtered_activity.append(event)
                
                all_activity.extend(filtered_activity)
            else:
                # Add lock name to events
                for event in activity:
                    event['lockName'] = lock_name
                all_activity.extend(activity)
        
        # Sort by date (newest first)
        all_activity.sort(key=lambda x: api.parse_date(x.get('date')), reverse=True)
        
        # Limit results if needed
        if limit > 0 and len(all_activity) > limit:
            all_activity = all_activity[:limit]
        
        # Process activity for display
        processed_activity = []
        for event in all_activity:
            # Extract event details
            event_id = event.get('id')
            lock_name = event.get('lockName', 'Unknown Lock')
            action = event.get('action')
            trigger = event.get('trigger')
            auth_id = event.get('authId')
            date = api.parse_date(event.get('date'))
            
            if not date:
                continue
            
            # Get action description
            action_description = api.get_action_description(event)
            
            # Get trigger description
            trigger_description = api.get_trigger_description(trigger)
            
            # Get user name
            user_name = "Auto Lock" if trigger == 6 else api.get_user_name(auth_id) if auth_id else "Unknown User"
            
            # Create processed event
            processed_event = {
                'id': event_id,
                'lock_name': lock_name,
                'action': action_description,
                'trigger': trigger_description,
                'user': user_name,
                'date': date.strftime('%Y-%m-%d %H:%M:%S'),
                'raw_date': date.isoformat()
            }
            
            processed_activity.append(processed_event)
        
        return jsonify(processed_activity)
    except Exception as e:
        logger.error(f"Error getting activity: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/status')
@login_required
def status():
    """Lock status page"""
    return render_template('status.html')

@app.route('/api/status', methods=['GET'])
@login_required
def get_status():
    """API endpoint to get lock status"""
    try:
        # Get locks
        locks = api.get_smartlocks()
        if not locks:
            return jsonify({"error": "No smartlocks found"}), 404
        
        # Process lock information
        lock_status = []
        for lock in locks:
            lock_id = lock.get('smartlockId')
            lock_name = lock.get('name', 'Unknown Lock')
            
            # Get current state
            state = lock.get('state', {})
            state_name = state.get('stateName')
            if not state_name:
                state_code = state.get('state')
                state_name = api.get_status_description(state_code)
            
            # Get battery info
            battery_critical = state.get('batteryCritical', False)
            battery_charging = state.get('batteryCharging', False)
            battery_charge = state.get('batteryCharge', 0)
            
            # Create status object
            status = {
                'id': lock_id,
                'name': lock_name,
                'state': state_name,
                'battery_critical': battery_critical,
                'battery_charging': battery_charging,
                'battery_charge': battery_charge,
                'last_activity': None,
                'last_user': None
            }
            
            # Get recent activity for this lock
            activity = api.get_smartlock_logs(lock_id, limit=1)
            if activity:
                last_event = activity[0]
                date = api.parse_date(last_event.get('date'))
                auth_id = last_event.get('authId')
                trigger = last_event.get('trigger')
                
                if date:
                    status['last_activity'] = date.strftime('%Y-%m-%d %H:%M:%S')
                    status['last_action'] = api.get_action_description(last_event)
                    status['last_user'] = "Auto Lock" if trigger == 6 else api.get_user_name(auth_id) if auth_id else "Unknown User"
            
            lock_status.append(status)
        
        return jsonify(lock_status)
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/notifications')
@admin_required
def notifications():
    """Notification settings page - Admin only"""
    return render_template('notifications.html')

@app.route('/api/notifications/settings', methods=['GET'])
@admin_required
def get_notification_settings():
    """API endpoint to get notification settings"""
    try:
        # Get notification settings
        settings = {
            'type': config.notification_type,
            'digest_mode': config.digest_mode,
            'notify_auto_lock': config.notify_auto_lock,
            'notify_system_events': config.notify_system_events,
            'excluded_users': config.excluded_users,
            'excluded_actions': config.excluded_actions,
            'excluded_triggers': config.excluded_triggers
        }
        
        return jsonify(settings)
    except Exception as e:
        logger.error(f"Error getting notification settings: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/notifications/settings', methods=['POST'])
@admin_required
def update_notification_settings():
    """API endpoint to update notification settings"""
    try:
        # Get data from request
        data = request.json
        
        # Get current config file path
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config_path = os.path.join(base_dir, "config", "config.ini")
        
        # Import the configuration utility functions
        sys.path.insert(0, os.path.join(parent_dir, "scripts"))
        from configure import update_config as update_config_func
        
        # Update notification type
        if 'type' in data:
            update_config_func(config_path, 'General', 'notification_type', data['type'])
        
        # Update digest mode
        if 'digest_mode' in data:
            update_config_func(config_path, 'Notification', 'digest_mode', str(data['digest_mode']).lower())
        
        # Update auto lock notifications
        if 'notify_auto_lock' in data:
            update_config_func(config_path, 'Notification', 'notify_auto_lock', str(data['notify_auto_lock']).lower())
        
        # Update system events notifications
        if 'notify_system_events' in data:
            update_config_func(config_path, 'Notification', 'notify_system_events', str(data['notify_system_events']).lower())
        
        # Update excluded users
        if 'excluded_users' in data:
            excluded_users = ','.join(data['excluded_users'])
            update_config_func(config_path, 'Filter', 'excluded_users', excluded_users)
        
        # Update excluded actions
        if 'excluded_actions' in data:
            excluded_actions = ','.join(data['excluded_actions'])
            update_config_func(config_path, 'Filter', 'excluded_actions', excluded_actions)
        
        # Update excluded triggers
        if 'excluded_triggers' in data:
            excluded_triggers = ','.join(data['excluded_triggers'])
            update_config_func(config_path, 'Filter', 'excluded_triggers', excluded_triggers)
        
        # Reload configuration
        global config, api
        config = ConfigManager(parent_dir)
        api = NukiAPI(config)
        
        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Error updating notification settings: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/config')
@admin_required
def config_page():
    """Configuration page - Admin only"""
    return render_template('config.html')

@app.route('/api/config', methods=['GET'])
@admin_required
def get_config():
    """API endpoint to get configuration"""
    try:
        # Mask API token for security but allow identifying it
        token = config.api_token
        masked_token = ""
        if token:
            if len(token) > 10:
                masked_token = f"{token[:5]}...{token[-5:]}"
            else:
                masked_token = "********"

        # Mask sensitive fields
        email_pass = "********" if config.email_password else ""
        telegram_token = ""
        if config.telegram_bot_token:
            token = config.telegram_bot_token
            telegram_token = f"{token[:5]}...{token[-5:]}" if len(token) > 10 else "********"

        # Get configuration
        config_data = {
            'nuki': {
                'api_token': masked_token
            },
            'general': {
                'notification_type': config.notification_type,
                'polling_interval': config.polling_interval
            },
            'notification': {
                'digest_mode': config.digest_mode,
                'digest_interval': config.digest_interval,
                'notify_auto_lock': config.notify_auto_lock,
                'notify_system_events': config.notify_system_events
            },
            'filter': {
                'excluded_users': config.excluded_users,
                'excluded_actions': config.excluded_actions,
                'excluded_triggers': config.excluded_triggers
            },
            'email': {
                'username': config.email_username,
                'password': email_pass,
                'smtp_server': config.smtp_server,
                'smtp_port': config.smtp_port,
                'sender': config.email_sender,
                'recipient': config.email_recipient,
                'use_html': config.use_html_email,
                'subject_prefix': config.email_subject_prefix
            },
            'telegram': {
                'bot_token': telegram_token,
                'chat_id': config.telegram_chat_id,
                'use_emoji': config.telegram_use_emoji,
                'format': config.telegram_format
            },
            'advanced': {
                'max_events_per_check': config.max_events_per_check,
                'max_historical_events': config.max_historical_events,
                'debug_mode': config.debug_mode,
                'user_cache_timeout': config.user_cache_timeout,
                'retry_on_failure': config.retry_on_failure,
                'max_retries': config.max_retries,
                'retry_delay': config.retry_delay
            }
        }
        
        return jsonify(config_data)
    except Exception as e:
        logger.error(f"Error getting configuration: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/config', methods=['POST'])
@admin_required
def update_config():
    """API endpoint to update configuration"""
    global config, api
    try:
        # Get current config file path
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config_path = os.path.join(base_dir, "config", "config.ini")
        config_dir = os.path.dirname(config_path)
        backup_path = os.path.join(config_dir, "config.ini.bak")
        
        # Create a backup before making changes
        import shutil
        try:
            if os.path.exists(config_path):
                shutil.copy2(config_path, backup_path)
                logger.info(f"Created backup at {backup_path}")
        except Exception as backup_error:
            logger.warning(f"Failed to create backup: {backup_error}")
        
        # Import the configuration utility functions
        sys.path.insert(0, os.path.join(parent_dir, "scripts"))
        from configure import update_config as update_config_func
        
        # Get data from request
        data = request.json
        
        success_count = 0
        error_count = 0
        
        # Handle Nuki API Token separately (credentials.ini)
        if 'nuki' in data and 'api_token' in data['nuki'] and data['nuki']['api_token'] and not data['nuki']['api_token'].startswith('***'):
            try:
                if not config.credentials.has_section('Nuki'):
                    config.credentials.add_section('Nuki')
                config.credentials.set('Nuki', 'api_token', data['nuki']['api_token'])
                logger.info("Queued Nuki API token update")
                success_count += 1
            except Exception as nuki_error:
                logger.error(f"Error updating Nuki API token: {nuki_error}")
                error_count += 1

        # Handle Email Credentials
        if 'email' in data:
            try:
                if not config.credentials.has_section('Email'):
                    config.credentials.add_section('Email')
                if 'username' in data['email'] and data['email']['username']:
                    config.credentials.set('Email', 'username', data['email']['username'])
                if 'password' in data['email'] and data['email']['password'] and not data['email']['password'].startswith('***'):
                    config.credentials.set('Email', 'password', data['email']['password'])
                success_count += 1
            except Exception as e:
                logger.error(f"Error updating email credentials: {e}")
                error_count += 1

        # Handle Telegram Credentials
        if 'telegram' in data:
            try:
                if not config.credentials.has_section('Telegram'):
                    config.credentials.add_section('Telegram')
                if 'bot_token' in data['telegram'] and data['telegram']['bot_token'] and not data['telegram']['bot_token'].startswith('***'):
                    config.credentials.set('Telegram', 'bot_token', data['telegram']['bot_token'])
                success_count += 1
            except Exception as e:
                logger.error(f"Error updating telegram credentials: {e}")
                error_count += 1

        # Save credentials.ini if any credential changes were made
        try:
            config._save_config(config.credentials, config.credentials_path)
            logger.info("Successfully updated credentials.ini")
        except Exception as e:
            logger.error(f"Failed to save credentials.ini: {e}")
            error_count += 1

        # Remove sensitive sections from data so they aren't processed by the standard loop
        if 'nuki' in data: del data['nuki']
        # Special case: keep non-sensitive parts of email/telegram for standard loop
        standard_data = data.copy()
        if 'email' in standard_data:
            if 'username' in standard_data['email']: del standard_data['email']['username']
            if 'password' in standard_data['email']: del standard_data['email']['password']
        if 'telegram' in standard_data:
            if 'bot_token' in standard_data['telegram']: del standard_data['telegram']['bot_token']
        
        # ... validation ...

        # Validate notification type to ensure it's not empty
        if 'general' in data and 'notification_type' in data['general']:
            if not data['general']['notification_type']:
                data['general']['notification_type'] = 'both'
        
        # Update standard configuration
        for section, options in standard_data.items():
            for option, value in options.items():
                # Convert boolean values to strings
                if isinstance(value, bool):
                    value = str(value).lower()
                
                try:
                    # Update config
                    update_config_func(config_path, section, option, str(value))
                    success_count += 1
                except Exception as option_error:
                    logger.error(f"Error updating option {section}.{option}: {option_error}")
                    error_count += 1
        
        if error_count > 0:
            logger.warning(f"Configuration update completed with {error_count} errors and {success_count} successes")
        else:
            logger.info(f"Configuration update completed successfully with {success_count} changes")
        
        # Reload configuration
        config = ConfigManager(parent_dir)
        api = NukiAPI(config)
        
        # Ensure file has proper permissions
        try:
            os.chmod(config_path, 0o640)
        except Exception as perm_error:
            logger.warning(f"Failed to set config file permissions: {perm_error}")
        
        return jsonify({"success": True, "changes": success_count, "errors": error_count})
    except Exception as e:
        logger.error(f"Error updating configuration: {e}")
        # Try to restore backup if it exists
        try:
            if os.path.exists(backup_path):
                import shutil
                shutil.copy2(backup_path, config_path)
                logger.info(f"Restored configuration from backup after error")
        except Exception as restore_error:
            logger.error(f"Failed to restore backup: {restore_error}")
            
        return jsonify({"error": str(e)}), 500

@app.route('/api/setup', methods=['POST'])
def api_setup():
    """API endpoint for initial system setup"""
    # If already configured, prevent further setup via this endpoint
    if config.is_configured:
        return jsonify({"error": "System is already configured"}), 403
        
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
        
    try:
        # Update Nuki API Token
        if 'nuki_token' in data and data['nuki_token']:
            if not config.credentials.has_section('Nuki'):
                config.credentials.add_section('Nuki')
            config.credentials.set('Nuki', 'api_token', data['nuki_token'])
            
        # Update Telegram Settings
        if 'telegram_bot_token' in data and data['telegram_bot_token']:
            if not config.credentials.has_section('Telegram'):
                config.credentials.add_section('Telegram')
            config.credentials.set('Telegram', 'bot_token', data['telegram_bot_token'])
        if 'telegram_chat_id' in data and data['telegram_chat_id']:
            if not config.config.has_section('Telegram'):
                config.config.add_section('Telegram')
            config.config.set('Telegram', 'chat_id', data['telegram_chat_id'])
            
        # Update Email Settings
        if 'email_username' in data and data['email_username']:
            if not config.credentials.has_section('Email'):
                config.credentials.add_section('Email')
            config.credentials.set('Email', 'username', data['email_username'])
        if 'email_password' in data and data['email_password']:
            if not config.credentials.has_section('Email'):
                config.credentials.add_section('Email')
            config.credentials.set('Email', 'password', data['email_password'])
        if 'email_smtp_server' in data and data['email_smtp_server']:
            if not config.config.has_section('Email'):
                config.config.add_section('Email')
            config.config.set('Email', 'smtp_server', data['email_smtp_server'])
        if 'email_smtp_port' in data and data['email_smtp_port']:
            if not config.config.has_section('Email'):
                config.config.add_section('Email')
            config.config.set('Email', 'smtp_port', str(data['email_smtp_port']))
        if 'email_sender' in data and data['email_sender']:
            if not config.config.has_section('Email'):
                config.config.add_section('Email')
            config.config.set('Email', 'sender', data['email_sender'])
        if 'email_recipient' in data and data['email_recipient']:
            if not config.config.has_section('Email'):
                config.config.add_section('Email')
            config.config.set('Email', 'recipient', data['email_recipient'])
            
        # Save both files
        config._save_config(config.config, config.config_path)
        config._save_config(config.credentials, config.credentials_path)
        
        # Reload configuration to apply changes
        config.reload()
        
        return jsonify({"success": True, "message": "Configuration saved successfully"})
    except Exception as e:
        logger.error(f"Error during setup: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/stats')
@login_required
def stats():
    """Statistics page"""
    return render_template('stats.html')

@app.route('/api/stats', methods=['GET'])
@login_required
def get_stats():
    """API endpoint to get usage statistics"""
    try:
        # Get parameters
        days = int(request.args.get('days', 30))
        
        # Get locks
        locks = api.get_smartlocks()
        if not locks:
            return jsonify({"error": "No smartlocks found"}), 404
        
        all_activity = []
        
        # Get activity for each lock
        for lock in locks:
            lock_id = lock.get('smartlockId')
            lock_name = lock.get('name', 'Unknown Lock')
            
            # Get activity logs (get more data for stats)
            activity = api.get_smartlock_logs(lock_id, limit=100)
            
            # Filter by date if needed
            cutoff_date = datetime.now() - timedelta(days=days)
            filtered_activity = []
            
            for event in activity:
                event_date = api.parse_date(event.get('date'))
                if event_date and event_date >= cutoff_date:
                    # Add lock name to event
                    event['lockName'] = lock_name
                    filtered_activity.append(event)
            
            all_activity.extend(filtered_activity)
        
        # No activity found
        if not all_activity:
            return jsonify({
                "by_user": [],
                "by_action": [],
                "by_hour": [0] * 24,
                "by_day": [0] * 7,
                "total_events": 0
            })
        
        # Calculate statistics
        user_stats = {}
        action_stats = {}
        hour_stats = [0] * 24
        day_stats = [0] * 7
        
        for event in all_activity:
            # Get event details
            trigger = event.get('trigger')
            auth_id = event.get('authId')
            action = event.get('action')
            date = api.parse_date(event.get('date'))
            
            if not date:
                continue
            
            # Update user stats
            user_name = "Auto Lock" if trigger == 6 else api.get_user_name(auth_id) if auth_id else "Unknown User"
            user_stats[user_name] = user_stats.get(user_name, 0) + 1
            
            # Update action stats
            action_name = api.get_action_description(event)
            action_stats[action_name] = action_stats.get(action_name, 0) + 1
            
            # Update hour stats
            hour = date.hour
            hour_stats[hour] += 1
            
            # Update day stats
            day = date.weekday()
            day_stats[day] += 1
        
        # Format for chart.js
        user_data = [{"name": name, "count": count} for name, count in user_stats.items()]
        user_data.sort(key=lambda x: x["count"], reverse=True)
        
        action_data = [{"name": name, "count": count} for name, count in action_stats.items()]
        action_data.sort(key=lambda x: x["count"], reverse=True)
        
        return jsonify({
            "by_user": user_data,
            "by_action": action_data,
            "by_hour": hour_stats,
            "by_day": day_stats,
            "total_events": len(all_activity)
        })
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/users')
@login_required
def users():
    """User management page"""
    return render_template('users.html')

@app.route('/api/users', methods=['GET'])
@login_required
def get_users():
    """API endpoint to get users"""
    try:
        # Get users from API
        users = api.get_users()
        
        # Format user data
        user_data = []
        for user in users:
            user_id = user.get('id')
            user_name = user.get('name', 'Unknown User')
            user_type = user.get('type', 'Unknown')
            enabled = user.get('enabled', True)
            
            # Create user object
            user_obj = {
                'id': user_id,
                'name': user_name,
                'type': user_type,
                'enabled': enabled
            }
            
            user_data.append(user_obj)
        
        return jsonify(user_data)
    except Exception as e:
        logger.error(f"Error getting users: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/temp-codes')
@agent_access_required
def temp_codes_page():
    """Temporary codes management page"""
    return render_template('temp_codes.html')

@app.route('/api/temp-codes', methods=['GET'])
@agent_access_required
def get_temp_codes():
    """API endpoint to get temporary codes"""
    try:
        # Clean expired codes
        temp_code_db.clean_expired_codes()
        
        # For agent users, only show codes they created
        if session.get('role') == 'agent':
            codes = temp_code_db.get_codes_by_creator(session.get('username'))
        else:
            # Admins see all codes
            codes = temp_code_db.get_all_codes()
        
        # Add creator names
        for code in codes:
            creator = user_db.get_user(code.get('created_by'))
            if creator:
                code['creator_name'] = code.get('created_by')
            else:
                code['creator_name'] = 'Unknown'
        
        return jsonify(codes)
    except Exception as e:
        logger.error(f"Error getting temporary codes: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/temp-codes', methods=['POST'])
@agent_access_required
def create_temp_code():
    """API endpoint to create a temporary code"""
    try:
        # Get data from request
        data = request.json
        code = data.get('code')
        name = data.get('name')
        expiry = data.get('expiry')
        
        if not code or not name or not expiry:
            return jsonify({"error": "Code, name, and expiry are required"}), 400
        
        # Validate code format (4-8 digits)
        if not code.isdigit() or len(code) < 4 or len(code) > 8:
            return jsonify({"error": "Code must be 4-8 digits"}), 400
        
        # Get first smartlock ID (we'll use the first one for simplicity)
        locks = api.get_smartlocks()
        if not locks:
            return jsonify({"error": "No smartlocks found"}), 404
        
        # Use the first smartlock
        smartlock_id = locks[0].get('smartlockId')
        
        # Convert expiry to datetime
        expiry_datetime = datetime.fromisoformat(expiry.replace('Z', '+00:00'))
        
        # Add code to Nuki API
        result = api.add_temporary_code(smartlock_id, code, name, expiry_datetime)
        
        if not result.get('success'):
            return jsonify({"error": result.get('message', 'Failed to add code to lock')}), 500
        
        # Generate a unique ID for the code
        code_id = str(int(time.time()))
        
        # Add code to database
        success = temp_code_db.add_code(
            code_id=code_id, 
            code=code, 
            name=name, 
            created_by=session.get('username'), 
            expiry=expiry_datetime
        )
        
        if not success:
            # Try to clean up the API authorization if database fails
            auth_id = result.get('auth_id')
            if auth_id:
                api.remove_code(smartlock_id, auth_id)
            return jsonify({"error": "Failed to save code to database"}), 500
        
        # Record the auth_id in our database for easier cleanup later
        temp_code_db.update_code(code_id, {"auth_id": result.get('auth_id')})
        
        return jsonify({
            "id": code_id,
            "code": code,
            "name": name,
            "created_by": session.get('username'),
            "created_at": datetime.now().isoformat(),
            "expiry": expiry_datetime.isoformat(),
            "auth_id": result.get('auth_id')
        })
    except Exception as e:
        logger.error(f"Error creating temporary code: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/temp-codes/<code_id>', methods=['DELETE'])
@agent_access_required
def delete_temp_code(code_id):
    """API endpoint to delete a temporary code"""
    try:
        # Get code from database
        code = temp_code_db.get_code(code_id)
        if not code:
            return jsonify({"error": "Code not found"}), 404
        
        # Check permissions for agent users
        if session.get('role') == 'agent' and code.get('created_by') != session.get('username'):
            return jsonify({"error": "You can only delete codes you created"}), 403
        
        # Get the auth_id
        auth_id = code.get('auth_id')
        
        # If no auth_id stored, try to find it
        if not auth_id:
            # Get first smartlock ID
            locks = api.get_smartlocks()
            if not locks:
                return jsonify({"error": "No smartlocks found"}), 404
            
            # Use the first smartlock
            smartlock_id = locks[0].get('smartlockId')
            
            # Find auth_id by code value
            auth_id = api.find_auth_id_by_code(smartlock_id, code.get('code'))
        
        # If we have an auth_id, delete from API
        if auth_id:
            # Get first smartlock ID
            locks = api.get_smartlocks()
            if locks:
                smartlock_id = locks[0].get('smartlockId')
                api.remove_code(smartlock_id, auth_id)
        
        # Delete from database
        success = temp_code_db.delete_code(code_id)
        if not success:
            return jsonify({"error": "Failed to delete code from database"}), 500
        
        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Error deleting temporary code: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/admin/create-agency', methods=['GET', 'POST'])
@admin_required
def create_agency_user():
    """Admin page to create agent users"""
    if request.method == 'POST':
        try:
            username = request.form.get('username')
            password = request.form.get('password')
            email = request.form.get('email')
            active = 'active' in request.form
            
            if not all([username, password, email]):
                flash('Username, password, and email are required', 'danger')
                return redirect(url_for('create_agency_user'))
            
            if user_db.user_exists(username):
                flash('Username already exists', 'danger')
                return redirect(url_for('create_agency_user'))
            
            # Create the agent user
            success = user_db.add_user(username, password, 'agent', active)
            
            if success:
                flash('Agent user created successfully', 'success')
                return redirect(url_for('users_manage'))
            else:
                flash('Failed to create agent user', 'danger')
                return redirect(url_for('create_agency_user'))
                
        except Exception as e:
            logger.error(f"Error creating agent user: {e}")
            flash(f"Error: {str(e)}", 'danger')
            return redirect(url_for('create_agency_user'))
    
    return render_template('create_agency.html')

@app.route('/health')
def health_check():
    """Health check endpoint for Docker healthchecks"""
    try:
        # Check if config files exist
        config_dir = os.environ.get('CONFIG_DIR', os.path.join(parent_dir, 'config'))
        config_file = os.path.join(config_dir, 'config.ini')
        creds_file = os.path.join(config_dir, 'credentials.ini')
        
        config_exists = os.path.exists(config_file)
        creds_exists = os.path.exists(creds_file)
        
        # Check logs directory is writable
        logs_dir = os.path.join(parent_dir, 'logs')
        logs_writable = os.access(logs_dir, os.W_OK)
        
        # Calculate uptime (simple version since we don't store start time)
        uptime = "healthy"
        
        # Create status response
        status = {
            "status": "healthy" if (config_exists and creds_exists and logs_writable) else "warning",
            "uptime": uptime,
            "config_files": {
                "config.ini": config_exists,
                "credentials.ini": creds_exists
            },
            "permissions": {
                "logs_writable": logs_writable
            },
            "timestamp": int(time.time())
        }
        
        if not logs_writable:
            logger.warning("Logs directory is not writable - this may cause issues")
            status["message"] = "Directory permission issues detected. See TROUBLESHOOTING.md"
        
        return jsonify(status), 200
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": int(time.time())
        }), 500

# Helper function to filter sensitive data for non-admin users
def filter_api_response_for_role(response):
    """Filter API responses to remove sensitive data for non-admin users"""
    if not response.is_json:
        return response
    
    # Only filter for non-admin users
    if 'logged_in' not in session or session.get('role') == 'admin':
        return response
    
    # Check if this is a sensitive API endpoint
    sensitive_endpoints = [
        '/api/config',
        '/api/status'
    ]
    
    is_sensitive = False
    for endpoint in sensitive_endpoints:
        if request.path.startswith(endpoint):
            is_sensitive = True
            break
    
    if not is_sensitive:
        return response
    
    try:
        # Get JSON data
        data = response.get_json()
        
        # Filter status endpoint to remove sensitive information
        if request.path.startswith('/api/status'):
            # Remove personal email and telegram details
            if isinstance(data, list):
                for lock in data:
                    if 'email_details' in lock:
                        lock.pop('email_details')
                    if 'telegram_details' in lock:
                        lock.pop('telegram_details')
        
        # Filter config endpoint (should be blocked by decorator, but just in case)
        if request.path.startswith('/api/config'):
            # Prepare limited config data for non-admin users
            limited_data = {}
            
            # Only include public configuration options
            if 'general' in data:
                limited_data['general'] = {
                    'polling_interval': data['general'].get('polling_interval')
                }
            
            data = limited_data
        
        # Set the modified data
        response.set_data(json.dumps(data))
    except Exception as e:
        logger.error(f"Error filtering API response: {e}")
    
    return response

# Apply theme to all responses and filter sensitive data
@app.after_request
def apply_theme_and_filter(response):
    # Apply dark theme to HTML responses
    if 'logged_in' in session and session.get('theme') == 'dark':
        # Only apply to HTML responses
        if response.content_type and 'text/html' in response.content_type:
            response_data = response.get_data(as_text=True)
            # Add dark-theme class to body
            if '<body>' in response_data and 'dark-theme' not in response_data:
                response_data = response_data.replace('<body>', '<body class="dark-theme">')
                response.set_data(response_data)
            # Add dark mode CSS link if not present
            if '<head>' in response_data and 'dark-mode.css' not in response_data:
                css_link = '<link rel="stylesheet" href="{{ url_for(\'static\', filename=\'css/dark-mode.css\') }}">' 
                response_data = response_data.replace('</head>', f'{css_link}\n</head>')
                response.set_data(response_data)
    
    # Filter sensitive data for non-admin users
    response = filter_api_response_for_role(response)
    
    return response

# Main entry point
if __name__ == '__main__':
    # Create logger directory if it doesn't exist
    os.makedirs(os.path.join(parent_dir, "logs"), exist_ok=True)
    
    # Ensure the users.json file exists and has the admin user
    if not user_db.get_user('admin'):
        user_db.add_user('admin', 'nukiadmin', 'admin', True)
    
    # Run the app
    app.run(debug=True, host='0.0.0.0', port=5000)
