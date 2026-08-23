from uuid import UUID

from src.authn.api_keys import hash_api_key
from src.authz.memory import InMemoryMembershipStore
from src.authz.models import OrgRole, TeamRole, UserPrincipal, Visibility
from src.workflows.passwords import hash_export_password

ORG_A = UUID("00000000-0000-0000-0000-00000000000a")
ORG_B = UUID("00000000-0000-0000-0000-00000000000b")
TEAM_DEFAULT_A = UUID("00000000-0000-0000-0000-0000000000d1")
TEAM_A1 = UUID("00000000-0000-0000-0000-0000000000a1")
TEAM_B1 = UUID("00000000-0000-0000-0000-0000000000b1")
WORKFLOW_A1 = UUID("00000000-0000-0000-0000-0000000000f1")
WORKFLOW_PUBLIC = UUID("00000000-0000-0000-0000-0000000000f2")
WORKFLOW_PASSWORD = UUID("00000000-0000-0000-0000-0000000000f3")
WORKFLOW_ORG = UUID("00000000-0000-0000-0000-0000000000f4")

SUPER_A = UserPrincipal(user_id=UUID("00000000-0000-0000-0000-000000000001"))
TEAM_ADMIN_A1 = UserPrincipal(user_id=UUID("00000000-0000-0000-0000-000000000002"))
EDITOR_A1 = UserPrincipal(user_id=UUID("00000000-0000-0000-0000-000000000003"))
VIEWER_A1 = UserPrincipal(user_id=UUID("00000000-0000-0000-0000-000000000004"))
ORG_MEMBER = UserPrincipal(user_id=UUID("00000000-0000-0000-0000-000000000005"))
OUTSIDER = UserPrincipal(user_id=UUID("00000000-0000-0000-0000-000000000006"))
TARGET = UserPrincipal(user_id=UUID("00000000-0000-0000-0000-000000000007"))

API_KEY_A = "sak_demo_acme_aaaaaaaaaaaaaaaaaaaaaaaaaaaa"
API_KEY_B = "sak_demo_other_bbbbbbbbbbbbbbbbbbbbbbbbbbbb"
EXPORT_PASSWORD = "export-secret"
EXPORT_PASSWORD_SALT = bytes(16)


def membership_store() -> InMemoryMembershipStore:
    seeded = InMemoryMembershipStore()
    seeded.add_org(ORG_A, "Acme")
    seeded.add_org(ORG_B, "Other Org")
    seeded.seed_team(TEAM_DEFAULT_A, ORG_A, "Default", is_default=True)
    seeded.seed_team(TEAM_A1, ORG_A, "Engineering", is_default=False)
    seeded.seed_team(TEAM_B1, ORG_B, "Default", is_default=True)
    seeded.seed_workflow(
        WORKFLOW_A1, ORG_A, TEAM_A1, "Demo workflow", Visibility.TEAM
    )
    seeded.seed_workflow(
        WORKFLOW_PUBLIC, ORG_A, TEAM_A1, "Public export", Visibility.PUBLIC
    )
    seeded.seed_workflow(
        WORKFLOW_PASSWORD,
        ORG_A,
        TEAM_A1,
        "Password export",
        Visibility.PASSWORD,
        hash_export_password(EXPORT_PASSWORD, salt=EXPORT_PASSWORD_SALT),
    )
    seeded.seed_workflow(
        WORKFLOW_ORG, ORG_A, TEAM_A1, "Org export", Visibility.ORG
    )
    seeded.seed_api_key(hash_api_key(API_KEY_A), ORG_A)
    seeded.seed_api_key(hash_api_key(API_KEY_B), ORG_B)

    seeded.add_org_member(SUPER_A.user_id, ORG_A, OrgRole.SUPER_ADMIN)
    seeded.add_team_member(SUPER_A.user_id, TEAM_A1, TeamRole.ADMIN)

    for user in (TEAM_ADMIN_A1, EDITOR_A1, VIEWER_A1, ORG_MEMBER, TARGET):
        seeded.add_org_member(user.user_id, ORG_A, OrgRole.MEMBER)

    seeded.add_team_member(TEAM_ADMIN_A1.user_id, TEAM_A1, TeamRole.ADMIN)
    seeded.add_team_member(EDITOR_A1.user_id, TEAM_A1, TeamRole.EDITOR)
    seeded.add_team_member(VIEWER_A1.user_id, TEAM_A1, TeamRole.VIEWER)

    seeded.add_org_member(OUTSIDER.user_id, ORG_B, OrgRole.MEMBER)
    seeded.seed_user(SUPER_A.user_id, "super-a@debug.local")
    seeded.seed_user(TEAM_ADMIN_A1.user_id, "team-admin@debug.local")
    seeded.seed_user(EDITOR_A1.user_id, "editor@debug.local")
    seeded.seed_user(VIEWER_A1.user_id, "viewer@debug.local")
    seeded.seed_user(ORG_MEMBER.user_id, "member@debug.local")
    seeded.seed_user(OUTSIDER.user_id, "outsider@debug.local")
    seeded.seed_user(TARGET.user_id, "target@debug.local")
    return seeded
