# ADR-004: Isolated Judge0 CE Execution & Problem Content Governance

- **Status:** Accepted
- **Date:** 2026-11-20
- **Decision Makers:** Full-Stack, Security & DevOps Engineering Team

## Context

Phase 3 introduces untrusted student code execution and an Admin-authored problem catalog containing private reference solutions and hidden test suites.

## Decision

1. **Zero In-Process Code Execution:** FastAPI never invokes `exec`, `eval`, or subprocesses on student code. Every `run` and `submit` request is serialized (base64-encoded), quota-checked (per-minute rate limit and daily quota), and dispatched asynchronously to an isolated **Judge0 CE `1.13.1`** container (`ENABLE_NETWORK=false`, bounded CPU/wall/memory/process limits).
2. **WSL2 / cgroup v2 Compatibility:** Local Docker Desktop environments running cgroup v2 enable `ENABLE_PER_PROCESS_AND_THREAD_TIME_LIMIT=true` and `ENABLE_PER_PROCESS_AND_THREAD_MEMORY_LIMIT=true` on Judge0 containers so `isolate` enforces resource limits reliably without requiring legacy cgroup v1 mounts.
3. **Database-Level Secret Isolation:** Private reference solutions and expected bug summaries live in a dedicated `public.problem_reference_solutions` table guarded by Admin-only PostgreSQL RLS (`public.has_role(auth.uid(), 'admin')`). Hidden `test_cases` rows (`is_hidden = true`) are similarly blocked by RLS for students and stripped of `input_data`, `expected_output`, `stdout`, and `stderr` in student-facing API responses.
4. **Validated Publishing Pipeline:** Problems follow `draft -> validated -> approved -> published`. Automated validation executes every variant's private reference solution against 100% of public + hidden tests on Judge0, and for `debugging` problems additionally verifies that `buggy_starter_code` fails at least one test. Publishing unvalidated drafts is rejected with `409 CANNOT_PUBLISH_UNVALIDATED`.
5. **Immutable Versioning:** Editing a published problem creates a new `version_number` draft so existing student submissions and historical evaluations remain linked to their exact `problem_version_id`.

## Consequences

- **Positive:** Strong execution sandbox isolation, provable hidden-test confidentiality at both API and PostgreSQL RLS layers, and verified debugging starter code before any student sees a problem.
- **Trade-offs:** Automated Admin validation requires a live Judge0 instance and runs synchronously across test cases for the authored problem.
