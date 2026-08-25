from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.authz.models import OrgRole, TeamRole


class OrgCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=200)


class OrgOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    name: str


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
