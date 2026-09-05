"""Tests for webhook wake path, quiet hours, door-state tracking, alerts and audit log."""
import os
import json
import time
import pytest
from datetime import datetime

from scripts.nuki.utils import WakeSignal, DoorStateStore
from scripts.nuki.notification import Notifier
from web.audit import AuditLog


class FakeConfig:
    """Minimal config stand-in for Notifier tests"""
    def __init__(self, **kw):
        self.notification_type = 'none'
        self.digest_mode = False
        self.digest_interval = 3600
        self.notify_auto_lock = True
        self.notify_system_events = True
        self.quiet_hours_enabled = False
        self.quiet_start = '22:00'
        self.quiet_end = '07:00'
        self.excluded_users = []
        self.excluded_actions = []
        self.excluded_triggers = []
        self.telegram_bot_token = ''
        self.telegram_chat_id = ''
        self.telegram_use_emoji = False
        self.telegram_format = 'compact'
        self.smtp_server = ''
        self.email_recipient = ''
        self.email_subject_prefix = 'Nuki'
        self.use_html_email = False
        self.__dict__.update(kw)


def make_event(**kw):
    event = {
        'lock_name': 'Front Door',
        'lock_id': 1,
        'event_type': 'Unlock',
        'action': 1,
        'trigger': 4,
        'user_name': 'Dave',
        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'event_id': 999,
    }
    event.update(kw)
    return event


# ---------------------------------------------------------------------------
# WakeSignal
# ---------------------------------------------------------------------------

def test_wake_signal_roundtrip(tmp_path):
    wake = WakeSignal(str(tmp_path))
    assert not wake.consume()
    assert wake.trigger()
    assert wake.consume()
    assert not wake.consume()


# ---------------------------------------------------------------------------
# DoorStateStore
# ---------------------------------------------------------------------------

def test_door_state_store_transitions(tmp_path):
    store = DoorStateStore(str(tmp_path))
    assert store.get(123) is None
    prev, cur = store.update(123, 3)
    assert prev is None and cur == 3
    prev, cur = store.update(123, 4)
    assert prev == 3 and cur == 4
    # persists across instances
    store2 = DoorStateStore(str(tmp_path))
    assert store2.get(123) == 4
    assert DoorStateStore.describe(4) == "Opened"
    assert DoorStateStore.describe(3) == "Closed"


# ---------------------------------------------------------------------------
# Quiet hours
# ---------------------------------------------------------------------------

def test_quiet_hours_disabled():
    n = Notifier(FakeConfig())
    assert not n.in_quiet_hours(datetime(2026, 9, 5, 23, 0))


def test_quiet_hours_overnight_window():
    n = Notifier(FakeConfig(quiet_hours_enabled=True, quiet_start='22:00', quiet_end='07:00'))
    assert n.in_quiet_hours(datetime(2026, 9, 5, 23, 30))
    assert n.in_quiet_hours(datetime(2026, 9, 5, 22, 0))
    assert n.in_quiet_hours(datetime(2026, 9, 5, 6, 59))
    assert not n.in_quiet_hours(datetime(2026, 9, 5, 7, 0))
    assert not n.in_quiet_hours(datetime(2026, 9, 5, 12, 0))


def test_quiet_hours_same_day_window():
    n = Notifier(FakeConfig(quiet_hours_enabled=True, quiet_start='01:00', quiet_end='05:00'))
    assert n.in_quiet_hours(datetime(2026, 9, 5, 3, 0))
    assert not n.in_quiet_hours(datetime(2026, 9, 5, 5, 0))
    assert not n.in_quiet_hours(datetime(2026, 9, 5, 0, 59))


def test_quiet_hours_defers_notification(monkeypatch):
    cfg = FakeConfig(quiet_hours_enabled=True, quiet_start='00:00', quiet_end='23:59')
    n = Notifier(cfg)
    sent = []
    monkeypatch.setattr(n, 'send_telegram', lambda m: sent.append(m) or True)
    result = n.send_notification(make_event())
    assert result is False
    assert len(n.digest_events) == 1
    assert n.quiet_flush_pending
    assert not sent


# ---------------------------------------------------------------------------
# System alerts
# ---------------------------------------------------------------------------

