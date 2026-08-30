"""Tests for passkey (WebAuthn) support and user-database fail-closed behavior.

Full browser ceremonies can't run in unit tests, so we verify the endpoints'
gating, option shapes, storage helpers, and the corrupt-users.json fail-closed
path.
"""
import json
import os
import pytest

from web import passkeys as pk
from web.models import UserDatabase


@pytest.fixture
def logged_in(app):
    """Log in as the seeded admin and return the client."""
    app.post('/login', data={'username': 'admin', 'password': 'nukiadmin'})
    return app


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

def test_register_begin_requires_login(app):
    app.get('/logout')
    response = app.post('/api/passkeys/register/begin')
    assert response.status_code == 302  # redirected to login


def test_register_begin_returns_options(logged_in):
    response = logged_in.post('/api/passkeys/register/begin')
    assert response.status_code == 200
    options = json.loads(response.data)
    public_key = options['publicKey']
    assert public_key['challenge']
    assert public_key['rp']
    assert public_key['user']['name'] == 'admin'
    assert any(p['alg'] for p in public_key['pubKeyCredParams'])


def test_register_finish_without_state_rejected(logged_in):
    response = logged_in.post('/api/passkeys/register/finish', json={'id': 'x'})
    assert response.status_code == 400


def test_register_begin_twice_replaces_state(logged_in):
    first = json.loads(logged_in.post('/api/passkeys/register/begin').data)
    second = json.loads(logged_in.post('/api/passkeys/register/begin').data)
    assert first['publicKey']['challenge'] != second['publicKey']['challenge']


def test_auth_begin_returns_options(app):
    response = app.post('/api/passkeys/auth/begin')
    assert response.status_code == 200
    options = json.loads(response.data)
    # Usernameless login: no allowCredentials restriction
    assert 'challenge' in options['publicKey']


def test_auth_finish_without_state_rejected(app):
    response = app.post('/api/passkeys/auth/finish', json={'id': 'x'})
    assert response.status_code == 400


def test_delete_unknown_passkey(logged_in):
    response = logged_in.delete('/api/passkeys/unknown-credential-id')
    assert response.status_code == 404


def test_passkey_list_empty(logged_in):
    response = logged_in.get('/api/passkeys')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['passkeys'] == []


# ---------------------------------------------------------------------------
# Storage helpers
# ---------------------------------------------------------------------------

def test_user_handle_is_stable():
    user = {}
    handle1 = pk.ensure_user_handle(user)
    handle2 = pk.ensure_user_handle(user)
    assert handle1 == handle2


def test_add_and_remove_passkey(tmp_path):
    data_dir = tmp_path / 'data'
    data_dir.mkdir()
    db = UserDatabase(str(data_dir))
    db.users['dave'] = {'role': 'admin', 'active': True}
    user = db.get_user('dave')

    pk.add_passkey(user, b'cred-1', b'\x01\x02', name='Yubikey')
    pk.add_passkey(user, b'cred-2', b'\x03\x04')
    assert len(pk.get_passkeys(user)) == 2

    assert pk.find_user_by_credential(db, pk.get_passkeys(user)[0]['id']) == 'dave'

    assert pk.remove_passkey(user, 'not-a-credential') is False
    assert pk.remove_passkey(user, pk.get_passkeys(user)[0]['id']) is True
    assert len(pk.get_passkeys(user)) == 1


def test_find_user_by_credential_missing(tmp_path):
    data_dir = tmp_path / 'data'
    data_dir.mkdir()
    db = UserDatabase(str(data_dir))
    db.users['a'] = {'passkeys': []}
    assert pk.find_user_by_credential(db, 'nope') is None


# ---------------------------------------------------------------------------
# Fail-closed on corrupt users.json
# ---------------------------------------------------------------------------

def test_corrupt_users_file_fails_closed(tmp_path):
    data_dir = tmp_path / 'data'
    data_dir.mkdir()
    (data_dir / 'users.json').write_text('{ this is not valid json')

    db = UserDatabase(str(data_dir))
    assert db.users == {}
    # Setup wizard must NOT reopen on corruption
    assert db.users_exist() is True
    assert db.load_error is not None


def test_missing_users_file_is_fresh_install(tmp_path):
    data_dir = tmp_path / 'data'
    data_dir.mkdir()
    db = UserDatabase(str(data_dir))
    assert db.users_exist() is False
    assert db.load_error is None


def test_non_object_users_file_fails_closed(tmp_path):
    data_dir = tmp_path / 'data'
    data_dir.mkdir()
    (data_dir / 'users.json').write_text('["not", "an", "object"]')

    db = UserDatabase(str(data_dir))
    assert db.users_exist() is True
