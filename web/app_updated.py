#!/usr/bin/env python3
import os
import sys
import json
import time
import logging
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

# Add parent directory to path to import nuki modules
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

from scripts.nuki.config import ConfigManager
from scripts.nuki.api import NukiAPI
from scripts.nuki.utils import ActivityTracker
from models import UserDatabase, User

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(parent_dir, "logs", "nuki_web.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('nuki_web')

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.urandom(24)  # Required for session and flash messages

# Provide common template variables
@app.context_processor
def inject_now():
    return {'now': datetime.now()}

# Load configuration
config = ConfigManager(parent_dir)
api = NukiAPI(config)
tracker = ActivityTracker(parent_dir)
user_db = UserDatabase(parent_dir)

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

# Apply theme to all responses
@app.after_request
def apply_theme(response):
    if 'logged_in' in session and session.get('theme') == 'dark':
        # Only apply to HTML responses
        if response.content_type and 'text/html' in response.content_type:
            response_data = response.get_data(as_text=True)
            # Add dark-theme class to body
            response_data = response_data.replace('<body>', '<body class="dark-theme">')
            response.set_data(response_data)
    return response

# Routes
@app.route('/')
@login_required
def index():
    """Dashboard home page"""
    return render_template('index.html')

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
            session['theme'] = user_data.get('theme', 'light')
            
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

@app.route('/profile')
@login_required
def profile():
    """User profile page"""
    return render_template('profile.html')

@app.route('/api/theme', methods=['POST'])
@login_required
def update_theme():
    """API endpoint to update user theme only (no password required)"""
    try:
        data = request.json
        username = session.get('username')
        theme = data.get('theme')
        
        # Update theme
        if theme:
            user_db.update_theme(username, theme)
            session['theme'] = theme
        
        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Error updating theme: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/profile', methods=['POST'])
@login_required
def update_profile():
    """API endpoint to update user profile"""
    try:
        data = request.json
        username = session.get('username')
        current_password = data.get('current_password')
        new_password = data.get('new_password')
        theme = data.get('theme')
        
        # Verify current password
        if not user_db.authenticate(username, current_password):
            return jsonify({"error": "Current password is incorrect"}), 401
        
        # Update password
        if new_password:
            user_db.update_password(username, new_password)
        
        # Update theme
        if theme:
            user_db.update_theme(username, theme)
            session['theme'] = theme
        
        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Error updating profile: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/users/manage')
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
            state_name = state.get('stateName', 'Unknown')
            
            # Get battery info
            battery_critical = state.get('batteryCritical', False)
            battery_charging = state.get('batteryCharging', False)
            
            # Create status object
            status = {
                'id': lock_id,
                'name': lock_name,
                'state': state_name,
                'battery_critical': battery_critical,
                'battery_charging': battery_charging,
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
@login_required
def notifications():
    """Notification settings page"""
    return render_template('notifications.html')

@app.route('/api/notifications/settings', methods=['GET'])
@login_required
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
    """Configuration page"""
    return render_template('config.html')

@app.route('/api/config', methods=['GET'])
@admin_required
def get_config():
    """API endpoint to get configuration"""
    try:
        # Get configuration
        config_data = {
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
                'smtp_server': config.smtp_server,
                'smtp_port': config.smtp_port,
                'sender': config.email_sender,
                'recipient': config.email_recipient,
                'use_html': config.use_html_email,
                'subject_prefix': config.email_subject_prefix
            },
            'telegram': {
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
    try:
        # Get current config file path
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config_path = os.path.join(base_dir, "config", "config.ini")
        
        # Import the configuration utility functions
        sys.path.insert(0, os.path.join(parent_dir, "scripts"))
        from configure import update_config as update_config_func
        
        # Get data from request
        data = request.json
        
        # Update configuration
        for section, options in data.items():
            for option, value in options.items():
                # Convert boolean values to strings
                if isinstance(value, bool):
                    value = str(value).lower()
                
                # Update config
                update_config_func(config_path, section, option, str(value))
        
        # Reload configuration
        global config, api
        config = ConfigManager(parent_dir)
        api = NukiAPI(config)
        
        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Error updating configuration: {e}")
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

# Main entry point
if __name__ == '__main__':
    # Create logger directory if it doesn't exist
    os.makedirs(os.path.join(parent_dir, "logs"), exist_ok=True)
    
    # Ensure the users.json file exists and has the admin user
    if not user_db.get_user('admin'):
        user_db.add_user('admin', 'nukiadmin', 'admin', True)
    
    # Run the app
    app.run(debug=True, host='0.0.0.0', port=5000)
