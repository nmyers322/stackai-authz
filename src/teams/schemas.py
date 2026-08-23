from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.authz.models import TeamRole


class TeamCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=200)


class TeamOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    org_id: UUID
    name: str
    is_default: bool


class TeamMemberWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: TeamRole


class TeamMemberOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    org_id: UUID
    team_id: UUID
    user_id: UUID
    role: TeamRole
