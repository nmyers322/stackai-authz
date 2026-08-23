from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from jwt import PyJWK
from jwt.algorithms import ECAlgorithm

from src.authn.jwks import JwksTokenVerifier
from src.exceptions import Unauthenticated

ISSUER = "https://example.supabase.co/auth/v1"
AUDIENCE = "authenticated"


class _StubJwkClient:
    def __init__(self, jwk: PyJWK) -> None:
        self._jwk = jwk

    def get_signing_key_from_jwt(self, token: str) -> PyJWK:
        _ = token
        return self._jwk


def _es256_verifier() -> tuple[JwksTokenVerifier, object]:
    private_key = ec.generate_private_key(ec.SECP256R1())
    public_jwk = ECAlgorithm.to_jwk(private_key.public_key(), as_dict=True)
    public_jwk["kid"] = "test-kid"
    public_jwk["alg"] = "ES256"
    client = _StubJwkClient(PyJWK.from_dict(public_jwk))
    verifier = JwksTokenVerifier(
        jwks_url=f"{ISSUER}/.well-known/jwks.json",
        issuer=ISSUER,
        audience=AUDIENCE,
        client=client,
    )
    return verifier, private_key


def test_jwks_verifier_accepts_es256_access_token():
    verifier, private_key = _es256_verifier()
    user_id = uuid4()
    token = jwt.encode(
        {
            "sub": str(user_id),
            "iss": ISSUER,
            "aud": AUDIENCE,
            "exp": datetime.now(UTC) + timedelta(minutes=5),
            "role": "authenticated",
        },
        private_key,
        algorithm="ES256",
        headers={"kid": "test-kid"},
    )
    principal = verifier.verify(token)
    assert principal.user_id == user_id


def test_jwks_verifier_rejects_bad_token():
    verifier, _private_key = _es256_verifier()
    with pytest.raises(Unauthenticated):
        verifier.verify("not-a-jwt")
