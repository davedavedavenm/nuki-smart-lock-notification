import pytest
import json
import time
from datetime import datetime, timedelta
from flask import session

# Import from the test_mocks module
from test_mocks import app_with_mocks, mock_api

def test_admin_login(app_with_mocks):
    """Test admin login"""
    response = app_with_mocks.post('/login', data={
        'username': 'admin',
        'password': 'nukiadmin'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Dashboard' in response.data

def test_temp_codes_page_admin(app_with_mocks):
    """Test admin can access temporary codes page"""
    # Login as admin
    app_with_mocks.post('/login', data={
        'username': 'admin',
        'password': 'nukiadmin'
    })
    
    # Access temp codes page
    response = app_with_mocks.get('/temp-codes')
    assert response.status_code == 200
    assert b'Temporary Access Codes' in response.data

def test_get_temp_codes_admin(app_with_mocks):
    """Test admin can get temporary codes"""
    # Login as admin
    app_with_mocks.post('/login', data={
        'username': 'admin',
        'password': 'nukiadmin'
    })
    
    # Get temp codes
    response = app_with_mocks.get('/api/temp-codes')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert isinstance(data, list)

def test_create_temp_code(app_with_mocks):
    """Test creating a temporary code"""
    # Login as admin
    app_with_mocks.post('/login', data={
        'username': 'admin',
        'password': 'nukiadmin'
    })
    
    # Create temp code
    expiry = (datetime.now() + timedelta(days=1)).isoformat()
    response = app_with_mocks.post('/api/temp-codes', json={
        'code': '1234',
        'name': 'Test Code',
        'expiry': expiry
    })
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['code'] == '1234'
    assert data['name'] == 'Test Code'
    assert 'id' in data
    assert 'auth_id' in data

def test_delete_temp_code(app_with_mocks, monkeypatch):
    """Test deleting a temporary code"""
    # Login as admin
    app_with_mocks.post('/login', data={
        'username': 'admin',
        'password': 'nukiadmin'
    })
    
    # Patch the temp_code_db
    from web.app import temp_code_db
    
    # Add a mock code
    code_id = str(int(time.time()))
    expiry = (datetime.now() + timedelta(days=1)).isoformat()
    temp_code_db.add_code(
        code_id=code_id,
        code='1234',
        name='Test Code',
        created_by='admin',
        expiry=expiry
    )
    
    # Delete the code
    response = app_with_mocks.delete(f'/api/temp-codes/{code_id}')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] == True
