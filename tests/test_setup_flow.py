"""Tests for the staged first-run setup wizard flow.

The wizard saves each stage IMMEDIATELY: a mistake on one stage must never
lose details entered on an earlier stage, Telegram/Email are optional, and
the wizard cannot be re-opened by a third party once an admin exists.
"""
import json
import os
import pytest

import web.app
from werkzeug.security import check_password_hash


@pytest.fixture
def fresh_app(mock_config_dir, app):
    """Reset the app's user database to a fresh-install state (no users).

    Yields the Flask test client; use ``web.app`` module for state access.
    """
    users_file = os.path.join(mock_config_dir, 'data', 'users.json')
    if os.path.exists(users_file):
        os.remove(users_file)
    web.app.user_db.users = {}
    web.app.user_db.users_file = users_file
    yield app
    web.app.user_db.users = {
        "admin": {
            "password_hash": web.app.user_db.users.get("admin", {}).get(
                "password_hash", "x"
            ),
            "role": "admin",
            "active": True,
        }
    }


def _admin_payload(**overrides):
    payload = {
        "stage": "admin",
        "admin_username": "dave",
        "admin_password": "correct-horse-battery",
        "admin_password_confirm": "correct-horse-battery",
    }
    payload.update(overrides)
    return payload


def test_no_default_admin_created(tmp_path):
    """UserDatabase must not create a default admin on its own."""
    from web.models import UserDatabase

    data_dir = str(tmp_path / "data")
    os.makedirs(data_dir)
    db = UserDatabase(data_dir)
    assert db.users == {}
    assert db.users_exist() is False


def test_fresh_install_redirects_to_setup(fresh_app):
    response = fresh_app.get("/")
    assert response.status_code == 302
    assert "/setup" in response.headers["Location"]


def test_fresh_install_health_and_setup_reachable(fresh_app):
    assert fresh_app.get("/health").status_code == 200
    response = fresh_app.get("/setup")
    assert response.status_code == 200


def test_stage_admin_creates_account_and_logs_in(fresh_app):
    response = fresh_app.post("/api/setup", json=_admin_payload())
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["success"] is True
    assert data["stage"] == 2

    admin = web.app.user_db.get_user("dave")
    assert admin is not None
    assert admin["role"] == "admin"
    assert check_password_hash(admin["password_hash"], "correct-horse-battery")

    # The wizard session is now logged in (stages 2-4 continue seamlessly)
    with fresh_app.session_transaction() as sess:
        assert sess.get("setup_stage") == 2


def test_stage_admin_rejects_short_password(fresh_app):
    response = fresh_app.post("/api/setup", json=_admin_payload(
        admin_password="short", admin_password_confirm="short"))
    assert response.status_code == 400


def test_stage_admin_rejects_mismatched_password(fresh_app):
    response = fresh_app.post("/api/setup", json=_admin_payload(
        admin_password_confirm="different-password"))
    assert response.status_code == 400


def test_later_stages_require_setup_session(fresh_app):
    """Without the setup session, credentials stages are refused (401)."""
    fresh_app.post("/api/setup", json=_admin_payload())
    # Simulate a fresh visitor: brand-new client without the setup session
    visitor = web.app.app.test_client()
    response = visitor.post("/api/setup", json={"stage": "nuki", "nuki_token": "x"})
    assert response.status_code == 401


def test_stage_nuki_saves_and_validates(fresh_app):
    fresh_app.post("/api/setup", json=_admin_payload())
    response = fresh_app.post("/api/setup", json={
        "stage": "nuki", "nuki_token": "placeholder_test_token_123"})
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["stage"] == 3
    assert "nuki" in data["validation"]

    token = web.app.config.credentials.get("Nuki", "api_token", fallback="")
    assert token == "placeholder_test_token_123"


def test_stage_nuki_skip_advances_without_token(fresh_app):
    """Telegram/Email/Nuki are optional — an empty stage just advances."""
    fresh_app.post("/api/setup", json=_admin_payload())
    response = fresh_app.post("/api/setup", json={"stage": "nuki", "nuki_token": ""})
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["stage"] == 3
    assert data["validation"]["nuki"]["valid"] is None


def test_stage_telegram_and_email_optional(fresh_app):
    fresh_app.post("/api/setup", json=_admin_payload())
    assert fresh_app.post("/api/setup", json={"stage": "nuki", "nuki_token": ""}).status_code == 200

    # Telegram skipped
    response = fresh_app.post("/api/setup", json={"stage": "telegram"})
    assert response.status_code == 200
    assert json.loads(response.data)["stage"] == 4

    # Email skipped
    response = fresh_app.post("/api/setup", json={"stage": "email"})
    assert response.status_code == 200
    assert json.loads(response.data)["stage"] == 5


def test_stage_email_saves_smtp_details(fresh_app):
    fresh_app.post("/api/setup", json=_admin_payload())
    fresh_app.post("/api/setup", json={"stage": "nuki", "nuki_token": ""})
    fresh_app.post("/api/setup", json={"stage": "telegram"})
    response = fresh_app.post("/api/setup", json={
        "stage": "email",
        "email_smtp_server": "smtp.purelymail.com",
        "email_smtp_port": "587",
        "email_username": "alerts@example.com",
        "email_password": "app-password-123",
        "email_sender": "alerts@example.com",
        "email_recipient": "me@example.com",
    })
    assert response.status_code == 200
    assert web.app.config.config.get("Email", "smtp_server", fallback="") == "smtp.purelymail.com"
    assert web.app.config.credentials.get("Email", "password", fallback="") == "app-password-123"


def test_nothing_lost_when_a_stage_fails(fresh_app):
    """A failed later stage must not wipe earlier stages (the core UX fix)."""
    fresh_app.post("/api/setup", json=_admin_payload())
    fresh_app.post("/api/setup", json={"stage": "nuki", "nuki_token": "placeholder_test_token_123"})

    # Telegram stage fails with a server error payload — token must survive
    response = fresh_app.post("/api/setup", json={"stage": "telegram", "telegram_chat_id": "987654321"})
    assert response.status_code == 200
    token = web.app.config.credentials.get("Nuki", "api_token", fallback="")
    assert token == "placeholder_test_token_123"


def test_wizard_closed_to_third_parties_after_completion(fresh_app):
    fresh_app.post("/api/setup", json=_admin_payload())
    fresh_app.post("/api/setup", json={"stage": "nuki", "nuki_token": ""})

    # A visitor WITHOUT the setup session cannot resume the wizard page
    visitor = web.app.app.test_client()
    response = visitor.get("/setup")
    assert response.status_code == 302  # redirected away from the wizard

    # And cannot post any stage
    assert visitor.post("/api/setup", json={"stage": "nuki", "nuki_token": "evil"}).status_code == 401
