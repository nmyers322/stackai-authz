from src.authz.engine import authorize
from src.authz.exceptions import AuthorizationError
from src.authz.models import Action, Principal, Resource
from src.authz.store import MembershipStore


def require(
    principal: Principal,
    action: Action,
    resource: Resource,
    store: MembershipStore,
) -> None:
    decision = authorize(principal, action, resource, store=store)
    if decision.denied:
        raise AuthorizationError(decision.reason)
