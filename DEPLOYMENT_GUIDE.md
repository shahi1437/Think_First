# Think_First (CodeMentor AI) — Production Deployment Guide

Complete production deployment runbook for **Think_First (CodeMentor AI)** preserving all existing features across Student, Teacher, and Admin portals, 5-language adaptive learning (Python, JavaScript, C, C++, Java), Socratic AI Mentor (Gemini + deterministic fallback), trained scikit-learn ML error classifier, pgvector RAG, Skill Graph, Daily Learning Plan, Spaced Retention, Classrooms & Grading, and isolated Judge0 CE code execution.

> **Security Policy:** Never place real passwords, API keys, database URLs with credentials, or service role tokens into Git commits, frontend `NEXT_PUBLIC_*` variables, logs, or this document.

---

## 1. Production Architecture

```text
User Browser (HTTPS)
   │
   ▼
Vercel — Next.js 16 Frontend (Root Directory: frontend/, Node.js 22.x)
   │  • Public Supabase Auth SSR + middleware session refresh
   │  • Calls FastAPI over HTTPS via NEXT_PUBLIC_API_BASE_URL
   ▼
Render — FastAPI Docker Service (Context: . , Dockerfile: infrastructure/docker/backend.Dockerfile)
   │  • Entrypoint: uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --no-proxy-headers
   │  • Asymmetric JWKS JWT verification (RS256/ES256/EdDSA) + DB-backed RBAC
   │  • Bundled scikit-learn ML classifier (/app/ml/artifacts/error_classifier_v1.joblib)
   │  • Sliding-window rate limiter + 2 MiB body guard + strict production CORS
   ├──► Supabase Cloud PostgreSQL 17 + Auth + pgvector (57/57 FORCE RLS)
   ├──► Judge0 CE Production Execution Plane (Managed RapidAPI OR Dedicated Hardened Linux VPS)
   └──► Google Gemini API (Socratic AI Mentor, server-side LLM_API_KEY only)
```

### Architecture Guardrails
- **Do NOT deploy `docker-compose.yml` to Vercel.** Vercel serves only `frontend/`.
- **Do NOT run privileged Judge0 containers inside Render's API container.**
- **Keep Piston fallback disabled (`PISTON_ENABLED=false`, `EXECUTION_FALLBACK_ENABLED=false`)** in public multi-tenant production unless hosted on a separate dedicated isolated VM/microVM with `PISTON_ISOLATED_HOST_VERIFIED=true`.

---

## 2. Target Repository & Branch

- **Repository:** `https://github.com/shahi1437/Think_First`
- **Target Branch:** `develop`
- **Existing Cloud Resources Identified During Audit:**
  - **Supabase Cloud Project Ref:** `vsmrwfoqqjvomtjpypyv` (`https://vsmrwfoqqjvomtjpypyv.supabase.co`, Project Name: `THINKFIRST`)
  - **Vercel Production Domain:** `https://think-first-pi.vercel.app` (Project: `staysafe/think-first`)
  - **Render Backend Service:** Deploy via `render.yaml` Blueprint (use the exact `https://<your-service>.onrender.com` URL returned by Render — never guess or hardcode an unverified hostname).

---

## 3. Step-by-Step Deployment Sequence

Deploy in this exact order so URLs, migrations, CORS, and Auth callbacks wire cleanly on the first try:

1. **Step 1 — Supabase Cloud Backup & Ordered SQL Migrations (`0001..0010`)**
2. **Step 2 — Judge0 Production Execution Setup (Option A: Managed RapidAPI OR Option B: Dedicated Linux VPS)**
3. **Step 3 — Render FastAPI Backend Deployment (Docker from Repo Root)**
4. **Step 4 — Vercel Next.js Frontend Deployment (`frontend/` Root Directory)**
5. **Step 5 — Cross-Wire CORS (`CORS_ORIGINS`), Frontend API URL (`NEXT_PUBLIC_API_BASE_URL`), and Supabase Auth Redirect URLs**
6. **Step 6 — Seed Non-Destructive Multi-Language Curriculum & Bootstrap First Admin (if not already present)**
7. **Step 7 — Run Full Production Smoke & End-to-End Verification**

---

## 4. Supabase Cloud Production Configuration

