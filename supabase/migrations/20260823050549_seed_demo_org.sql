-- Demo org/teams with stable ids used by the seed and HTTP examples. Memberships attach
-- to existing Auth users (no users.role). Extra fake test UUIDs are not
-- inserted here; they cannot reference auth.users.

insert into organizations (id, name)
values
  ('00000000-0000-0000-0000-00000000000a', 'Acme'),
  ('00000000-0000-0000-0000-00000000000b', 'Other Org');

insert into teams (id, org_id, name, is_default)
values
  ('00000000-0000-0000-0000-0000000000d1', '00000000-0000-0000-0000-00000000000a', 'Default', true),
  ('00000000-0000-0000-0000-0000000000a1', '00000000-0000-0000-0000-00000000000a', 'Engineering', false),
  ('00000000-0000-0000-0000-0000000000b1', '00000000-0000-0000-0000-00000000000b', 'Default', true);

insert into workflows (id, org_id, team_id, name, visibility)
values
  (
    '00000000-0000-0000-0000-0000000000f1',
    '00000000-0000-0000-0000-00000000000a',
    '00000000-0000-0000-0000-0000000000a1',
    'Demo workflow',
    'team'
  );

insert into organization_members (org_id, user_id, role)
select '00000000-0000-0000-0000-00000000000a', id, 'super_admin'
from auth.users
order by created_at
limit 1;

insert into team_members (team_id, user_id, role)
select '00000000-0000-0000-0000-0000000000a1', id, 'admin'
from auth.users
order by created_at
limit 1
on conflict do nothing;
