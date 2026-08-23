from uuid import UUID

from pydantic import BaseModel, ConfigDict

from src.authz.models import OrgRole, TeamRole


class OrgMemberWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: OrgRole


class OrgMemberOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    org_id: UUID
    user_id: UUID
    role: OrgRole


class UserTeamOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    team_id: UUID
    name: str
    role: TeamRole
    is_default: bool


class UserOrgOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    org_id: UUID
    name: str
    role: OrgRole