### 4.1 Safety & Backup Before Any Migration
- **NEVER run `supabase db reset`, `DROP TABLE`, or `TRUNCATE` on production.**
- Before applying migrations to Supabase Cloud (`vsmrwfoqqjvomtjpypyv`), take a manual snapshot/backup from **Supabase Dashboard → Database → Backups** (or `pg_dump --schema=public --no-owner --no-privileges` into encrypted local storage).
- All 11 SQL migrations in `supabase/migrations/` are strictly additive and ordered:
  1. `20261120000001_identity_roles_and_audit.sql` (enables `pgcrypto` + `vector` extensions, identity, RBAC, audit logs)
  2. `20261120000002_problems_and_execution.sql`
  3. `20261120000003_ai_mentor_rag_and_verification.sql`
  4. `20261120000004_learning_tracks_lessons_diagnostics_skill_graph.sql`
  5. `20261120000005_learning_dna_daily_plan_history_retention.sql`
  6. `20261120000006_classrooms_assignments_grading.sql`
  7. `20261120000007_admin_studio_curriculum_governance.sql`
  8. `20261120000008_phase9_performance_indexes.sql`
  9. `20261122000009_multilanguage_learning_and_execution.sql` *(adds 5-language support, `active_language_slug`, per-language isolation, and `execution_provider` without modifying or removing any existing Python data)*
  10. `20261123000010_execution_worker_queue.sql` *(adds `execution_workers` and `execution_jobs` with `FORCE ROW LEVEL SECURITY` for the free outbound local Judge0 worker queue)*
  11. `20261127000011_in_app_notifications.sql` *(adds `user_notifications` with `FORCE ROW LEVEL SECURITY`, recipient/unread indexes, and deduplication source key for the role-scoped Notification Center; total `58/58` `FORCE RLS` public tables)*

### 4.2 Dry-Run & Apply Migrations
```powershell
# Authenticate once with Supabase CLI
npx supabase login

# Link to existing Supabase Cloud project
npx supabase link --project-ref vsmrwfoqqjvomtjpypyv

# 1. Always inspect pending migrations with dry-run first!
npx supabase db push --dry-run

# 2. Only after reviewing dry-run output and confirming backup:
npx supabase db push
```

### 4.3 Verify Extensions & 58/58 FORCE RLS in Supabase SQL Editor
```sql
SELECT extname FROM pg_extension WHERE extname IN ('pgcrypto', 'vector') ORDER BY extname;

SELECT
  count(*) AS total_tables,
  count(*) FILTER (WHERE relrowsecurity AND relforcerowsecurity) AS force_rls_tables
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public' AND c.relkind = 'r';
-- Expected: total_tables = 58, force_rls_tables = 58

SELECT slug, display_name, judge0_language_id, is_enabled
FROM public.supported_languages
ORDER BY slug;
-- Expected: c, cpp, java, javascript, python (all is_enabled = true)
```

### 4.4 Idempotent Curriculum & Multi-Language Seeding
Run once against the production `DATABASE_URL` (safe & idempotent; never overwrites existing Python records or user progress):
```powershell
cd backend
# Optional: import private Python curriculum bundle if fresh cloud DB
# .venv\Scripts\python.exe scripts\import_curriculum_bundle.py --file protected_content/phase8_curriculum.local.json

# Seed 40 JS/C/C++/Java lessons, 36 multi-language diagnostics, 5-language problem variants & RAG docs
$env:DATABASE_URL="postgresql+asyncpg://<SESSION_POOLER_URI>"
.venv\Scripts\python.exe scripts\seed_multilanguage_curriculum.py
```

### 4.5 Production `DATABASE_URL` Format (Render IPv4 + Supavisor Compatibility)
Render's standard outbound networking uses **IPv4**. In **Supabase Dashboard → Connect → Session Pooler (IPv4 compatible, Port `5432`)**, copy the URI and use the `postgresql+asyncpg://` scheme:
```text
postgresql+asyncpg://postgres.<project-ref>:<URL_ENCODED_DB_PASSWORD>@aws-0-<region>.pooler.supabase.com:5432/postgres
```
> Note: `backend/app/core/database.py` automatically normalizes `postgresql://` -> `postgresql+asyncpg://`, enables `ssl="require"` for `*.supabase.co` and `*.pooler.supabase.com`, and sets `statement_cache_size=0` for Supavisor/PgBouncer compatibility. Always URL-encode special characters in the password (e.g., `@` -> `%40`, `#` -> `%23`).