def test_send_alert_uses_telegram_when_configured(monkeypatch):
    cfg = FakeConfig(notification_type='none', telegram_bot_token='t', telegram_chat_id='c')
    n = Notifier(cfg)
    sent = []
    monkeypatch.setattr(n, 'send_telegram', lambda m: sent.append(m) or True)
    monkeypatch.setattr(n, 'send_email', lambda s, b: sent.append(('email', s)) or True)
    assert n.send_alert("test failure alert")
    assert len(sent) == 1 and 'test failure alert' in sent[0]


def test_send_alert_falls_back_to_email(monkeypatch):
    cfg = FakeConfig(smtp_server='smtp.example.com', email_recipient='a@b.c')
    n = Notifier(cfg)
    sent = []
    monkeypatch.setattr(n, 'send_email', lambda s, b: sent.append((s, b)) or True)
    assert n.send_alert("email only alert")
    assert len(sent) == 1


def test_send_alert_no_channel_returns_false():
    n = Notifier(FakeConfig())
    assert not n.send_alert("nowhere to go")


# ---------------------------------------------------------------------------
# AuditLog
# ---------------------------------------------------------------------------

def test_audit_log_record_and_recent(tmp_path):
    audit = AuditLog(str(tmp_path))
    audit.record('login.success', actor='dave', ip='10.0.0.1')
    audit.record('login.failure', actor='eve', status='failure', ip='10.0.0.2')
    entries = audit.recent()
    assert len(entries) == 2
    assert entries[0]['action'] == 'login.failure'  # newest first
    assert entries[1]['actor'] == 'dave'
    failures = audit.recent(status_filter='failure')
    assert len(failures) == 1
    logins = audit.recent(action_filter='login')
    assert len(logins) == 2


def test_audit_log_rotation(tmp_path, monkeypatch):
    import web.audit as audit_mod
    monkeypatch.setattr(audit_mod, 'MAX_BYTES', 500)
    audit = AuditLog(str(tmp_path))
    for i in range(100):
        audit.record(f'action.{i}', detail='x' * 20)
    entries = audit.recent(limit=1000)
    assert 0 < len(entries) < 100
    assert entries[0]['action'] == 'action.99'


# ---------------------------------------------------------------------------
# Webhook endpoint (Flask)
# ---------------------------------------------------------------------------

def _login_admin(client):
    return client.post('/login', data={'username': 'admin', 'password': 'nukiadmin'},
                       follow_redirects=True)


def test_webhook_rejects_bad_secret(app):
    import web.app as app_module
    app_module.config.webhook_secret = 'correct-secret'
    resp = app.post('/webhook/nuki/wrong-secret', json={})
    assert resp.status_code == 403
    entries = app_module.audit.recent(action_filter='webhook.rejected')
    assert len(entries) == 1


def test_webhook_accepts_good_secret_and_wakes(app):
    import web.app as app_module
    app_module.config.webhook_secret = 'correct-secret'
    app_module.config.webhook_enabled = True
    resp = app.post('/webhook/nuki/correct-secret', json={})
    assert resp.status_code == 200
    assert resp.get_json()['status'] == 'ok'
    assert os.path.exists(app_module.wake_signal.path)
    assert app_module.wake_signal.consume()


def test_webhook_valid_secret_but_disabled(app):
    import web.app as app_module
    app_module.config.webhook_secret = 'correct-secret'
    app_module.config.webhook_enabled = False
    resp = app.post('/webhook/nuki/correct-secret', json={})
    assert resp.status_code == 200
    assert resp.get_json()['status'] == 'ignored'
    assert not os.path.exists(app_module.wake_signal.path)


def test_webhook_requires_post(app):
    import web.app as app_module
    app_module.config.webhook_secret = 'correct-secret'
    resp = app.get('/webhook/nuki/correct-secret')
    assert resp.status_code == 405


def test_audit_page_requires_admin(app):
    resp = app.get('/admin/audit', follow_redirects=True)
    assert b'Login' in resp.data
    _login_admin(app)
    resp = app.get('/admin/audit')
    assert resp.status_code == 200


def test_audit_api_returns_entries(app):
    import web.app as app_module
    _login_admin(app)
    app_module.audit.record('test.entry', actor='admin')
    resp = app.get('/api/audit')
    assert resp.status_code == 200
    data = resp.get_json()
    assert any(e['action'] == 'test.entry' for e in data)


def test_failed_login_is_audited_and_alerts(app, monkeypatch):
    import web.app as app_module
    alerts = []
    monkeypatch.setattr(app_module, '_send_alert_async', lambda msg, subject=None: alerts.append(msg))
    with app_module._RATE_LOCK:
        app_module._login_alert_times.clear()
    resp = app.post('/login', data={'username': 'admin', 'password': 'wrongpass'})
    assert resp.status_code == 200
    entries = app_module.audit.recent(action_filter='login.failure')
    assert len(entries) == 1
    assert alerts  # rate limiter allows the first one


