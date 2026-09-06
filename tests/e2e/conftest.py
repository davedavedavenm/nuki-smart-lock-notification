"""E2E harness: real app in a subprocess + real browser via Playwright.

Skipped unless RUN_E2E=1. The app runs with a seeded temp config and its
Nuki traffic pointed at the local mock server (NUKI_BASE_URL).
"""
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from web import totp as totp_lib  # noqa: E402
import mock_nuki  # noqa: E402

pytestmark = pytest.mark.e2e


def _free_port():
    s = socket.socket()
    s.bind(('127.0.0.1', 0))
    port = s.getsockname()[1]
    s.close()
    return port


@pytest.fixture(scope='session')
def e2e_base_url():
    """Seed a temp install, start the mock Nuki API and the real web app"""
    if os.environ.get('RUN_E2E') != '1':
        pytest.skip('E2E tests require RUN_E2E=1')

    mock = mock_nuki.start_mock_nuki()
    mock_port = mock.server_address[1]

    base = tempfile.mkdtemp(prefix='nuki-e2e-')
    for d in ('config', 'data', 'logs', 'flask_session'):
        os.makedirs(os.path.join(base, d), exist_ok=True)

    with open(os.path.join(base, 'config', 'config.ini'), 'w') as f:
        f.write("""
[General]
notification_type = none
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
filter_mode = all

[Email]
smtp_server =
smtp_port = 587

[Telegram]
chat_id = 123

[Advanced]
user_management_enabled = false
debug_mode = false
""")
    with open(os.path.join(base, 'config', 'credentials.ini'), 'w') as f:
        f.write("[Nuki]\napi_token = e2e-token\n[Telegram]\nbot_token =\n[Webhook]\nsecret =\n")

    from werkzeug.security import generate_password_hash
    users = {
        "admin": {"password_hash": generate_password_hash('nukiadmin', method='pbkdf2:sha256'),
                  "role": "admin", "active": True, "theme": "dark"},
        "sitter": {"password_hash": generate_password_hash('agentpass', method='pbkdf2:sha256'),
                   "role": "agent", "active": True, "theme": "dark"},
    }
    with open(os.path.join(base, 'data', 'users.json'), 'w') as f:
        json.dump(users, f)
    with open(os.path.join(base, 'data', 'temp_codes.json'), 'w') as f:
        json.dump({}, f)

    web_port = _free_port()
    env = dict(os.environ)
    env.update({
        'CONFIG_DIR': os.path.join(base, 'config'),
        'DATA_DIR': os.path.join(base, 'data'),
        'LOGS_DIR': os.path.join(base, 'logs'),
        'SESSION_FILE_DIR': os.path.join(base, 'flask_session'),
        'SECRET_KEY': 'e2e-secret-key',
        'WEB_PORT': str(web_port),
        'ALLOW_MISSING_TOKEN': 'true',
        'NUKI_BASE_URL': f'http://127.0.0.1:{mock_port}',
        'NUKI_WEB_PORT': str(web_port),
    })
    app_log_path = os.path.join(base, 'logs', 'app_stdout.log')
    proc = subprocess.Popen([sys.executable, os.path.join(REPO_ROOT, 'web', 'app.py')],
                            cwd=REPO_ROOT, env=env,
                            stdout=open(app_log_path, 'w'),
                            stderr=subprocess.STDOUT)

    base_url = f'http://127.0.0.1:{web_port}'
    import urllib.request
    deadline = time.time() + 30
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(base_url + '/health', timeout=2) as r:
                if r.status == 200:
                    break
        except Exception:
            time.sleep(0.5)
    else:
        proc.kill()
        try:
            out = open(os.path.join(base, 'logs', 'app_stdout.log')).read()
        except Exception:
            out = ''
        shutil.rmtree(base, ignore_errors=True)
        raise RuntimeError(f'E2E app failed to start:\n{out[-2000:]}')

    yield {'base_url': base_url, 'mock_port': mock_port, 'app_log': app_log_path,
           'data_dir': os.path.join(base, 'data')}

    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
    mock.shutdown()
    shutil.rmtree(base, ignore_errors=True)


@pytest.fixture(scope='session')
def browser():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        yield b
        b.close()


@pytest.fixture
def page(browser, e2e_base_url):
    """Fresh mobile-viewport context per test, with console-error capture"""
    context = browser.new_context(viewport={'width': 390, 'height': 844})
    page = context.new_page()
    page.console_errors = []
    page.on('console', lambda msg: page.console_errors.append(msg.text) if msg.type == 'error' else None)
    page.on('pageerror', lambda err: page.console_errors.append(str(err)))
    page.base_url = e2e_base_url['base_url']
    yield page
    context.close()
