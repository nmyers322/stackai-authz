from fastapi.testclient import TestClient

from src.authn.jwks import StaticTokenVerifier
from src.main import create_app
from src.seed import ORG_A, ORG_MEMBER, TEAM_A1, TEAM_DEFAULT_A, membership_store


def _client() -> TestClient:
    application = create_app(
        store=membership_store(),
        verifier=StaticTokenVerifier({"member-token": ORG_MEMBER.user_id}),
    )
    return TestClient(application)


def test_smoke_allowed_lists_teams():
    client = _client()
    response = client.get(
        f"/orgs/{ORG_A}/teams",
        headers={"Authorization": "Bearer member-token"},
    )
    assert response.status_code == 200
    ids = {row["id"] for row in response.json()}
    assert str(TEAM_DEFAULT_A) in ids
    assert str(TEAM_A1) in ids


def test_smoke_forbidden_create_team():
    client = _client()
    response = client.post(
        f"/orgs/{ORG_A}/teams",
        headers={"Authorization": "Bearer member-token"},
        json={"name": "Nope"},
    )
    assert response.status_code == 403
    body = response.json()
    assert body["error"] == "forbidden"
    assert body["reason"] == "org_role_insufficient"


def test_smoke_unauthenticated_bad_jwt():
    client = _client()
    response = client.get(
        f"/orgs/{ORG_A}/teams",
        headers={"Authorization": "Bearer definitely-not-a-jwt"},
    )
    assert response.status_code == 401
    assert response.json() == {"error": "unauthenticated"}
