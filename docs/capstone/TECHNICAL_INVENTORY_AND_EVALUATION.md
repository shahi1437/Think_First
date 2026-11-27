# CodeMentor AI (Think_First) — Technical Inventory, Deployment Runbook & Evaluation Summary

## 1. Complete Technical Feature Inventory
- **Phase 1–2 (Foundation & Auth/RBAC):** Modular Monolith FastAPI + Next.js 16 App Router, Supabase asymmetric JWKS auth (`RS256`/`ES256`/`EdDSA`), DB-backed `user_roles`, PostgreSQL `FORCE ROW LEVEL SECURITY` on `57/57` tables.
- **Phase 3 (Problem Bank & Execution):** Monaco Editor workspace, isolated Judge0 CE sandbox (`Python 3.8.1`), hidden-test sanitization, deterministic verdicts, immutable versioned problems.
- **Phase 4 (ML + RAG + Socratic AI + Transfer):** Own `scikit-learn` error classifier (`error-clf-v1.0.0`), `pgvector` RAG strictly over `status='approved'` docs, progressive Socratic state machine with injection & solution-leakage guards, isomorphic unseen Transfer Verification.
- **Phase 5–6 (Adaptive Learning & Growth):** 4 learner tracks, 24 bilingual lessons (EN/BN), 8-domain adaptive diagnostic, 18-node prerequisite DAG Skill Graph, 6-axis Learning DNA, Adaptive Daily Plan, Searchable Learning History, 24-hour Spaced Retention gates.
- **Phase 7–8 (Teacher Portal & Admin Studio):** Classrooms + SHA-256 invitation codes, pinned-version assignments, Judge0 auto-evaluation + revision/grading workflow, Admin Validation Engine (AST + quality + Judge0), protected curriculum bundle importer (`phase8_curriculum.local.json`), immutable audit logs.
- **Phase 9–10 (Hardening, Telemetry & Deployment Readiness):** HTTP security headers (`nosniff`, `DENY`, `Referrer-Policy`, `Permissions-Policy`, `Cache-Control: no-store`), sliding-window API rate limiter, 2 MiB payload cap, `GET /api/v1/admin/operations/health`, Migration `0008` performance indexes, backup/restore verification script, `render.yaml` & Docker ML bundle fix, compromised public seed protection (`prepare_production_content.py`).

## 2. Production Deployment Runbook (4-Component Architecture)
1. **Supabase Cloud:** Create project -> enable `vector` + `pgcrypto` extensions -> apply all 10 ordered migrations (`supabase/migrations/20261120000001..20261123000010.sql`) -> run `seed/004_phase8_curriculum_skills.sql` -> import private `backend/protected_content/*.local.json` via `import_curriculum_bundle.py` -> configure Auth Redirect URL (`https://<vercel-domain>/auth/callback`) -> bootstrap Admin account cleanly.
2. **Isolated Judge0 CE Host:** Deploy Judge0 CE (`judge0/judge0:1.13.1` + Redis + Postgres) on an isolated Linux VM supporting `privileged: true` cgroup sandboxes (required by Judge0 `isolate`; free serverless tiers cannot run `isolate`), firewalling Judge0 port `:2358` to the backend host with `JUDGE0_AUTH_TOKEN`.
3. **FastAPI Backend (`render.yaml` / `infrastructure/docker/backend.Dockerfile`):** Deploy container bundling `backend/` + `ml/` with `APP_ENV=production`, `DATABASE_URL`, `SUPABASE_URL`, `CORS_ORIGINS=["https://<vercel-domain>"]`, `JUDGE0_BASE_URL`, `JUDGE0_AUTH_TOKEN`, `LLM_PROVIDER=gemini`, `LLM_MODEL`, and `LLM_API_KEY`. Verify `/health/ready` returns `200`.
4. **Vercel Frontend (`frontend/`):** Import `shahi1437/Think_First`, set Root Directory = `frontend`, branch = `develop`, set `NEXT_PUBLIC_APP_URL`, `NEXT_PUBLIC_API_BASE_URL`, `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, deploy, and verify HTTPS endpoints.

## 3. Verification & Testing Summary
| Scope | Suite | Observed Result |
|---|---|---|
| **Local / CI Backend Static** | `ruff check`, `ruff format --check`, `mypy app` | Passed (`112+` files, `91` source files) |
| **Local / Live Backend Suite** | `RUN_LIVE_INTEGRATION_TESTS=1 pytest -v tests` | `51+` passed (includes real Supabase RLS, Judge0, Gemini, Admin Ops, Security) |
| **ML Pipeline** | `pytest -v ml/tests` | `1/1` passed (`error-clf-v1.0.0`) |
| **Local Frontend Static & Unit** | ESLint, `tsc --noEmit`, `vitest run`, `next build`, `npm audit --omit=dev` | `25/25` Vitest passed, `0` vulnerabilities |
| **Local Full-Stack E2E** | Playwright (`phase3`..`phase8`) against `:3100` & `:8100` | `6/6` specs passed |
| **Backup/Restore Parity** | `backend/scripts/backup_verify.py` on disposable DB | `57/57` tables & `FORCE RLS`, `13/13` tables `100%` row parity |
| **Public Staging/Production** | Live HTTPS Vercel + Cloud Backend + Cloud Supabase + Cloud Judge0 | **Pending Cloud Authorization** |

## 4. ML Classifier & RAG Evaluation Explanation
- **Own ML Classifier (`error-clf-v1.0.0`):** Trained on `309` execution-validated samples across `42` original Python program families using `StratifiedGroupKFold(n_splits=5)` (`249` train / `60` held-out test, `0` family leakage).
  - **Rule-Based Baseline:** Held-out Macro F1 = `0.5945`
  - **Selected Model (TF-IDF word+char n-grams + AST/execution cues + Logistic Regression):** Held-out Macro F1 = **`0.7196`** (`Weighted F1 = 0.7487`; 5-Fold Grouped CV Macro F1 = **`0.7745 ± 0.057`**).
  - High separability on `syntax_error` (`F1 = 1.0`) and `runtime_error` (`0.9412`); overlapping semantic classes (`condition_error` vs `logic_error`) trigger uncertainty alerts when confidence `< 0.55` or top-2 margin `< 0.12`.
- **Verified RAG (`pgvector` 256-dim):** Benchmarked on `14` in-domain queries (`Hit@1 = 1.0000`, `MRR = 1.0000`) and `3` out-of-domain queries (`1.0000` clean no-match fallback rejection).

## 5. Known Limitations & Future Scope
- **Single-Process Rate Limiter:** Current in-memory sliding-window rate limiter resets per worker; multi-replica production scaling should back it with Redis.
- **Language Support:** All 5 target languages (`Python 3`, `JavaScript Node.js`, `C`, `C++`, and `Java`) are enabled across lessons, diagnostics, problem variants, RAG chunks, and Judge0 execution; the bundled scikit-learn ML classifier (`error-clf-v1.0.0`) is trained on an execution-validated Python corpus and combines compiler/runtime feature cues for multi-language error diagnosis.
- **Judge0 Infrastructure Requirement:** Judge0 CE requires Linux kernel cgroups (`privileged: true`), preventing deployment inside standard serverless/unprivileged PaaS sandboxes without a dedicated VM, managed Judge0 host, or the implemented `$0` outbound local Windows execution worker (`worker_queue`).
- **Empirical Learning Study:** Controlled classroom user testing (`docs/capstone/USER_TESTING_AND_CONSENT.md`) is prepared and marked pending prior to live cohort evaluation.
