# ADR-001: Modular Monolith Backend with Isolated Code Execution

- **Status:** Accepted
- **Date:** 2026-11-20
- **Decision Makers:** Architecture & Capstone Engineering Team

## Context

CodeMentor AI spans identity, curriculum, adaptive recommendations, untrusted code execution, ML error classification, RAG retrieval, Socratic tutoring, classroom assignments, and admin governance. We need an architecture that is reliable, explainable in a capstone viva, simple to test end-to-end, and secure when running arbitrary student code.

## Decision

1. Implement the application backend as a **Modular Monolith** in FastAPI (`backend/app/`) with clear domain boundaries under `services/`, `repositories/`, `schemas/`, `models/`, and `integrations/`.
2. Isolate **untrusted student code execution** completely outside the API host inside dedicated **Judge0 CE** containers (`docker-compose.yml` `execution` profile).
3. Run own `scikit-learn` ML inference in-process behind a versioned service interface so it can later be extracted if load requires.

## Consequences

- **Positive:** Single deployable backend, transactional consistency across learning events and submissions, fast local debugging, clean OpenAPI contract, strong security boundary for student code.
- **Trade-offs:** Domain module boundaries must be enforced via code review and architecture discipline so modules do not tightly couple to each other's internals.
