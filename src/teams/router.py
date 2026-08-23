from uuid import UUID

from fastapi import APIRouter, status
from starlette.concurrency import run_in_threadpool

from src.authn.dependencies import PrincipalDep, StoreDep, require_http
from src.authz.models import Action, Resource, TeamRole
from src.teams import service as teams_service
from src.teams.schemas import TeamCreate, TeamMemberOut, TeamMemberWrite, TeamOut

router = APIRouter(prefix="/orgs/{org_id}/teams", tags=["teams"])


@router.post("", status_code=status.HTTP_201_CREATED, response_model=TeamOut)
async def create_team(
    org_id: UUID,
    body: TeamCreate,
    principal: PrincipalDep,
    store: StoreDep,
) -> dict[str, UUID | str | bool]:
    await require_http(principal, Action.TEAM_CREATE, Resource(org_id=org_id), store)
    team = await run_in_threadpool(teams_service.create_team, store, org_id, body.name)
    return {
        "id": team.id,
        "org_id": team.org_id,
        "name": team.name,
        "is_default": team.is_default,
    }


@router.get("", response_model=list[TeamOut])
async def list_teams(
    org_id: UUID, principal: PrincipalDep, store: StoreDep
) -> list[dict[str, UUID | str | bool]]:
    await require_http(principal, Action.TEAM_LIST, Resource(org_id=org_id), store)
    teams = await run_in_threadpool(teams_service.list_teams, store, org_id)
    return [
        {
            "id": team.id,
            "org_id": team.org_id,
            "name": team.name,
            "is_default": team.is_default,
        }
        for team in teams
    ]


@router.delete("/{team_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_team(
    org_id: UUID, team_id: UUID, principal: PrincipalDep, store: StoreDep
) -> None:
    team = await run_in_threadpool(teams_service.load_team, store, org_id, team_id)
    await require_http(
        principal,
        Action.TEAM_DELETE,
        Resource(org_id=org_id, team_id=team_id, is_default_team=team.is_default),
        store,
    )
    await run_in_threadpool(teams_service.delete_team, store, org_id, team_id)


@router.post(
    "/{team_id}/members/{user_id}",
    status_code=status.HTTP_201_CREATED,
    response_model=TeamMemberOut,
)
async def add_team_member(
    org_id: UUID,
    team_id: UUID,
    user_id: UUID,
    body: TeamMemberWrite,
    principal: PrincipalDep,
    store: StoreDep,
) -> dict[str, UUID | TeamRole]:
    await run_in_threadpool(teams_service.load_team, store, org_id, team_id)
    await require_http(
        principal,
        Action.TEAM_MEMBER_ADD,
        Resource(org_id=org_id, team_id=team_id, user_id=user_id),
        store,
    )
    await run_in_threadpool(
        teams_service.add_member, store, org_id, team_id, user_id, body.role
    )
    return {
        "org_id": org_id,
        "team_id": team_id,
        "user_id": user_id,
        "role": body.role,
    }


@router.delete("/{team_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_team_member(
    org_id: UUID,
    team_id: UUID,
    user_id: UUID,
    principal: PrincipalDep,
    store: StoreDep,
) -> None:
    team = await run_in_threadpool(teams_service.load_team, store, org_id, team_id)
    await require_http(
        principal,
        Action.TEAM_MEMBER_REMOVE,
        Resource(
            org_id=org_id,
            team_id=team_id,
            user_id=user_id,
            is_default_team=team.is_default,
        ),
        store,
    )
    await run_in_threadpool(teams_service.remove_member, store, team_id, user_id)


@router.patch("/{team_id}/members/{user_id}", response_model=TeamMemberOut)
async def change_team_membership_role(
    org_id: UUID,
    team_id: UUID,
    user_id: UUID,
    body: TeamMemberWrite,
    principal: PrincipalDep,
    store: StoreDep,
) -> dict[str, UUID | TeamRole]:
    await run_in_threadpool(teams_service.load_team, store, org_id, team_id)
    await require_http(
        principal,
        Action.TEAM_MEMBER_ROLE_CHANGE,
        Resource(org_id=org_id, team_id=team_id, user_id=user_id),
        store,
    )
    await run_in_threadpool(
        teams_service.change_member_role, store, team_id, user_id, body.role
    )
    return {
        "org_id": org_id,
        "team_id": team_id,
        "user_id": user_id,
        "role": body.role,
    }
