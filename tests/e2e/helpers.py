"""Shared helpers for E2E browser tests (page-level operations)."""
import json
import os
import time

from web import totp as totp_lib


def login(page, username='admin', password='nukiadmin'):
    page.goto(page.base_url + '/login')
    page.fill('input[name=username]', username)
    page.fill('input[name=password]', password)
    page.click('button[type=submit]')
    page.wait_for_selector('text=Nuki Smart Lock Dashboard', timeout=15000)


def js_errors(page):
    """Console errors that indicate real JS problems (ignore CDN hiccups)"""
    return [e for e in page.console_errors
            if 'net::' not in e and 'Failed to load resource' not in e]


def _assert_no_js_errors(page):
    errs = js_errors(page)
    assert not errs, f"JS console errors: {errs}"


def _assert_no_horizontal_overflow(page):
    overflow = page.evaluate(
        "() => document.scrollingElement.scrollWidth - window.innerWidth")
    assert overflow <= 1, f"page overflows horizontally by {overflow}px at 390px viewport"


def enroll_and_elevate(page, data_dir=None):
    """Enroll TOTP for the logged-in user and open an elevated session.

    Works even if the user enrolled in an earlier test: the harness reads the
    enrolled secret straight from users.json (it owns that data dir).
    """
    status = page.request.get(page.base_url + '/api/totp/status').json()
    if status.get('enrolled'):
        with open(os.path.join(data_dir, 'users.json')) as f:
            secret = json.load(f)['admin']['totp_secret']
    else:
        resp = page.request.post(page.base_url + '/api/totp/enroll/begin', data='{}',
                                 headers={'Content-Type': 'application/json'})
        assert resp.ok, resp.text()
        secret = resp.json()['secret']
    code = totp_lib._code_at(secret, int(time.time() // 30))
    url = page.base_url + ('/api/totp/enroll/finish' if not status.get('enrolled') else '/api/totp/verify')
    resp = page.request.post(url, data=json.dumps({'code': code}),
                             headers={'Content-Type': 'application/json'})
    assert resp.ok, resp.text()
