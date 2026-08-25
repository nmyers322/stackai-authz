from enum import StrEnum
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class OrgRole(StrEnum):
    SUPER_ADMIN = "super_admin"
    MEMBER = "member"


class TeamRole(StrEnum):
    ADMIN = "admin"
    EDITOR = "editor"
    VIEWER = "viewer"


class Visibility(StrEnum):
    TEAM = "team"
    PUBLIC = "public"
    PASSWORD = "password"
    ORG = "org"


class Action(StrEnum):
    TEAM_CREATE = "team.create"
    TEAM_LIST = "team.list"
    TEAM_DELETE = "team.delete"
    TEAM_MEMBER_ADD = "team.member.add"
    TEAM_MEMBER_REMOVE = "team.member.remove"
    TEAM_MEMBER_ROLE_CHANGE = "team.member.role.change"
    ORG_MEMBER_ADD = "org.member.add"
    ORG_MEMBER_REMOVE = "org.member.remove"
    ORG_MEMBER_ROLE_CHANGE = "org.member.role.change"
    ORG_MEMBER_TEAMS_LIST = "org.member.teams.list"
    ORG_CREATE = "org.create"
    USER_ORGS_LIST = "user.orgs.list"
    WORKFLOW_LIST = "workflow.list"
    WORKFLOW_CREATE = "workflow.create"
    WORKFLOW_UPDATE = "workflow.update"
    WORKFLOW_DELETE = "workflow.delete"
    WORKFLOW_EXECUTE = "workflow.execute"
    WORKFLOW_EXECUTE_EXPORTED = "workflow.execute_exported"


class Reason(StrEnum):
    ALLOWED = "allowed"
    ANONYMOUS_DENIED = "anonymous_denied"
    API_KEY_DENIED = "api_key_denied"
    NOT_ORG_MEMBER = "not_org_member"
    ORG_ROLE_INSUFFICIENT = "org_role_insufficient"
    NOT_TEAM_MEMBER = "not_team_member"
    TEAM_ROLE_INSUFFICIENT = "team_role_insufficient"
    SELF_MEMBERSHIP_MUTATION = "self_membership_mutation"
    DEFAULT_TEAM_IMMUTABLE = "default_team_immutable"
    IDENTITY_MISMATCH = "identity_mismatch"
    WRONG_ORG = "wrong_org"
    EXPORT_NOT_PERMITTED = "export_not_permitted"
    EXPORT_PASSWORD_REQUIRED = "export_password_required"
    RESOURCE_INCOMPLETE = "resource_incomplete"


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True)


class UserPrincipal(FrozenModel):
    kind: Literal["user"] = "user"
    user_id: UUID


class ApiKeyPrincipal(FrozenModel):
    kind: Literal["api_key"] = "api_key"
    org_id: UUID


class AnonymousPrincipal(FrozenModel):
    kind: Literal["anonymous"] = "anonymous"


Principal = Annotated[
    UserPrincipal | ApiKeyPrincipal | AnonymousPrincipal,
    Field(discriminator="kind"),
]


class Resource(FrozenModel):
    org_id: UUID | None = None
    team_id: UUID | None = None
    workflow_id: UUID | None = None
    user_id: UUID | None = None
    visibility: Visibility | None = None
    is_default_team: bool = False
    export_password_ok: bool = False


class Decision(FrozenModel):
    allowed: bool
    reason: Reason

    @property
    def denied(self) -> bool:
        return not self.allowed


TEAM_RANK: dict[TeamRole, int] = {
    TeamRole.VIEWER: 1,
    TeamRole.EDITOR: 2,
    TeamRole.ADMIN: 3,
}

ORG_ADMIN_ACTIONS: frozenset[Action] = frozenset(
    {
        Action.TEAM_CREATE,
        Action.TEAM_DELETE,
        Action.ORG_MEMBER_ADD,
        Action.ORG_MEMBER_REMOVE,
        Action.ORG_MEMBER_ROLE_CHANGE,
    }
)

TEAM_ADMIN_ACTIONS: frozenset[Action] = frozenset(
    {
        Action.TEAM_MEMBER_ADD,
        Action.TEAM_MEMBER_REMOVE,
        Action.TEAM_MEMBER_ROLE_CHANGE,
    }
)

MEMBERSHIP_MUTATIONS: frozenset[Action] = frozenset(
    {
        Action.TEAM_MEMBER_ADD,
        Action.TEAM_MEMBER_REMOVE,
        Action.TEAM_MEMBER_ROLE_CHANGE,
        Action.ORG_MEMBER_ADD,
        Action.ORG_MEMBER_REMOVE,
        Action.ORG_MEMBER_ROLE_CHANGE,
    }
)

EDITOR_WORKFLOW_ACTIONS: frozenset[Action] = frozenset(
    {
        Action.WORKFLOW_CREATE,
        Action.WORKFLOW_UPDATE,
        Action.WORKFLOW_DELETE,
    }
)

API_KEY_ACTIONS: frozenset[Action] = frozenset(
    {
        Action.WORKFLOW_LIST,
        Action.WORKFLOW_EXECUTE,
        Action.WORKFLOW_EXECUTE_EXPORTED,
    }
)
