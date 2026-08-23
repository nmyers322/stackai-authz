from uuid import UUID

from fastapi import APIRouter, status
from starlette.concurrency import run_in_threadpool

from src.authn.dependencies import PrincipalDep, StoreDep, require_http
from src.authz.models import Action, Resource
from src.authz.store import WorkflowRecord
from src.teams import service as teams_service
from src.workflows import service as workflows_service
from src.workflows.schemas import (
    ExecuteExported,
    ExecuteOut,
    WorkflowOut,
    WorkflowWrite,
)

router = APIRouter(prefix="/orgs/{org_id}/workflows", tags=["workflows"])


@router.get("", response_model=list[WorkflowOut])
async def list_workflows(
    org_id: UUID,
    principal: PrincipalDep,
    store: StoreDep,
) -> list[dict[str, UUID | str]]:
    await require_http(principal, Action.WORKFLOW_LIST, Resource(org_id=org_id), store)
    workflows = await run_in_threadpool(
        workflows_service.listed_workflows, store, principal, org_id
    )
    return [_workflow_body(workflow) for workflow in workflows]


@router.post("", status_code=status.HTTP_201_CREATED, response_model=WorkflowOut)
async def create_workflow(
    org_id: UUID,
    body: WorkflowWrite,
    principal: PrincipalDep,
    store: StoreDep,
) -> dict[str, UUID | str]:
    await run_in_threadpool(teams_service.load_team, store, org_id, body.team_id)
    await require_http(
        principal,
        Action.WORKFLOW_CREATE,
        Resource(org_id=org_id, team_id=body.team_id),
        store,
    )
    workflow = await run_in_threadpool(
        workflows_service.create_workflow,
        store,
        org_id,
        body.team_id,
        body.name,
        body.visibility,
        body.password,
    )
    return _workflow_body(workflow)


@router.post("/{workflow_id}/execute", response_model=ExecuteOut)
async def execute_workflow(
    org_id: UUID,
    workflow_id: UUID,
    principal: PrincipalDep,
    store: StoreDep,
) -> dict[str, str | UUID]:
    workflow = await run_in_threadpool(
        workflows_service.load_workflow, store, org_id, workflow_id
    )
    await require_http(
        principal,
        Action.WORKFLOW_EXECUTE,
        Resource(
            org_id=org_id,
            team_id=workflow.team_id,
            workflow_id=workflow_id,
            visibility=workflow.visibility,
        ),
        store,
    )
    return {"status": "ok", "workflow_id": workflow_id}


@router.post("/{workflow_id}/execute-exported", response_model=ExecuteOut)
async def execute_exported_workflow(
    org_id: UUID,
    workflow_id: UUID,
    principal: PrincipalDep,
    store: StoreDep,
    body: ExecuteExported | None = None,
) -> dict[str, str | UUID]:
    workflow = await run_in_threadpool(
        workflows_service.load_workflow, store, org_id, workflow_id
    )
    password = None if body is None else body.password
    await require_http(
        principal,
        Action.WORKFLOW_EXECUTE_EXPORTED,
        Resource(
            org_id=org_id,
            team_id=workflow.team_id,
            workflow_id=workflow_id,
            visibility=workflow.visibility,
            export_password_ok=workflows_service.password_matches(workflow, password),
        ),
        store,
    )
    return {"status": "ok", "workflow_id": workflow_id}


@router.put("/{workflow_id}", response_model=WorkflowOut)
async def update_workflow(
    org_id: UUID,
    workflow_id: UUID,
    body: WorkflowWrite,
    principal: PrincipalDep,
    store: StoreDep,
) -> dict[str, UUID | str]:
    existing = await run_in_threadpool(
        workflows_service.load_workflow, store, org_id, workflow_id
    )
    await require_http(
        principal,
        Action.WORKFLOW_UPDATE,
        Resource(
            org_id=org_id,
            team_id=existing.team_id,
            workflow_id=workflow_id,
            visibility=existing.visibility,
        ),
        store,
    )
    if body.team_id != existing.team_id:
        await run_in_threadpool(teams_service.load_team, store, org_id, body.team_id)
        await require_http(
            principal,
            Action.WORKFLOW_CREATE,
            Resource(org_id=org_id, team_id=body.team_id),
            store,
        )
    workflow = await run_in_threadpool(
        workflows_service.replace_workflow,
        store,
        org_id,
        workflow_id,
        body.team_id,
        body.name,
        body.visibility,
        body.password,
    )
    return _workflow_body(workflow)


@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workflow(
    org_id: UUID,
    workflow_id: UUID,
    principal: PrincipalDep,
    store: StoreDep,
) -> None:
    workflow = await run_in_threadpool(
        workflows_service.load_workflow, store, org_id, workflow_id
    )
    await require_http(
        principal,
        Action.WORKFLOW_DELETE,
        Resource(
            org_id=org_id,
            team_id=workflow.team_id,
            workflow_id=workflow_id,
            visibility=workflow.visibility,
        ),
        store,
    )
    await run_in_threadpool(
        workflows_service.delete_workflow, store, org_id, workflow_id
    )


def _workflow_body(workflow: WorkflowRecord) -> dict[str, UUID | str]:
    return {
        "id": workflow.id,
        "org_id": workflow.org_id,
        "team_id": workflow.team_id,
        "name": workflow.name,
        "visibility": workflow.visibility,
    }
