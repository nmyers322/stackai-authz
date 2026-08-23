-- Org-scoped API keys (hashed) and demo export workflows.
-- Plaintext demo keys live in README / src/seed.py, not in this table.

create table api_keys (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references organizations (id) on delete cascade,
  name text not null,
  key_hash text not null unique,
  created_at timestamptz not null default now()
);

create index api_keys_org_id_idx on api_keys (org_id);

alter table api_keys enable row level security;
revoke all on table api_keys from public, anon, authenticated;

insert into api_keys (id, org_id, name, key_hash)
values
  (
    '00000000-0000-0000-0000-0000000000c1',
    '00000000-0000-0000-0000-00000000000a',
    'Acme demo',
    'ffbe1ae759a492c26a91033fb425cf361722de408ab7b498e0bfd1151f6a34fe'
  ),
  (
    '00000000-0000-0000-0000-0000000000c2',
    '00000000-0000-0000-0000-00000000000b',
    'Other demo',
    'e3a54f9df6c6aa563ffeb25e1efed5b99ada232b471613fb7b9defc2a80420b3'
  );

insert into workflows (id, org_id, team_id, name, visibility, export_password_hash)
values
  (
    '00000000-0000-0000-0000-0000000000f2',
    '00000000-0000-0000-0000-00000000000a',
    '00000000-0000-0000-0000-0000000000a1',
    'Public export',
    'public',
    null
  ),
  (
    '00000000-0000-0000-0000-0000000000f3',
    '00000000-0000-0000-0000-00000000000a',
    '00000000-0000-0000-0000-0000000000a1',
    'Password export',
    'password',
    '00000000000000000000000000000000c8bfdde19051fcb5794b0d581e1e1c8e389ddcfec6d0d8b8dd04a3f23c4f60ed'
  ),
  (
    '00000000-0000-0000-0000-0000000000f4',
    '00000000-0000-0000-0000-00000000000a',
    '00000000-0000-0000-0000-0000000000a1',
    'Org export',
    'org',
    null
  );