### 4.6 Supabase Authentication URL Configuration
In **Supabase Dashboard → Authentication → URL Configuration**:
- **Site URL:** `https://<your-vercel-domain>` (e.g. `https://think-first-pi.vercel.app`)
- **Redirect URLs:**
  - `https://<your-vercel-domain>/auth/callback`
  - `https://<your-vercel-domain>/reset-password`
  - *(Add any additional custom or preview Vercel domain callbacks explicitly; avoid overly broad wildcards.)*

---

## 5. Backend Deployment on Render (Docker)

The repository root includes [`render.yaml`](./render.yaml) wired directly to [`infrastructure/docker/backend.Dockerfile`](./infrastructure/docker/backend.Dockerfile).

### 5.1 Required Render Service Settings
| Setting | Required Value |
|---|---|
| Service Type | Web Service (Docker) |
| Repository | `https://github.com/shahi1437/Think_First` |
| Branch | `develop` |
| **Docker Build Context** | **`.` (Repository Root — REQUIRED because Dockerfile copies both `backend/` and `ml/`)** |
| **Dockerfile Path** | **`./infrastructure/docker/backend.Dockerfile`** |
| Start Command | *(Leave default — Dockerfile runs `uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --no-proxy-headers`)* |
| Health Check Path | `/health/ready` |
| Memory Footprint | ~192 MiB verified locally with ML classifier warmed up (fits Render Free 512 MiB; Starter 512 MiB+ recommended to avoid cold-start sleep) |

### 5.2 Render Deployment Steps
1. Open **Render Dashboard → New → Blueprint** (or **New → Web Service**).
2. Connect GitHub repository `shahi1437/Think_First` and select branch **`develop`**.
3. If creating manually (not via Blueprint), verify **Root Directory is blank / `.`**, **Runtime = Docker**, **Dockerfile Path = `infrastructure/docker/backend.Dockerfile`**, and **Health Check Path = `/health/ready`**.
4. Enter all private environment variables listed in Section 7.1.
5. Click **Deploy** and record the exact production URL returned by Render (e.g., `https://<actual-render-service>.onrender.com`).
6. Verify backend health:
   - `GET https://<actual-render-service>.onrender.com/health/live` -> `HTTP 200` `{"status":"ok",...}`
   - `GET https://<actual-render-service>.onrender.com/health/ready` -> `HTTP 200` `{"status":"ok","database":"ok",...}`
   - `GET https://<actual-render-service>.onrender.com/api/v1/meta` -> `HTTP 200` `{"environment":"production",...}`
   - `GET https://<actual-render-service>.onrender.com/docs` -> `HTTP 404` *(Swagger UI intentionally disabled in production)*

---

## 6. Frontend Deployment on Vercel

The `frontend/` directory includes [`frontend/vercel.json`](./frontend/vercel.json) and pins `"engines": { "node": "22.x" }` in [`frontend/package.json`](./frontend/package.json).

### 6.1 Required Vercel Project Settings
| Setting | Required Value |
|---|---|
| Repository | `shahi1437/Think_First` |
| Production / Preview Branch | `develop` |
| **Root Directory** | **`frontend`** |
| Framework Preset | **Next.js** |
| Node.js Version | **22.x** |
| Install Command | `npm ci` |
| Build Command | `npm run build` |

### 6.2 Vercel Environment Variables (Public Only!)
Configure ONLY these 4 public variables in **Vercel Project → Settings → Environment Variables**:
- `NEXT_PUBLIC_APP_URL` = `https://<your-vercel-production-domain>` (e.g. `https://think-first-pi.vercel.app`)
- `NEXT_PUBLIC_API_BASE_URL` = `https://<actual-render-service>.onrender.com` *(origin only — no trailing `/api/v1` needed)*
- `NEXT_PUBLIC_SUPABASE_URL` = `https://vsmrwfoqqjvomtjpypyv.supabase.co`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY` = `<Supabase Cloud anon/publishable key>`

> **NEVER add these to Vercel:** `DATABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `LLM_API_KEY`, `JUDGE0_AUTH_TOKEN`, `JUDGE0_RAPIDAPI_KEY`.

