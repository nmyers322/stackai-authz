from uuid import UUID

from fastapi import APIRouter, status
from starlette.concurrency import run_in_threadpool

from src.authn.dependencies import PrincipalDep, StoreDep, require_http
from src.authz.models import Action, OrgRole, Resource
from src.orgs import service as orgs_service
from src.orgs.schemas import OrgMemberOut, OrgMemberWrite, UserOrgOut, UserTeamOut

router = APIRouter(prefix="/orgs/{org_id}/members", tags=["org-members"])
user_orgs_router = APIRouter(prefix="/users/{user_id}/orgs", tags=["user-orgs"])


@router.post(
    "/{user_id}",
    status_code=status.HTTP_201_CREATED,
    response_model=OrgMemberOut,
)
async def add_org_member(
    org_id: UUID,
    user_id: UUID,
    body: OrgMemberWrite,
    principal: PrincipalDep,
    store: StoreDep,
) -> dict[str, UUID | OrgRole]:
    await require_http(
        principal,
        Action.ORG_MEMBER_ADD,
        Resource(org_id=org_id, user_id=user_id),
        store,
    )
    await run_in_threadpool(
        orgs_service.add_member, store, org_id, user_id, body.role
    )
    return {"org_id": org_id, "user_id": user_id, "role": body.role}


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_org_member(
    org_id: UUID, user_id: UUID, principal: PrincipalDep, store: StoreDep
) -> None:
    await require_http(
        principal,
        Action.ORG_MEMBER_REMOVE,
        Resource(org_id=org_id, user_id=user_id),
        store,
    )
    await run_in_threadpool(orgs_service.remove_member, store, org_id, user_id)


@router.patch("/{user_id}", response_model=OrgMemberOut)
async def change_org_membership_role(
    org_id: UUID,
    user_id: UUID,
    body: OrgMemberWrite,
    principal: PrincipalDep,
    store: StoreDep,
) -> dict[str, UUID | OrgRole]:
    await require_http(
        principal,
        Action.ORG_MEMBER_ROLE_CHANGE,
        Resource(org_id=org_id, user_id=user_id),
        store,
    )
    await run_in_threadpool(
        orgs_service.change_member_role, store, org_id, user_id, body.role
    )
    return {"org_id": org_id, "user_id": user_id, "role": body.role}


@router.get("/{user_id}/teams", response_model=list[UserTeamOut])
async def list_user_team_memberships(
    org_id: UUID, user_id: UUID, principal: PrincipalDep, store: StoreDep
) -> list[dict[str, UUID | str | bool]]:
    await require_http(
        principal,
        Action.ORG_MEMBER_TEAMS_LIST,
        Resource(org_id=org_id, user_id=user_id),
        store,
    )
    rows = await run_in_threadpool(
        orgs_service.list_user_teams, store, org_id, user_id
    )
    return [
        {
            "team_id": row.team_id,
            "name": row.team_name,
            "role": row.role,
            "is_default": row.is_default,
        }
        for row in rows
    ]


@user_orgs_router.get("", response_model=list[UserOrgOut])
async def list_user_orgs(
    user_id: UUID, principal: PrincipalDep, store: StoreDep
) -> list[dict[str, UUID | str]]:
    await require_http(
        principal,
        Action.USER_ORGS_LIST,
        Resource(user_id=user_id),
        store,
    )
    rows = await run_in_threadpool(orgs_service.list_user_orgs, store, user_id)
    return [
        {"org_id": row.org_id, "name": row.org_name, "role": row.role} for row in rows
    ]
