import pytest

from src.authz.engine import authorize
from src.authz.models import (
    Action,
    AnonymousPrincipal,
    ApiKeyPrincipal,
    Reason,
    Resource,
    Visibility,
)
from src.seed import (
    EDITOR_A1,
    ORG_A,
    ORG_B,
    ORG_MEMBER,
    OUTSIDER,
    SUPER_A,
    TARGET,
    TEAM_A1,
    TEAM_ADMIN_A1,
    TEAM_DEFAULT_A,
    VIEWER_A1,
    membership_store,
)

KEY_A = ApiKeyPrincipal(org_id=ORG_A)
KEY_B = ApiKeyPrincipal(org_id=ORG_B)
ANON = AnonymousPrincipal()

ORG_A_RES = Resource(org_id=ORG_A)
ORG_B_RES = Resource(org_id=ORG_B)
TEAM_A1_RES = Resource(org_id=ORG_A, team_id=TEAM_A1)
TEAM_DEFAULT_RES = Resource(org_id=ORG_A, team_id=TEAM_DEFAULT_A, is_default_team=True)
TEAM_DEFAULT_TARGET = Resource(
    org_id=ORG_A,
    team_id=TEAM_DEFAULT_A,
    user_id=TARGET.user_id,
    is_default_team=True,
)
TEAM_A1_TARGET = Resource(org_id=ORG_A, team_id=TEAM_A1, user_id=TARGET.user_id)
TEAM_A1_SELF_ADMIN = Resource(
    org_id=ORG_A, team_id=TEAM_A1, user_id=TEAM_ADMIN_A1.user_id
)
ORG_A_TARGET = Resource(org_id=ORG_A, user_id=TARGET.user_id)
ORG_A_SELF_SUPER = Resource(org_id=ORG_A, user_id=SUPER_A.user_id)
LIST_TEAMS_SELF = Resource(org_id=ORG_A, user_id=VIEWER_A1.user_id)
LIST_TEAMS_OTHER = Resource(org_id=ORG_A, user_id=TARGET.user_id)
LIST_ORGS_SELF = Resource(user_id=VIEWER_A1.user_id)
LIST_ORGS_OTHER = Resource(user_id=TARGET.user_id)
WF_TEAM = Resource(org_id=ORG_A, team_id=TEAM_A1, visibility=Visibility.TEAM)
WF_PUBLIC = Resource(org_id=ORG_A, team_id=TEAM_A1, visibility=Visibility.PUBLIC)
WF_PASSWORD_OK = Resource(
    org_id=ORG_A,
    team_id=TEAM_A1,
    visibility=Visibility.PASSWORD,
    export_password_ok=True,
)
WF_PASSWORD_BAD = Resource(
    org_id=ORG_A,
    team_id=TEAM_A1,
    visibility=Visibility.PASSWORD,
    export_password_ok=False,
)
WF_ORG = Resource(org_id=ORG_A, team_id=TEAM_A1, visibility=Visibility.ORG)


@pytest.fixture
def store():
    return membership_store()


