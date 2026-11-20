# Backup, Restore & Least-Privilege Recovery Guide

## 1. Automated Local Backup & Restore Verification
Think_First includes `backend/scripts/backup_verify.py`, which:
1. Measures live table counts and `FORCE ROW LEVEL SECURITY` coverage on `public`.
2. Creates a full schema + data SQL backup via `pg_dump --schema=public --no-owner --no-privileges`.
3. Creates a disposable database (`thinkfirst_backup_verify_tmp`), installs required extensions (`pgcrypto`, `vector`), restores the dump with `ON_ERROR_STOP=1`, verifies 100% row-count and RLS parity across critical educational and operational tables, and drops the disposable database cleanly.

Run locally against Docker Supabase Postgres:
```powershell
cd backend
.venv\Scripts\python.exe scripts\backup_verify.py
```

## 2. Critical Data Domains & Recovery Priority
| Domain | Tables | Recovery Priority | Notes |
|---|---|---|---|
| Identity & RBAC | `profiles`, `user_roles` | Tier 1 (Critical) | Restored alongside Supabase `auth.users` IDs |
| Published Curriculum | `learning_tracks`, `skill_nodes`, `lessons`, `lesson_versions`, `problems`, `problem_versions`, `diagnostic_questions`, `knowledge_documents` | Tier 1 (Critical) | Never expose hidden tests or reference solutions outside Admin/Service roles |
| Classrooms & Assignments | `courses`, `course_memberships`, `class_invitations`, `assignments`, `assignment_submissions`, `assignment_attempts` | Tier 1 (Critical) | Preserves teacher grading history and immutable enrollment records |
| Execution & Learning Evidence | `submissions`, `execution_results`, `error_diagnoses`, `mentor_sessions`, `verification_attempts`, `learning_events` | Tier 2 (High) | Ground truth for Learning DNA and mastery progression |
| Security Audit Trail | `audit_logs` | Tier 1 (Immutable) | Append-only governance record |

## 3. Safe Production Recovery Protocol
- Always verify backups into a **staging/disposable database** first (`ON_ERROR_STOP=1`).
- Never truncate `audit_logs` or `profiles` in production.
- Perform point-in-time recovery (PITR) through managed Supabase Postgres snapshots before re-applying forward-only migrations.
- Confirm `relrowsecurity = true AND relforcerowsecurity = true` across all `public` tables after every restore.
