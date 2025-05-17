# Nuki Smart Lock Notification System - Refactoring Examples

This document provides concrete examples of code refactoring for key components of the Nuki Smart Lock Notification System. These examples demonstrate the recommended approach to restructuring and improving the codebase.

## 1. API Module Refactoring

### Current Structure (`scripts/nuki/api.py`):
```python
import requests
import logging
import time
from datetime import datetime

logger = logging.getLogger('nuki_monitor')

class NukiAPI:
    def __init__(self, config):
        self.config = config
        self.action_map = {
            # ... action map ...
        }
        self.trigger_map = {
            # ... trigger map ...
        }
        self.user_cache = {}
        self.user_cache_timestamp = 0
        self.user_cache_timeout = config.user_cache_timeout
    
    def _make_request(self, method, url, params=None, json=None, retry=True):
        # ... request handling code ...
    
    def get_action_description(self, event):
        # ... action description code ...
    
    # ... more methods ...
```

### New Structure:

#### 1. Core API Client (`app/api/nuki_api.py`):
```python
import requests
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Any, Union

from app.config import settings
from app.utils.logging import get_logger
from app.utils.date_utils import parse_date

logger = get_logger(__name__)

class NukiAPI:
    """
    Client for interacting with the Nuki Web API.
    
    Handles authentication, request retries, and provides
    methods for all available API endpoints.
    """
    
    # Action type mapping
    ACTION_TYPES = {
        1: "Unlock",
        2: "Lock",
        3: "Unlatch",
        4: "Lock 'n' Go",
        5: "Lock 'n' Go with unlatch",
        6: "Full Lock"
    }
    
    # Trigger source mapping
    TRIGGER_TYPES = {
        0: "System",
        1: "Manual",
        2: "Button",
        3: "Automatic",
        4: "App",
        5: "Website",
        6: "Auto Lock",
        7: "Time Control"
    }
    
    def __init__(self, config):
        """
        Initialize the Nuki API client.
        
        Args:
            config: Configuration object with API settings
        """
        self.config = config
        self.base_url = "https://api.nuki.io"
        self.headers = {
            "Authorization": f"Bearer {config.api_token}",
            "Accept": "application/json"
        }
        
        # User cache
        self._user_cache = {}
        self._user_cache_timestamp = 0
        self._user_cache_timeout = config.user_cache_timeout
    
    def _make_request(self, 
                     method: str, 
                     endpoint: str, 
                     params: Optional[Dict] = None, 
                     json: Optional[Dict] = None, 
                     retry: bool = True) -> Optional[Dict]:
        """
        Make an API request with retry logic.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (without base URL)
            params: Query parameters
            json: JSON body for POST/PUT requests
            retry: Whether to retry failed requests
            
        Returns:
            Response JSON or None if request failed
        """
        url = f"{self.base_url}{endpoint}"
        max_retries = self.config.max_retries if retry else 1
        retry_delay = self.config.retry_delay
        
        logger.debug(f"Making {method} request to {url}")
        
        for attempt in range(max_retries):
            try:
                response = requests.request(
                    method=method,
                    url=url,
                    headers=self.headers,
                    params=params,
                    json=json,
                    timeout=30
                )
                
                logger.debug(f"Response status: {response.status_code}")
                
                # Handle rate limiting
                if response.status_code == 429:
                    wait_time = int(response.headers.get('Retry-After', retry_delay))
                    logger.warning(f"Rate limited. Waiting {wait_time} seconds before retry.")
                    time.sleep(wait_time)
                    continue
                
                # Handle authentication errors
                if response.status_code == 401:
                    self._handle_auth_error(response)
                    return None
                
                # Raise exception for other error codes
                response.raise_for_status()
                return response.json()
                
            except requests.exceptions.RequestException as e:
                error_msg = f"API request failed: {str(e)}"
                if hasattr(e, 'response') and hasattr(e.response, 'text'):
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
    
    def _handle_auth_error(self, response):
        """Handle authentication errors and provide helpful guidance."""
        error_msg = "API Authentication Failed: Your Nuki API token appears to be invalid or expired"
        response_text = ""
        
        try:
            json_resp = response.json()
            if "detailMessage" in json_resp:
                error_msg += f": {json_resp['detailMessage']}"
                response_text = json_resp
        except:
            if hasattr(response, 'text'):
                response_text = response.text
        
        logger.error(error_msg)
        if response_text:
            logger.error(f"Response: {response_text}")
            
        # Provide help message
        logger.warning("To fix this issue:")
        logger.warning("1. Use the token manager to generate a new API token")
        logger.warning("2. Update your credentials.ini file")
        logger.warning("3. Restart the application")
        
    def get_smartlocks(self) -> List[Dict]:
        """
        Get all smartlocks associated with the account.
        
        Returns:
            List of smartlock objects
        """
        result = self._make_request('GET', "/smartlock")
        return result or []
    
    # ... more methods ...
```