After setting/updating environment variables in Vercel, trigger a fresh **Redeploy** (Next.js inlines `NEXT_PUBLIC_*` variables at build time).

---

## 7. Complete Audited Environment Variable Reference

Every variable below was audited directly against `backend/app/core/config.py` and `frontend/src/lib/env.ts`.

### 7.1 Backend (Render — Server-Side Only)
| Variable | Required in Prod | Recommended Production Value / Format | Secret? |
|---|:---:|---|:---:|
| `APP_ENV` | Yes | `production` | No |
| `LOG_LEVEL` | Yes | `INFO` | No |
| `DATABASE_URL` | Yes | `postgresql+asyncpg://postgres.<ref>:<encoded_pw>@aws-0-<region>.pooler.supabase.com:5432/postgres` | **YES** |
| `SUPABASE_URL` | Yes | `https://vsmrwfoqqjvomtjpypyv.supabase.co` | No |
| `SUPABASE_JWT_AUDIENCE` | Yes | `authenticated` | No |
| `CORS_ORIGINS` | Yes | `https://<your-vercel-domain>` (or JSON array `["https://..."]`; NEVER `*` or `localhost`) | No |
| `JUDGE0_AUTH_MODE` | Yes | `rapidapi` (Option A) OR `auth_token` (Option B VPS) OR `auto` | No |
| `JUDGE0_BASE_URL` | Yes* | `https://judge0-ce.p.rapidapi.com` (Option A) OR `https://judge0.<your-domain>` (Option B) | No |
| `JUDGE0_AUTH_TOKEN` | Option B | Strong 32-byte random hex matching Judge0 VPS `AUTHN_TOKEN` | **YES** |
| `JUDGE0_RAPIDAPI_KEY` | Option A | RapidAPI subscription key for Judge0 CE | **YES** |
| `JUDGE0_RAPIDAPI_HOST` | Option A | `judge0-ce.p.rapidapi.com` | No |
| `EXECUTION_FALLBACK_ENABLED` | Yes | `false` (unless dedicated isolated Piston VM verified) | No |
| `PISTON_ENABLED` | Yes | `false` (auto-defaults to `false` when `APP_ENV=production`) | No |
| `PISTON_ISOLATED_HOST_VERIFIED` | Yes | `false` (set `true` ONLY if running dedicated isolated Piston VM) | No |
| `ML_MODEL_ARTIFACT_PATH` | Yes | `/app/ml/artifacts/error_classifier_v1.joblib` (pre-set in Dockerfile) | No |
| `RAG_SIMILARITY_THRESHOLD` | Optional | `0.22` (verified multi-language OOD rejection threshold) | No |
| `LLM_PROVIDER` | Recommended | `gemini` (or `none` for deterministic fallback) | No |
| `LLM_MODEL` | Recommended | `gemini-2.5-flash-lite` | No |
| `LLM_API_KEY` | Recommended | Google AI Studio Gemini API key | **YES** |
| `LLM_TIMEOUT_SECONDS` | Optional | `30.0` | No |
| `RATE_LIMIT_ENABLED` | Yes | `true` | No |
| `TRUSTED_PROXY_CIDRS` | Recommended | Comma-separated or JSON CIDR allowlist of verified reverse proxies (empty = use socket peer IP only) | No |
| `TRUSTED_PROXY_HOPS` | Optional | `1` (number of trusted reverse-proxy hops at the right end of `X-Forwarded-For`) | No |
| `TRUSTED_PROXY_CLIENT_IP_HEADER` | Optional | Unset by default (`cf-connecting-ip`, `true-client-ip`, or `x-real-ip` ONLY if direct peer matches `TRUSTED_PROXY_CIDRS`) | No |
| `MAX_REQUEST_BODY_BYTES` | Optional | `2097152` (2 MiB) | No |

*\*If deploying the backend before Judge0 is provisioned, set `JUDGE0_AUTH_MODE=disabled` temporarily so auth, onboarding, lessons, diagnostics, RAG, ML, and Teacher/Admin portals stay online while code execution honestly returns `503 EXECUTION_SERVICE_UNAVAILABLE`.*

