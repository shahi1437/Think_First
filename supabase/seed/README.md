# Local Supabase Seed & Privileged Role Bootstrapping

New users registered through Supabase Auth automatically receive **only** the `student` role via the `on_auth_user_created` database trigger.

## Bootstrapping the First Admin Account (Local / Staging)

Never expose a public endpoint or client flag to self-assign `admin` or `teacher` roles. To promote an initial bootstrap Admin account after signing up in local Supabase:

```sql
-- Run once in local Supabase Studio SQL Editor or via psql as postgres/service_role
INSERT INTO public.user_roles (user_id, role, granted_by)
SELECT id, 'admin', id
FROM public.profiles
WHERE email = 'admin@example.edu'
ON CONFLICT (user_id, role) DO NOTHING;

INSERT INTO public.audit_logs (actor_user_id, action, target_type, target_id, metadata)
SELECT id, 'role.bootstrap_admin', 'user', id::text, '{"source": "manual_sql_bootstrap"}'::jsonb
FROM public.profiles
WHERE email = 'admin@example.edu';
```

Once at least one Admin exists, all subsequent `teacher` or `admin` grants and revocations must go through the audited Admin API (`POST /api/v1/admin/users/{user_id}/roles`).