#### 2. API Models (`app/models/api_models.py`):
```python
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from datetime import datetime


@dataclass
class SmartLock:
    """Represents a Nuki Smart Lock device."""
    id: str
    name: str
    state: Dict
    type: int
    
    @property
    def is_locked(self) -> bool:
        """Check if the lock is currently locked."""
        return self.state.get('state') == 1
    
    @property
    def battery_critical(self) -> bool:
        """Check if battery level is critical."""
        return self.state.get('batteryCritical', False)


@dataclass
class LockEvent:
    """Represents a lock activity event."""
    id: str
    lock_id: str
    action: int
    trigger: int
    name: str
    date: datetime
    auth_id: Optional[str] = None
    
    @property
    def action_name(self) -> str:
        """Get human-readable action name."""
        from app.api.nuki_api import NukiAPI
        return NukiAPI.ACTION_TYPES.get(self.action, "Unknown Action")
    
    @property
    def trigger_name(self) -> str:
        """Get human-readable trigger name."""
        from app.api.nuki_api import NukiAPI
        return NukiAPI.TRIGGER_TYPES.get(self.trigger, "Unknown Trigger")
```

#### 3. API Utilities (`app/utils/date_utils.py`):
```python
from datetime import datetime
import logging
from typing import Optional

logger = logging.getLogger(__name__)

def parse_date(date_str) -> Optional[datetime]:
    """
    Parse date from various formats to datetime.
    
    Supports:
    - ISO format strings
    - Unix timestamps (seconds or milliseconds)
    
    Args:
        date_str: Date string or timestamp
        
    Returns:
        Datetime object or None if parsing fails
    """
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
```

## 2. Configuration Module Refactoring

### Current Structure (`scripts/nuki/config.py`):
```python
import os
import configparser
import logging
import sys

logger = logging.getLogger('nuki_monitor')

class ConfigManager:
    def __init__(self, base_dir):
        self.base_dir = base_dir
        self.config_path = os.path.join(self.base_dir, "config", "config.ini")
        self.credentials_path = os.path.join(self.base_dir, "config", "credentials.ini")
        
        # ... more initialization code ...
        
        # Configuration settings
        self.notification_type = self.config.get('General', 'notification_type', fallback='both')
        self.polling_interval = self.config.getint('General', 'polling_interval', fallback=60)
        # ... more settings ...
    
    def _parse_list(self, value_str):
        # ... parsing method ...
    
    def _load_config(self):
        # ... loading method ...
        
    def _load_credentials(self):
        # ... loading method ...
    
    # ... more methods ...
```

### New Structure:

