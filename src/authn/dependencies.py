from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, Request
from starlette.concurrency import run_in_threadpool

from src.authn.api_keys import hash_api_key
from src.authn.jwks import TokenVerifier
from src.authz.guard import require
from src.authz.models import (
    Action,
    AnonymousPrincipal,
    ApiKeyPrincipal,
    Principal,
    Resource,
    UserPrincipal,
)
from src.authz.store import AppStore, MembershipStore
from src.exceptions import Unauthenticated


def get_store(request: Request) -> AppStore:
    return request.app.state.store


def get_verifier(request: Request) -> TokenVerifier:
    return request.app.state.verifier


async def get_principal(
    request: Request,
    store: Annotated[AppStore, Depends(get_store)],
    verifier: Annotated[TokenVerifier, Depends(get_verifier)],
    authorization: Annotated[str | None, Header()] = None,
    x_api_key: Annotated[str | None, Header(alias="X-Api-Key")] = None,
    x_debug_user: Annotated[str | None, Header(alias="X-Debug-User")] = None,
) -> Principal:
    if request.app.state.debug and x_debug_user and x_debug_user.strip():
        try:
            return UserPrincipal(user_id=UUID(x_debug_user.strip()))
        except ValueError as exc:
            raise Unauthenticated from exc
    if x_api_key is not None and x_api_key.strip():
        org_id = await run_in_threadpool(
            store.org_id_for_key_hash, hash_api_key(x_api_key.strip())
        )
        if org_id is None:
            raise Unauthenticated
        return ApiKeyPrincipal(org_id=org_id)
    if authorization is None:
        return AnonymousPrincipal()
    scheme, separator, token = authorization.partition(" ")
    if separator == "" or scheme.lower() != "bearer" or not token.strip():
        raise Unauthenticated
    return await run_in_threadpool(verifier.verify, token.strip())


async def require_http(
    principal: Principal,
    action: Action,
    resource: Resource,
    store: MembershipStore,
) -> None:
    await run_in_threadpool(require, principal, action, resource, store)


PrincipalDep = Annotated[Principal, Depends(get_principal)]
StoreDep = Annotated[AppStore, Depends(get_store)]
