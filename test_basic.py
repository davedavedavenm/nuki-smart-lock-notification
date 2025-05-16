import pytest
import json

def test_health_check(app):
    """Test the health check endpoint"""
    response = app.get('/health')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'healthy'

def test_login_page(app):
    """Test the login page loads"""
    response = app.get('/login')
    assert response.status_code == 200
    assert b'Login' in response.data

def test_login_redirect(app):
    """Test unauthorized access redirects to login"""
    response = app.get('/', follow_redirects=True)
    assert response.status_code == 200
    assert b'Login' in response.data

def test_temp_codes_redirect(app):
    """Test the temporary codes page redirects when not logged in"""
    response = app.get('/temp-codes', follow_redirects=True)
    assert response.status_code == 200
    assert b'Login' in response.data
