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

### ML & RAG Evaluation (Phase 4)
```bash
# 1. Regenerate execution-validated Python error dataset (42 families, 309 samples)
python -m ml.preprocessing.generate_dataset

# 2. Train & evaluate grouped-split models (Rule-Based vs TF-IDF+LogReg vs Random Forest)
python -m ml.training.train

# 3. Evaluate verified RAG retrieval & no-match fallback
python -m ml.evaluation.evaluate_rag

# 4. Run ML pipeline tests
python -m pytest -v ml/tests
```

## Phase 4 API Endpoints (AI Mentor, Verified RAG & Independent Transfer)

| Method & Path | Role | Purpose |
| --- | --- | --- |
| `POST /api/v1/mentor/sessions` | Authenticated | Start or resume a Socratic AI Mentor session grounded in real Judge0 evidence |
| `GET /api/v1/mentor/sessions/{session_id}` | Owner / Admin | Fetch session dialogue, ML diagnosis, and approved RAG citations |
| `POST /api/v1/mentor/sessions/{session_id}/turns` | Owner / Admin | Submit `diagnose`, `respond`, or `request_hint` (3 progressive levels; 0 hints on transfer challenges) |
| `POST /api/v1/mentor/diagnose/{submission_id}` | Owner / Admin | Run own scikit-learn error classifier directly on a Judge0 submission |
| `GET /api/v1/verifications/problem/{source_problem_id}` | Authenticated | Inspect linked unseen transfer challenge and unlock status |
| `POST /api/v1/verifications/{link_id}/attempts` | Authenticated | Submit independent transfer solution evaluated on real Judge0 |
| `GET /api/v1/verifications/attempts` | Owner | List persisted transfer verification outcomes (`verified_independent` / `attempted_not_verified`) |
| `GET /api/v1/learning/events` | Owner | List traceable Phase 4 learning evidence events |
| `GET/POST /api/v1/admin/knowledge` | Admin | Manage instructor-reviewable RAG documents & `pgvector` embeddings |
| `POST /api/v1/admin/knowledge/seed` | Admin | Idempotently seed all 10 curated approved Python educational documents |
| `PATCH /api/v1/admin/knowledge/{doc_id}/status` | Admin | Approve, draft, or archive a knowledge document |
| `POST /api/v1/admin/knowledge/search` | Admin | Debug `pgvector` retrieval strictly over approved documents |

## Phase 5 API Endpoints (Tracks, Beginner Lessons, Adaptive Diagnostic & Skill Graph)

| Method & Path | Role | Purpose |
| --- | --- | --- |
| `GET /api/v1/learning/dashboard` | Authenticated | Unified Student Learning Dashboard (track status, lessons, Skill Graph, explainable recommendations) |
| `GET /api/v1/learning/tracks` | Authenticated | List 4 learner tracks and student's active vs. evidence-recommended track |
| `POST /api/v1/learning/tracks/select` | Authenticated | Select active learner track |
| `GET /api/v1/learning/lessons` | Authenticated | List 8 published bilingual beginner Python lessons with per-student progress |
| `GET /api/v1/learning/lessons/{slug}` | Authenticated | Fetch bilingual lesson markdown, interactive examples, and Judge0 guided exercise |
| `POST /api/v1/learning/lessons/{id}/reading` | Authenticated | Record reading completion (advances Skill Graph to `introduced`, not mastery) |
| `POST /api/v1/learning/lessons/{id}/exercise/run` | Authenticated | Execute guided practice on real Judge0 CE and persist lesson completion (`guided`) |
| `POST /api/v1/learning/diagnostics/sessions` | Authenticated | Start or resume 8-domain adaptive diagnostic assessment |
| `GET /api/v1/learning/diagnostics/sessions/{id}` | Owner / Admin | Fetch diagnostic state, adaptive follow-ups, and factual 8-domain evidence |
| `POST /api/v1/learning/diagnostics/sessions/{id}/answers` | Owner / Admin | Submit MCQ or real Judge0 code check and trigger adaptive next-question selection |
| `GET /api/v1/learning/skill-graph` | Authenticated | Fetch prerequisite-aware 10-node Skill Graph, uncertainty notes, and audited transitions |
| `GET /api/v1/learning/recommendations` | Authenticated | Explainable prerequisite-based next lesson, diagnostic, debugging, and transfer recommendations |
| `POST /api/v1/admin/learning/lessons` | Admin | Create/version/publish bilingual beginner lessons |
| `POST /api/v1/admin/learning/diagnostic-questions` | Admin | Create/publish diagnostic items with isolated private answer keys |

## Phase 6 API Endpoints (Learning DNA, Adaptive Daily Plan, Persistent History & Retention)

| Method & Path | Role | Purpose |
| --- | --- | --- |
| `GET /api/v1/growth/learning-dna` | Authenticated | Compute & persist evidence-based 6-dimension Learning DNA snapshot (tracing, coding, debugging, testing, transfer, retention) |
| `GET /api/v1/growth/daily-plan` | Authenticated | Fetch or generate today's time-budgeted Adaptive Daily Learning Plan & version history |
| `POST /api/v1/growth/daily-plan/regenerate` | Authenticated | Regenerate today's plan with updated study time budget while archiving prior versions |
| `PATCH /api/v1/growth/daily-plan/tasks/{task_id}` | Owner / Admin | Update task completion status (`pending` / `completed` / `skipped`) |
| `GET /api/v1/growth/history` | Authenticated | Searchable, category-filterable longitudinal timeline across lessons, diagnostics, Judge0, revisions, Mentor, hints, transfers, skills, daily plans, and retention |
| `GET /api/v1/growth/retention` | Authenticated | Sync 24-hour spaced retention schedules & list upcoming/due checks + attempt history |
| `POST /api/v1/growth/retention/{schedule_id}/attempts` | Owner / Admin | Execute real Judge0 retention check enforcing `>=24h` spacing before promoting Skill Graph to `retained` |

