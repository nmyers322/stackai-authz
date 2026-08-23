from typing import cast
from uuid import UUID

from psycopg.errors import ForeignKeyViolation, UniqueViolation
from psycopg.rows import tuple_row
from psycopg_pool import ConnectionPool

from src.authz.models import OrgRole, TeamRole, Visibility
from src.authz.store import (
    OrgMembershipRecord,
    TeamMembershipRecord,
    TeamRecord,
    WorkflowRecord,
)
from src.exceptions import Conflict, NotFound


class PostgresMembershipStore:
    def __init__(self, pool: ConnectionPool) -> None:
        self._pool = pool

    def org_role(self, user_id: UUID, org_id: UUID) -> OrgRole | None:
        row = self._fetchone(
            "select role from organization_members where user_id = %s and org_id = %s",
            (user_id, org_id),
        )
        return None if row is None else OrgRole(row[0])

    def team_role(self, user_id: UUID, team_id: UUID) -> TeamRole | None:
        row = self._fetchone(
            "select role from team_members where user_id = %s and team_id = %s",
            (user_id, team_id),
        )
        return None if row is None else TeamRole(row[0])

    def org_exists(self, org_id: UUID) -> bool:
        row = self._fetchone("select 1 from organizations where id = %s", (org_id,))
        return row is not None

    def get_team(self, org_id: UUID, team_id: UUID) -> TeamRecord | None:
        row = self._fetchone(
            """
            select id, org_id, name, is_default
            from teams
            where id = %s and org_id = %s
            """,
            (team_id, org_id),
        )
        return None if row is None else _team(row)

    def list_teams(self, org_id: UUID) -> list[TeamRecord]:
        rows = self._fetchall(
            """
            select id, org_id, name, is_default
            from teams
            where org_id = %s
            order by is_default desc, name
            """,
            (org_id,),
        )
        return [_team(row) for row in rows]

    def create_team(self, org_id: UUID, name: str) -> TeamRecord:
        try:
            row = self._fetchone(
                """
                insert into teams (org_id, name, is_default)
                values (%s, %s, false)
                returning id, org_id, name, is_default
                """,
                (org_id, name),
            )
        except ForeignKeyViolation as exc:
            raise NotFound from exc
        if row is None:
            raise NotFound
        return _team(row)

    def delete_team(self, org_id: UUID, team_id: UUID) -> None:
        row = self._fetchone(
            "delete from teams where id = %s and org_id = %s returning id",
            (team_id, org_id),
        )
        if row is None:
            raise NotFound

    def add_org_member(self, user_id: UUID, org_id: UUID, role: OrgRole) -> None:
        try:
            self._execute(
                """
                insert into organization_members (org_id, user_id, role)
                values (%s, %s, %s)
                """,
                (org_id, user_id, role.value),
            )
        except UniqueViolation as exc:
            raise Conflict from exc
        except ForeignKeyViolation as exc:
            raise NotFound from exc

    def remove_org_member(self, org_id: UUID, user_id: UUID) -> None:
        with self._pool.connection() as conn, conn.transaction():
            row = conn.execute(
                """
                    delete from organization_members
                    where org_id = %s and user_id = %s
                    returning user_id
                    """,
                (org_id, user_id),
            ).fetchone()
            if row is None:
                raise NotFound
            conn.execute(
                """
                    delete from team_members
                    where user_id = %s
                      and team_id in (select id from teams where org_id = %s)
                    """,
                (user_id, org_id),
            )

    def set_org_role(self, org_id: UUID, user_id: UUID, role: OrgRole) -> None:
        row = self._fetchone(
            """
            update organization_members
            set role = %s
            where org_id = %s and user_id = %s
            returning user_id
            """,
            (role.value, org_id, user_id),
        )
        if row is None:
            raise NotFound

    def list_user_orgs(self, user_id: UUID) -> list[OrgMembershipRecord]:
        rows = self._fetchall(
            """
            select m.org_id, o.name, m.role
            from organization_members m
            join organizations o on o.id = m.org_id
            where m.user_id = %s
            order by o.name
            """,
            (user_id,),
        )
        return [
            OrgMembershipRecord(
                org_id=row[0], org_name=row[1], role=OrgRole(row[2])
            )
            for row in rows
        ]

    def add_team_member(self, user_id: UUID, team_id: UUID, role: TeamRole) -> None:
        try:
            self._execute(
                """
                insert into team_members (team_id, user_id, role)
                values (%s, %s, %s)
                """,
                (team_id, user_id, role.value),
            )
        except UniqueViolation as exc:
            raise Conflict from exc
        except ForeignKeyViolation as exc:
            raise NotFound from exc

    def remove_team_member(self, team_id: UUID, user_id: UUID) -> None:
        row = self._fetchone(
            """
            delete from team_members
            where team_id = %s and user_id = %s
            returning user_id
            """,
            (team_id, user_id),
        )
        if row is None:
            raise NotFound

    def set_team_role(self, team_id: UUID, user_id: UUID, role: TeamRole) -> None:
        row = self._fetchone(
            """
            update team_members
            set role = %s
            where team_id = %s and user_id = %s
            returning user_id
            """,
            (role.value, team_id, user_id),
        )
        if row is None:
            raise NotFound

    def list_user_teams(
        self, org_id: UUID, user_id: UUID
    ) -> list[TeamMembershipRecord]:
        rows = self._fetchall(
            """
            select t.id, t.name, m.role, t.is_default
            from team_members m
            join teams t on t.id = m.team_id
            where m.user_id = %s and t.org_id = %s
            order by t.is_default desc, t.name
            """,
            (user_id, org_id),
        )
        return [
            TeamMembershipRecord(
                team_id=row[0],
                team_name=row[1],
                role=TeamRole(row[2]),
                is_default=row[3],
            )
            for row in rows
        ]

    def org_id_for_key_hash(self, key_hash: str) -> UUID | None:
        row = self._fetchone(
            "select org_id from api_keys where key_hash = %s", (key_hash,)
        )
        return None if row is None else cast(UUID, row[0])

    def get_workflow(self, org_id: UUID, workflow_id: UUID) -> WorkflowRecord | None:
        row = self._fetchone(
            """
            select id, org_id, team_id, name, visibility, export_password_hash
            from workflows
            where id = %s and org_id = %s
            """,
            (workflow_id, org_id),
        )
        return None if row is None else _workflow(row)

    def list_workflows(self, org_id: UUID) -> list[WorkflowRecord]:
        rows = self._fetchall(
            """
            select id, org_id, team_id, name, visibility, export_password_hash
            from workflows
            where org_id = %s
            order by name
            """,
            (org_id,),
        )
        return [_workflow(row) for row in rows]

    def create_workflow(
        self,
        org_id: UUID,
        team_id: UUID,
        name: str,
        visibility: Visibility,
        export_password_hash: str | None,
    ) -> WorkflowRecord:
        try:
            row = self._fetchone(
                """
                insert into workflows (
                    org_id, team_id, name, visibility, export_password_hash
                )
                values (%s, %s, %s, %s, %s)
                returning id, org_id, team_id, name, visibility, export_password_hash
                """,
                (org_id, team_id, name, visibility.value, export_password_hash),
            )
        except ForeignKeyViolation as exc:
            raise NotFound from exc
        if row is None:
            raise NotFound
        return _workflow(row)

    def replace_workflow(
        self,
        org_id: UUID,
        workflow_id: UUID,
        team_id: UUID,
        name: str,
        visibility: Visibility,
        export_password_hash: str | None,
    ) -> WorkflowRecord:
        try:
            row = self._fetchone(
                """
                update workflows
                set team_id = %s,
                    name = %s,
                    visibility = %s,
                    export_password_hash = %s
                where id = %s and org_id = %s
                returning id, org_id, team_id, name, visibility, export_password_hash
                """,
                (
                    team_id,
                    name,
                    visibility.value,
                    export_password_hash,
                    workflow_id,
                    org_id,
                ),
            )
        except ForeignKeyViolation as exc:
            raise NotFound from exc
        if row is None:
            raise NotFound
        return _workflow(row)

    def delete_workflow(self, org_id: UUID, workflow_id: UUID) -> None:
        row = self._fetchone(
            "delete from workflows where id = %s and org_id = %s returning id",
            (workflow_id, org_id),
        )
        if row is None:
            raise NotFound

    def _fetchone(
        self, sql: str, params: tuple[object, ...]
    ) -> tuple[object, ...] | None:
        with self._pool.connection() as conn:
            conn.row_factory = tuple_row
            return conn.execute(sql, params).fetchone()

    def _fetchall(
        self, sql: str, params: tuple[object, ...]
    ) -> list[tuple[object, ...]]:
        with self._pool.connection() as conn:
            conn.row_factory = tuple_row
            return list(conn.execute(sql, params).fetchall())

    def _execute(self, sql: str, params: tuple[object, ...]) -> None:
        with self._pool.connection() as conn:
            conn.execute(sql, params)


def _team(row: tuple[object, ...]) -> TeamRecord:
    return TeamRecord(
        id=cast(UUID, row[0]),
        org_id=cast(UUID, row[1]),
        name=cast(str, row[2]),
        is_default=cast(bool, row[3]),
    )


def _workflow(row: tuple[object, ...]) -> WorkflowRecord:
    return WorkflowRecord(
        id=cast(UUID, row[0]),
        org_id=cast(UUID, row[1]),
        team_id=cast(UUID, row[2]),
        name=cast(str, row[3]),
        visibility=Visibility(cast(str, row[4])),
        export_password_hash=cast(str | None, row[5]),
    )
