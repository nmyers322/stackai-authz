from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from src.authn.jwks import StaticTokenVerifier
from src.authz.exceptions import AuthorizationError
from src.authz.guard import require
from src.authz.models import Action, Resource, TeamRole, Visibility
from src.exceptions import Conflict, NotFound
from src.main import create_app
from src.orgs import service as orgs_service
from src.seed import (
    EDITOR_A1,
    ORG_A,
    ORG_MEMBER,
    SUPER_A,
    TARGET,
    TEAM_A1,
    TEAM_DEFAULT_A,
    VIEWER_A1,
    WORKFLOW_A1,
    membership_store,
)
from src.teams import service as teams_service
from src.workflows import service as workflows_service


def test_create_list_delete_team_reflects_writes():
    store = membership_store()
    created = teams_service.create_team(store, ORG_A, "Design")
    names = {team.name for team in teams_service.list_teams(store, ORG_A)}
    assert {"Design", "Default", "Engineering"} <= names
    teams_service.delete_team(store, ORG_A, created.id)
    remaining = {team.id for team in teams_service.list_teams(store, ORG_A)}
    assert created.id not in remaining
    assert TEAM_A1 in remaining


def test_delete_unknown_team_is_not_found():
    store = membership_store()
    with pytest.raises(NotFound):
        teams_service.delete_team(store, ORG_A, uuid4())


def test_delete_team_cascades_workflows():
    store = membership_store()
    team = teams_service.create_team(store, ORG_A, "Temp")
    workflow = workflows_service.create_workflow(
        store, ORG_A, team.id, "Temp flow", Visibility.TEAM, None
    )
    teams_service.delete_team(store, ORG_A, team.id)
    assert store.get_workflow(ORG_A, workflow.id) is None


def test_add_team_member_then_list_roles():
    store = membership_store()
    teams_service.add_member(store, ORG_A, TEAM_A1, TARGET.user_id, TeamRole.VIEWER)
    rows = orgs_service.list_user_teams(store, ORG_A, TARGET.user_id)
    by_id = {row.team_id: row.role for row in rows}
    assert by_id[TEAM_DEFAULT_A] is TeamRole.VIEWER
    assert by_id[TEAM_A1] is TeamRole.VIEWER


def test_duplicate_team_member_conflicts():
    store = membership_store()
    with pytest.raises(Conflict):
        teams_service.add_member(
            store, ORG_A, TEAM_A1, VIEWER_A1.user_id, TeamRole.VIEWER
        )


def test_remove_org_member_drops_team_memberships():
    store = membership_store()
    orgs_service.remove_member(store, ORG_A, VIEWER_A1.user_id)
    assert store.org_role(VIEWER_A1.user_id, ORG_A) is None
    assert store.team_role(VIEWER_A1.user_id, TEAM_A1) is None
    assert store.team_role(VIEWER_A1.user_id, TEAM_DEFAULT_A) is None


def test_org_member_does_not_see_other_team_workflows():
    store = membership_store()
    visible = workflows_service.listed_workflows(store, ORG_MEMBER, ORG_A)
    assert WORKFLOW_A1 not in {row.id for row in visible}


def test_team_viewer_sees_team_workflow():
    store = membership_store()
    visible = workflows_service.listed_workflows(store, VIEWER_A1, ORG_A)
    assert WORKFLOW_A1 in {row.id for row in visible}


def test_org_member_sees_org_visibility_workflow():
    store = membership_store()
    created = workflows_service.create_workflow(
        store, ORG_A, TEAM_A1, "Shared", Visibility.ORG, None
    )
    visible = workflows_service.listed_workflows(store, ORG_MEMBER, ORG_A)
    assert created.id in {row.id for row in visible}


def test_put_workflow_replaces_fields():
    store = membership_store()
    updated = workflows_service.replace_workflow(
        store,
        ORG_A,
        WORKFLOW_A1,
        TEAM_A1,
        "Renamed",
        Visibility.PUBLIC,
        None,
    )
    assert updated.name == "Renamed"
    assert updated.visibility is Visibility.PUBLIC


def test_unknown_workflow_is_not_found():
    store = membership_store()
    with pytest.raises(NotFound):
        workflows_service.load_workflow(store, ORG_A, uuid4())


def test_list_own_orgs_includes_role():
    store = membership_store()
    rows = orgs_service.list_user_orgs(store, SUPER_A.user_id)
    assert len(rows) == 1
    assert rows[0].org_id == ORG_A
    assert rows[0].role.value == "super_admin"


def test_default_team_remove_denied_before_write():
    store = membership_store()
    with pytest.raises(AuthorizationError) as caught:
        require(
            SUPER_A,
            Action.TEAM_MEMBER_REMOVE,
            Resource(
                org_id=ORG_A,
                team_id=TEAM_DEFAULT_A,
                user_id=TARGET.user_id,
                is_default_team=True,
            ),
            store,
        )
    assert caught.value.reason.value == "default_team_immutable"


def _client() -> TestClient:
    return TestClient(
        create_app(
            store=membership_store(),
            verifier=StaticTokenVerifier(
                {
                    "super": SUPER_A.user_id,
                    "editor": EDITOR_A1.user_id,
                }
            ),
        )
    )


def test_http_lists_reflect_team_create_and_delete():
    client = _client()
    created = client.post(
        f"/orgs/{ORG_A}/teams",
        headers={"Authorization": "Bearer super"},
        json={"name": "Design"},
    )
    assert created.status_code == 201
    team_id = created.json()["id"]
    listed = client.get(
        f"/orgs/{ORG_A}/teams",
        headers={"Authorization": "Bearer super"},
    )
    assert listed.status_code == 200
    ids = {row["id"] for row in listed.json()}
    assert team_id in ids
    deleted = client.delete(
        f"/orgs/{ORG_A}/teams/{team_id}",
        headers={"Authorization": "Bearer super"},
    )
    assert deleted.status_code == 204
    listed_after = client.get(
        f"/orgs/{ORG_A}/teams",
        headers={"Authorization": "Bearer super"},
    )
    assert team_id not in {row["id"] for row in listed_after.json()}


def test_http_unknown_team_is_404():
    client = _client()
    response = client.delete(
        f"/orgs/{ORG_A}/teams/{uuid4()}",
        headers={"Authorization": "Bearer super"},
    )
    assert response.status_code == 404
    assert response.json() == {"error": "not_found"}


def test_http_unknown_workflow_is_404():
    client = _client()
    response = client.delete(
        f"/orgs/{ORG_A}/workflows/{uuid4()}",
        headers={"Authorization": "Bearer editor"},
    )
    assert response.status_code == 404
