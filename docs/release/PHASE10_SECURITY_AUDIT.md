# Phase 10 Pre-Deployment Security Audit & Remediation Report

## 1. Repository Secret & Private Content Hygiene
- Checked tracked files across `develop`: zero `.env`, `.env.local`, `backend/.env`, `frontend/.env.local`, or `backend/protected_content/*.local.json` files are committed in Git.
- Verified `.github/workflows/ci.yml` includes an automated check rejecting any tracked `.local.json` or `.env*` file.
- **CI Fix Applied:** Removed `|| true` from `npm audit --omit=dev --audit-level=high` in `.github/workflows/ci.yml` so production dependency vulnerabilities fail CI cleanly (`0` vulnerabilities currently reported).

## 2. Compromised Public Demo Seed Assessment Content (Important)
The following public repository SQL seed files on GitHub contain demonstration problem reference solutions, hidden test inputs/outputs, or MCQ answer keys visible in public history:
1. `supabase/seed/001_python_problems_seed.sql`: `sum-of-even-numbers`, `count-vowels`, `debug-range-sum-off-by-one`, `debug-max-negative-init` (includes `problem_reference_solutions` and `test_cases` with `is_hidden = true`).
2. `supabase/seed/002_phase4_transfer_and_taxonomy_seed.sql`: `transfer-step-range-sum`, `transfer-negative-threshold-min` (includes `problem_reference_solutions` and hidden `test_cases`).
3. `supabase/seed/003_phase5_tracks_lessons_diagnostics_seed.sql`: baseline `diagnostic_question_answers` for public demo calibration.

### Required Handling & Remediation
- **Live / Production Rule:** Public GitHub seed hidden tests and solutions MUST be treated as demonstration-only and compromised for real graded assessment. Real production assessment uses private gitignored bundles (`backend/protected_content/*.local.json`) imported via `backend/scripts/import_curriculum_bundle.py` or newly authored private items created directly inside Admin Studio (`/admin/problems`, `/admin/diagnostics`).
- **Database Protection Script:** Added `backend/scripts/prepare_production_content.py` (`--mode audit` and `--mode archive-compromised-demo`) so operators can safely archive public demo problems after importing private production problems without losing any historical submissions.
- **Git History & Key Rotation Note:** Git history was **not** rewritten without explicit owner authorization. Before opening the platform to high-stakes graded exams, generate fresh private test cases/solutions in Admin Studio and (if any demo password/token was ever used in local testing) rotate cloud credentials independently inside Supabase Cloud and Gemini AI Studio.

## 3. Core Application Security Controls Verified
| Control | Implementation | Verification |
|---|---|---|
| Database Isolation | PostgreSQL RLS + `FORCE ROW LEVEL SECURITY` on `57/57` tables in `public`; `problem_reference_solutions` and `diagnostic_question_answers` locked to Admin-only | Live `pg_class` query & pytest RLS tests |
| Auth & RBAC | Supabase asymmetric JWKS (`RS256`/`ES256`/`EdDSA`), DB-backed `user_roles`, privilege-escalation blocked | `test_auth_and_rbac.py` & live Supabase tests |
| Code Execution | Strict delegation to isolated Judge0 CE sandbox (`ENABLE_NETWORK=false`, time/memory limits); zero `eval`/`exec` | `test_live_phase3_judge0.py` |
| HTTP & API Hardening | Security headers (`nosniff`, `DENY`, `Referrer-Policy`, `Permissions-Policy`, `Cache-Control: no-store` on `/api/*`), 2 MiB body cap (`413`), sliding-window rate limiter (`429`) | `test_phase9_security_and_observability.py` & `phase9-ux.test.tsx` |
| Secret Isolation | `NEXT_PUBLIC_*` only contains URL + public Supabase anon key; `DATABASE_URL`, `LLM_API_KEY`, `JUDGE0_AUTH_TOKEN` stay server-side only | Static audit & `frontend/src/lib/env.ts` |