### 7.2 Frontend (Vercel — Public Only)
| Variable | Required | Value Format |
|---|:---:|---|
| `NEXT_PUBLIC_APP_URL` | Yes | `https://<your-vercel-domain>` |
| `NEXT_PUBLIC_API_BASE_URL` | Yes | `https://<actual-render-service>.onrender.com` |
| `NEXT_PUBLIC_SUPABASE_URL` | Yes | `https://vsmrwfoqqjvomtjpypyv.supabase.co` |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Yes | Supabase Cloud anon/publishable key |

---

## 8. Judge0 Production Code Execution Setup

Think_First executes student code in **Python 3 (71)**, **JavaScript Node.js (63)**, **C GCC (50)**, **C++ GCC (54)**, and **Java OpenJDK (62)**.

### Option A — Managed Judge0 CE via RapidAPI (Fastest Production Launch)
1. Subscribe to **Judge0 CE** on RapidAPI (`judge0-ce.p.rapidapi.com`).
2. Set in **Render → Environment**:
   - `JUDGE0_AUTH_MODE=rapidapi`
   - `JUDGE0_BASE_URL=https://judge0-ce.p.rapidapi.com`
   - `JUDGE0_RAPIDAPI_KEY=<your-rapidapi-key>`
   - `JUDGE0_RAPIDAPI_HOST=judge0-ce.p.rapidapi.com`
   - `EXECUTION_FALLBACK_ENABLED=false`
   - `PISTON_ENABLED=false`

### Option B — Dedicated Hardened Linux x86_64 VPS (Full Control, Unlimited Quota)
Use the hardened production templates already prepared in `infrastructure/judge0/`:
- [`infrastructure/judge0/SETUP_HARDENED_JUDGE0_VPS.md`](./infrastructure/judge0/SETUP_HARDENED_JUDGE0_VPS.md)
- [`infrastructure/judge0/docker-compose.prod.yml`](./infrastructure/judge0/docker-compose.prod.yml)
- [`infrastructure/judge0/judge0.conf.example`](./infrastructure/judge0/judge0.conf.example)
- [`infrastructure/judge0/Caddyfile.example`](./infrastructure/judge0/Caddyfile.example)

Key hardening requirements enforced:
- Dedicated `x86_64` Ubuntu 22.04/24.04 VPS (minimum 2 vCPU, 4 GB RAM, `cgroup v1` enabled).
- Judge0 bound strictly to `127.0.0.1:2358` behind Caddy TLS (`:443`) with strong `AUTHN_TOKEN` (`X-Auth-Token`).
- UFW firewall allows ONLY `22/tcp` and `443/tcp`.
- `ENABLE_NETWORK=false`, strict per-process CPU/memory/process limits, Redis `--requirepass`, and isolated Judge0 Postgres.
- In Render Dashboard, set `JUDGE0_AUTH_MODE=auth_token`, `JUDGE0_BASE_URL=https://judge0.<your-domain>`, `JUDGE0_AUTH_TOKEN=<AUTHN_TOKEN>`.

---

## 9. Health Check & Admin Telemetry Endpoints

| Endpoint | Auth | Expected Healthy Response |
|---|---|---|
| `GET /health/live` | Public | `200 OK` `{"status":"ok","service":"CodeMentor AI API","version":"0.1.0"}` |
| `GET /health/ready` | Public | `200 OK` `{"status":"ok","database":"ok",...}` (`503` if DB unreachable) |
| `GET /api/v1/meta` | Public | `200 OK` `{"environment":"production","api_version":"v1",...}` |
| `GET /api/v1/admin/operations/health` | Admin JWT | `200 OK` telemetry for `postgresql`, `judge0`, `ml_classifier`, `llm_provider_mode` |

---

## 10. Troubleshooting

