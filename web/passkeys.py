"""Passkey (WebAuthn) support for the Nuki dashboard.

Passkeys are an optional, phishing-resistant alternative to passwords.
Ceremonies are handled by python-fido2; credentials live inside the user's
entry in users.json.

Note: WebAuthn requires a *secure context* — HTTPS, or http://localhost.
On plain-HTTP LAN access the browser hides the passkey option automatically
(the UI checks window.isSecureContext). Set WEB_HTTPS=true behind a reverse
proxy for full support.
"""

import os
from datetime import datetime

from fido2.server import Fido2Server
from fido2.utils import websafe_decode, websafe_encode
from fido2.webauthn import (
    AttestedCredentialData,
    PublicKeyCredentialDescriptor,
    PublicKeyCredentialRpEntity,
    PublicKeyCredentialUserEntity,
)

# ---------------------------------------------------------------------------
# Storage helpers (user entries in users.json)
# ---------------------------------------------------------------------------

def get_passkeys(user):
    """Return the passkey list for a user entry (never None)."""
    return user.get('passkeys', [])


def _descriptors(user):
    return [
        PublicKeyCredentialDescriptor(id=websafe_decode(pk['id']))
        for pk in get_passkeys(user)
    ]


def _attested(user):
    return [
        AttestedCredentialData(websafe_decode(pk['id_key']))
        for pk in get_passkeys(user)
        if pk.get('id_key')
    ]


def _user_entity(user, username):
    # The WebAuthn user handle must be stable and binary-safe.
    handle = websafe_decode(user.get('user_handle') or '')
    return PublicKeyCredentialUserEntity(
        id=handle,
        name=username,
        display_name=username,
    )


def ensure_user_handle(user):
    """Assign a stable WebAuthn user handle once."""
    if not user.get('user_handle'):
        user['user_handle'] = websafe_encode(os.urandom(32))
    return user['user_handle']


def add_passkey(user, credential_id_bytes, attested_bytes, name=None):
    """Store a registered passkey on the user entry."""
    entry = {
        'id': websafe_encode(credential_id_bytes),
        'id_key': websafe_encode(attested_bytes),
        'sign_count': 0,
        'name': name or 'Passkey',
        'created_at': datetime.now().isoformat(),
    }
    user.setdefault('passkeys', []).append(entry)
    return entry


def remove_passkey(user, credential_id_b64):
    """Remove a stored passkey by credential id. True if removed."""
    keys = user.get('passkeys', [])
    kept = [pk for pk in keys if pk['id'] != credential_id_b64]
    if len(kept) == len(keys):
        return False
    user['passkeys'] = kept
    return True


def find_user_by_credential(user_db, credential_id):
    """Usernameless login: find the owning user for a credential.

    ``credential_id`` may be raw bytes or the stored base64url string —
    both sides are normalised through websafe_decode so the lookup cannot
    fail on a representation mismatch.
    """
    def _norm(value):
        if isinstance(value, (bytes, bytearray)):
            return bytes(value)
        return websafe_decode(value)

    wanted = _norm(credential_id)
    for username, user in user_db.users.items():
        for pk in get_passkeys(user):
            try:
                if _norm(pk['id']) == wanted:
                    return username
            except Exception:
                continue
    return None


# ---------------------------------------------------------------------------
# Ceremonies
# ---------------------------------------------------------------------------

def _server(rp_id):
    return Fido2Server(PublicKeyCredentialRpEntity(id=rp_id, name='Nuki Console'))


def rp_from_request(request):
    """Derive the WebAuthn Relying Party id from the incoming request.

    The RP id is the hostname without port. Registration/login will only
    succeed if the browser's origin matches (HTTPS or localhost).
    """
    host = (request.host or 'localhost').split(':')[0]
    return host or 'localhost'


def begin_registration(user, username, rp_id):
    """Create a registration (attestation) ceremony."""
    ensure_user_handle(user)
    server = _server(rp_id)
    options, state = server.register_begin(
        _user_entity(user, username),
        credentials=_descriptors(user),
        resident_key_requirement='required',
        user_verification='preferred',
    )
    return dict(options), state


def complete_registration(server_state, response_json, rp_id):
    """Verify a registration response.

    Returns (credential_id_bytes, attested_credential_data_bytes).
    Raises fido2 exceptions on failure.
    """
    server = _server(rp_id)
    auth_data = server.register_complete(server_state, response=response_json)
    return auth_data.credential_data.credential_id, bytes(auth_data.credential_data)


def begin_authentication(user_db, rp_id):
    """Create an authentication (assertion) ceremony.

    Uses discoverable credentials: allowCredentials stays empty so the
    authenticator offers any passkey registered with this RP.
    """
    server = _server(rp_id)
    options, state = server.authenticate_begin(
        credentials=[], user_verification='preferred'
    )
    return dict(options), state


def complete_authentication(server_state, response_json, user_db, rp_id):
    """Verify an assertion response.

    Returns the username on success. Raises fido2 exceptions on failure.
    """
    server = _server(rp_id)
    # The assertion's "id" is the base64url credential id; find_user_by_credential
    # normalises encodings on both sides.
    credential_id = response_json['id']
    username = find_user_by_credential(user_db, credential_id)
    if not username:
        raise ValueError('Unknown passkey')

    user = user_db.get_user(username)
    credentials = _attested(user)
    if not credentials:
        raise ValueError('Unknown passkey')

    pk_entry = next(
        pk for pk in get_passkeys(user) if pk['id'] == credential_id
    )
    attested = AttestedCredentialData(websafe_decode(pk_entry['id_key']))

    # authenticate_complete returns the matched credential; a mismatch or
    # invalid signature raises.
    server.authenticate_complete(
        server_state,
        [attested],
        response=response_json,
    )

    # Update the signature counter to detect cloned authenticators.
    try:
        new_count = response_json.get('response', {}).get('signCount')
        if new_count is not None and int(new_count) >= int(pk_entry.get('sign_count', 0)):
            pk_entry['sign_count'] = int(new_count)
    except (TypeError, ValueError):
        pass

    return username
