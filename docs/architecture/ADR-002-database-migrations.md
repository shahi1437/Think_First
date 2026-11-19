# ADR-002: Authoritative Supabase SQL Migrations as Single Source of Truth

- **Status:** Accepted
- **Date:** 2026-11-20
- **Decision Makers:** Database & Architecture Team

## Context

The platform relies heavily on PostgreSQL-native features: Row Level Security (RLS) policies, `auth.users` foreign keys, signup triggers, check constraints, and `pgvector` HNSW indexes. Maintaining both Alembic migrations and Supabase SQL migrations risks schema drift and conflicting histories.

## Decision

1. Designate `supabase/migrations/` as the **single authoritative migration workflow**.
2. Author version-controlled, timestamped SQL migrations (`YYYYMMDDHHMMSS_<slug>.sql`) covering schema tables, constraints, indexes, extensions (`pgcrypto`, `vector`), triggers, and RLS policies together.
3. Map SQLAlchemy 2.x models in `backend/app/models/` strictly to the tables defined by `supabase/migrations/` without generating Alembic migration files.
4. Validate migrations from scratch in CI against a clean PostgreSQL + `pgvector` container starting in Phase 2.

## Consequences

- **Positive:** Zero competing migration histories; RLS policies and schema evolve atomically; full fidelity for PostgreSQL and `pgvector` features.
- **Trade-offs:** Developers must keep SQLAlchemy ORM models synchronized with SQL migrations and verify alignment via integration tests.
