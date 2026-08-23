import os
from uuid import uuid4

import pytest
from psycopg_pool import ConnectionPool

from src.authn.api_keys import hash_api_key
from src.authz.models import OrgRole, TeamRole
from src.authz.postgres import PostgresMembershipStore
from src.config import settings
from src.seed import API_KEY_A, ORG_A, TEAM_A1, TEAM_DEFAULT_A

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_LIVE_DB") != "1" or not settings.DATABASE_URL,
    reason="set RUN_LIVE_DB=1 with APP_DATABASE_URL to probe cloud Postgres",
)


def test_seeded_memberships_from_postgres() -> None:
    assert settings.DATABASE_URL is not None
    pool = ConnectionPool(
        conninfo=settings.DATABASE_URL,
        min_size=1,
        max_size=1,
        kwargs={"prepare_threshold": None},
        open=True,
    )
    try:
        store = PostgresMembershipStore(pool)
        with pool.connection() as conn:
            row = conn.execute(
                "select user_id from organization_members limit 1"
            ).fetchone()
        assert row is not None
        user_id = row[0]
        assert store.org_role(user_id, ORG_A) is OrgRole.SUPER_ADMIN
        assert store.team_role(user_id, TEAM_DEFAULT_A) is TeamRole.ADMIN
        assert store.team_role(user_id, TEAM_A1) is TeamRole.ADMIN
    finally:
        pool.close()


def test_create_list_delete_team_postgres() -> None:
    assert settings.DATABASE_URL is not None
    pool = ConnectionPool(
        conninfo=settings.DATABASE_URL,
        min_size=1,
        max_size=1,
        kwargs={"prepare_threshold": None},
        open=True,
    )
    store = PostgresMembershipStore(pool)
    try:
        team = store.create_team(ORG_A, f"tmp-{uuid4().hex[:8]}")
        assert store.get_team(ORG_A, team.id) is not None
        ids = {row.id for row in store.list_teams(ORG_A)}
        assert team.id in ids
        store.delete_team(ORG_A, team.id)
        assert store.get_team(ORG_A, team.id) is None
    finally:
        pool.close()


def test_seeded_api_key_from_postgres() -> None:
    assert settings.DATABASE_URL is not None
    pool = ConnectionPool(
        conninfo=settings.DATABASE_URL,
        min_size=1,
        max_size=1,
        kwargs={"prepare_threshold": None},
        open=True,
    )
    try:
        store = PostgresMembershipStore(pool)
        assert store.org_id_for_key_hash(hash_api_key(API_KEY_A)) == ORG_A
        assert store.org_id_for_key_hash(hash_api_key("sak_unknown")) is None
    finally:
        pool.close()
