# CodeMentor AI (Think_First) — Local Setup & CI Guide

## 1. Prerequisites
- **Node.js** `>= 22` and `npm`
- **Python** `3.12`–`3.14`
- **Docker Desktop** (for local Supabase PostgreSQL + `pgvector` and Judge0 CE isolated code execution)

## 2. Isolated Local Services
1. Start local Supabase stack (API `:54321`, Postgres `:54322`) and Judge0 CE (`:2359`):
   ```powershell
   npx supabase start
   docker compose up -d
   ```
2. Apply ordered SQL migrations cleanly (single source of truth in `supabase/migrations/20261120000001..0008.sql`) and idempotent seeds (`supabase/seed/001..004.sql`).
3. Import protected curriculum bundles safely (kept gitignored in `backend/protected_content/*.local.json`):
   ```powershell
   cd backend
   .venv\Scripts\python.exe scripts\import_curriculum_bundle.py --file protected_content/phase8_curriculum.local.json
   ```

## 3. Running Backend & Frontend Locally
- **FastAPI Backend (`http://127.0.0.1:8100`):**
  ```powershell
  cd backend
  .venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8100
  ```
- **Next.js Frontend (`http://localhost:3100`):**
  ```powershell
  cd frontend
  npm run dev -- --port 3100
  ```

## 4. Verification & Reproducibility Commands
### Backend + ML
```powershell
cd backend
.venv\Scripts\ruff.exe check app tests scripts
.venv\Scripts\ruff.exe format --check app tests scripts
.venv\Scripts\mypy.exe app
.venv\Scripts\python.exe -m pytest -v tests
```
For full live PostgreSQL + Judge0 + Gemini integration verification:
```powershell
$env:RUN_LIVE_INTEGRATION_TESTS="1"
.venv\Scripts\python.exe -m pytest -v tests
```
Run ML pipeline verification from repository root:
```powershell
backend\.venv\Scripts\python.exe -m pytest -v ml/tests
```

### Frontend & Playwright E2E
```powershell
cd frontend
npm run lint
npx tsc --noEmit
npx vitest run
npm run build
npx playwright test --reporter=list
```

## 5. Continuous Integration (`.github/workflows/ci.yml`)
CI triggers automatically on push/PR to `main` and `develop`:
1. **secret-hygiene-and-migrations:** Ensures no `.env*` or `*.local.json` curriculum bundles are committed and verifies monotonic SQL migration filenames.
2. **backend:** Runs `ruff check`, `ruff format --check`, `mypy app`, `pytest -v`, and `ml/tests`.
3. **frontend:** Runs `npm ci`, `npm audit`, ESLint, `tsc --noEmit`, Vitest, and `next build`.