AUTHZ_MATRIX: list[tuple[object, Action, Resource, bool]] = [
    # team.create
    (SUPER_A, Action.TEAM_CREATE, ORG_A_RES, True),
    (ORG_MEMBER, Action.TEAM_CREATE, ORG_A_RES, False),
    (OUTSIDER, Action.TEAM_CREATE, ORG_A_RES, False),
    (KEY_A, Action.TEAM_CREATE, ORG_A_RES, False),
    (ANON, Action.TEAM_CREATE, ORG_A_RES, False),
    # team.list
    (ORG_MEMBER, Action.TEAM_LIST, ORG_A_RES, True),
    (SUPER_A, Action.TEAM_LIST, ORG_A_RES, True),
    (OUTSIDER, Action.TEAM_LIST, ORG_A_RES, False),
    (KEY_A, Action.TEAM_LIST, ORG_A_RES, False),
    (ANON, Action.TEAM_LIST, ORG_A_RES, False),
    # team.delete
    (SUPER_A, Action.TEAM_DELETE, TEAM_A1_RES, True),
    (SUPER_A, Action.TEAM_DELETE, TEAM_DEFAULT_RES, False),
    (TEAM_ADMIN_A1, Action.TEAM_DELETE, TEAM_A1_RES, False),
    (KEY_A, Action.TEAM_DELETE, TEAM_A1_RES, False),
    (ANON, Action.TEAM_DELETE, TEAM_A1_RES, False),
    # team.member.add
    (TEAM_ADMIN_A1, Action.TEAM_MEMBER_ADD, TEAM_A1_TARGET, True),
    (SUPER_A, Action.TEAM_MEMBER_ADD, TEAM_A1_TARGET, True),
    (TEAM_ADMIN_A1, Action.TEAM_MEMBER_ADD, TEAM_A1_SELF_ADMIN, False),
    (EDITOR_A1, Action.TEAM_MEMBER_ADD, TEAM_A1_TARGET, False),
    (KEY_A, Action.TEAM_MEMBER_ADD, TEAM_A1_TARGET, False),
    (ANON, Action.TEAM_MEMBER_ADD, TEAM_A1_TARGET, False),
    # team.member.remove
    (TEAM_ADMIN_A1, Action.TEAM_MEMBER_REMOVE, TEAM_A1_TARGET, True),
    (EDITOR_A1, Action.TEAM_MEMBER_REMOVE, TEAM_A1_TARGET, False),
    (TEAM_ADMIN_A1, Action.TEAM_MEMBER_REMOVE, TEAM_A1_SELF_ADMIN, False),
    (SUPER_A, Action.TEAM_MEMBER_REMOVE, TEAM_DEFAULT_TARGET, False),
    (KEY_A, Action.TEAM_MEMBER_REMOVE, TEAM_A1_TARGET, False),
    (ANON, Action.TEAM_MEMBER_REMOVE, TEAM_A1_TARGET, False),
    # team.member.role.change
    (TEAM_ADMIN_A1, Action.TEAM_MEMBER_ROLE_CHANGE, TEAM_A1_TARGET, True),
    (VIEWER_A1, Action.TEAM_MEMBER_ROLE_CHANGE, TEAM_A1_TARGET, False),
    (KEY_A, Action.TEAM_MEMBER_ROLE_CHANGE, TEAM_A1_TARGET, False),
    (ANON, Action.TEAM_MEMBER_ROLE_CHANGE, TEAM_A1_TARGET, False),
    # org.member.add
    (SUPER_A, Action.ORG_MEMBER_ADD, ORG_A_TARGET, True),
    (SUPER_A, Action.ORG_MEMBER_ADD, ORG_A_SELF_SUPER, False),
    (ORG_MEMBER, Action.ORG_MEMBER_ADD, ORG_A_TARGET, False),
    (KEY_A, Action.ORG_MEMBER_ADD, ORG_A_TARGET, False),
    (ANON, Action.ORG_MEMBER_ADD, ORG_A_TARGET, False),
    # org.member.remove
    (SUPER_A, Action.ORG_MEMBER_REMOVE, ORG_A_TARGET, True),
    (ORG_MEMBER, Action.ORG_MEMBER_REMOVE, ORG_A_TARGET, False),
    (KEY_A, Action.ORG_MEMBER_REMOVE, ORG_A_TARGET, False),
    (ANON, Action.ORG_MEMBER_REMOVE, ORG_A_TARGET, False),
    # org.member.role.change
    (SUPER_A, Action.ORG_MEMBER_ROLE_CHANGE, ORG_A_TARGET, True),
    (SUPER_A, Action.ORG_MEMBER_ROLE_CHANGE, ORG_A_SELF_SUPER, False),
    (TEAM_ADMIN_A1, Action.ORG_MEMBER_ROLE_CHANGE, ORG_A_TARGET, False),
    (KEY_A, Action.ORG_MEMBER_ROLE_CHANGE, ORG_A_TARGET, False),
    (ANON, Action.ORG_MEMBER_ROLE_CHANGE, ORG_A_TARGET, False),
    # org.member.teams.list
    (VIEWER_A1, Action.ORG_MEMBER_TEAMS_LIST, LIST_TEAMS_SELF, True),
    (SUPER_A, Action.ORG_MEMBER_TEAMS_LIST, LIST_TEAMS_OTHER, True),
    (VIEWER_A1, Action.ORG_MEMBER_TEAMS_LIST, LIST_TEAMS_OTHER, False),
    (KEY_A, Action.ORG_MEMBER_TEAMS_LIST, LIST_TEAMS_SELF, False),
    (ANON, Action.ORG_MEMBER_TEAMS_LIST, LIST_TEAMS_SELF, False),
    # user.orgs.list
    (VIEWER_A1, Action.USER_ORGS_LIST, LIST_ORGS_SELF, True),
    (SUPER_A, Action.USER_ORGS_LIST, LIST_ORGS_OTHER, False),
    (VIEWER_A1, Action.USER_ORGS_LIST, LIST_ORGS_OTHER, False),
    (KEY_A, Action.USER_ORGS_LIST, LIST_ORGS_SELF, False),
    (ANON, Action.USER_ORGS_LIST, LIST_ORGS_SELF, False),
    # workflow.list
    (VIEWER_A1, Action.WORKFLOW_LIST, ORG_A_RES, True),
    (KEY_A, Action.WORKFLOW_LIST, ORG_A_RES, True),
    (KEY_B, Action.WORKFLOW_LIST, ORG_A_RES, False),
    (OUTSIDER, Action.WORKFLOW_LIST, ORG_A_RES, False),
    (ANON, Action.WORKFLOW_LIST, ORG_A_RES, False),
    # workflow.create
    (EDITOR_A1, Action.WORKFLOW_CREATE, TEAM_A1_RES, True),
    (TEAM_ADMIN_A1, Action.WORKFLOW_CREATE, TEAM_A1_RES, True),
    (SUPER_A, Action.WORKFLOW_CREATE, TEAM_A1_RES, True),
    (VIEWER_A1, Action.WORKFLOW_CREATE, TEAM_A1_RES, False),
    (ORG_MEMBER, Action.WORKFLOW_CREATE, TEAM_A1_RES, False),
    (KEY_A, Action.WORKFLOW_CREATE, TEAM_A1_RES, False),
    (ANON, Action.WORKFLOW_CREATE, TEAM_A1_RES, False),
    # workflow.update
    (EDITOR_A1, Action.WORKFLOW_UPDATE, WF_TEAM, True),
    (VIEWER_A1, Action.WORKFLOW_UPDATE, WF_TEAM, False),
    (KEY_A, Action.WORKFLOW_UPDATE, WF_TEAM, False),
    (ANON, Action.WORKFLOW_UPDATE, WF_TEAM, False),
    # workflow.delete
    (EDITOR_A1, Action.WORKFLOW_DELETE, WF_TEAM, True),
    (VIEWER_A1, Action.WORKFLOW_DELETE, WF_TEAM, False),
    (KEY_A, Action.WORKFLOW_DELETE, WF_TEAM, False),
    (ANON, Action.WORKFLOW_DELETE, WF_TEAM, False),
    # workflow.execute
    (VIEWER_A1, Action.WORKFLOW_EXECUTE, WF_TEAM, True),
    (EDITOR_A1, Action.WORKFLOW_EXECUTE, WF_TEAM, True),
    (SUPER_A, Action.WORKFLOW_EXECUTE, WF_TEAM, True),
    (KEY_A, Action.WORKFLOW_EXECUTE, WF_TEAM, True),
    (ORG_MEMBER, Action.WORKFLOW_EXECUTE, WF_TEAM, False),
    (KEY_B, Action.WORKFLOW_EXECUTE, WF_TEAM, False),
    (OUTSIDER, Action.WORKFLOW_EXECUTE, WF_TEAM, False),
    (ANON, Action.WORKFLOW_EXECUTE, WF_TEAM, False),
    # workflow.execute_exported — public
    (ANON, Action.WORKFLOW_EXECUTE_EXPORTED, WF_PUBLIC, True),
    (OUTSIDER, Action.WORKFLOW_EXECUTE_EXPORTED, WF_PUBLIC, True),
    (KEY_A, Action.WORKFLOW_EXECUTE_EXPORTED, WF_PUBLIC, True),
    (KEY_B, Action.WORKFLOW_EXECUTE_EXPORTED, WF_PUBLIC, False),
    (ANON, Action.WORKFLOW_EXECUTE_EXPORTED, WF_TEAM, False),
    # password
    (ANON, Action.WORKFLOW_EXECUTE_EXPORTED, WF_PASSWORD_OK, True),
    (ANON, Action.WORKFLOW_EXECUTE_EXPORTED, WF_PASSWORD_BAD, False),
    (KEY_A, Action.WORKFLOW_EXECUTE_EXPORTED, WF_PASSWORD_OK, True),
    (KEY_A, Action.WORKFLOW_EXECUTE_EXPORTED, WF_PASSWORD_BAD, False),
    # org-only export
    (ORG_MEMBER, Action.WORKFLOW_EXECUTE_EXPORTED, WF_ORG, True),
    (SUPER_A, Action.WORKFLOW_EXECUTE_EXPORTED, WF_ORG, True),
    (OUTSIDER, Action.WORKFLOW_EXECUTE_EXPORTED, WF_ORG, False),
    (ANON, Action.WORKFLOW_EXECUTE_EXPORTED, WF_ORG, False),
    (KEY_A, Action.WORKFLOW_EXECUTE_EXPORTED, WF_ORG, False),
    (SUPER_A, Action.TEAM_CREATE, ORG_B_RES, False),
]


