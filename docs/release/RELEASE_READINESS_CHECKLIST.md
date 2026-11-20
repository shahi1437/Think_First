# CodeMentor AI (Think_First) — Release Readiness & Architecture Notes

## 1. Environment Variables Matrix
| Variable | Side | Purpose | Public Safe? |
|---|---|---|---|
| `NEXT_PUBLIC_APP_URL` | Frontend | Canonical frontend origin | Yes |
| `NEXT_PUBLIC_API_BASE_URL` | Frontend | FastAPI base URL | Yes |
| `NEXT_PUBLIC_SUPABASE_URL` | Frontend | Supabase Auth endpoint | Yes |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Frontend | Public Supabase anon key (RLS enforced) | Yes |
| `DATABASE_URL` | Backend | Async PostgreSQL connection string (`asyncpg`) | **NO** |
| `SUPABASE_URL` | Backend | Used for JWKS asymmetric token verification | Internal |
| `JUDGE0_BASE_URL` / `JUDGE0_AUTH_TOKEN` | Backend | Isolated Judge0 CE execution engine | **Token: NO** |
| `LLM_PROVIDER`, `LLM_MODEL`, `LLM_API_KEY` | Backend | Socratic AI Mentor provider (`gemini`) | **API Key: NO** |
| `RATE_LIMIT_ENABLED`, `API_WRITE_RATE_LIMIT_PER_MINUTE`, `CLASS_JOIN_RATE_LIMIT_PER_MINUTE` | Backend | Sliding-window write/join protection | Config only |
| `CORS_ORIGINS` | Backend | Allowed frontend origins | Config only |

> Never commit `.env`, `.env.local`, `backend/.env`, `frontend/.env.local`, or `backend/protected_content/*.local.json`.

## 2. Deployment Architecture & Security Controls
- **Browser -> Next.js (`:3100` / Vercel/Container):** Enforces HTTP security headers (`X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy`, `Permissions-Policy`, `poweredByHeader: false`).
- **Next.js / Browser -> FastAPI (`:8100`):** Asymmetric JWKS verification (`RS256`/`ES256`/`EdDSA`), DB-backed RBAC (`student`, `teacher`, `admin`), sliding-window IP rate limiter, 2 MiB body guard, `Cache-Control: no-store` on `/api/*`, structured JSON logs + slow-request warnings (`>= 2500 ms`).
- **FastAPI -> PostgreSQL (`pgvector`):** `FORCE ROW LEVEL SECURITY` enabled on **55/55** tables in `public`.
- **FastAPI -> Judge0 CE:** Untrusted learner code runs exclusively inside Judge0 sandboxes — never via `eval`/`exec`.

## 3. Migration Safety & Rollback Plan
- All schema changes live strictly in ordered files `supabase/migrations/20261120000001..0008.sql` and are additive/idempotent where practical (`CREATE INDEX IF NOT EXISTS`).
- **Rollback Plan:**
  1. Application rollback: revert to previous tagged release commit (`git checkout <tag>`) while keeping forward-compatible columns intact.
  2. Index rollback: drop newly added Phase 9 indexes individually with `DROP INDEX IF EXISTS` without downtime.
  3. Full DB rollback: restore pre-release PITR snapshot using `docs/operations/BACKUP_AND_RECOVERY.md`.

## 4. Known Limitations & Operational Notes
- Rate limiting (`InMemorySlidingWindowRateLimiter`) operates per backend worker process; multi-replica production deployments should front FastAPI with a shared Redis limiter or API gateway rate limit.
- Next.js `npm audit` reports upstream transitive findings inside dev/build tooling or framework packages that should be tracked during scheduled dependency upgrades without breaking React 19 / Next.js 16 compatibility.
- Protected curriculum bundles (`phase8_curriculum.local.json`) remain outside Git and must be imported into new environments via `backend/scripts/import_curriculum_bundle.py`.

## 5. Pre-Demo & Verification Checklist
- [ ] Docker Supabase & Judge0 containers healthy (`docker ps`)
- [ ] FastAPI `/health/ready` returns `200` and `/api/v1/admin/operations/health` reports `postgresql=ok`, `judge0=ok`, `ml_classifier=ok`, `llm_provider_mode=live_llm`
- [ ] All 6 Playwright specs (`phase3`..`phase8`), backend `pytest`, `ml/tests`, `ruff`, `mypy`, `vitest`, and `next build` pass
- [ ] Public repository has zero tracked `.env` or `.local.json` files
