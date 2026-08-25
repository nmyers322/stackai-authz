# Spec

Authorization service for organizations, teams, users, and workflows.

Identity answers who is acting. Authorization answers whether they may perform an action. Those stay separate. Project axioms: `.cursor/rules/code-quality.mdc`, `.cursor/rules/rls.mdc`. Explicit locks and open holes: [`decisions.md`](decisions.md). When a choice is made or a gap is found, write it there.

Initialize tools the way they expect. Do not paste a finished monolith.

## Locked platform

| Choice | Value |
| --- | --- |
| Installer | pip + venv (`python -m venv .venv`) |
| Language | Current CPython 3 on PATH (phase 0: 3.13) |
| API | FastAPI (`fastapi[standard]`) + Pydantic v2 |
| Settings | `pydantic-settings` |
| Lint | Ruff |
| JWT | PyJWT + JWKS (`PyJWKClient`). New projects sign asymmetrically (ES256/RS256). Not the legacy HS256 JWT secret. [D7](decisions.md) |
| Database | Supabase **free**, **cloud**. Direct Postgres with a privileged role (`postgres` via the IPv4 session pooler, `BYPASSRLS`). Not PostgREST |
| RLS | Enabled, default-deny, no `anon`/`authenticated` policies |
| Org context | Path `/orgs/{org_id}/...` (UUID). No `X-Org-Id` |
| Containers | `python:<minor>-slim` matching the interpreter; Compose service `api` |
| Tests | Method-level `authorize()` matrix is the bar. One HTTP smoke suite (happy path, 403, 401) is insurance, not proof. [D8](decisions.md) |
| Users | No signup. Seed in Supabase Auth (dashboard or SQL). **Users have no roles.** |

Postgres client is psycopg 3 + pool ([D11](decisions.md)).

## Assumptions (underspecified in the source prompt)

Documented here so AuthZ is not invented per route:

- **Roles live on memberships**, never on the user. Org role is `organization_members.role`. Team role is `team_members.role`. A user can have different roles in different orgs and teams.
- Org **member** (membership type) has no org-admin powers. Access is via team membership plus the default org team.
- **Create team** and **delete team**: org `super_admin` only. The default org team cannot be deleted.
- Add/remove org members and change org membership role: org `super_admin` only.
- **Delete workflow**: same as update — team editor+ (includes admin) or org super-admin. API keys may not delete.
- **Team admin** manages that team’s memberships (add/remove/change team role). Includes editor. Team admin cannot delete the team.
- **Editor** may create/update/delete workflows on that team (includes viewer).
- **Viewer** may list and execute team workflows, not update or delete them.
- **Anonymous** may only `execute-exported`, and only when visibility allows.
- Every org has a **default team**. Every org member is on it. Org-shared workflows live there.
- Users may belong to many orgs and many teams. `org_id` in the path is the active org.
- **Self-serve org create.** Any authenticated user may `POST /orgs`. The creator becomes that org’s `super_admin` and an `admin` on the default team. Seeded orgs remain for demos. [D5](decisions.md), [D9](decisions.md), [D15](decisions.md).
- **No self-service membership mutation** except the org-create bootstrap (D5). A caller cannot add themselves, change their own membership roles, or leave a team/org through the membership routes. Only team admin (team memberships) or org super-admin (org memberships) mutate those rows.
- Listing memberships is not mutation: a user may list **their own** org memberships and **their own** team memberships; an org super-admin may list anyone’s **in-org** team memberships. Listing another user’s orgs is denied (would leak other-org memberships). There is no platform-wide admin.
- API keys are **seeded** (no create-key HTTP route unless we add one later).
- Execute is an AuthZ gate plus a canned/no-op body. There is no workflow runtime.
- Export password is sent as JSON `{ "password": "..." }` on `execute-exported`. Hash check is persistence. The engine sees `Resource.export_password_ok`.
- Visibility is set on create/PUT: `team | public | password | org`.
- Workflow **PUT** replaces the resource (full body). Membership role changes stay **PATCH** (partial on the membership row).