# ---------------------------------------------------------------------------
# Filter modes (all / include / exclude)
# ---------------------------------------------------------------------------

def test_filter_mode_all_notifies_everything():
    n = Notifier(FakeConfig(filter_mode='all', excluded_actions=['1']))
    assert not n._should_filter_event(make_event(action=1))


def test_filter_mode_include_allowlist():
    n = Notifier(FakeConfig(filter_mode='include', excluded_actions=['2']))
    assert not n._should_filter_event(make_event(action=2))     # selected -> notify
    assert n._should_filter_event(make_event(action=1))         # not selected -> muted


def test_filter_mode_include_empty_list_means_no_restriction():
    n = Notifier(FakeConfig(filter_mode='include', excluded_actions=[]))
    assert not n._should_filter_event(make_event(action=1))
    assert not n._should_filter_event(make_event(action=2))


def test_filter_mode_include_users_dimension():
    n = Notifier(FakeConfig(filter_mode='include', excluded_users=['Dave']))
    assert not n._should_filter_event(make_event(user_name='Dave'))
    assert n._should_filter_event(make_event(user_name='Jennifer'))


def test_filter_mode_exclude_legacy():
    n = Notifier(FakeConfig(filter_mode='exclude', excluded_actions=['1']))
    assert n._should_filter_event(make_event(action=1))         # selected -> muted
    assert not n._should_filter_event(make_event(action=2))     # rest notify


def test_system_events_toggle_applies_in_all_modes():
    ev = make_event(event_type='Nuki Bridge', trigger=0, action=None)
    n = Notifier(FakeConfig(filter_mode='all', notify_system_events=True))
    assert not n._should_filter_event(ev)
    n2 = Notifier(FakeConfig(filter_mode='all', notify_system_events=False))
    assert n2._should_filter_event(ev)


def test_config_filter_mode_fallback(mock_config_dir):
    os.environ['CONFIG_DIR'] = os.path.join(mock_config_dir, 'config')
    from scripts.nuki.config import ConfigManager
    cfg = ConfigManager(mock_config_dir)
    assert cfg.filter_mode == 'all'  # no lists configured anywhere
    cfg.config.set('Filter', 'excluded_actions', '1')
    cfg._save_config(cfg.config, cfg.config_path)
    cfg.reload()
    assert cfg.filter_mode == 'exclude'  # legacy config keeps its semantics


# ---------------------------------------------------------------------------
# PWA routes
# ---------------------------------------------------------------------------

def test_manifest_route(app):
    resp = app.get('/manifest.webmanifest')
    assert resp.status_code == 200
    assert resp.content_type.startswith('application/manifest+json')
    data = resp.get_json()
    assert data['display'] == 'standalone'
    assert data['start_url'] == '/'


def test_service_worker_route(app):
    resp = app.get('/sw.js')
    assert resp.status_code == 200
    assert 'text/javascript' in resp.content_type
    assert resp.headers.get('Service-Worker-Allowed') == '/'
    assert b"addEventListener('fetch'" in resp.data


# ---------------------------------------------------------------------------
# Config additions
# ---------------------------------------------------------------------------

def test_config_webhook_full_url(mock_config_dir):
    os.environ['CONFIG_DIR'] = os.path.join(mock_config_dir, 'config')
    from scripts.nuki.config import ConfigManager
    cfg = ConfigManager(mock_config_dir)
    cfg.webhook_public_url = 'https://hook.nuki.example.com'
    cfg.webhook_secret = 'abc123'
    assert cfg.webhook_full_url == 'https://hook.nuki.example.com/webhook/nuki/abc123'
    cfg.webhook_secret = ''
    assert cfg.webhook_full_url == ''


def test_config_quiet_hours_defaults(mock_config_dir):
    os.environ['CONFIG_DIR'] = os.path.join(mock_config_dir, 'config')
    from scripts.nuki.config import ConfigManager
    cfg = ConfigManager(mock_config_dir)
    assert cfg.quiet_hours_enabled is False
    assert cfg.quiet_start == '22:00'
    assert cfg.quiet_end == '07:00'
    assert cfg.notify_door_open is False
    assert cfg.alert_failure_threshold == 3