#### 1. Settings Manager (`app/config/settings.py`):
```python
import os
import configparser
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

from app.utils.logging import setup_logger
from app.config.validators import validate_config

# Set up logger
logger = setup_logger(__name__)

class Settings:
    """
    Manages application settings.
    
    Handles loading configuration from files, environment variables,
    and provides access to settings values.
    """
    
    def __init__(self, base_dir: Optional[str] = None):
        """
        Initialize settings manager.
        
        Args:
            base_dir: Base directory for application
        """
        # Determine base directory
        self.base_dir = base_dir or os.getenv('APP_DIR') or os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        # Configuration file paths
        config_dir = os.getenv('CONFIG_DIR') or os.path.join(self.base_dir, "config")
        self.config_path = os.path.join(config_dir, "config.ini")
        self.credentials_path = os.path.join(config_dir, "credentials.ini")
        
        # Ensure directories exist
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        
        # Load configuration
        self.config = self._load_config()
        self.credentials = self._load_credentials()
        
        # Validate configuration
        self.validation_errors = validate_config(self.config, self.credentials)
        if self.validation_errors:
            for error in self.validation_errors:
                logger.error(f"Configuration error: {error}")
        
        # Load settings from configuration
        self._load_settings()
    
    def _load_settings(self):
        """Load all settings from configuration files."""
        # General settings
        self.notification_type = self.config.get('General', 'notification_type', fallback='both')
        self.polling_interval = self.config.getint('General', 'polling_interval', fallback=60)
        
        # API settings
        self.api_token = self.credentials.get('Nuki', 'api_token', fallback='')
        self.base_url = "https://api.nuki.io"
        
        # Smartlock settings
        self.smartlock_id = self.config.get('Nuki', 'smartlock_id', fallback='')
        self.use_explicit_id = self.config.getboolean('Nuki', 'use_explicit_id', fallback=False)
        
        # Email settings
        self.smtp_server = self.config.get('Email', 'smtp_server', fallback='')
        self.smtp_port = self.config.getint('Email', 'smtp_port', fallback=587)
        self.email_username = self.credentials.get('Email', 'username', fallback='')
        self.email_password = self.credentials.get('Email', 'password', fallback='')
        self.email_sender = self.config.get('Email', 'sender', fallback='')
        self.email_recipient = self.config.get('Email', 'recipient', fallback='')
        self.use_html_email = self.config.getboolean('Email', 'use_html', fallback=True)
        self.email_subject_prefix = self.config.get('Email', 'subject_prefix', fallback='Nuki Alert')
        
        # Telegram settings
        self.telegram_bot_token = self.credentials.get('Telegram', 'bot_token', fallback='')
        self.telegram_chat_id = self.config.get('Telegram', 'chat_id', fallback='')
        self.telegram_use_emoji = self.config.getboolean('Telegram', 'use_emoji', fallback=True)
        self.telegram_format = self.config.get('Telegram', 'format', fallback='detailed')
        
        # Advanced settings
        self.debug_mode = self.config.getboolean('Advanced', 'debug_mode', fallback=False)
        self.user_cache_timeout = self.config.getint('Advanced', 'user_cache_timeout', fallback=3600)
        self.retry_on_failure = self.config.getboolean('Advanced', 'retry_on_failure', fallback=True)
        self.max_retries = self.config.getint('Advanced', 'max_retries', fallback=3)
        self.retry_delay = self.config.getint('Advanced', 'retry_delay', fallback=5)
        
        # Set debug logging if enabled
        if self.debug_mode:
            for handler in logger.handlers:
                handler.setLevel(logging.DEBUG)
            logger.setLevel(logging.DEBUG)
            logger.debug("Debug logging enabled")
    
    def _load_config(self):
        """Load the main configuration file."""
        config = configparser.ConfigParser()
        
        try:
            if os.path.exists(self.config_path):
                if not os.access(self.config_path, os.R_OK):
                    raise PermissionError(f"Cannot read configuration file: {self.config_path}")
                config.read(self.config_path)
                logger.info(f"Loaded configuration from {self.config_path}")
            else:
                logger.warning(f"Config file not found at {self.config_path}, creating default")
                self._create_default_config(config)
                self._save_config(config, self.config_path)
        except Exception as e:
            logger.error(f"Error loading config file: {e}")
            self._create_default_config(config)
            
        return config
    
    # ... additional methods ...
```

#### 2. Configuration Validators (`app/config/validators.py`):
```python
import configparser
import re
from typing import List, Dict, Any, Optional

def validate_config(config: configparser.ConfigParser, 
                    credentials: configparser.ConfigParser) -> List[str]:
    """
    Validate configuration and credentials.
    
    Args:
        config: Configuration object
        credentials: Credentials object
        
    Returns:
        List of validation error messages
    """
    errors = []
    
    # Check API token
    api_token = credentials.get('Nuki', 'api_token', fallback='')
    if not api_token:
        errors.append("API token is missing. Please set it in credentials.ini")
    
    # Check notification settings
    notification_type = config.get('General', 'notification_type', fallback='')
    if notification_type not in ['email', 'telegram', 'both', '']:
        errors.append(f"Invalid notification_type: {notification_type}. Must be 'email', 'telegram', or 'both'")
    
    # Check email settings if email notifications are enabled
    if notification_type in ['email', 'both']:
        smtp_server = config.get('Email', 'smtp_server', fallback='')
        if not smtp_server:
            errors.append("SMTP server is required for email notifications")
        
        email_recipient = config.get('Email', 'recipient', fallback='')
        if not email_recipient:
            errors.append("Email recipient is required for email notifications")
        elif not is_valid_email(email_recipient):
            errors.append(f"Invalid email recipient: {email_recipient}")
    
    # Check Telegram settings if Telegram notifications are enabled
    if notification_type in ['telegram', 'both']:
        telegram_bot_token = credentials.get('Telegram', 'bot_token', fallback='')
        if not telegram_bot_token:
            errors.append("Telegram bot token is required for Telegram notifications")
        
        telegram_chat_id = config.get('Telegram', 'chat_id', fallback='')
        if not telegram_chat_id:
            errors.append("Telegram chat ID is required for Telegram notifications")
    
    return errors

def is_valid_email(email: str) -> bool:
    """
    Validate email address format.
    
    Args:
        email: Email address to validate
        
    Returns:
        True if valid, False otherwise
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))
```

