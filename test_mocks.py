import pytest
import os
import json
import time
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

# Mock API responses
class MockAPIResponse:
    def __init__(self, data, status_code=200):
        self.data = data
        self.status_code = status_code
        
    def json(self):
        return self.data

@pytest.fixture
def mock_api():
    """Mock the Nuki API"""
    with patch('scripts.nuki.api.NukiAPI') as mock:
        # Set up mock responses
        api_instance = mock.return_value
        
        # Mock smartlocks
        api_instance.get_smartlocks.return_value = [
            {
                'smartlockId': '12345',
                'name': 'Front Door',
                'state': {
                    'stateName': 'locked',
                    'batteryCritical': False,
                    'batteryCharging': False
                }
            }
        ]
        
        # Mock logs
        api_instance.get_smartlock_logs.return_value = [
            {
                'id': '1',
                'action': 1,  # Unlock
                'trigger': 4,  # App
                'authId': '101',
                'date': datetime.now().isoformat()
            },
            {
                'id': '2',
                'action': 2,  # Lock
                'trigger': 6,  # Auto Lock
                'authId': None,
                'date': (datetime.now() - timedelta(hours=1)).isoformat()
            }
        ]
        
        # Mock users
        api_instance.get_users.return_value = [
            {
                'id': '101',
                'name': 'John Doe',
                'type': 'app',
                'enabled': True
            },
            {
                'id': '102',
                'name': 'Jane Smith',
                'type': 'app',
                'enabled': True
            }
        ]
        
        # Mock add_temporary_code
        api_instance.add_temporary_code.return_value = {
            'success': True,
            'auth_id': '201'
        }
        
        # Mock remove_code
        api_instance.remove_code.return_value = {
            'success': True
        }
        
        # Mock find_auth_id_by_code
        api_instance.find_auth_id_by_code.return_value = '201'
        
        # Mock parse_date
        api_instance.parse_date.side_effect = lambda date_str: datetime.fromisoformat(date_str) if date_str else None
        
        # Mock get_action_description
        api_instance.get_action_description.side_effect = lambda event: 'Unlock' if event.get('action') == 1 else 'Lock'
        
        # Mock get_trigger_description
        api_instance.get_trigger_description.side_effect = lambda trigger: 'App' if trigger == 4 else 'Auto Lock'
        
        # Mock get_user_name
        api_instance.get_user_name.side_effect = lambda auth_id: 'John Doe' if auth_id == '101' else 'Unknown User'
        
        yield api_instance

# Override the app fixture to use the mock API
@pytest.fixture
def app_with_mocks(app, mock_api):
    """Create a test Flask app with mock API"""
    from web.app import app as flask_app
    
    # Replace the API instance
    import web.app
    web.app.api = mock_api
    
    # Return test client
    with flask_app.test_client() as client:
        with flask_app.app_context():
            yield client
