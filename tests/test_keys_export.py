from fastapi.testclient import TestClient

from src.authn.jwks import StaticTokenVerifier
from src.main import create_app
from src.seed import (
    API_KEY_A,
    API_KEY_B,
    EXPORT_PASSWORD,
    ORG_A,
    ORG_MEMBER,
    WORKFLOW_A1,
    WORKFLOW_ORG,
    WORKFLOW_PASSWORD,
    WORKFLOW_PUBLIC,
    membership_store,
)


def _client() -> TestClient:
    return TestClient(
        create_app(
            store=membership_store(),
            verifier=StaticTokenVerifier({"member-token": ORG_MEMBER.user_id}),
        )
    )


def test_api_key_lists_and_executes_in_org():
    client = _client()
    listed = client.get(
        f"/orgs/{ORG_A}/workflows",
        headers={"X-Api-Key": API_KEY_A},
    )
    assert listed.status_code == 200
    ids = {row["id"] for row in listed.json()}
    assert str(WORKFLOW_A1) in ids
    executed = client.post(
        f"/orgs/{ORG_A}/workflows/{WORKFLOW_A1}/execute",
        headers={"X-Api-Key": API_KEY_A},
    )
    assert executed.status_code == 200
    assert executed.json() == {"status": "ok", "workflow_id": str(WORKFLOW_A1)}


def test_api_key_cannot_create_team():
    client = _client()
    response = client.post(
        f"/orgs/{ORG_A}/teams",
        headers={"X-Api-Key": API_KEY_A},
        json={"name": "Nope"},
    )
    assert response.status_code == 403
    assert response.json()["reason"] == "api_key_denied"


def test_foreign_api_key_is_wrong_org():
    client = _client()
    response = client.get(
        f"/orgs/{ORG_A}/workflows",
        headers={"X-Api-Key": API_KEY_B},
    )
    assert response.status_code == 403
    assert response.json()["reason"] == "wrong_org"


def test_unknown_api_key_is_401():
    client = _client()
    response = client.get(
        f"/orgs/{ORG_A}/workflows",
        headers={"X-Api-Key": "sak_not_a_real_key"},
    )
    assert response.status_code == 401


def test_public_export_allows_anonymous():
    client = _client()
    response = client.post(
        f"/orgs/{ORG_A}/workflows/{WORKFLOW_PUBLIC}/execute-exported"
    )
    assert response.status_code == 200


def test_password_export_requires_matching_password():
    client = _client()
    missing = client.post(
        f"/orgs/{ORG_A}/workflows/{WORKFLOW_PASSWORD}/execute-exported"
    )
    assert missing.status_code == 403
    assert missing.json()["reason"] == "export_password_required"
    wrong = client.post(
        f"/orgs/{ORG_A}/workflows/{WORKFLOW_PASSWORD}/execute-exported",
        json={"password": "nope"},
    )
    assert wrong.status_code == 403
    assert wrong.json()["reason"] == "export_password_required"
    ok = client.post(
        f"/orgs/{ORG_A}/workflows/{WORKFLOW_PASSWORD}/execute-exported",
        json={"password": EXPORT_PASSWORD},
    )
    assert ok.status_code == 200


def test_org_export_requires_org_member():
    client = _client()
    anonymous = client.post(
        f"/orgs/{ORG_A}/workflows/{WORKFLOW_ORG}/execute-exported"
    )
    assert anonymous.status_code == 403
    member = client.post(
        f"/orgs/{ORG_A}/workflows/{WORKFLOW_ORG}/execute-exported",
        headers={"Authorization": "Bearer member-token"},
    )
    assert member.status_code == 200
    key = client.post(
        f"/orgs/{ORG_A}/workflows/{WORKFLOW_ORG}/execute-exported",
        headers={"X-Api-Key": API_KEY_A},
    )
    assert key.status_code == 403
    assert key.json()["reason"] == "api_key_denied"


def test_team_workflow_is_not_exported():
    client = _client()
    response = client.post(
        f"/orgs/{ORG_A}/workflows/{WORKFLOW_A1}/execute-exported"
    )
    assert response.status_code == 403
    assert response.json()["reason"] == "export_not_permitted"
