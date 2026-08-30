"""Tests for the admin backup export/import feature."""
import json
import pytest

import web.app


@pytest.fixture
def logged_in_admin(app):
    app.post('/login', data={'username': 'admin', 'password': 'nukiadmin'})
    return app


def test_export_masks_secrets_by_default(logged_in_admin):
    response = logged_in_admin.get('/api/admin/backup/export')
    assert response.status_code == 200
    bundle = json.loads(response.data)
    assert bundle['include_secrets'] is False
    assert bundle['credentials']['Nuki']['api_token'] == '***'
    # Users are exported without credential material
    assert 'password_hash' not in bundle['users']['admin']
    assert 'passkeys' not in bundle['users']['admin']


def test_export_with_secrets_is_full(logged_in_admin):
    response = logged_in_admin.get('/api/admin/backup/export?include_secrets=true')
    bundle = json.loads(response.data)
    assert bundle['include_secrets'] is True
    assert bundle['credentials']['Nuki']['api_token'] == 'test_token'
    assert bundle['users']['admin']['password_hash']


def test_export_requires_admin(app):
    assert app.get('/api/admin/backup/export').status_code == 302


def test_import_requires_confirmation(logged_in_admin):
    response = logged_in_admin.post('/api/admin/backup/import', json={
        'backup': {'app': 'nuki-smart-lock-notification', 'config': {}},
        'sections': {'config': True},
    })
    assert response.status_code == 400
    assert 'confirm' in json.loads(response.data)['error'].lower()


def test_import_rejects_foreign_backup(logged_in_admin):
    response = logged_in_admin.post('/api/admin/backup/import', json={
        'confirm': True,
        'backup': {'app': 'something-else', 'config': {}},
        'sections': {'config': True},
    })
    assert response.status_code == 400


def test_import_refuses_masked_credentials(logged_in_admin):
    response = logged_in_admin.post('/api/admin/backup/import', json={
        'confirm': True,
        'backup': {
            'app': 'nuki-smart-lock-notification',
            'credentials': {'Nuki': {'api_token': '***'}},
        },
        'sections': {'credentials': True},
    })
    assert response.status_code == 400
    assert 'masked' in json.loads(response.data)['error'].lower()


def test_import_refuses_users_without_working_admin(logged_in_admin):
    """An import that would leave no admin with a sign-in method is refused."""
    response = logged_in_admin.post('/api/admin/backup/import', json={
        'confirm': True,
        'backup': {
            'app': 'nuki-smart-lock-notification',
            'users': {'agent1': {'role': 'agent', 'password_hash': 'x'}},
        },
        'sections': {'users': True},
    })
    assert response.status_code == 400
    assert 'admin' in json.loads(response.data)['error'].lower()


def test_import_refuses_removing_own_account(logged_in_admin):
    response = logged_in_admin.post('/api/admin/backup/import', json={
        'confirm': True,
        'backup': {
            'app': 'nuki-smart-lock-notification',
            'users': {'other': {'role': 'admin', 'password_hash': 'x'}},
        },
        'sections': {'users': True},
    })
    assert response.status_code == 400
    assert 'own account' in json.loads(response.data)['error'].lower()


def test_export_import_roundtrip_restores_settings(logged_in_admin):
    # 1. export with secrets
    export = json.loads(logged_in_admin.get('/api/admin/backup/export?include_secrets=true').data)

    # 2. damage the live config
    web.app.config.config.set('General', 'polling_interval', '123')

    # 3. restore
    response = logged_in_admin.post('/api/admin/backup/import', json={
        'confirm': True,
        'backup': export,
        'sections': {'config': True, 'credentials': True},
    })
    assert response.status_code == 200
    assert 'config' in json.loads(response.data)['applied']

    # 4. values restored
    assert web.app.config.config.get('General', 'polling_interval', fallback='') == '60'
    assert web.app.config.credentials.get('Nuki', 'api_token', fallback='') == 'test_token'