## HTTP contract

Invalid UUID → `422`. `401` unauthenticated, `403` authenticated but denied, `404` unknown resource. Creates `201`, PUT `200`, PATCH `200`, deletes `204`.

| Method | Path | Meaning |
| --- | --- | --- |
| `POST` | `/orgs` | Create an org (caller becomes org `super_admin` + default-team `admin`) |
| `POST` | `/orgs/{org_id}/teams` | Create a team |
| `GET` | `/orgs/{org_id}/teams` | Teams in the org the caller may see (browse; not the membership+role list) |
| `DELETE` | `/orgs/{org_id}/teams/{team_id}` | Delete a team (not the default org team) |
| `POST` | `/orgs/{org_id}/teams/{team_id}/members/{user_id}` | Add a **team membership** (role in body) |
| `DELETE` | `/orgs/{org_id}/teams/{team_id}/members/{user_id}` | Remove a team membership |
| `PATCH` | `/orgs/{org_id}/teams/{team_id}/members/{user_id}` | Change **team membership** role |
| `POST` | `/orgs/{org_id}/members/{user_id}` | Add an **org membership** |
| `DELETE` | `/orgs/{org_id}/members/{user_id}` | Remove an org membership |
| `PATCH` | `/orgs/{org_id}/members/{user_id}` | Change **org membership** role |
| `GET` | `/orgs/{org_id}/members/{user_id}/teams` | Teams that **this user** belongs to in this org, **with team membership role**. Self or org super-admin |
| `GET` | `/users/{user_id}/orgs` | Orgs that **this user** belongs to, **with org membership role**. Self only. Not org-scoped — this is how a token finds its orgs |
| `GET` | `/orgs/{org_id}/workflows` | Workflows the caller may see |
| `POST` | `/orgs/{org_id}/workflows` | Create workflow |
| `PUT` | `/orgs/{org_id}/workflows/{workflow_id}` | Replace workflow (including visibility / export password) |
| `DELETE` | `/orgs/{org_id}/workflows/{workflow_id}` | Delete a workflow |
| `POST` | `/orgs/{org_id}/workflows/{workflow_id}/execute` | Execute (logged-in / API key) |
| `POST` | `/orgs/{org_id}/workflows/{workflow_id}/execute-exported` | Execute exported (anonymous allowed when visibility permits; optional `password`) |
| Header | `X-Api-Key` | Second principal on workflow routes |

`POST /workflows` is create only. It is not upsert. `PUT` is the update.

`src/authz/engine.py` never imports FastAPI or a database SDK. The Postgres adapter is `src/authz/postgres.py`.

---

## Phase 0 — Toolchain and stubs (done)

Shipped:

- `.venv`, `requirements.txt`, `pyproject.toml`
- `src/` packages `orgs`, `teams`, `workflows` with stub routers
- Canned JSON; no `authorize()`, no JWT, no Postgres
- `PUT /workflows/{id}`, `DELETE` team and workflow, `GET /members/{user_id}/teams`, `GET /users/{user_id}/orgs`, `PATCH` team membership role
- `Dockerfile` (`python:3.13-slim`) and Compose `api` only
- `fastapi dev src/main.py` / `docker compose up --build`

Not in this phase: engine, Auth, schema, RLS, 401/403.

---

## Phase 1 — Authorization engine (done)

Shipped:

- Pure `src/authz/`: `authorize(principal, action, resource, store) -> Decision`
- Typed `Principal` (user, api_key, anonymous), `Action` (one per HTTP operation), `Resource`, `Decision` with stable `Reason`
- `MembershipStore` Protocol; `InMemoryMembershipStore` for tests and phase 2
- Grants keyed off **membership roles**, not a user.role field
- Self-or-super-admin for listing a user’s in-org teams; self-only for listing a user’s orgs
- Default-team delete denied even for super-admin
- API-key principal: list/execute (and execute-exported) workflows in-org; never membership mutation, never delete
- Parametrized matrix: every action has allow and deny, including export modes

