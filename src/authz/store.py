from typing import Protocol
from uuid import UUID

from src.authz.models import FrozenModel, OrgRole, TeamRole, Visibility


class OrgRecord(FrozenModel):
    id: UUID
    name: str


class TeamRecord(FrozenModel):
    id: UUID
    org_id: UUID
    name: str
    is_default: bool


class WorkflowRecord(FrozenModel):
    id: UUID
    org_id: UUID
    team_id: UUID
    name: str
    visibility: Visibility
    export_password_hash: str | None = None


class OrgMembershipRecord(FrozenModel):
    org_id: UUID
    org_name: str
    role: OrgRole


class TeamMembershipRecord(FrozenModel):
    team_id: UUID
    team_name: str
    role: TeamRole
    is_default: bool


class MembershipStore(Protocol):
    def org_role(self, user_id: UUID, org_id: UUID) -> OrgRole | None: ...

    def team_role(self, user_id: UUID, team_id: UUID) -> TeamRole | None: ...


class AppStore(MembershipStore, Protocol):
    def org_exists(self, org_id: UUID) -> bool: ...

    def create_org(self, name: str, creator_user_id: UUID) -> OrgRecord: ...

    def delete_org(self, org_id: UUID) -> None: ...

    def org_member_count(self, org_id: UUID) -> int: ...

    def org_ids_for_user(self, user_id: UUID) -> list[UUID]: ...

    def get_team(self, org_id: UUID, team_id: UUID) -> TeamRecord | None: ...

    def list_teams(self, org_id: UUID) -> list[TeamRecord]: ...

    def create_team(self, org_id: UUID, name: str) -> TeamRecord: ...

    def delete_team(self, org_id: UUID, team_id: UUID) -> None: ...

    def add_org_member(self, user_id: UUID, org_id: UUID, role: OrgRole) -> None: ...

    def remove_org_member(self, org_id: UUID, user_id: UUID) -> None: ...

    def set_org_role(self, org_id: UUID, user_id: UUID, role: OrgRole) -> None: ...

    def list_user_orgs(self, user_id: UUID) -> list[OrgMembershipRecord]: ...

    def add_team_member(self, user_id: UUID, team_id: UUID, role: TeamRole) -> None: ...

    def remove_team_member(self, team_id: UUID, user_id: UUID) -> None: ...

    def set_team_role(self, team_id: UUID, user_id: UUID, role: TeamRole) -> None: ...

    def list_user_teams(
        self, org_id: UUID, user_id: UUID
    ) -> list[TeamMembershipRecord]: ...

    def org_id_for_key_hash(self, key_hash: str) -> UUID | None: ...

    def get_workflow(
        self, org_id: UUID, workflow_id: UUID
    ) -> WorkflowRecord | None: ...

    def list_workflows(self, org_id: UUID) -> list[WorkflowRecord]: ...

    def create_workflow(
        self,
        org_id: UUID,
        team_id: UUID,
        name: str,
        visibility: Visibility,
        export_password_hash: str | None,
    ) -> WorkflowRecord: ...

    def replace_workflow(
        self,
        org_id: UUID,
        workflow_id: UUID,
        team_id: UUID,
        name: str,
        visibility: Visibility,
        export_password_hash: str | None,
    ) -> WorkflowRecord: ...

    def delete_workflow(self, org_id: UUID, workflow_id: UUID) -> None: ...
