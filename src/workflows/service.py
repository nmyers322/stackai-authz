from uuid import UUID

from src.authz.models import (
    AnonymousPrincipal,
    ApiKeyPrincipal,
    OrgRole,
    Principal,
    UserPrincipal,
    Visibility,
)
from src.authz.store import AppStore, WorkflowRecord
from src.exceptions import NotFound
from src.workflows.passwords import export_password_ok, hash_export_password


def load_workflow(
    store: AppStore, org_id: UUID, workflow_id: UUID
) -> WorkflowRecord:
    workflow = store.get_workflow(org_id, workflow_id)
    if workflow is None:
        raise NotFound
    return workflow


def listed_workflows(
    store: AppStore, principal: Principal, org_id: UUID
) -> list[WorkflowRecord]:
    return [
        workflow
        for workflow in store.list_workflows(org_id)
        if _visible(principal, workflow, store)
    ]


def create_workflow(
    store: AppStore,
    org_id: UUID,
    team_id: UUID,
    name: str,
    visibility: Visibility,
    password: str | None,
) -> WorkflowRecord:
    if store.get_team(org_id, team_id) is None:
        raise NotFound
    return store.create_workflow(
        org_id,
        team_id,
        name,
        visibility,
        _hash_if_present(password),
    )


def replace_workflow(
    store: AppStore,
    org_id: UUID,
    workflow_id: UUID,
    team_id: UUID,
    name: str,
    visibility: Visibility,
    password: str | None,
) -> WorkflowRecord:
    if store.get_team(org_id, team_id) is None:
        raise NotFound
    return store.replace_workflow(
        org_id,
        workflow_id,
        team_id,
        name,
        visibility,
        _hash_if_present(password),
    )


def delete_workflow(store: AppStore, org_id: UUID, workflow_id: UUID) -> None:
    store.delete_workflow(org_id, workflow_id)


def password_matches(workflow: WorkflowRecord, password: str | None) -> bool:
    return export_password_ok(password, workflow.export_password_hash)


def _hash_if_present(password: str | None) -> str | None:
    if password is None:
        return None
    return hash_export_password(password)


def _visible(
    principal: Principal, workflow: WorkflowRecord, store: AppStore
) -> bool:
    if isinstance(principal, AnonymousPrincipal):
        return False
    if isinstance(principal, ApiKeyPrincipal):
        return True
    if not isinstance(principal, UserPrincipal):
        return False
    org_role = store.org_role(principal.user_id, workflow.org_id)
    if org_role is OrgRole.SUPER_ADMIN:
        return True
    if store.team_role(principal.user_id, workflow.team_id) is not None:
        return True
    return workflow.visibility is not Visibility.TEAM
