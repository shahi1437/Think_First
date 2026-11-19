# CodeMentor AI — Think First. Code Better.

An industry-oriented AI-powered adaptive programming and debugging learning platform built as a university capstone project.

## Architecture Overview

CodeMentor AI is implemented as a **Modular Monolith** with strict execution isolation:

- **Frontend (`frontend/`):** Next.js 16 (App Router), React 19, TypeScript, Tailwind CSS v4, TanStack Query, Zod, Monaco Editor (Phase 3+), Supabase SSR (`@supabase/ssr`, Phase 2+).
- **Backend (`backend/`):** FastAPI, Pydantic v2, SQLAlchemy 2.x (async), `asyncpg`, structured JSON logging (`structlog`), OpenAPI 3.1 contract generation.
- **Database & Auth (`supabase/`):** Supabase PostgreSQL with Row Level Security (RLS), `pgvector` for RAG retrieval, and single-source-of-truth SQL migrations.
- **Code Execution (`docker-compose.yml`):** Isolated Judge0 CE execution service (Phase 3+).
- **AI / ML (`ml/`, `backend/app/services/mentor/`):** Own `scikit-learn` error classifier, `pgvector` RAG over approved knowledge documents, and a bounded Socratic state-machine tutor (Phase 4 & 6).

## Local Prerequisites

- Node.js `>= 22` and npm
- Python `>= 3.12, < 3.15`
- Docker Desktop (for local PostgreSQL + `pgvector` and Judge0 CE)

## Quick Start (Phase 1 Foundation)

### 1. Configure Environment Variables

Copy `.env.example` to `.env` (root), `backend/.env`, and `frontend/.env.local` as needed. Never commit `.env` files.

```bash
cp .env.example .env
```

### 2. Start Local Database (PostgreSQL + pgvector)

```bash
docker compose up -d postgres
```

### 3. Run Backend (FastAPI)

```bash
cd backend
python3 -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

Verify health endpoints:
- Liveness: `GET http://localhost:8000/health/live`
- Readiness: `GET http://localhost:8000/health/ready`
- OpenAPI docs: `http://localhost:8000/docs`

### 4. Run Frontend (Next.js)

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`.

## Quality & Verification Commands

### Backend
```bash
cd backend
ruff check .
ruff format --check .
mypy app
pytest
```

### Frontend
```bash
cd frontend
npm run lint
npx tsc --noEmit
npm test
npm run build
```

## Documentation

- [ADR-001: Modular Monolith Architecture](docs/architecture/ADR-001-modular-monolith.md)
- [ADR-002: Authoritative Supabase SQL Migrations](docs/architecture/ADR-002-database-migrations.md)
- [ADR-003: Asymmetric JWKS Auth, DB-Backed RBAC & PostgreSQL RLS](docs/architecture/ADR-003-auth-jwks-and-rls.md)
- [ADR-004: Isolated Judge0 CE Execution & Problem Content Governance](docs/architecture/ADR-004-judge0-and-problem-governance.md)