@pytest.mark.parametrize("principal,action,resource,allowed", AUTHZ_MATRIX)
def test_authorize_matrix(principal, action, resource, allowed, store):
    decision = authorize(principal, action, resource, store=store)
    assert decision.allowed is allowed


def test_matrix_covers_every_action():
    covered = {action for _, action, _, _ in AUTHZ_MATRIX}
    assert covered == set(Action)


def test_every_action_has_allow_and_deny():
    by_action: dict[Action, set[bool]] = {action: set() for action in Action}
    for _, action, _, allowed in AUTHZ_MATRIX:
        by_action[action].add(allowed)
    missing = {
        action.value: sorted(values)
        for action, values in by_action.items()
        if values != {True, False}
    }
    assert missing == {}


@pytest.mark.parametrize(
    "principal,action,resource,reason",
    [
        (SUPER_A, Action.TEAM_DELETE, TEAM_DEFAULT_RES, Reason.DEFAULT_TEAM_IMMUTABLE),
        (
            SUPER_A,
            Action.TEAM_MEMBER_REMOVE,
            TEAM_DEFAULT_TARGET,
            Reason.DEFAULT_TEAM_IMMUTABLE,
        ),
        (
            TEAM_ADMIN_A1,
            Action.TEAM_MEMBER_ADD,
            TEAM_A1_SELF_ADMIN,
            Reason.SELF_MEMBERSHIP_MUTATION,
        ),
        (SUPER_A, Action.USER_ORGS_LIST, LIST_ORGS_OTHER, Reason.IDENTITY_MISMATCH),
        (KEY_A, Action.WORKFLOW_DELETE, WF_TEAM, Reason.API_KEY_DENIED),
        (
            ANON,
            Action.WORKFLOW_EXECUTE_EXPORTED,
            WF_PASSWORD_BAD,
            Reason.EXPORT_PASSWORD_REQUIRED,
        ),
        (ANON, Action.WORKFLOW_EXECUTE_EXPORTED, WF_TEAM, Reason.EXPORT_NOT_PERMITTED),
        (KEY_A, Action.WORKFLOW_EXECUTE_EXPORTED, WF_ORG, Reason.API_KEY_DENIED),
        (KEY_B, Action.WORKFLOW_LIST, ORG_A_RES, Reason.WRONG_ORG),
    ],
)
def test_deny_reasons(principal, action, resource, reason, store):
    decision = authorize(principal, action, resource, store=store)
    assert decision.denied
    assert decision.reason is reason
