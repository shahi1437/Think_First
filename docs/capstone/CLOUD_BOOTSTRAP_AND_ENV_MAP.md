# Cloud Deployment & Secure Bootstrap Reference (Vercel + Supabase Cloud + Render + Judge0)

## 1. Vercel Project (`staysafe/think-first`)
- **Framework:** Next.js | **Root Directory:** `frontend` | **Production Branch:** `develop`
- **Canonical Production URL:** `https://think-first-pi.vercel.app`
- **Required Public Env Vars (NEVER place `DATABASE_URL`, `LLM_API_KEY`, `SERVICE_ROLE`, or `JUDGE0_AUTH_TOKEN` here):**
  - `NEXT_PUBLIC_APP_URL=https://think-first-pi.vercel.app` *(already configured in Vercel Production)*
  - `NEXT_PUBLIC_API_BASE_URL=https://<your-render-backend>.onrender.com`
  - `NEXT_PUBLIC_SUPABASE_URL=https://<your-cloud-ref>.supabase.co`
  - `NEXT_PUBLIC_SUPABASE_ANON_KEY=<cloud-anon-or-publishable-key>`

## 2. Supabase Cloud Database Setup (Run Once Connected)
1. Enable `vector` (`pgvector`) and `pgcrypto` extensions in Supabase Cloud.
2. Link & apply ordered SQL migrations `20261120000001..0008.sql`:
   ```powershell
   npx supabase link --project-ref <CLOUD_REF>
   npx supabase db push
   ```
3. Apply non-compromised Skill Graph taxonomy (`supabase/seed/004_phase8_curriculum_skills.sql`), then import private curriculum & hidden tests via `backend/scripts/import_curriculum_bundle.py`:
   ```powershell
   cd backend
   .venv\Scripts\python.exe scripts\import_curriculum_bundle.py --file protected_content/phase8_curriculum.local.json
   .venv\Scripts\python.exe scripts\prepare_production_content.py --mode audit
   ```
4. Configure **Supabase Auth → URL Configuration**:
   - **Site URL:** `https://think-first-pi.vercel.app`
   - **Additional Redirect URLs:** `https://think-first-pi.vercel.app/auth/callback`, `https://think-first-staysafe.vercel.app/auth/callback`

## 3. Render Backend (`render.yaml` + `infrastructure/docker/backend.Dockerfile`)
- Deploy `shahi1437/Think_First` (`develop` branch) via `render.yaml` (`healthCheckPath: /health/ready`).
- Required private server env vars (`sync: false` in Render Blueprint form — **only 3 values needed**):
  - `DATABASE_URL`: Supabase Cloud **Session Pooler (IPv4)** URI on port `5432` (Render Free uses IPv4-only outbound networking). Use `postgresql+asyncpg://...` (plain `postgresql://` is also auto-normalized).
  - `SUPABASE_URL`: `https://vsmrwfoqqjvomtjpypyv.supabase.co`
  - `CORS_ORIGINS`: `https://think-first-pi.vercel.app` (both JSON array `["https://..."]` and comma-separated URLs are accepted)
- Judge0 starts in `JUDGE0_AUTH_MODE=disabled` so login, lessons, diagnostics, RAG, ML diagnosis, and Teacher/Admin portals work with zero paid services while code execution clearly returns `503 EXECUTION_SERVICE_UNAVAILABLE`.
- Optional later in Render Dashboard → Environment:
  - Self-hosted Judge0 VPS: `JUDGE0_AUTH_MODE=auth_token`, `JUDGE0_BASE_URL`, `JUDGE0_AUTH_TOKEN`
  - Temporary RapidAPI Demo: `JUDGE0_AUTH_MODE=rapidapi`, `JUDGE0_BASE_URL=https://judge0-ce.p.rapidapi.com`, `JUDGE0_RAPIDAPI_KEY`, `JUDGE0_RAPIDAPI_HOST=judge0-ce.p.rapidapi.com`
  - Optional AI Mentor key: `LLM_API_KEY` (when omitted, Socratic mentor runs in deterministic fallback mode)

## 4. Secure First-Admin Bootstrap (Cloud & Local)
Remember: **Local Supabase accounts and roles do NOT carry over to Supabase Cloud.**
1. Register your intended Admin account through `/register` on `https://think-first-pi.vercel.app` (creates `student` role only).
2. With explicit approval of the exact target email and environment, run `backend/scripts/bootstrap_first_admin.py` against the target database:
   ```powershell
   cd backend
   .venv\Scripts\python.exe scripts\bootstrap_first_admin.py --email <APPROVED_EMAIL> --environment production --confirm
   ```
3. Sign in at `/login`: Role-aware login routes Admins to `/admin` with Portal Switcher access across `Student`, `Teacher`, and `Admin`, and Admin can grant additional `teacher`/`admin` roles inside `/admin/audit`.
