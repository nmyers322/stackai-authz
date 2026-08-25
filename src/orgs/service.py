from uuid import UUID

from src.authz.models import OrgRole, UserPrincipal
from src.authz.store import (
    AppStore,
    OrgMembershipRecord,
    OrgRecord,
    TeamMembershipRecord,
)


def create_org(store: AppStore, name: str, creator: UserPrincipal) -> OrgRecord:
    return store.create_org(name, creator.user_id)


def add_member(
    store: AppStore, org_id: UUID, user_id: UUID, role: OrgRole
) -> None:
    store.add_org_member(user_id, org_id, role)


def remove_member(store: AppStore, org_id: UUID, user_id: UUID) -> None:
    store.remove_org_member(org_id, user_id)


def change_member_role(
    store: AppStore, org_id: UUID, user_id: UUID, role: OrgRole
) -> None:
    store.set_org_role(org_id, user_id, role)


def list_user_teams(
    store: AppStore, org_id: UUID, user_id: UUID
) -> list[TeamMembershipRecord]:
    return store.list_user_teams(org_id, user_id)


def list_user_orgs(store: AppStore, user_id: UUID) -> list[OrgMembershipRecord]:
    return store.list_user_orgs(user_id)
