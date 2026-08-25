from fastapi.testclient import TestClient

from src.authn.jwks import StaticTokenVerifier
from src.main import create_app
from src.seed import ORG_A, ORG_MEMBER, membership_store


def test_debug_ui_is_off_by_default():
    client = TestClient(
        create_app(
            store=membership_store(),
            verifier=StaticTokenVerifier({}),
            debug=False,
        )
    )
    assert client.get("/debug").status_code == 404


def test_debug_impersonation_uses_x_debug_user():
    client = TestClient(
        create_app(
            store=membership_store(),
            verifier=StaticTokenVerifier({}),
            debug=True,
        )
    )
    ignored = client.get(f"/orgs/{ORG_A}/teams")
    assert ignored.status_code == 403
    allowed = client.get(
        f"/orgs/{ORG_A}/teams",
        headers={"X-Debug-User": str(ORG_MEMBER.user_id)},
    )
    assert allowed.status_code == 200
    page = client.get("/debug")
    assert page.status_code == 200
    assert "AuthZ debug" in page.text
    assert "Create org" in page.text
    assert "Event Log" in page.text
    state = client.get("/debug/state")
    assert state.status_code == 200
    body = state.json()
    assert body["orgs"]
    assert body["users"]
    created = client.post("/debug/users", json={"email": "debug-ui@example.com"})
    assert created.status_code == 201
    user_id = created.json()["id"]
    deleted = client.delete(f"/debug/users/{user_id}")
    assert deleted.status_code == 204
