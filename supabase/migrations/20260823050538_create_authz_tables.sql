-- AuthZ tables. RLS on, no policies: default-deny for anon/authenticated.
-- The FastAPI process uses a privileged connection (BYPASSRLS). AuthZ is in Python.

create table organizations (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  created_at timestamptz not null default now()
);

create table organization_members (
  org_id uuid not null references organizations (id) on delete cascade,
  user_id uuid not null references auth.users (id) on delete cascade,
  role text not null check (role in ('super_admin', 'member')),
  primary key (org_id, user_id)
);

create table teams (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references organizations (id) on delete cascade,
  name text not null,
  is_default boolean not null default false,
  created_at timestamptz not null default now()
);

create table team_members (
  team_id uuid not null references teams (id) on delete cascade,
  user_id uuid not null references auth.users (id) on delete cascade,
  role text not null check (role in ('admin', 'editor', 'viewer')),
  primary key (team_id, user_id)
);

create table workflows (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references organizations (id) on delete cascade,
  team_id uuid not null references teams (id) on delete cascade,
  name text not null,
  visibility text not null check (visibility in ('team', 'public', 'password', 'org')),
  export_password_hash text,
  created_at timestamptz not null default now()
);

create index organization_members_user_id_idx on organization_members (user_id);
create index teams_org_id_idx on teams (org_id);
create unique index teams_one_default_per_org on teams (org_id) where is_default;
create index team_members_user_id_idx on team_members (user_id);
create index workflows_org_id_idx on workflows (org_id);
create index workflows_team_id_idx on workflows (team_id);

create function add_org_member_to_default_team()
returns trigger
language plpgsql
as $$
begin
  insert into team_members (team_id, user_id, role)
  select t.id,
         new.user_id,
         case
           when new.role = 'super_admin' then 'admin'
           else 'viewer'
         end
  from teams t
  where t.org_id = new.org_id
    and t.is_default
  on conflict do nothing;
  return new;
end;
$$;

create trigger organization_members_default_team
after insert on organization_members
for each row
execute function add_org_member_to_default_team();

alter table organizations enable row level security;
alter table organization_members enable row level security;
alter table teams enable row level security;
alter table team_members enable row level security;
alter table workflows enable row level security;

revoke all on table organizations from public, anon, authenticated;
revoke all on table organization_members from public, anon, authenticated;
revoke all on table teams from public, anon, authenticated;
revoke all on table team_members from public, anon, authenticated;
revoke all on table workflows from public, anon, authenticated;
revoke all on function add_org_member_to_default_team() from public, anon, authenticated;
