# ADR-003: Asymmetric Supabase JWKS Authentication, DB-Backed RBAC & PostgreSQL RLS

- **Status:** Accepted
- **Date:** 2026-11-20
- **Decision Makers:** Security & Backend Architecture Team

## Context

CodeMentor AI serves three distinct roles (`student`, `teacher`, `admin`) with strict isolation requirements (students must never read other students' submissions or self-promote roles; teachers must only access authorized courses; hidden tests and reference solutions must remain strictly private).

## Decision

1. **Identity Provider:** Supabase Auth manages user registration, login, password recovery, and JWT issuance.
2. **Backend JWT Verification (`PyJWT[crypto]`):** FastAPI verifies Bearer JWTs locally using Supabase's asymmetric public key set (`{SUPABASE_URL}/auth/v1/.well-known/jwks.json`) cached in memory with TTL and single-refresh key-rotation fallback. `alg=none`, invalid signatures, expired tokens, wrong issuers, and wrong audiences are rejected with `401 UNAUTHORIZED`.
3. **Database-Backed Authorization:** Application roles (`student`, `teacher`, `admin`) are stored in `public.user_roles` and loaded on the backend for authorization decisions—never trusted from client requests or unverified frontend state.
4. **Signup Least Privilege:** The `on_auth_user_created` trigger provisions `profiles` and grants **only** the `student` role, ignoring any role metadata supplied by the client.
5. **Defense-in-Depth RLS:** PostgreSQL Row Level Security (`FORCE ROW LEVEL SECURITY`) restricts direct table access to own rows (or `admin` via `SECURITY DEFINER` helper `public.has_role`), with zero client write policies on `user_roles` and `audit_logs`.
6. **Frontend Session Refresh (`src/proxy.ts`):** Next.js 16 `proxy.ts` refreshes `@supabase/ssr` cookies on navigation and performs optimistic redirects, while Server Component guards verify DB-backed roles against `GET /api/v1/users/me`.

## Consequences

- **Positive:** Zero per-request auth roundtrip to Supabase, seamless asymmetric key rotation, verifiable protection against privilege escalation, auditable admin role mutations.
- **Trade-offs:** Backend requires database access on protected endpoints to verify active DB-backed roles (mitigated by primary-key indexed lookups on `user_roles`).