## 3. Web Application Refactoring

### Current Structure (`web/app.py`):
```python
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
from flask_session import Session

# ... imports and setup ...

app = Flask(__name__)
# ... app configuration ...

# Load configuration
config = ConfigManager(parent_dir)
api = NukiAPI(config)
tracker = ActivityTracker(parent_dir)
user_db = UserDatabase(parent_dir)
temp_code_db = TemporaryCodeDatabase(parent_dir)

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # ... authentication logic ...
    return decorated_function

# Routes
@app.route('/')
@login_required
def index():
    """Dashboard home page"""
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    # ... login logic ...

# ... many more routes ...

# Main entry point
if __name__ == '__main__':
    # ... setup code ...
    app.run(debug=True, host='0.0.0.0', port=5000)
```

### New Structure:

#### 1. Core Flask App (`app/web/app.py`):
```python
import os
import sys
import logging
from flask import Flask
from flask_session import Session
from datetime import timedelta

from app.config.settings import Settings
from app.web.middleware.auth import setup_auth
from app.web.middleware.error_handlers import setup_error_handlers
from app.web.middleware.theme import setup_theme_handler
from app.web.routes import register_routes
from app.utils.logging import setup_logger

logger = setup_logger(__name__)

def create_app(settings=None):
    """
    Create and configure the Flask application.
    
    Args:
        settings: Application settings
        
    Returns:
        Configured Flask application
    """
    # Initialize app
    app = Flask(__name__)
    
    # Load settings
    settings = settings or Settings()
    
    # Configure app
    app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))
    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['SESSION_FILE_DIR'] = os.environ.get('SESSION_FILE_DIR', 
                                                  os.path.join(settings.base_dir, 'flask_session'))
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)
    app.config['SESSION_COOKIE_SECURE'] = settings.session_cookie_secure
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    
    # Initialize Flask-Session
    Session(app)
    
    # Register middleware
    setup_auth(app)
    setup_error_handlers(app)
    setup_theme_handler(app)
    
    # Register routes
    register_routes(app, settings)
    
    # Configure logging
    if settings.debug_mode:
        app.logger.setLevel(logging.DEBUG)
    
    return app
```

#### 2. Route Registration (`app/web/routes/__init__.py`):
```python
from app.web.routes.admin import register_admin_routes
from app.web.routes.api import register_api_routes
from app.web.routes.auth import register_auth_routes
from app.web.routes.dashboard import register_dashboard_routes
from app.web.routes.activity import register_activity_routes

def register_routes(app, settings):
    """
    Register all application routes.
    
    Args:
        app: Flask application
        settings: Application settings
    """
    # Register route modules
    register_dashboard_routes(app, settings)
    register_auth_routes(app, settings)
    register_api_routes(app, settings)
    register_admin_routes(app, settings)
    register_activity_routes(app, settings)
```

#### 3. Authentication Routes (`app/web/routes/auth.py`):
```python
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.models.user import UserDatabase
from app.web.middleware.auth import login_required

def register_auth_routes(app, settings):
    """
    Register authentication routes.
    
    Args:
        app: Flask application
        settings: Application settings
    """
    # Initialize database
    user_db = UserDatabase(settings.base_dir)
    
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
                
                session.permanent = True
                
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
```

