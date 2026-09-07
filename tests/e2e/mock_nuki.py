"""Minimal in-process mock of the Nuki Web API for E2E tests.

Implements only the endpoints the app uses, with deterministic canned data.
Runs on 127.0.0.1 with an ephemeral port; point the app at it via
NUKI_BASE_URL.
"""
import json
import re
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

LOCK_ID = 18255246837

_NOW_MS = int(time.time() * 1000)

SMARTLOCKS = [{
    "smartlockId": LOCK_ID,
    "name": "Test Lock",
    "state": {"state": 1, "stateName": "locked", "batteryCritical": False,
              "batteryCharging": False, "batteryCharge": 88,
              "doorState": 3, "nightMode": False},
}]

LOGS = [
    {"id": 4, "name": "Mallory <img src=x onerror=window.__xss_pwned=1>", "action": 1,
     "trigger": 4, "authId": "aaaa0001", "date": _NOW_MS - 60_000},
    {"id": 3, "name": "Lock", "action": 2, "trigger": 6, "authId": None,
     "date": _NOW_MS - 300_000},
    {"id": 2, "name": "", "action": 1, "trigger": 2, "authId": None,
     "date": _NOW_MS - 600_000},
    {"id": 1, "name": "Jennifer", "action": 1, "trigger": 4, "authId": "676a8a3fc52a77633bb8d51d",
     "date": _NOW_MS - 900_000},
]

AUTHS = [
    {"id": "aaaa0001", "authId": 101, "smartlockId": LOCK_ID, "type": 0,
     "name": "Dave Phone", "enabled": True, "remoteAllowed": True},
    {"id": "aaaa0002", "authId": 102, "smartlockId": LOCK_ID, "type": 3,
     "name": "Keypad", "enabled": True, "remoteAllowed": True},
    {"id": "aaaa0003", "authId": 103, "smartlockId": LOCK_ID, "type": 13,
     "name": "Cleaner", "enabled": True, "remoteAllowed": True, "code": 556677},
]

USERS_BY_ID = {"676a8a3fc52a77633bb8d51d": "Jennifer"}


class MockNukiHandler(BaseHTTPRequestHandler):
    def log_message(self, *args):  # silence
        pass

    def _send(self, obj=None, status=200):
        print(f"[mock-nuki] {self.command} {self.path} -> {status}", flush=True)
        body = json.dumps(obj if obj is not None else {}).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _body(self):
        length = int(self.headers.get('Content-Length') or 0)
        return json.loads(self.rfile.read(length) or b'{}') if length else {}

    def do_GET(self):
        path = self.path.split('?')[0]
        if path == '/smartlock':
            return self._send(SMARTLOCKS)
        if re.fullmatch(r'/smartlock/\d+/log', path):
            return self._send(LOGS)
        if path == '/smartlock/auth' or re.fullmatch(r'/smartlock/\d+/auth', path):
            return self._send(AUTHS)
        return self._send({"code": 404}, 404)

    def do_PUT(self):
        path = self.path.split('?')[0]
        body = self._body()
        if path == '/notification':
            return self._send({"notificationId": "mockhook"})
        if re.fullmatch(r'/smartlock/\d+/auth', path):
            if not body.get('name'):
                return self._send({"detailMessage": "name missing"}, 400)
            new_id = 'bbbb' + str(len(AUTHS) + 1).zfill(4)
            AUTHS.append({"id": new_id, "authId": 200 + len(AUTHS),
                          "smartlockId": LOCK_ID, "type": body.get('type', 0),
                          "name": body.get('name'), "enabled": True,
                          "remoteAllowed": True, "code": body.get('code')})
            return self._send({"id": new_id})
        return self._send({"code": 404}, 404)

    def do_POST(self):
        path = self.path.split('?')[0]
        body = self._body()
        m = re.fullmatch(r'/smartlock/(\d+)/auth/(\d+)', path)
        if m:
            # update: apply to the in-memory list so the UI reflects it
            for a in AUTHS:
                if str(a.get('authId')) == m.group(2):
                    a.update({k: v for k, v in body.items() if k in ('name', 'enabled')})
            return self._send({})
        return self._send({"code": 404}, 404)

    def do_DELETE(self):
        path = self.path.split('?')[0]
        m = re.fullmatch(r'/smartlock/(\d+)/auth/(\d+)', path)
        if m:
            AUTHS[:] = [a for a in AUTHS if str(a.get('authId')) != m.group(2)]
            return self._send({})
        m = re.fullmatch(r'/notification/(.+)', path)
        if m:
            return self._send({})
        return self._send({"code": 404}, 404)


def start_mock_nuki():
    server = ThreadingHTTPServer(('127.0.0.1', 0), MockNukiHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def reset_mock_nuki():
    AUTHS[:] = [a.copy() for a in [
        {"id": "aaaa0001", "authId": 101, "smartlockId": LOCK_ID, "type": 0,
         "name": "Dave Phone", "enabled": True, "remoteAllowed": True},
        {"id": "aaaa0002", "authId": 102, "smartlockId": LOCK_ID, "type": 3,
         "name": "Keypad", "enabled": True, "remoteAllowed": True},
        {"id": "aaaa0003", "authId": 103, "smartlockId": LOCK_ID, "type": 13,
         "name": "Cleaner", "enabled": True, "remoteAllowed": True, "code": 556677},
    ]]


if __name__ == '__main__':
    s = start_mock_nuki()
    print(s.server_address[1], flush=True)
    threading.Event().wait()
