# ADR-006: Evidence-Based Four Learning Tracks, Bilingual Beginner Lessons, Adaptive 8-Domain Diagnostics & Prerequisite Skill Graph

- **Status:** Accepted (Phase 5)
- **Date:** 2026-11-20
- **Decision Makers:** CodeMentor AI Architecture Team

## Context

Phase 5 introduces structured beginner onboarding, diagnostic assessment, prerequisite-aware competency modeling, and explainable next-step recommendations while preserving all Phase 1–4 auth, RBAC, Judge0, ML, RAG, Socratic Mentor, and Transfer Verification capabilities.

Key pedagogical and engineering invariants:
1. **No mastery from self-report:** Onboarding preferences may suggest an initial track, but verified placement requires observed 8-domain diagnostic evidence.
2. **Honest competency states:** Reading a lesson or recognizing an MCQ option (`introduced`) is NOT mastery; guided practice (`guided`) is distinct from unassisted execution (`independent`), unseen transfer (`transferred`), and delayed retention (`retained`, >= 24h later).
3. **Strict answer-key isolation:** Private diagnostic answers and Judge0 evaluation tests live in a separate table (`diagnostic_question_answers`) protected by admin-only `FORCE ROW LEVEL SECURITY`.
4. **Explainable recommendations first:** Next-step recommendations use deterministic prerequisite & evidence-gap rules with explicit English/Bangla rationale and `evidence_factors` rather than opaque or fabricated AI personalization claims.

## Decisions

### 1. Four Learning Tracks (`learning_tracks`, `student_track_enrollments`)
- Seeded 4 tracks (`absolute_beginner`, `basic_university`, `intermediate`, `advanced`) with bilingual descriptions and focus skills.
- `student_track_enrollments` separates `selected_track_slug`, `recommended_track_slug`, and `recommendation_source` (`onboarding_initial` | `diagnostic_evidence` | `manual_selection`).

### 2. Versioned Bilingual Beginner Python Lessons (`lessons`, `lesson_versions`, `lesson_progress`)
- Seeded 8 published English/Bangla Python lessons (`intro-to-programming`, `variables-and-data-types`, `input-and-output`, `conditions-and-branching`, `loops-and-boundaries`, `lists-and-indexing`, `functions-and-returns`, `debugging-basics`).
- Each lesson includes concept markdown, learning objectives, worked interactive examples, and a real Judge0 CE guided practice exercise. Lesson completion (`status = 'completed'`) requires passing all Judge0 test cases.

### 3. Adaptive 8-Domain Diagnostic Assessment (`diagnostic_questions`, `diagnostic_question_answers`, `diagnostic_sessions`, `diagnostic_responses`)
- Covers all 8 domains: `variables`, `syntax_runtime_debugging`, `conditions`, `loop_boundaries`, `arrays_lists`, `indexing`, `functions`, and `mixed_logic` (`18` admin-reviewed published items, including `4` real Judge0 execution checks).
- Adaptive queue starts with 1 `core` probe per domain and dynamically adds up to 3 targeted follow-ups (`foundation` probes after misses; real Judge0 `stretch` coding probes after passing key `core` checks).
- Computes factual per-domain evidence (`observed_correct / observed_attempts`, `execution_verified`, `evidence_status`) without fabricating marks or percentages.

### 4. Prerequisite-Aware Skill Graph (`skill_nodes`, `skill_prerequisites`, `student_skill_states`, `skill_state_transitions`)
- Models a 10-node, 16-edge Python prerequisite DAG across 5 tiers.
- Enforces monotonic evidence-based transitions (`unobserved -> introduced -> guided -> independent -> transferred -> retained`), automatically projecting Phase 4 `verified_independent` transfer attempts into `transferred`, logging every transition in `skill_state_transitions`, and blocking immediate `retained` claims unless >= 24h have elapsed since first verification.

### 5. Security & Governance
- All 14 new Phase 5 tables enforce `FORCE ROW LEVEL SECURITY`.
- Admin-only publishing endpoints (`/api/v1/admin/learning/lessons`, `/api/v1/admin/learning/diagnostic-questions`) require DB-backed `admin` role.
- Cross-student isolation is enforced in both FastAPI services and PostgreSQL RLS.
