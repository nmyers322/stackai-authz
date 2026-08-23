from uuid import UUID, uuid4

from src.authz.models import OrgRole, TeamRole, Visibility
from src.authz.store import (
    OrgMembershipRecord,
    TeamMembershipRecord,
    TeamRecord,
    WorkflowRecord,
)
from src.exceptions import Conflict, NotFound


class InMemoryMembershipStore:
    def __init__(self) -> None:
        self._org_names: dict[UUID, str] = {}
        self._org: dict[tuple[UUID, UUID], OrgRole] = {}
        self._teams: dict[UUID, TeamRecord] = {}
        self._team: dict[tuple[UUID, UUID], TeamRole] = {}
        self._workflows: dict[UUID, WorkflowRecord] = {}
        self._api_keys: dict[str, UUID] = {}
        self._users: dict[UUID, str] = {}

    def seed_user(self, user_id: UUID, email: str) -> None:
        self._users[user_id] = email

    def add_org(self, org_id: UUID, name: str) -> None:
        self._org_names[org_id] = name

    def seed_team(
        self, team_id: UUID, org_id: UUID, name: str, *, is_default: bool
    ) -> None:
        self._teams[team_id] = TeamRecord(
            id=team_id, org_id=org_id, name=name, is_default=is_default
        )

    def seed_workflow(
        self,
        workflow_id: UUID,
        org_id: UUID,
        team_id: UUID,
        name: str,
        visibility: Visibility,
        export_password_hash: str | None = None,
    ) -> None:
        self._workflows[workflow_id] = WorkflowRecord(
            id=workflow_id,
            org_id=org_id,
            team_id=team_id,
            name=name,
            visibility=visibility,
            export_password_hash=export_password_hash,
        )

    def seed_api_key(self, key_hash: str, org_id: UUID) -> None:
        self._api_keys[key_hash] = org_id

    def org_role(self, user_id: UUID, org_id: UUID) -> OrgRole | None:
        return self._org.get((user_id, org_id))

    def team_role(self, user_id: UUID, team_id: UUID) -> TeamRole | None:
        return self._team.get((user_id, team_id))

    def org_exists(self, org_id: UUID) -> bool:
        return org_id in self._org_names

    def get_team(self, org_id: UUID, team_id: UUID) -> TeamRecord | None:
        team = self._teams.get(team_id)
        if team is None or team.org_id != org_id:
            return None
        return team

    def list_teams(self, org_id: UUID) -> list[TeamRecord]:
        teams = [team for team in self._teams.values() if team.org_id == org_id]
        return sorted(teams, key=lambda team: (not team.is_default, team.name))

    def create_team(self, org_id: UUID, name: str) -> TeamRecord:
        if org_id not in self._org_names:
            raise NotFound
        team = TeamRecord(id=uuid4(), org_id=org_id, name=name, is_default=False)
        self._teams[team.id] = team
        return team

    def delete_team(self, org_id: UUID, team_id: UUID) -> None:
        if self.get_team(org_id, team_id) is None:
            raise NotFound
        del self._teams[team_id]
        self._team = {
            key: role for key, role in self._team.items() if key[1] != team_id
        }
        self._workflows = {
            key: workflow
            for key, workflow in self._workflows.items()
            if workflow.team_id != team_id
        }

    def add_org_member(self, user_id: UUID, org_id: UUID, role: OrgRole) -> None:
        if org_id not in self._org_names:
            raise NotFound
        if (user_id, org_id) in self._org:
            raise Conflict
        self._org[(user_id, org_id)] = role
        default_role = (
            TeamRole.ADMIN if role is OrgRole.SUPER_ADMIN else TeamRole.VIEWER
        )
        for team in self._teams.values():
            if team.org_id == org_id and team.is_default:
                self._team.setdefault((user_id, team.id), default_role)

    def remove_org_member(self, org_id: UUID, user_id: UUID) -> None:
        if self._org.pop((user_id, org_id), None) is None:
            raise NotFound
        team_ids = {team.id for team in self._teams.values() if team.org_id == org_id}
        self._team = {
            key: role
            for key, role in self._team.items()
            if not (key[0] == user_id and key[1] in team_ids)
        }

    def set_org_role(self, org_id: UUID, user_id: UUID, role: OrgRole) -> None:
        if (user_id, org_id) not in self._org:
            raise NotFound
        self._org[(user_id, org_id)] = role

    def list_user_orgs(self, user_id: UUID) -> list[OrgMembershipRecord]:
        rows: list[OrgMembershipRecord] = []
        for (member_id, org_id), role in self._org.items():
            if member_id != user_id:
                continue
            rows.append(
                OrgMembershipRecord(
                    org_id=org_id, org_name=self._org_names[org_id], role=role
                )
            )
        return sorted(rows, key=lambda row: row.org_name)

    def add_team_member(self, user_id: UUID, team_id: UUID, role: TeamRole) -> None:
        if team_id not in self._teams:
            raise NotFound
        if (user_id, team_id) in self._team:
            raise Conflict
        self._team[(user_id, team_id)] = role

    def remove_team_member(self, team_id: UUID, user_id: UUID) -> None:
        if self._team.pop((user_id, team_id), None) is None:
            raise NotFound

    def set_team_role(self, team_id: UUID, user_id: UUID, role: TeamRole) -> None:
        if (user_id, team_id) not in self._team:
            raise NotFound
        self._team[(user_id, team_id)] = role

    def list_user_teams(
        self, org_id: UUID, user_id: UUID
    ) -> list[TeamMembershipRecord]:
        rows: list[TeamMembershipRecord] = []
        for team in self._teams.values():
            if team.org_id != org_id:
                continue
            role = self._team.get((user_id, team.id))
            if role is None:
                continue
            rows.append(
                TeamMembershipRecord(
                    team_id=team.id,
                    team_name=team.name,
                    role=role,
                    is_default=team.is_default,
                )
            )
        return sorted(rows, key=lambda row: (not row.is_default, row.team_name))

    def org_id_for_key_hash(self, key_hash: str) -> UUID | None:
        return self._api_keys.get(key_hash)

    def get_workflow(self, org_id: UUID, workflow_id: UUID) -> WorkflowRecord | None:
        workflow = self._workflows.get(workflow_id)
        if workflow is None or workflow.org_id != org_id:
            return None
        return workflow

    def list_workflows(self, org_id: UUID) -> list[WorkflowRecord]:
        workflows = [
            workflow
            for workflow in self._workflows.values()
            if workflow.org_id == org_id
        ]
        return sorted(workflows, key=lambda workflow: workflow.name)

    def create_workflow(
        self,
        org_id: UUID,
        team_id: UUID,
        name: str,
        visibility: Visibility,
        export_password_hash: str | None,
    ) -> WorkflowRecord:
        if self.get_team(org_id, team_id) is None:
            raise NotFound
        workflow = WorkflowRecord(
            id=uuid4(),
            org_id=org_id,
            team_id=team_id,
            name=name,
            visibility=visibility,
            export_password_hash=export_password_hash,
        )
        self._workflows[workflow.id] = workflow
        return workflow

    def replace_workflow(
        self,
        org_id: UUID,
        workflow_id: UUID,
        team_id: UUID,
        name: str,
        visibility: Visibility,
        export_password_hash: str | None,
    ) -> WorkflowRecord:
        if self.get_workflow(org_id, workflow_id) is None:
            raise NotFound
        if self.get_team(org_id, team_id) is None:
            raise NotFound
        workflow = WorkflowRecord(
            id=workflow_id,
            org_id=org_id,
            team_id=team_id,
            name=name,
            visibility=visibility,
            export_password_hash=export_password_hash,
        )
        self._workflows[workflow_id] = workflow
        return workflow

    def delete_workflow(self, org_id: UUID, workflow_id: UUID) -> None:
        if self.get_workflow(org_id, workflow_id) is None:
            raise NotFound
        del self._workflows[workflow_id]