#### 4. Authentication Middleware (`app/web/middleware/auth.py`):
```python
from functools import wraps
from flask import session, redirect, url_for, flash, request

def login_required(f):
    """Decorator to require login for a route."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            flash('Please log in to access this page')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator to require admin privileges for a route."""
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

def agent_access_required(f):
    """Decorator to require agent or admin privileges for a route."""
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

def setup_auth(app):
    """Set up authentication for the application."""
    
    @app.before_request
    def make_session_permanent():
        """Make sessions permanent by default."""
        session.permanent = True
```

## 4. Docker Configuration Refactoring

### Current Structure (`docker-compose.yml`):
```yaml
services:
  nuki-monitor:
    build:
      context: .
      dockerfile: Dockerfile.monitor
    container_name: nuki-monitor
    restart: unless-stopped
    volumes:
      - ./config:/app/config:rw
      - ./logs:/app/logs:rw
      - ./data:/app/data:rw
      - ./flask_session:/app/flask_session:rw
    environment:
      - CONFIG_DIR=/app/config
      - LOGS_DIR=/app/logs
      - TZ=Europe/London
      - DEBUG=true
      - DEFAULT_THEME=dark
      - SECRET_KEY=nuki-smart-lock-dashboard-fixed-key
    networks:
      - nuki-network
    healthcheck:
      test: ["CMD", "bash", "-c", "python /app/scripts/health_monitor.py || exit 0"]
      interval: 5m
      timeout: 30s
      retries: 3
      start_period: 60s
    user: root
    # Add resource limits for better performance
    deploy:
      resources:
        limits:
          cpus: '0.50'
          memory: 256M
        reservations:
          cpus: '0.25'
          memory: 128M

  nuki-web:
    build:
      context: .
      dockerfile: Dockerfile.web
    container_name: nuki-web
    restart: unless-stopped
    ports:
      - "5000:5000"
    volumes:
      - ./config:/app/config:rw
      - ./logs:/app/logs:rw
      - ./data:/app/data:rw
      - ./flask_session:/app/flask_session:rw
    environment:
      - CONFIG_DIR=/app/config
      - LOGS_DIR=/app/logs
      - FLASK_APP=web/app.py
      - FLASK_ENV=production
      - TZ=Europe/London
      - DEFAULT_THEME=dark
      - SECRET_KEY=nuki-smart-lock-dashboard-fixed-key
    networks:
      - nuki-network
    depends_on:
      nuki-monitor:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
      interval: 1m
      timeout: 10s
      retries: 3
      start_period: 20s
    # Add resource limits for better performance
    deploy:
      resources:
        limits:
          cpus: '0.50'
          memory: 256M
        reservations:
          cpus: '0.25'
          memory: 128M

networks:
  nuki-network:
    driver: bridge

volumes:
  nuki_data:
    driver: local
```

### New Structure (`docker-compose.yml`):
```yaml
version: '3.8'

services:
  nuki-monitor:
    build:
      context: .
      dockerfile: docker/monitor/Dockerfile
    container_name: nuki-monitor
    restart: unless-stopped
    volumes:
      - nuki_config:/app/config:rw
      - nuki_logs:/app/logs:rw
      - nuki_data:/app/data:rw
      - nuki_sessions:/app/flask_session:rw
    environment:
      - CONFIG_DIR=/app/config
      - LOGS_DIR=/app/logs
      - DATA_DIR=/app/data
      - TZ=${TZ:-Europe/London}
      - DEBUG=${DEBUG:-false}
      - DEFAULT_THEME=${DEFAULT_THEME:-dark}
      - SECRET_KEY=${SECRET_KEY:-changeme_in_production}
    networks:
      - nuki-network
    healthcheck:
      test: ["CMD", "python", "/app/cli/health_check.py", "--service=monitor"]
      interval: 5m
      timeout: 30s
      retries: 3
      start_period: 60s
    deploy:
      resources:
        limits:
          cpus: '0.50'
          memory: 256M
        reservations:
          cpus: '0.25'
          memory: 128M
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  nuki-web:
    build:
      context: .
      dockerfile: docker/web/Dockerfile
    container_name: nuki-web
    restart: unless-stopped
    ports:
      - "${WEB_PORT:-5000}:5000"
    volumes:
      - nuki_config:/app/config:rw
      - nuki_logs:/app/logs:rw
      - nuki_data:/app/data:rw
      - nuki_sessions:/app/flask_session:rw
    environment:
      - CONFIG_DIR=/app/config
      - LOGS_DIR=/app/logs
      - DATA_DIR=/app/data
      - TZ=${TZ:-Europe/London}
      - DEBUG=${DEBUG:-false}
      - DEFAULT_THEME=${DEFAULT_THEME:-dark}
      - SECRET_KEY=${SECRET_KEY:-changeme_in_production}
      - FLASK_APP=app.web.app:create_app()
      - WORKERS=${WEB_WORKERS:-2}
    networks:
      - nuki-network
    depends_on:
      nuki-monitor:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
      interval: 1m
      timeout: 10s
      retries: 3
      start_period: 20s
    deploy:
      resources:
        limits:
          cpus: '0.50'
          memory: 256M
        reservations:
          cpus: '0.25'
          memory: 128M
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

networks:
  nuki-network:
    driver: bridge

volumes:
  nuki_config:
    name: nuki_config
    driver: local
  nuki_logs:
    name: nuki_logs
    driver: local
  nuki_data:
    name: nuki_data
    driver: local
  nuki_sessions:
    name: nuki_sessions
    driver: local
```