| Symptom | Likely Cause | Fix |
|---|---|---|
| Render `/health/ready` returns `503` with `network_or_dns_error` | Using Supabase Direct IPv6 host (`db.<ref>.supabase.co`) on IPv4-only Render | Switch `DATABASE_URL` to Supabase **Session Pooler (IPv4)** URI (`*.pooler.supabase.com:5432`) |
| Render fails on startup with `InvalidPasswordError` or URL parse error | Special characters in DB password (`@`, `#`, `:`, `/`) not URL-encoded | Percent-encode special characters in `DATABASE_URL` password |
| Browser shows CORS error calling Render API | `CORS_ORIGINS` missing exact Vercel origin or includes trailing slash | Set `CORS_ORIGINS=https://<exact-vercel-domain>` (no trailing slash) and redeploy Render |
| Email confirmation / password reset redirects to `localhost` or fails | Supabase Auth Site URL / Redirect URLs not updated OR `NEXT_PUBLIC_APP_URL` stale | Update Supabase Auth URL Configuration + Vercel `NEXT_PUBLIC_APP_URL`, then redeploy Vercel |
| Login returns `401 AUTH_PROVIDER_UNAVAILABLE` | `SUPABASE_URL` on Render does not match `NEXT_PUBLIC_SUPABASE_URL` on Vercel | Ensure both point to `https://vsmrwfoqqjvomtjpypyv.supabase.co` |
| Code execution returns `503 EXECUTION_SERVICE_UNAVAILABLE` | `JUDGE0_AUTH_MODE=disabled`, missing Judge0 key/token, or Judge0 VPS unreachable | Verify `JUDGE0_AUTH_MODE`, `JUDGE0_BASE_URL`, and `JUDGE0_RAPIDAPI_KEY`/`JUDGE0_AUTH_TOKEN` in Render |
| Render Free tier slow first request (~30–50s) | Render Free web services spin down after 15 min idle | Upgrade Render to Starter (`$7/mo`) or warm `/health/live` before live demos |

---

## 11. Redeployment & Rollback Procedure

### Safe Redeployment
1. Run local quality gates before pushing:
   - Backend: `ruff check app worker tests scripts && ruff format --check app worker tests scripts && mypy app worker && pytest -v -m "not live"` and `pytest -c pyproject.toml -v ../ml/tests`
   - Frontend: `npm ci && npm run lint && npm run typecheck && npm test && npm run build`
2. Push reviewed commits normally (never `--force`) to the target branch.
3. Apply any new additive SQL migrations via `npx supabase db push --dry-run` -> `npx supabase db push` **before** rolling out dependent backend code.
4. Render and Vercel automatically redeploy from GitHub (or trigger manual deploy in Render/Vercel dashboards).
5. Verify `/health/ready`, login, onboarding, lessons, Judge0 execution, AI Mentor, and Admin telemetry.

### Safe Rollback
- **Frontend (Vercel):** Instant 1-click rollback in **Vercel Dashboard → Deployments → Promote Previous Production Deployment**.
- **Backend (Render):** Instant rollback in **Render Dashboard → Events → Rollback to previous commit/image**.
- **Database (Supabase):** Migrations are additive and forward-compatible. For catastrophic recovery, restore via Supabase Point-in-Time Recovery (PITR) or verified `pg_dump` backup into a staging DB first.

---

## 12. Backup & Recovery Guidance

- **Supabase Cloud Automated Backups:** Enable Daily Backups / PITR in **Supabase Dashboard → Database → Backups**.
- **Automated Backup + Restore Parity Verification:** Run `backend/scripts/backup_verify.py` locally/staging to verify full dump, restore with `ON_ERROR_STOP=1`, row-count parity across all 13 critical educational/governance tables, and `57/57` `FORCE ROW LEVEL SECURITY` enforcement.
- **First Admin Bootstrap (New Cloud Environment Only):**
  1. Register the intended admin user normally at `https://<your-vercel-domain>/register` (assigns `student` role only).
  2. Run with explicit confirmation:
     ```powershell
     cd backend
     .venv\Scripts\python.exe scripts\bootstrap_first_admin.py --email <ADMIN_EMAIL> --environment production --confirm
     ```
  3. All subsequent `teacher` / `admin` role grants happen strictly inside `/admin/audit` with immutable `audit_logs` records.
- See [`docs/operations/BACKUP_AND_RECOVERY.md`](./docs/operations/BACKUP_AND_RECOVERY.md) for Tier-1/Tier-2 table recovery priority.
