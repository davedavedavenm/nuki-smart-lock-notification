"""Minimal RFC 6238 TOTP (SHA-1, 30s step, 6 digits) — stdlib only.

Used as the second factor for lock-access management actions.
"""
import base64
import hashlib
import hmac
import secrets
import struct
import time


def generate_secret(num_bytes=20):
    """New random TOTP secret, base32-encoded (RFC 4228 charset, no padding)"""
    return base64.b32encode(secrets.token_bytes(num_bytes)).decode('ascii').rstrip('=')


def _code_at(secret, counter):
    key = base64.b32decode(secret + '=' * ((8 - len(secret) % 8) % 8), casefold=True)
    msg = struct.pack('>Q', counter)
    digest = hmac.new(key, msg, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    bin_code = struct.unpack('>I', digest[offset:offset + 4])[0] & 0x7FFFFFFF
    return f"{bin_code % 1_000_000:06d}"


def verify_code(secret, code, window=1, now=None):
    """Constant-time check of a 6-digit code, tolerating ±window time steps.

    Accepts the code formatted with optional spaces (users often type
    '123 456').
    """
    if not secret or not code:
        return False
    code = str(code).replace(' ', '').strip()
    if not (code.isdigit() and len(code) == 6):
        return False
    counter_now = int((now if now is not None else time.time()) // 30)
    for offset in range(-window, window + 1):
        expected = _code_at(secret, counter_now + offset)
        if hmac.compare_digest(expected, code):
            return True
    return False


def otpauth_uri(secret, account, issuer='Nuki Console'):
    label = f"{issuer}:{account}".replace(' ', '%20')
    return (f"otpauth://totp/{label}?secret={secret}"
            f"&issuer={issuer.replace(' ', '%20')}&algorithm=SHA1&digits=6&period=30")