## Phase 7 API Endpoints (Teacher Dashboard, Classrooms, Assignments, Judge0 Submissions & Grading)

| Method & Path | Role | Purpose |
| --- | --- | --- |
| `GET /api/v1/teacher/dashboard` | Teacher / Admin | Real aggregated Teacher Dashboard (classes, enrolled students, active assignments, pending grading, Judge0 verdicts, ML misconceptions, skill gaps, support flags) |
| `GET/POST /api/v1/teacher/classes` | Teacher / Admin | List or create courses with auto-generated high-entropy invitation codes |
| `GET/PATCH /api/v1/teacher/classes/{course_id}` | Course Owner / Admin | Inspect or edit class metadata, invitations, student roster, assignments, and class analytics |
| `POST /api/v1/teacher/classes/{course_id}/archive` | Course Owner / Admin | Archive or restore a class without losing historical submissions or grades |
| `POST /api/v1/teacher/classes/{course_id}/invitations` | Course Owner / Admin | Generate new high-entropy SHA-256 hashed class invitation codes |
| `POST /api/v1/teacher/classes/{course_id}/invitations/{id}/revoke` | Course Owner / Admin | Revoke an invitation code |
| `PATCH /api/v1/teacher/classes/{course_id}/memberships/{id}` | Course Owner / Admin | Approve pending student membership or remove student from class roster |
| `GET/POST /api/v1/teacher/assignments` | Teacher / Admin | List or create draft/published assignments pinned to Admin-approved problem versions |
| `GET/PATCH /api/v1/teacher/assignments/{id}` | Assignment Owner / Admin | Inspect assignment submissions, code, Judge0 verdicts, grades, and immutable audit trail |
| `POST /api/v1/teacher/assignments/{id}/publish` | Assignment Owner / Admin | Publish a draft assignment to enrolled students |
| `POST /api/v1/teacher/assignments/{id}/archive` | Assignment Owner / Admin | Archive an assignment safely |
| `POST /api/v1/teacher/submissions/{id}/grade` | Assignment Owner / Admin | Save draft grade, request revision, or publish grade & written feedback with audit logging |
| `GET /api/v1/student/classes` | Authenticated | List student's active/pending enrolled classes |
| `POST /api/v1/student/classes/join` | Authenticated | Redeem a rate-limited class invitation code (`CM-XXXXX-XXXXX`) |
| `POST /api/v1/student/classes/{course_id}/leave` | Enrolled Student | Leave an enrolled class when permitted by class policy |
| `GET /api/v1/student/assignments` | Enrolled Student | Filter assignments (`all`, `pending`, `submitted`, `revision_requested`, `graded`, `overdue`) |
| `GET /api/v1/student/assignments/{id}` | Enrolled Student | Fetch assignment details, pinned problems, attempts, released grade, and feedback |
| `POST /api/v1/student/assignments/{id}/submit` | Enrolled Student | Evaluate code on real Judge0 and record an assignment attempt with server-enforced deadline, attempt, and hint limits |

## Documentation

- [ADR-001: Modular Monolith Architecture](docs/architecture/ADR-001-modular-monolith.md)
- [ADR-002: Authoritative Supabase SQL Migrations](docs/architecture/ADR-002-database-migrations.md)
- [ADR-003: Asymmetric JWKS Auth, DB-Backed RBAC & PostgreSQL RLS](docs/architecture/ADR-003-auth-jwks-and-rls.md)
- [ADR-004: Isolated Judge0 CE Execution & Problem Content Governance](docs/architecture/ADR-004-judge0-and-problem-governance.md)
- [ADR-005: Hybrid ML, Verified pgvector RAG, Socratic Mentor & Transfer Verification](docs/architecture/ADR-005-hybrid-ml-rag-socratic-mentor.md)
- [ADR-006: Adaptive Learning Tracks, Bilingual Lessons, 8-Domain Diagnostics & Skill Graph](docs/architecture/ADR-006-adaptive-learning-diagnostics-skill-graph.md)
- [ADR-007: Live Gemini Socratic Tutor, Learning DNA, Daily Plan, History & Spaced Retention](docs/architecture/ADR-007-learning-dna-daily-plan-history-retention.md)
- [ADR-008: Teacher Dashboard, Classroom Management, Assignments, Judge0 Evaluation & Auditable Grading](docs/architecture/ADR-008-teacher-dashboard-classrooms-assignments-grading.md)
- [ML Error Classifier Evaluation Report](docs/ai/ml-evaluation-report.md)
- [Verified RAG Retrieval Evaluation Report](docs/ai/rag-evaluation-report.md)

## Configuring a Live LLM Provider (Google Gemini / OpenAI / Ollama)

When configured in `backend/.env` (never commit real keys), the Socratic AI Mentor authenticates directly with the live provider and reports `provider_mode="live_llm"`, while keeping deterministic prompt-injection blocking, solution-leakage checks, and safe fallback (`provider_mode="deterministic_fallback"`):

- **Google Gemini (Verified Live):** `LLM_PROVIDER=gemini`, `LLM_MODEL=gemini-3.5-flash-lite`, `LLM_API_KEY=<your-key>`
- **OpenAI:** `LLM_PROVIDER=openai`, `LLM_MODEL=gpt-4o-mini`, `LLM_API_KEY=<your-key>`
- **Local Ollama:** `LLM_PROVIDER=ollama`, `LLM_MODEL=qwen2.5-coder:7b`, `LLM_BASE_URL=http://127.0.0.1:11434`
