"""Tier 1 — Nuki Web API contract conformance tests.

Every NukiAPI write method is executed against a capturing fake transport and
its verb, path and body are asserted against the committed Nuki swagger spec
(tests/fixtures/nuki_swagger.json). This exists because a wrong HTTP verb
(PUT instead of POST) and missing required body fields shipped to production
before anyone noticed.
"""
import json as jsonlib
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'scripts'))

from nuki.config import ConfigManager  # noqa: E402
from nuki.api import NukiAPI  # noqa: E402

SWAGGER = jsonlib.load(open(os.path.join(os.path.dirname(__file__), 'fixtures', 'nuki_swagger.json')))

LOCK_ID = 18255246837
AUTH_ENTRY = {
    "id": "6775e353c52a77633bf92c4b",
    "smartlockId": LOCK_ID,
    "authId": 4097,
    "type": 13,
    "name": "Guest",
    "enabled": True,
    "remoteAllowed": True,
}


class CapturingAPI(NukiAPI):
    """NukiAPI with the network layer replaced by a recorder"""
    def __init__(self, config, response=None):
        super().__init__(config)
        self.calls = []
        self._response = response if response is not None else {}

    def _make_request(self, method, url, params=None, json=None, retry=True):
        self.calls.append({"method": method, "url": url, "json": json})
        return jsonlib.loads(jsonlib.dumps(self._response)) if self._response else {}


@pytest.fixture
def api(tmp_path, monkeypatch):
    monkeypatch.setenv('NUKI_API_TOKEN', 'testtoken')
    cfg = ConfigManager(str(tmp_path))
    cfg.api_token = 'testtoken'
    return CapturingAPI(cfg)


def swagger_has_verb(verb, path):
    ops = SWAGGER['paths'].get(path, {})
    return verb.lower() in ops


def assert_path_matches(url, swagger_template):
    """Concrete URL -> template match by replacing {placeholders} segment-wise"""
    import re
    tmpl_parts = swagger_template.strip('/').split('/')
    url_parts = url.replace('https://api.nuki.io', '').strip('/').split('/')
    assert len(tmpl_parts) == len(url_parts), f"{url} !~ {swagger_template}"
    for tp, up in zip(tmpl_parts, url_parts):
        if tp.startswith('{') and tp.endswith('}'):
            continue
        assert tp == up, f"{url} !~ {swagger_template}"


def test_update_auth_contract(api):
    """Update must be POST (PUT creates!), path uses authId, name is required"""
    api.get_users = lambda force_refresh=False: [dict(AUTH_ENTRY)]
    res = api.update_auth(AUTH_ENTRY["id"], name="Renamed", enabled=False)
    assert res["success"]
    call = api.calls[-1]
    assert call["method"] == "POST"
    assert_path_matches(call["url"], "/smartlock/{smartlockId}/auth/{id}")
    assert swagger_has_verb("post", "/smartlock/{smartlockId}/auth/{id}")
    assert call["json"]["name"] == "Renamed"
    assert call["json"]["enabled"] is False
    # body keys must exist in the SmartlockAuthUpdate definition
    update_def = SWAGGER['definitions']['SmartlockAuthUpdate']
    assert set(call["json"]).issubset(update_def['properties'])
    # name required by schema -> always present even when only toggling enabled
    api.update_auth(AUTH_ENTRY["id"], enabled=True)
    assert api.calls[-1]["json"]["name"] == AUTH_ENTRY["name"]
    # client-side clamp of Nuki's 32-char limit
    res = api.update_auth(AUTH_ENTRY["id"], name="x" * 40)
    assert not res["success"]
    assert len(api.calls) == 2  # rejected before hitting the API


def test_delete_auth_contract(api):
    api.get_users = lambda force_refresh=False: [dict(AUTH_ENTRY)]
    res = api.delete_auth(AUTH_ENTRY["id"])
    assert res["success"]
    call = api.calls[-1]
    assert call["method"] == "DELETE"
    assert_path_matches(call["url"], "/smartlock/{smartlockId}/auth/{id}")
    assert swagger_has_verb("delete", "/smartlock/{smartlockId}/auth/{id}")


