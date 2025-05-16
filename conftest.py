import os
import sys
import tempfile
import pytest
import json
from pathlib import Path

# Add the project root to the Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'web'))

# Mock data and configs for testing
@pytest.fixture
def mock_config_dir():
    """Create a temporary directory for config files"""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create config directory
        config_dir = os.path.join(temp_dir, 'config')
        os.makedirs(config_dir, exist_ok=True)
        
        # Create logs directory
        logs_dir = os.path.join(temp_dir, 'logs')
        os.makedirs(logs_dir, exist_ok=True)
        
        # Create example config files
        with open(os.path.join(config_dir, 'config.ini'), 'w') as f:
            f.write("""
[General]
notification_type = both
polling_interval = 60

[Notification]
digest_mode = false
digest_interval = 3600
notify_auto_lock = true
notify_system_events = true

[Filter]
excluded_users = 
excluded_actions = 
excluded_triggers = 

[Email]
smtp_server = smtp.example.com
smtp_port = 587
sender = test@example.com
recipient = recipient@example.com
use_html = true
subject_prefix = [Nuki]

[Telegram]
chat_id = 123456789
use_emoji = true
format = markdown

[Advanced]
max_events_per_check = 10
max_historical_events = 50
debug_mode = false
user_cache_timeout = 300
retry_on_failure = true
max_retries = 3
retry_delay = 5
            """)
            
        with open(os.path.join(config_dir, 'credentials.ini'), 'w') as f:
            f.write("""
[API]
token = test_token

[Email]
username = test@example.com
password = test_password

[Telegram]
bot_token = test_bot_token
            """)
            
        # Create users file
        with open(os.path.join(config_dir, 'users.json'), 'w') as f:
            users = {
                "admin": {
                    "password_hash": "pbkdf2:sha256:150000$pSu9azsA$b045ed592b6e72...",
                    "role": "admin",
                    "active": True,
                    "created_at": "2023-01-01T00:00:00",
                    "last_login": None,
                    "theme": "light"
                }
            }
            json.dump(users, f, indent=2)
            
        # Create empty temp_codes file
        with open(os.path.join(config_dir, 'temp_codes.json'), 'w') as f:
            json.dump({}, f, indent=2)
        
        yield temp_dir

@pytest.fixture
def app(mock_config_dir):
    """Create a test Flask app with a temporary config"""
    # Set environment variables
    os.environ['CONFIG_DIR'] = os.path.join(mock_config_dir, 'config')
    os.environ['LOGS_DIR'] = os.path.join(mock_config_dir, 'logs')
    
    # Import the app after setting up environment
    from web.app import app as flask_app
    
    # Configure for testing
    flask_app.config['TESTING'] = True
    flask_app.config['WTF_CSRF_ENABLED'] = False
    
    # Return test client
    with flask_app.test_client() as client:
        with flask_app.app_context():
            yield client
