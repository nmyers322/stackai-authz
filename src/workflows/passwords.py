import hashlib
import hmac
import os

_SALT_BYTES = 16
_ROUNDS = 100_000


def hash_export_password(password: str, *, salt: bytes | None = None) -> str:
    used_salt = salt if salt is not None else os.urandom(_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), used_salt, _ROUNDS)
    return used_salt.hex() + digest.hex()


def export_password_ok(password: str | None, stored_hash: str | None) -> bool:
    if password is None or stored_hash is None:
        return False
    salt_hex_len = _SALT_BYTES * 2
    if len(stored_hash) <= salt_hex_len:
        return False
    salt = bytes.fromhex(stored_hash[:salt_hex_len])
    expected = bytes.fromhex(stored_hash[salt_hex_len:])
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _ROUNDS)
    return hmac.compare_digest(digest, expected)
