from src.authn.api_keys import hash_api_key
from src.seed import API_KEY_A, EXPORT_PASSWORD, EXPORT_PASSWORD_SALT
from src.workflows.passwords import export_password_ok, hash_export_password


def test_api_key_hash_is_lookup_stable():
    assert hash_api_key(API_KEY_A) == hash_api_key(API_KEY_A)
    assert hash_api_key(API_KEY_A) != hash_api_key("other")


def test_export_password_round_trip():
    stored = hash_export_password(EXPORT_PASSWORD, salt=EXPORT_PASSWORD_SALT)
    assert export_password_ok(EXPORT_PASSWORD, stored)
    assert not export_password_ok("nope", stored)
    assert not export_password_ok(None, stored)
    assert not export_password_ok(EXPORT_PASSWORD, None)