### Monitor Dockerfile (`docker/monitor/Dockerfile`):
```dockerfile
FROM python:3.9-slim-bullseye

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# Create a non-root user to run the application
RUN groupadd -r nuki && \
    useradd -r -g nuki -s /bin/bash -d /home/nuki nuki && \
    mkdir -p /home/nuki && \
    chown -R nuki:nuki /home/nuki

# Create application directories with proper permissions
RUN mkdir -p /app/logs /app/data /app/config /app/flask_session && \
    chown -R nuki:nuki /app

# Copy application code
COPY --chown=nuki:nuki app /app/app
COPY --chown=nuki:nuki cli /app/cli
COPY --chown=nuki:nuki config /app/config
COPY --chown=nuki:nuki docker/monitor/entrypoint.sh /app/entrypoint.sh

# Make the entrypoint script executable
RUN chmod +x /app/entrypoint.sh

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV LOG_LEVEL=INFO

# Switch to non-root user
USER nuki

# Health check
HEALTHCHECK --interval=5m --timeout=30s --start-period=60s --retries=3 \
    CMD python /app/cli/health_check.py --service=monitor || exit 1

# Run the monitor script
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["python", "/app/cli/nuki_monitor.py"]
```

### Monitor Entrypoint Script (`docker/monitor/entrypoint.sh`):
```bash
#!/bin/bash
set -e

echo "Starting Nuki Monitor..."

# Check for required directories
for dir in /app/config /app/logs /app/data /app/flask_session; do
    if [ ! -d "$dir" ]; then
        echo "Creating directory: $dir"
        mkdir -p "$dir"
    fi
    
    # Check permissions
    if [ ! -w "$dir" ]; then
        echo "⚠️ Warning: Directory $dir is not writable"
        echo "This may cause issues with the application"
    fi
done

# Check for configuration files
if [ ! -f "/app/config/config.ini" ]; then
    echo "⚠️ Configuration file not found, creating from example"
    if [ -f "/app/config/config.ini.example" ]; then
        cp /app/config/config.ini.example /app/config/config.ini
    else
        echo "❌ Error: Example configuration file not found"
        echo "Please create a config.ini file in the config directory"
    fi
fi

if [ ! -f "/app/config/credentials.ini" ]; then
    echo "⚠️ Credentials file not found, creating from example"
    if [ -f "/app/config/credentials.ini.example" ]; then
        cp /app/config/credentials.ini.example /app/config/credentials.ini
        echo "⚠️ Please edit the credentials.ini file to add your API token"
    else
        echo "❌ Error: Example credentials file not found"
        echo "Please create a credentials.ini file in the config directory"
    fi
fi

# Run health check
echo "Running health check..."
python /app/cli/health_check.py --service=monitor || true

# Start the application
echo "Starting Nuki Monitor application..."
exec "$@"
```

These examples demonstrate the recommended approach for refactoring key components of the Nuki Smart Lock Notification System. Each example shows how to split monolithic code into more maintainable, modular components with proper separation of concerns.

By following these patterns, the entire codebase can be restructured to improve maintainability, readability, and testability while maintaining all existing functionality.
