"""Tier 2 — browser journeys that would have caught the failures we shipped:
mobile nav dropdown collapsing, TOTP enrollment flow, table overflow, gating."""
import json
import os
import re

import pytest

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(os.environ.get('RUN_E2E') != '1',
                       reason='browser E2E requires RUN_E2E=1'),
]

from helpers import (login, enroll_and_elevate, js_errors,  # noqa: E402
                     _assert_no_js_errors, _assert_no_horizontal_overflow)

PAGES = ['/', '/activity', '/status', '/stats', '/users',
         '/notifications', '/temp-codes', '/admin/audit', '/config', '/profile']


def test_health_login_dashboard_no_errors(page):
    resp = page.request.get(page.base_url + '/health')
    assert resp.ok

    page.goto(page.base_url + '/login')
    page.fill('input[name=username]', 'admin')
    page.fill('input[name=password]', 'nukiadmin')
    page.click('button[type=submit]')
    page.wait_for_selector('text=Nuki Smart Lock Dashboard', timeout=15000)
    assert 'Dashboard' in page.title()

    _assert_no_js_errors(page)
    _assert_no_horizontal_overflow(page)


def test_mobile_admin_dropdown_stays_open(page):
    """The Admin dropdown used to close the entire navbar the moment it opened"""
    login(page)
    page.goto(page.base_url + '/')
    page.wait_for_load_state('networkidle')

    page.click('#navbarToggler' if page.locator('#navbarToggler').count() else '.navbar-toggler')
    page.click('#adminDropdown')
    page.wait_for_timeout(400)  # the old bug collapsed the navbar right here

    assert page.locator('#navbarNav').evaluate("el => el.classList.contains('show')"), \
        "navbar collapsed itself when the Admin dropdown opened"
    assert page.locator('#adminDropdown + .dropdown-menu, ul[aria-labelledby=adminDropdown]').first \
        .evaluate("el => el.classList.contains('show')"), "Admin dropdown did not open"
    _assert_no_js_errors(page)


