from typing import Protocol
from uuid import UUID

import jwt
from jwt import PyJWK, PyJWKClient

from src.authz.models import UserPrincipal
from src.exceptions import Unauthenticated

_ASYMMETRIC = frozenset({"RS256", "ES256", "EdDSA"})


class TokenVerifier(Protocol):
    def verify(self, token: str) -> UserPrincipal: ...


class SigningKeyClient(Protocol):
    def get_signing_key_from_jwt(self, token: str) -> PyJWK: ...


class UnconfiguredVerifier:
    def verify(self, token: str) -> UserPrincipal:
        raise Unauthenticated


class StaticTokenVerifier:
    def __init__(self, tokens: dict[str, UUID]) -> None:
        self._tokens = tokens

    def verify(self, token: str) -> UserPrincipal:
        user_id = self._tokens.get(token)
        if user_id is None:
            raise Unauthenticated
        return UserPrincipal(user_id=user_id)


class JwksTokenVerifier:
    def __init__(
        self,
        jwks_url: str,
        issuer: str,
        audience: str,
        client: SigningKeyClient | None = None,
    ) -> None:
        self._client: SigningKeyClient = client or PyJWKClient(
            jwks_url, cache_jwk_set=True
        )
        self._issuer = issuer
        self._audience = audience

    @classmethod
    def from_supabase_url(
        cls, supabase_url: str, audience: str = "authenticated"
    ) -> "JwksTokenVerifier":
        base = supabase_url.rstrip("/")
        issuer = f"{base}/auth/v1"
        jwks_url = f"{issuer}/.well-known/jwks.json"
        return cls(jwks_url=jwks_url, issuer=issuer, audience=audience)

    def verify(self, token: str) -> UserPrincipal:
        try:
            header = jwt.get_unverified_header(token)
            algorithm = header.get("alg")
            if algorithm not in _ASYMMETRIC:
                raise Unauthenticated
            signing_key = self._client.get_signing_key_from_jwt(token)
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=[algorithm],
                audience=self._audience,
                issuer=self._issuer,
            )
        except Unauthenticated:
            raise
        except Exception as exc:
            raise Unauthenticated from exc

        sub = payload.get("sub")
        if not isinstance(sub, str):
            raise Unauthenticated
        try:
            return UserPrincipal(user_id=UUID(sub))
        except ValueError as exc:
            raise Unauthenticated from exc
