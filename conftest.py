import os
import sys
import tempfile
import pytest
import json
from pathlib import Path

from werkzeug.security import generate_password_hash

# Add the project root to the Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'web'))

# Mock data and configs for testing
@pytest.fixture
def mock_config_dir():
    """Create a temporary directory with config, logs and data for testing.

    Everything lives inside a temp dir so tests never touch real runtime data.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create directories
        config_dir = os.path.join(temp_dir, 'config')
        logs_dir = os.path.join(temp_dir, 'logs')
        data_dir = os.path.join(temp_dir, 'data')
        for d in (config_dir, logs_dir, data_dir):
            os.makedirs(d, exist_ok=True)

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
[Nuki]
api_token = test_token

[Email]
username = test@example.com
password = test_password

[Telegram]
bot_token = test_bot_token
            """)

        # Create users file (in the DATA dir, matching UserDatabase paths)
        # with a REAL hash so test logins work
        with open(os.path.join(data_dir, 'users.json'), 'w') as f:
            users = {
                "admin": {
                    "password_hash": generate_password_hash('nukiadmin', method='pbkdf2:sha256'),
                    "role": "admin",
                    "active": True,
                    "created_at": "2023-01-01T00:00:00",
                    "last_login": None,
                    "theme": "light"
                }
            }
            json.dump(users, f, indent=2)

        # Create empty temp_codes file
        with open(os.path.join(data_dir, 'temp_codes.json'), 'w') as f:
            json.dump({}, f, indent=2)

        yield temp_dir

@pytest.fixture
def app(mock_config_dir):
    """Create a test Flask app with a temporary config.

    web.app binds its managers (ConfigManager, UserDatabase, ...) at import
    time. Because importing the module happens during test collection (before
    any fixture runs), we rebind those singletons here to per-test temp dirs —
    this keeps tests fully isolated from the real runtime state and from each
    other.
    """
    os.environ['CONFIG_DIR'] = os.path.join(mock_config_dir, 'config')
    os.environ['LOGS_DIR'] = os.path.join(mock_config_dir, 'logs')
    os.environ['DATA_DIR'] = os.path.join(mock_config_dir, 'data')

    import web.app as app_module
    from scripts.nuki.api import NukiAPI
    from scripts.nuki.utils import ActivityTracker
    from web.models import UserDatabase
    from web.temp_codes import TemporaryCodeDatabase

    app_module.config = app_module.ConfigManager(app_module.parent_dir)
    app_module.api = NukiAPI(app_module.config)
    app_module.tracker = ActivityTracker(app_module.config.data_dir)
    app_module.user_db = UserDatabase(app_module.config.data_dir)
    app_module.temp_code_db = TemporaryCodeDatabase(app_module.config.data_dir)

    flask_app = app_module.app

    # Configure for testing
    flask_app.config['TESTING'] = True
    flask_app.config['WTF_CSRF_ENABLED'] = False

    # Return test client
    with flask_app.test_client() as client:
        with flask_app.app_context():
            yield client
