from uuid import UUID, uuid4

from psycopg.errors import UniqueViolation
from psycopg_pool import ConnectionPool

from src.authz.memory import InMemoryMembershipStore
from src.authz.store import AppStore
from src.exceptions import Conflict, NotFound
from src.seed import API_KEY_A, API_KEY_B, EXPORT_PASSWORD, ORG_A, ORG_B


def snapshot(store: AppStore, pool: ConnectionPool | None) -> dict[str, object]:
    if pool is not None:
        data = _postgres_snapshot(pool)
    elif isinstance(store, InMemoryMembershipStore):
        data = _memory_snapshot(store)
    else:
        data = {
            "orgs": [],
            "teams": [],
            "users": [],
            "org_members": [],
            "team_members": [],
            "workflows": [],
        }
    data["api_keys"] = [
        {"org_id": str(ORG_A), "name": "Acme demo", "key": API_KEY_A},
        {"org_id": str(ORG_B), "name": "Other demo", "key": API_KEY_B},
    ]
    data["export_password"] = EXPORT_PASSWORD
    return data


def create_user(
    store: AppStore, pool: ConnectionPool | None, email: str
) -> dict[str, str]:
    if pool is not None:
        return _postgres_create_user(pool, email)
    if not isinstance(store, InMemoryMembershipStore):
        raise NotFound
    if email in store._users.values():
        raise Conflict
    user_id = uuid4()
    store.seed_user(user_id, email)
    return {"id": str(user_id), "email": email}


def delete_user(store: AppStore, pool: ConnectionPool | None, user_id: UUID) -> None:
    if pool is not None:
        _postgres_delete_user(pool, user_id)
        return
    if not isinstance(store, InMemoryMembershipStore):
        raise NotFound
    if user_id not in store._users:
        raise NotFound
    del store._users[user_id]


def _memory_snapshot(store: InMemoryMembershipStore) -> dict[str, object]:
    emails = store._users
    orgs = [
        {"id": str(org_id), "name": name}
        for org_id, name in sorted(store._org_names.items(), key=lambda item: item[1])
    ]
    teams = [
        {
            "id": str(team.id),
            "org_id": str(team.org_id),
            "name": team.name,
            "is_default": team.is_default,
        }
        for team in sorted(
            store._teams.values(), key=lambda team: (str(team.org_id), team.name)
        )
    ]
    users = [
        {"id": str(user_id), "email": email}
        for user_id, email in sorted(emails.items(), key=lambda item: item[1])
    ]
    org_members = [
        {
            "org_id": str(org_id),
            "org_name": store._org_names.get(org_id, ""),
            "user_id": str(user_id),
            "email": emails.get(user_id, ""),
            "role": role.value,
        }
        for (user_id, org_id), role in store._org.items()
    ]
    team_members = []
    for (user_id, team_id), role in store._team.items():
        team = store._teams.get(team_id)
        team_members.append(
            {
                "team_id": str(team_id),
                "team_name": team.name if team else "",
                "org_id": str(team.org_id) if team else "",
                "user_id": str(user_id),
                "email": emails.get(user_id, ""),
                "role": role.value,
            }
        )
    workflows = [
        {
            "id": str(workflow.id),
            "org_id": str(workflow.org_id),
            "team_id": str(workflow.team_id),
            "name": workflow.name,
            "visibility": workflow.visibility.value,
        }
        for workflow in sorted(
            store._workflows.values(), key=lambda workflow: workflow.name
        )
    ]
    return {
        "orgs": orgs,
        "teams": teams,
        "users": users,
        "org_members": org_members,
        "team_members": team_members,
        "workflows": workflows,
    }


def _postgres_snapshot(pool: ConnectionPool) -> dict[str, object]:
    with pool.connection() as conn:
        orgs = [
            {"id": str(row[0]), "name": row[1]}
            for row in conn.execute(
                "select id, name from organizations order by name"
            ).fetchall()
        ]
        teams = [
            {
                "id": str(row[0]),
                "org_id": str(row[1]),
                "name": row[2],
                "is_default": row[3],
            }
            for row in conn.execute(
                """
                select id, org_id, name, is_default
                from teams
                order by org_id, is_default desc, name
                """
            ).fetchall()
        ]
        users = [
            {"id": str(row[0]), "email": row[1] or ""}
            for row in conn.execute(
                """
                select id, email
                from auth.users
                where deleted_at is null
                order by created_at
                """
            ).fetchall()
        ]
        org_members = [
            {
                "org_id": str(row[0]),
                "org_name": row[1],
                "user_id": str(row[2]),
                "email": row[3] or "",
                "role": row[4],
            }
            for row in conn.execute(
                """
                select m.org_id, o.name, m.user_id, u.email, m.role
                from organization_members m
                join organizations o on o.id = m.org_id
                left join auth.users u on u.id = m.user_id
                order by o.name, u.email
                """
            ).fetchall()
        ]
        team_members = [
            {
                "team_id": str(row[0]),
                "team_name": row[1],
                "org_id": str(row[2]),
                "user_id": str(row[3]),
                "email": row[4] or "",
                "role": row[5],
            }
            for row in conn.execute(
                """
                select t.id, t.name, t.org_id, m.user_id, u.email, m.role
                from team_members m
                join teams t on t.id = m.team_id
                left join auth.users u on u.id = m.user_id
                order by t.org_id, t.name, u.email
                """
            ).fetchall()
        ]
        workflows = [
            {
                "id": str(row[0]),
                "org_id": str(row[1]),
                "team_id": str(row[2]),
                "name": row[3],
                "visibility": row[4],
            }
            for row in conn.execute(
                """
                select id, org_id, team_id, name, visibility
                from workflows
                order by name
                """
            ).fetchall()
        ]
    return {
        "orgs": orgs,
        "teams": teams,
        "users": users,
        "org_members": org_members,
        "team_members": team_members,
        "workflows": workflows,
    }


def _postgres_create_user(pool: ConnectionPool, email: str) -> dict[str, str]:
    user_id = uuid4()
    try:
        with pool.connection() as conn, conn.transaction():
            conn.execute(
                """
                insert into auth.users (
                    instance_id, id, aud, role, email, encrypted_password,
                    email_confirmed_at, raw_app_meta_data, raw_user_meta_data,
                    created_at, updated_at, confirmation_token, email_change,
                    email_change_token_new, recovery_token, is_sso_user,
                    is_anonymous
                )
                values (
                    '00000000-0000-0000-0000-000000000000',
                    %s, 'authenticated', 'authenticated', %s,
                    crypt(%s, gen_salt('bf')),
                    now(),
                    '{"provider":"email","providers":["email"]}'::jsonb,
                    '{}'::jsonb,
                    now(), now(), '', '', '', '', false, false
                )
                """,
                (user_id, email, str(uuid4())),
            )
            conn.execute(
                """
                insert into auth.identities (
                    id, user_id, identity_data, provider, provider_id,
                    last_sign_in_at, created_at, updated_at
                )
                values (
                    gen_random_uuid(), %s,
                    jsonb_build_object('sub', %s::text, 'email', %s),
                    'email', %s, now(), now(), now()
                )
                """,
                (user_id, str(user_id), email, str(user_id)),
            )
    except UniqueViolation as exc:
        raise Conflict from exc
    return {"id": str(user_id), "email": email}


def _postgres_delete_user(pool: ConnectionPool, user_id: UUID) -> None:
    with pool.connection() as conn:
        row = conn.execute(
            "delete from auth.users where id = %s returning id", (user_id,)
        ).fetchone()
    if row is None:
        raise NotFound
