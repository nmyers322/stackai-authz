from uuid import UUID

from src.authz.models import TeamRole
from src.authz.store import AppStore, TeamRecord
from src.exceptions import NotFound


def load_team(store: AppStore, org_id: UUID, team_id: UUID) -> TeamRecord:
    team = store.get_team(org_id, team_id)
    if team is None:
        raise NotFound
    return team


def require_org_member(store: AppStore, org_id: UUID, user_id: UUID) -> None:
    if store.org_role(user_id, org_id) is None:
        raise NotFound


def list_teams(store: AppStore, org_id: UUID) -> list[TeamRecord]:
    return store.list_teams(org_id)


def create_team(store: AppStore, org_id: UUID, name: str) -> TeamRecord:
    return store.create_team(org_id, name)


def delete_team(store: AppStore, org_id: UUID, team_id: UUID) -> None:
    store.delete_team(org_id, team_id)


def add_member(
    store: AppStore, org_id: UUID, team_id: UUID, user_id: UUID, role: TeamRole
) -> None:
    require_org_member(store, org_id, user_id)
    store.add_team_member(user_id, team_id, role)


def remove_member(store: AppStore, team_id: UUID, user_id: UUID) -> None:
    store.remove_team_member(team_id, user_id)


def change_member_role(
    store: AppStore, team_id: UUID, user_id: UUID, role: TeamRole
) -> None:
    store.set_team_role(team_id, user_id, role)