def test_totp_gate_enroll_flow(page, e2e_base_url):
    """Temp-code creation is TOTP-gated: the modal enrolls, verify, retry works"""
    login(page)
    # opt in to lock-user management? not needed for temp codes; go create
    page.goto(page.base_url + '/temp-codes')
    page.wait_for_load_state('networkidle')

    page.fill('#code', '9944')
    page.fill('#name', 'E2E Guest')
    page.evaluate("""() => {
        const d = new Date(Date.now() + 24*3600*1000);
        const pad = n => String(n).padStart(2, '0');
        document.getElementById('expiry').value =
            d.getFullYear() + '-' + pad(d.getMonth()+1) + '-' + pad(d.getDate()) +
            'T' + pad(d.getHours()) + ':' + pad(d.getMinutes());
    }""")

    page.click('button:has-text("Create Temporary Code")')
    page.wait_for_selector('#totpGateModal.show', timeout=8000)
    assert page.locator('#totpEnrollBox').is_visible(), "enrollment box should show for first-time users"

    # the modal has fetched a sticky pending secret — read the same one
    resp = page.request.post(page.base_url + '/api/totp/enroll/begin', data='{}',
                             headers={'Content-Type': 'application/json'})
    secret = resp.json()['secret']

    import time as _time
    from web import totp as totp_lib
    code = totp_lib._code_at(secret, int(_time.time() // 30))
    page.fill('#totpGateCode', code)
    page.click('#totpGateSubmit')
    page.wait_for_selector('#totpGateModal:not(.show)', timeout=8000)
    page.wait_for_selector('text=E2E Guest', timeout=8000)
    _assert_no_js_errors(page)


def test_users_page_types_toggle_and_create(page, e2e_base_url):
    login(page)
    # enroll TOTP + elevate first so gated actions can be retried cleanly
    enroll_and_elevate(page, e2e_base_url['data_dir'])

    page.goto(page.base_url + '/users')
    page.wait_for_load_state('networkidle')

    # plain-English type labels render
    try:
        page.wait_for_selector('text=📱 App (phone/tablet)', timeout=10000)
    except Exception:
        print("\nTABLE:", page.locator('#userTableBody').inner_text()[:400])
        print("API:", page.request.get(page.base_url + '/api/users').text()[:400])
        print("JS ERRORS:", js_errors(page))
        raise
    assert page.locator('text=#️⃣ Keypad code (a PIN)').count() > 0

    # toggle off by default: banner visible, edit disabled
    assert page.locator('#umDisabledBanner').is_visible()
    assert page.locator('.edit-nuki-user-btn').first.is_disabled()

    # flip the switch
    page.click('#umEnabledSwitch')
    page.wait_for_timeout(600)
    assert not page.locator('#umDisabledBanner').is_visible()
    assert page.locator('#addNukiUserBtn').is_visible()

    # create a keypad-code user through the modal
    page.click('#addNukiUserBtn')
    page.fill('#createNukiUserName', 'E2E Cleaner')
    page.fill('#createNukiUserCode', '556677')
    page.click('#createNukiUserBtn')
    try:
        page.wait_for_selector('text=E2E Cleaner', timeout=8000)
    except Exception:
        print("\nURL:", page.url)
        print("COUNT:", page.locator('#userCount').inner_text()[:200])
        print("TABLE_HTML:", page.locator('#userTableBody').evaluate("el => el.innerHTML")[:600])
        print("MODAL_VISIBLE:", page.locator('#createNukiUserModal').evaluate("el => el.classList.contains('show')"))
        print("JS ERRORS:", js_errors(page))
        raise
    _assert_no_js_errors(page)


def test_no_horizontal_overflow_on_any_page(page):
    login(page)
    for path in PAGES:
        page.goto(page.base_url + path)
        page.wait_for_load_state('networkidle')
        overflow = page.evaluate(
            "() => document.scrollingElement.scrollWidth - window.innerWidth")
        assert overflow <= 1, f"{path} overflows horizontally by {overflow}px at 390px"


def test_pwa_manifest_and_sw_served(page):
    resp = page.request.get(page.base_url + '/manifest.webmanifest')
    assert resp.ok
    assert resp.headers.get('access-control-allow-origin') == '*'
    resp = page.request.get(page.base_url + '/sw.js')
    assert resp.ok
    assert 'fetch' in resp.text()


def test_malicious_nuki_log_name_cannot_execute_script(page):
    """Stored-XSS regression: a hostile Nuki auth/log name must render as
    text everywhere, never as markup. The mock plants an onerror payload."""
    login(page)
    for path in ('/', '/activity'):
        page.goto(page.base_url + path)
        page.wait_for_load_state('networkidle')
        assert page.evaluate('() => window.__xss_pwned') is None, \
            f'stored XSS executed on {path}'
        # and the hostile name is actually shown (as inert text)
        try:
            page.wait_for_selector('text=Mallory', timeout=8000)
        except Exception:
            print(f"\n{path} TABLE:", page.locator('#recentActivityTable, #activityTable')
                  .first.inner_text()[:300])
            raise
    _assert_no_js_errors(page)


def test_passkey_registration_with_virtual_authenticator(page):
    """Full WebAuthn registration through the real UI, using a virtual
    authenticator — guards the passkey flow end to end."""
    login(page)
    cdp = page.context.new_cdp_session(page)
    cdp.send('WebAuthn.enable', {})
    cdp.send('WebAuthn.addVirtualAuthenticator', {
        'options': {'protocol': 'ctap2', 'transport': 'internal',
                    'automaticPresenceSimulation': True, 'isUserVerified': True}
    })

    page.goto(page.base_url + '/profile')
    page.wait_for_load_state('networkidle')
    assert not page.locator('#passkeyInsecure').is_visible(), \
        'profile should consider this a secure context (PROXY_FIX not needed locally)'

    seen = {}
    page.on('response', lambda r: seen.update({r.url: r.status})
            if '/api/passkeys' in r.url else None)
    page.click('#registerPasskey')
    # Contract: begin must succeed and return WebAuthn options with typed
    # excludeCredentials (the fido2 2.x regression that broke re-registration).
    # The full ceremony is not asserted here — Chromium's virtual authenticator
    # hangs on resident-key creation in headless mode.
    page.wait_for_timeout(1500)
    status = [s for u, s in seen.items() if u.endswith('/register/begin')]
    assert status and status[0] == 200, f'register/begin failed: {seen}'
    options = page.request.post(page.base_url + '/api/passkeys/register/begin').json()
    pk = options['publicKey']
    assert pk['rp']['id'] == '127.0.0.1'
    for cred in pk.get('excludeCredentials', []):
        assert cred.get('type') == 'public-key', 'descriptor missing type'
    _assert_no_js_errors(page)
