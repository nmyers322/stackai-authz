from src.authz.models import (
    API_KEY_ACTIONS,
    EDITOR_WORKFLOW_ACTIONS,
    MEMBERSHIP_MUTATIONS,
    ORG_ADMIN_ACTIONS,
    TEAM_ADMIN_ACTIONS,
    TEAM_RANK,
    Action,
    AnonymousPrincipal,
    ApiKeyPrincipal,
    Decision,
    OrgRole,
    Principal,
    Reason,
    Resource,
    TeamRole,
    UserPrincipal,
    Visibility,
)
from src.authz.store import MembershipStore


def authorize(
    principal: Principal,
    action: Action,
    resource: Resource,
    store: MembershipStore,
) -> Decision:
    if isinstance(principal, AnonymousPrincipal):
        return _anonymous(action, resource)
    if isinstance(principal, ApiKeyPrincipal):
        return _api_key(principal, action, resource)
    return _user(principal, action, resource, store)


def _allow() -> Decision:
    return Decision(allowed=True, reason=Reason.ALLOWED)


def _deny(reason: Reason) -> Decision:
    return Decision(allowed=False, reason=reason)


def _exported(action: Action, resource: Resource) -> Decision:
    if resource.visibility is None:
        return _deny(Reason.RESOURCE_INCOMPLETE)
    if resource.visibility is Visibility.TEAM:
        return _deny(Reason.EXPORT_NOT_PERMITTED)
    if resource.visibility is Visibility.PUBLIC:
        return _allow()
    if resource.visibility is Visibility.PASSWORD:
        if resource.export_password_ok:
            return _allow()
        return _deny(Reason.EXPORT_PASSWORD_REQUIRED)
    return _deny(Reason.EXPORT_NOT_PERMITTED)


def _anonymous(action: Action, resource: Resource) -> Decision:
    if action is Action.WORKFLOW_EXECUTE_EXPORTED:
        return _exported(action, resource)
    return _deny(Reason.ANONYMOUS_DENIED)


def _api_key(
    principal: ApiKeyPrincipal, action: Action, resource: Resource
) -> Decision:
    if action not in API_KEY_ACTIONS:
        return _deny(Reason.API_KEY_DENIED)
    if resource.org_id is None:
        return _deny(Reason.RESOURCE_INCOMPLETE)
    if resource.org_id != principal.org_id:
        return _deny(Reason.WRONG_ORG)
    if action is Action.WORKFLOW_EXECUTE_EXPORTED:
        if resource.visibility is Visibility.ORG:
            return _deny(Reason.API_KEY_DENIED)
        return _exported(action, resource)
    return _allow()


def _has_team_rank(role: TeamRole | None, needed: TeamRole) -> bool:
    if role is None:
        return False
    return TEAM_RANK[role] >= TEAM_RANK[needed]


def _user(
    principal: UserPrincipal,
    action: Action,
    resource: Resource,
    store: MembershipStore,
) -> Decision:
    if action is Action.ORG_CREATE:
        return _allow()

    if action is Action.USER_ORGS_LIST:
        if resource.user_id is None:
            return _deny(Reason.RESOURCE_INCOMPLETE)
        if principal.user_id != resource.user_id:
            return _deny(Reason.IDENTITY_MISMATCH)
        return _allow()

    if resource.org_id is None:
        return _deny(Reason.RESOURCE_INCOMPLETE)

    org_role = store.org_role(principal.user_id, resource.org_id)
    is_super = org_role is OrgRole.SUPER_ADMIN

    if action is Action.ORG_MEMBER_TEAMS_LIST:
        if resource.user_id is None:
            return _deny(Reason.RESOURCE_INCOMPLETE)
        if principal.user_id == resource.user_id:
            return _allow()
        if is_super:
            return _allow()
        return _deny(Reason.IDENTITY_MISMATCH)

    if action in MEMBERSHIP_MUTATIONS:
        if resource.user_id is None:
            return _deny(Reason.RESOURCE_INCOMPLETE)
        if principal.user_id == resource.user_id:
            return _deny(Reason.SELF_MEMBERSHIP_MUTATION)

    if action is Action.TEAM_DELETE and resource.is_default_team:
        return _deny(Reason.DEFAULT_TEAM_IMMUTABLE)

    if action is Action.TEAM_MEMBER_REMOVE and resource.is_default_team:
        return _deny(Reason.DEFAULT_TEAM_IMMUTABLE)

    if action in ORG_ADMIN_ACTIONS:
        if is_super:
            return _allow()
        if org_role is None:
            return _deny(Reason.NOT_ORG_MEMBER)
        return _deny(Reason.ORG_ROLE_INSUFFICIENT)

    if org_role is None:
        if action is Action.WORKFLOW_EXECUTE_EXPORTED:
            return _exported(action, resource)
        return _deny(Reason.NOT_ORG_MEMBER)

    if action is Action.TEAM_LIST or action is Action.WORKFLOW_LIST:
        return _allow()

    if action is Action.WORKFLOW_EXECUTE_EXPORTED:
        if resource.visibility is Visibility.ORG:
            return _allow()
        return _exported(action, resource)

    needs_team = action in TEAM_ADMIN_ACTIONS | EDITOR_WORKFLOW_ACTIONS or (
        action is Action.WORKFLOW_EXECUTE
    )
    if needs_team and resource.team_id is None:
        return _deny(Reason.RESOURCE_INCOMPLETE)

    if is_super:
        return _allow()

    if resource.team_id is None:
        return _deny(Reason.RESOURCE_INCOMPLETE)

    team_role = store.team_role(principal.user_id, resource.team_id)

    if action in TEAM_ADMIN_ACTIONS:
        if team_role is TeamRole.ADMIN:
            return _allow()
        if team_role is None:
            return _deny(Reason.NOT_TEAM_MEMBER)
        return _deny(Reason.TEAM_ROLE_INSUFFICIENT)

    if action in EDITOR_WORKFLOW_ACTIONS:
        if _has_team_rank(team_role, TeamRole.EDITOR):
            return _allow()
        if team_role is None:
            return _deny(Reason.NOT_TEAM_MEMBER)
        return _deny(Reason.TEAM_ROLE_INSUFFICIENT)

    if action is Action.WORKFLOW_EXECUTE:
        if _has_team_rank(team_role, TeamRole.VIEWER):
            return _allow()
        if team_role is None:
            return _deny(Reason.NOT_TEAM_MEMBER)
        return _deny(Reason.TEAM_ROLE_INSUFFICIENT)

    return _deny(Reason.ORG_ROLE_INSUFFICIENT)
