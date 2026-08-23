from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.authz.models import Visibility


class WorkflowWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    team_id: UUID
    name: str = Field(min_length=1, max_length=200)
    visibility: Visibility
    password: str | None = None


class WorkflowOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    org_id: UUID
    team_id: UUID
    name: str
    visibility: Visibility


class ExecuteExported(BaseModel):
    model_config = ConfigDict(extra="forbid")

    password: str | None = None


class ExecuteOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
    workflow_id: UUID