Routes stay stubs. No FastAPI imports in `authz/engine.py`.

**Done when:** `pytest` on the matrix is green.

---

## Phase 2 — Wire HTTP to the engine (done)

Shipped:

- Domain exceptions (`Unauthenticated`, `AuthorizationError`, `NotFound`) mapped to HTTP once
- Missing `Authorization` → anonymous; `Authorization: Bearer` → user via **JWKS** (`PyJWKClient`). No `JWT_SECRET`. API key still unused
- In-memory membership seed so deny paths work without Postgres
- Stub routes call `require()` then return canned JSON
- Smoke (not proof): allowed `200`, authenticated deny `403` + reason, bad JWT `401`

`APP_SUPABASE_URL` enables the real JWKS verifier. Without it, a Bearer token cannot be verified (401). JWKS on this project is ES256 (G2 closed).

**Done when:** allowed stub still returns canned JSON; forbidden returns `403` + reason; bad JWT returns `401`; the three smoke tests pass.

---

## Phase 3 — Supabase and schema (done)

Shipped:

- Postgres client: **psycopg 3** + `ConnectionPool` (max 4). `prepare_threshold=None` so transaction-mode pooling stays valid
- Cloud project linked; migrations from `supabase migration new`
- Tables `organizations`, `organization_members.role`, `teams`, `team_members.role`, `workflows`. Users stay in `auth.users`
- Inserting an org member adds them to that org’s default team (trigger)
- RLS enabled; `anon` / `authenticated` / `PUBLIC` grants revoked; no policies (default-deny). Advisor `rls_enabled_no_policy` is expected
- Seed: Acme + Other Org with stable UUIDs; first Auth user is org super-admin and Engineering team admin
- `PostgresMembershipStore` implements `MembershipStore`. In-memory fake remains for unit tests and smoke
- `APP_DATABASE_URL` selects the Postgres store at lifespan

**Done when:** the process reads memberships from cloud Postgres; RLS is on; Data API as `anon` sees nothing.

---

## Phase 4 — Persist the resources (done)

Shipped:

- `AppStore` Protocol (memberships + teams/workflows). In-memory fake and Postgres implement it
- Domain services write rows after `authorize()`. Routes do not branch on role
- Create/delete team (cascade memberships + workflows). Default team cannot be deleted or have members removed
- Org/team membership add/remove/PATCH role. Removing an org member drops their in-org team memberships. Inserting an org member still adds them to the default team
- Create/PUT/delete workflow. `GET /teams` is browse. `GET /members/{user_id}/teams` and `GET /users/{user_id}/orgs` return membership + role
- Workflow list is org-gated then filtered: super-admin sees all; team members see that team’s workflows; other org members see non-`team` visibility
- Execute endpoints no-op after allow. Unknown team/workflow in-org → `404`
- Duplicate membership → `409`

**Done when:** lists reflect writes; 404 for unknown ids the caller is allowed to know about.

---

## Phase 5 — API keys and export modes (done)

Shipped:

- `api_keys` table: org-scoped, SHA-256 of the raw key, RLS default-deny, seeded demo keys
- `X-Api-Key` resolves to `ApiKeyPrincipal` (invalid key → `401`). If both headers are present, the API key wins
- PUT/create already persist `visibility` and optional password hash (PBKDF2)
- `execute-exported` passes `export_password_ok` into `authorize()`: public (anonymous), password (matching body), org (user JWT in that org)
- Engine matrix already covered keys and the three export modes; HTTP tests match

**Done when:** matrix covers keys and all three export modes; HTTP matches.

---

## Phase 6 — Ship

Shipped:

- README: venv, env vars (no secrets in git), `fastapi dev`, `docker compose up`, seed, **documented assumptions**, and that HTTP tests are **smoke, not proof** of AuthZ
- Compose env for cloud URL; image secret-free (`src/` + `requirements.txt` only)
- Gaps in README: JWT TTL, no key rotation, no audit table, privileged Postgres role bypasses RLS
- Debug UI at `/debug` when `APP_DEBUG=true` (local lab only; not part of the HTTP contract)
- Cleanup: drop CLI temp cache, unused package barrels, dangling `seed.sql` reference; Cursor rules match the shipped layout (engine vs Postgres adapter, `APP_` settings, pooler role). This spec stays — it is the phase record and the decision surface for a walkthrough

**Not done (requirement):** two recordings — (1) run the API (2) walk the design. The source prompt’s “install the bot” means this API.

**Done when:** a clean machine can run the API against the free cloud project from the README alone, and both recordings exist.

---

## Phase 7 — Self-serve org create (done)

Minimal design: any authenticated **user** may create an org and becomes its first super-admin. No platform uber-admin. No slug, no name uniqueness beyond `id`, no profanity filter. API keys and anonymous cannot create orgs. [D15](decisions.md).

Shipped:

- `Action.ORG_CREATE` in the engine. Allow `UserPrincipal`; deny API key and anonymous. Matrix rows for allow and deny.
- `POST /orgs` with body `{ "name": "..." }` → `201` + org payload (`id`, `name`).
- Service path after allow: create org → default team → attach creator as org `super_admin` → creator is default-team `admin` (same semantics as the DB trigger). This bootstrap is the **only** self-assignment of membership; it is not `ORG_MEMBER_ADD` on self.
- Org names: uniqueness on `id` only. Duplicate display names allowed.
- **User delete** (debug catalog): for each org the user belonged to, if they were the **last org member**, delete that org (cascade). If other members remain, only their memberships are removed.
- Quotas / rate limits: not implemented; noted in [decisions.md](decisions.md) Limits.
- Audit: no audit table; noted in Limits (debug Event Log is local-only, not an audit trail).

**Done when:** matrix covers `ORG_CREATE`; `POST /orgs` as a user returns `201` and the creator can list that org via `GET /users/{user_id}/orgs`; API key / anonymous denied; deleting the sole member of an org removes the org.

---

## Vs the source prompt

Covered: dummy REST for teams/org/workflows; AuthN via Supabase tokens; AuthZ as a reusable service; org/team hierarchy; default team; editor vs viewer vs external; extras (API key reduced privilege, password export, org-only export); free-tier Supabase; no signup; Docker; document edge cases.

Deliberate diffs:

| Source prompt | This spec |
| --- | --- |
| “Create/Update” as one action | `POST` create + `PUT` replace + `DELETE` |
| Super-admin “delete all resources” | `DELETE` team and `DELETE` workflow (prompt dummy list omitted these; that was G7) |
| “List teams a user belongs to and his role” | `GET /members/{user_id}/teams` (self or super-admin). `GET /teams` is org browse |
| Users in many orgs | `GET /users/{user_id}/orgs` (self only, with org membership role) |
| User “has roles” | Roles only on org/team **membership** rows |
| “authentication service using supabase’s API” | Verify user JWTs locally via project JWKS (PyJWT). New apps are asymmetric by default |
| Demo “install the bot” | Run this API |
| Business rules incomplete | Assumptions section above |
| Extra points optional | Phase 5 implements them |

## Out of scope

Signup UI, frontend, email, local Supabase, Casbin/OPA, SAML, RLS as the permission matrix, HTTP integration tests as the **proof** of AuthZ (a three-assertion smoke suite is in scope), a workflow execution engine, a `users.role` column, verifying user tokens with the legacy JWT secret.

## Completion

Phases 0–5 done. Phase 6 README and cleanup done. Phase 7 self-serve org create done. Ship-complete when recordings exist and the authorize matrix still passes.
