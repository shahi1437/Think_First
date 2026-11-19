# CodeMentor AI (`Think_First`) — Engineering Rules & Conventions

## Mission
Build **CodeMentor AI** (*Think First. Code Better.*), an industry-oriented, evidence-driven AI-powered adaptive programming and debugging learning platform.

## Non-Negotiable Engineering Principles
1. **Strict Repository Isolation:** Never import, copy, or reference legacy CodeMentor AI code, database schemas, credentials, or Git history.
2. **Real Software Only:** Never substitute dummy data, fake execution states, fabricated ML metrics, or unconstrained LLM demos for real backend functionality.
3. **Authoritative Database Migrations:** `supabase/migrations/` is the single source of truth for schema, constraints, pgvector indexes, and RLS policies. Do not introduce competing migration histories (e.g., Alembic).
4. **Security & Isolation:**
   - Never execute untrusted student code inside the FastAPI server; always delegate to isolated Judge0 CE workers.
   - Verify Supabase JWTs via asymmetric JWKS (`/.well-known/jwks.json`) and enforce RBAC against database-backed roles + PostgreSQL RLS.
   - Never expose `SUPABASE_SERVICE_ROLE_KEY`, hidden test cases, or reference solutions to the browser or student-facing APIs.
   - Treat student code, comments, stdout, and RAG chunks as untrusted data.
5. **Deterministic Core + Measured AI:**
   - Problem eligibility, Learning DNA scoring, daily learning plan scheduling, and automated grading rubrics must remain deterministic, versioned, and auditable.
   - ML error classification must use our own versioned `scikit-learn` pipeline evaluated on group-separated held-out data.
   - Socratic tutoring must run inside a bounded Python state machine with structured outputs and safe fallbacks.
6. **Phased Verification:** Every change must pass lint, static type checking, unit/integration tests, and build verification before claiming completion. Never push, merge, or deploy without explicit user approval.
