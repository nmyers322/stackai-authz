# Design decisions

Ledger for this service. [`SPEC.md`](SPEC.md) is the plan and the phase record. Axioms live in `.cursor/rules/`. When a choice is locked or a hole is found, write it here — not only in chat.

---

### D1 — App AuthZ is the engine; RLS is a backstop

`authorize(principal, action, resource) -> Decision` in `authz/` is the permission matrix. FastAPI uses a Postgres role with `BYPASSRLS` for every query, including anonymous HTTP. Enable RLS on every exposed table and add no `anon` / `authenticated` policies. See `.cursor/rules/rls.mdc`.

### D2 — Org context is a path parameter

`org_id` is `/orgs/{org_id}/...`. A token never implies “the user’s only org.” No `X-Org-Id`.

### D3 — Roles live on memberships, not users

`organization_members.role` and `team_members.role`. No `users.role`. Org `member` has no org-admin powers. Team admin ⊃ editor ⊃ viewer. Super-admin bypasses team checks inside the engine.

### D4 — HTTP verbs match resource shape

Workflow create is `POST`; replace is `PUT` (full body, including visibility); delete is `DELETE`. Membership role changes are `PATCH`. `GET /orgs/{org_id}/teams` is org browse. `GET /orgs/{org_id}/members/{user_id}/teams` is that user’s teams with team-membership role. `GET /users/{user_id}/orgs` is that user’s orgs with org-membership role (not nested under `org_id` — the caller does not have an active org yet).

### D5 — No self-service membership mutation

Callers cannot add themselves, change their own membership roles, or leave a team/org. Only team admin (team memberships) or org super-admin (org memberships) mutate those rows. Listing own memberships is allowed (D6). Cheaper than “self-leave except last super-admin.”

### D6 — Listing another user’s memberships is identity-match, not rank-only

- `GET /orgs/{org_id}/members/{user_id}/teams`: allow if `principal.user_id == resource.user_id`, or if the principal has org `super_admin` in that org.
- `GET /users/{user_id}/orgs`: allow only if `principal.user_id == resource.user_id`. An org super-admin of org A must not learn that the user is also in org B. No platform-wide admin. API key and anonymous deny.

### D7 — Supabase JWT verification is JWKS, not the legacy JWT secret

New Supabase projects issue asymmetric JWTs (ES256 / RS256). This service uses PyJWT + `PyJWKClient`, verifies `iss`, and treats `sub` as `user_id`. It does not decode with `SUPABASE_JWT_SECRET`. If JWKS `keys` is empty, the project is still on a symmetric key — fix dashboard settings; do not fall back to HS256.

### D8 — `authorize()` matrix is the bar; HTTP smoke is not proof

Authorization is proven by a parametrized unit matrix over `authorize()` with an in-memory store. One thin FastAPI `TestClient` smoke suite (happy path, 403 + reason, 401) exists so HTTP wiring cannot silently break. README calls that **smoke, not proof**.

### D9 — Platform

pip + venv; CPython 3.13; FastAPI + Pydantic v2; `pydantic-settings`; Ruff; Docker `python:3.13-slim`; Compose service `api`; secrets as runtime env. Supabase **free cloud**, not a local stack. No signup; seed Auth users. No `POST /orgs`. API keys are seeded (no create-key route). Execute is AuthZ + no-op; no workflow runtime.

### D10 — Deletes and default-team protection

- `DELETE /orgs/{org_id}/teams/{team_id}` — org super-admin only. Deny if the team is the org’s default team. Cascade memberships and workflows on that team.
- `DELETE .../teams/{team_id}/members/{user_id}` — denied on the default team (`default_team_immutable`). Remove the org membership instead.
- `DELETE /orgs/{org_id}/workflows/{workflow_id}` — same grant as update: team editor+ or org super-admin. API keys cannot delete.

### D11 — Postgres client is psycopg 3

Direct SQL with `psycopg` + `psycopg_pool.ConnectionPool` (small pool, no prepared statements). Not SQLAlchemy. Queries from FastAPI run in a thread pool. Unit tests keep the in-memory store. Free-tier `db.*.supabase.co` is IPv6-only; `APP_DATABASE_URL` uses the IPv4 session pooler.

### D12 — Workflow list is org-gated, then filtered

`WORKFLOW_LIST` is “any org member (or in-org API key).” The JSON list then drops `visibility=team` workflows the caller is not on. Super-admin sees every org workflow. This is not a second permission matrix and not RLS.

### D13 — `X-Api-Key` is the principal when present

A non-empty `X-Api-Key` is looked up by SHA-256 hash and becomes `ApiKeyPrincipal`. Unknown keys are `401`. The header wins over `Authorization` on the same request.

### D14 — Export password is hashed; the engine sees a boolean

Persistence stores PBKDF2-HMAC-SHA256 of the export password. `authorize()` only sees `Resource.export_password_ok`. Routes must not re-implement visibility rules.

---

## Limits

- No custom JWT TTL hook, signing-key rotation runbook, or audit table.
- No HTTP route to create API keys.
- Create team is org super-admin only. Team admins manage memberships, not the team row.
