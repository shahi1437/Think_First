# Think_First (CodeMentor AI) — Phase 10 Teacher/Admin Access Repair & Cloud Readiness Checkpoint

**Active Branch:** `develop`  
**Vercel Project:** `staysafe/think-first` (`prj_HIa4MuCokmukyZ3QgiVt2nPYX5nH`)  
**Public Frontend URL:** `https://think-first-pi.vercel.app`  
**Last Updated:** 2026-11-20

## Root-Cause Diagnosis & Implemented Fixes
1. **Local Database Role Finding:** Out of `341` local profiles, `340` are synthetic E2E/pytest accounts and only `1` real human profile (`sha***@gmail.com`) exists, currently holding **`{student}`** only (`0` real human Admins or Teachers). Left unpromoted pending explicit user approval.
2. **Role-Aware Login Fixed:**
   - Added `frontend/src/lib/auth/roles.ts` (`canAccessPortal`, `getAuthorizedPortals`, `resolveDefaultPortalPath`, `resolvePostLoginRedirect`) with `Admin -> /admin`, `Teacher -> /teacher`, `Student -> /student` priority and role-checked internal redirects.
   - Updated `frontend/src/features/auth/login-form.tsx`, `frontend/src/app/(auth)/login/page.tsx`, and `frontend/src/app/auth/callback/route.ts` to query verified `/api/v1/users/me` DB roles after authentication instead of blindly pushing `/student`.
3. **Portal Switcher & Admin -> Teacher Inheritance Fixed:**
   - Updated `frontend/src/components/nav-links.tsx` and `frontend/src/components/app-shell.tsx` so multi-role users and Admin accounts (even without an explicit `teacher` role row, matching backend `require_roles("teacher", "admin")`) see an accessible desktop + mobile Portal Switcher (`Student`, `Teacher`, `Admin`), while student-only accounts never see Teacher/Admin links.
   - Updated `frontend/src/lib/auth/server-guard.ts`, `frontend/src/app/student/page.tsx`, and `frontend/src/app/teacher/page.tsx` so unauthorized role redirects route to the user's authorized home portal with a visible `?error=forbidden` alert rather than trapping Teachers in Student onboarding.
4. **Safe One-Time First-Admin Bootstrap Tool:**
   - Added `backend/scripts/bootstrap_first_admin.py` requiring explicit `--email` and `--confirm` (never guessing emails or storing passwords) and recording an immutable `role.bootstrap_admin` entry in `audit_logs`.
   - Added `docs/capstone/CLOUD_BOOTSTRAP_AND_ENV_MAP.md` for parallel Supabase Cloud + Render + Judge0 deployment setup.

## Remaining Cloud Infrastructure Blockers
1. **Supabase Cloud:** Target project confirmation / DB credentials required before running `npx supabase db push` (`0001`–`0008`), `import_curriculum_bundle.py`, and Auth redirect URLs (`https://think-first-pi.vercel.app/auth/callback`).
2. **FastAPI Cloud Hosting:** Render (`render.yaml` / `backend.Dockerfile`) or Railway login authorization required.
3. **Judge0 CE Cloud Host:** Dedicated Linux VM/Docker host supporting `privileged: true` cgroup sandboxes required.