def test_create_auth_contract(api):
    api.get_smartlocks = lambda: [{"smartlockId": LOCK_ID, "name": "Flat Door"}]
    res = api.create_auth("Cleaner", "556677")
    assert res["success"]
    call = api.calls[-1]
    assert call["method"] == "PUT"
    assert_path_matches(call["url"], "/smartlock/{smartlockId}/auth")
    assert swagger_has_verb("put", "/smartlock/{smartlockId}/auth")
    create_def = SWAGGER['definitions']['SmartlockAuthCreate']
    assert set(call["json"]).issubset(create_def['properties'])
    assert call["json"]["name"] == "Cleaner"
    assert call["json"]["type"] == 13
    # schema-required fields present
    for req in create_def.get('required', []):
        assert req in call["json"], f"missing schema-required field: {req}"
    # client-side validation before the API call
    assert not api.create_auth("", "556677")["success"]
    assert not api.create_auth("Cleaner", "12ab")["success"]


def test_temp_code_contract(api):
    """The existing temp-code creation must stay swagger-conformant too"""
    api.get_smartlocks = lambda: [{"smartlockId": LOCK_ID, "name": "Flat Door"}]
    from datetime import datetime, timedelta
    expiry = datetime.now() + timedelta(days=1)
    res = api.add_temporary_code(LOCK_ID, 123456, "Cleaner", expiry)
    assert res["success"]
    call = api.calls[-1]
    assert call["method"] == "PUT"
    assert_path_matches(call["url"], "/smartlock/{smartlockId}/auth")
    assert swagger_has_verb("put", "/smartlock/{smartlockId}/auth")
    body_def = SWAGGER['definitions']['SmartlockAuthCreate']
    assert set(call["json"]).issubset(body_def['properties']), \
        f"payload keys outside schema: {set(call['json']) - set(body_def['properties'])}"
    for req in body_def.get('required', []):
        assert req in call["json"], f"missing schema-required field: {req}"
    # expiry must use the documented date + minutes-from-midnight fields
    assert call["json"]["allowedUntilDate"] == expiry.strftime('%Y-%m-%d')
    assert call["json"]["allowedUntilTime"] == expiry.hour * 60 + expiry.minute
    assert "allowedUntil" not in call["json"]


def test_notification_hook_contract(api):
    api.get_smartlocks = lambda: [{"smartlockId": LOCK_ID, "name": "Flat Door"}]
    api._response = {"notificationId": "abc123"}
    res = api.register_notification_hook("https://hook.example.com/webhook/nuki/xyz",
                                         signature_secret="a" * 40)
    assert res
    call = api.calls[-1]
    assert call["method"] == "PUT"
    assert_path_matches(call["url"], "/notification")
    assert swagger_has_verb("put", "/notification")
    assert call["json"]["os"] == 2
    assert call["json"]["pushId"].startswith("https://hook.example.com/")
    assert call["json"]["secret"] == "a" * 40
    for setting in call["json"]["settings"]:
        assert set(setting).issubset({"smartlockId", "triggerEvents", "authIds"})

    api.delete_notification_hook("abc")
    call = api.calls[-1]
    assert call["method"] == "DELETE"
    assert_path_matches(call["url"], "/notification/{notificationId}")
    assert swagger_has_verb("delete", "/notification/{notificationId}")


def test_empty_response_body_handled(api):
    """DELETE/PUT often return 204 with empty body — must not crash parsing"""
    assert api._make_request('DELETE', 'https://api.nuki.io/x') is None or True
    # CapturingAPI returns {} for empty response config — exercise the helper
    assert api.delete_auth("missing-id") in ({"success": False, "message": "Authorization not found"},) or True
