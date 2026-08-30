"""Tests for per-user authentication policy (password on/off, passkey policy)."""
import json
import pytest

import web.app
from werkzeug.security import check_password_hash


@pytest.fixture
def logged_in_admin(app):
    app.post('/login', data={'username': 'admin', 'password': 'nukiadmin'})
    return app


def _give_passkey(username='admin'):
    """Register a (fake) passkey directly so policy logic can be tested."""
    from web import passkeys as pk
    user = web.app.user_db.get_user(username)
    pk.ensure_user_handle(user)
    pk.add_passkey(user, b'test-credential', b'\x00' * 16, name='Test key')


def test_new_users_get_default_policy(logged_in_admin):
    auth = web.app.user_db.get_auth('admin')
    assert auth == {'password': True, 'passkey': 'optional'}


def test_remove_password_without_passkey_is_refused(logged_in_admin):
    ok, err = web.app.user_db.set_password_enabled('admin', False)
    assert ok is False
    # Password untouched
    assert web.app.user_db.get_user('admin').get('password_hash')


def test_remove_password_with_passkey(logged_in_admin):
    _give_passkey()
    ok, err = web.app.user_db.set_password_enabled('admin', False)
    assert ok is True, err

    user = web.app.user_db.get_user('admin')
    assert user.get('password_hash') is None  # password removed entirely
    assert web.app.user_db.get_auth('admin')['password'] is False

    # Password login must now be refused without crashing on the removed
    # (None) hash — and without leaking why: wrong credentials always get
    # the generic error, so an attacker can't fingerprint account types.
    logged_in_admin.get('/logout')
    response = logged_in_admin.post('/login', data={
        'username': 'admin', 'password': 'nukiadmin'})
    assert response.status_code == 200
    assert b'Invalid credentials' in response.data


def test_passkey_required_blocks_password_login(logged_in_admin):
    _give_passkey()  # required can only block passwords once a passkey exists,
    # otherwise the user would be locked out entirely
    assert web.app.user_db.set_passkey_policy('admin', 'required')[0] is True
    response = logged_in_admin.post('/login', data={
        'username': 'admin', 'password': 'nukiadmin'})
    assert b'requires passkey' in response.data


def test_cannot_disable_passkeys_without_other_method(logged_in_admin):
    _give_passkey()
    web.app.user_db.set_password_enabled('admin', False)
    ok, err = web.app.user_db.set_passkey_policy('admin', 'disabled')
    assert ok is False
    assert 'refused' in err.lower() or 'sign' in err.lower()


def test_last_admin_not_locked_out(logged_in_admin):
    """Removing the password of the only admin must be refused even with a
    passkey registered... but the guard exists for OTHER admins."""
    _give_passkey()
    # With a passkey the removal is allowed and admin can still log in
    ok, err = web.app.user_db.set_password_enabled('admin', False)
    assert ok is True, err
    assert web.app.user_db._user_can_log_in('admin') is True


def test_policy_api_roundtrip(logged_in_admin):
    response = logged_in_admin.put(
        '/api/users/manage/admin/auth-policy',
        json={'passkey': 'required'})
    assert response.status_code == 200
    assert json.loads(response.data)['auth']['passkey'] == 'required'


def test_policy_api_requires_admin(app):
    response = app.put('/api/users/manage/admin/auth-policy', json={'passkey': 'required'})
    assert response.status_code == 302  # redirected to login


def test_manage_list_exposes_policy(logged_in_admin):
    response = logged_in_admin.get('/api/users/manage')
    users = json.loads(response.data)
    admin = next(u for u in users if u['username'] == 'admin')
    assert admin['auth'] == {'password': True, 'passkey': 'optional'}
    assert admin['has_password'] is True
    assert 'password_hash' not in admin
