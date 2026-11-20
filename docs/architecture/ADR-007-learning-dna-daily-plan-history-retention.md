# ADR-007: Live Gemini Socratic Tutor, Learning DNA, Adaptive Daily Plan, Persistent History & Spaced Retention

- **Status:** Accepted
- **Date:** 2026-11-20
- **Phase:** Phase 6 (with Live Gemini AI Activation)

## Context
Phases 1–5 established isolated Judge0 execution, own ML error classification, approved `pgvector` RAG, bounded Socratic tutoring, 4 learning tracks, 8 bilingual beginner lessons, an 8-domain adaptive diagnostic, and a prerequisite-aware Skill Graph. Two major milestones remained:
1. Activating a real live Gemini LLM inside the bounded Socratic Mentor while preserving prompt-injection protection, solution-leakage blocking, Bangla/English pedagogy, and honest `provider_mode` reporting.
2. Providing longitudinal student growth tooling: evidence-based Learning DNA, time-budgeted Adaptive Daily Learning Plans, a searchable Persistent Learning History timeline, and delayed Judge0-backed Retention Verification.

## Decision

### 1. Live Gemini Integration (`backend/app/integrations/llm/client.py`)
- Authenticate against Google AI Studio (`generativelanguage.googleapis.com/v1beta/models/{LLM_MODEL}:generateContent`) via the `x-goog-api-key` header (never URL query parameters, preventing key leakage in logs).
- Enforce structured JSON output via Gemini `responseMimeType: "application/json"` + `responseSchema`.
- Preserve deterministic Python state-machine invariants server-side: `next_state` and `hint_level` remain controlled by Python, prompt-injection detection executes *before* any LLM call, and solution-leakage checks run *after* every LLM response.
- Report `provider_mode="live_llm"` only when Gemini returns a validated, leak-free response; fall back transparently to `provider_mode="deterministic_fallback"` on provider error or safety block.

### 2. Evidence-Based Learning DNA (`learning_dna_snapshots`)
- Compute 6 dimensions (`tracing`, `coding`, `debugging`, `testing`, `transfer`, `retention`) deterministically from persisted diagnostic responses, lesson progress, Judge0 submissions, code revisions, ML diagnoses, hint events, transfer attempts, retention attempts, and authoritative Skill Graph states.
- Use categorical evidence bands (`unobserved`, `emerging`, `developing`, `verified`) backed by exact counts — never fabricated numeric percentages or mastery marks.

### 3. Adaptive Daily Learning Plans (`daily_learning_plans`, `daily_plan_tasks`)
- Deterministically schedule daily tasks within `available_minutes` (15–240 min) prioritized by: due retention checks → incomplete 8-domain diagnostic → diagnostic-gap / prerequisite-ready lessons → unlocked transfer challenges → debugging/coding problems → upcoming retention prep.
- Regeneration archives the prior active version and creates `version_number + 1`, preserving complete plan history under a partial unique index `(student_id, plan_date) WHERE is_active = TRUE`.

### 4. Persistent Learning History & Spaced Retention (`retention_schedules`, `retention_attempts`)
- Aggregate all real persisted learner artifacts across 10 searchable, filterable categories (`lesson`, `diagnostic`, `submission`, `revision`, `mentor`, `hint`, `transfer`, `skill`, `daily_plan`, `retention`).
- Auto-schedule 24-hour spaced retention checks for verified skills using real published Python problems.
- Execute all retention attempts on real Judge0 (`ExecutionService`, full public + hidden tests). Enforce `elapsed_hours >= 24.0` before transitioning Skill Graph to `retained`; early passes are honestly recorded as `passed_too_early`.
- Enforce `ENABLE ROW LEVEL SECURITY` and `FORCE ROW LEVEL SECURITY` across all 5 Phase 6 tables with strict `student_id = auth.uid()` isolation.

## Consequences
- Every learner recommendation, DNA band, timeline entry, and retention badge is fully auditable for capstone viva review.
- Zero dummy data, zero client-side code execution, and zero unverified retention claims.
