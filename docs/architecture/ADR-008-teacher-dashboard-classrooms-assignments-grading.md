# ADR-008: Teacher Dashboard, Classroom Management, Assignments, Judge0 Evaluation & Auditable Grading

- **Status:** Accepted
- **Date:** 2026-11-20
- **Phase:** Phase 7

## Context
Phases 1–6 delivered the student-facing adaptive learning and debugging ecosystem. Phase 7 extends `Think_First` (**CodeMentor AI**) into an instructor-led university classroom platform where Admin-authorized teachers manage courses, invite students securely, assign Admin-approved published problems, inspect real Judge0 student attempts, request revisions, and publish auditable grades and written feedback.

## Decision

### 1. Authoritative Schema & Strict Row-Level Security (`20261120000006_classrooms_assignments_grading.sql`)
- Added 10 tables in `public`: `courses`, `class_invitations`, `course_memberships`, `assignments`, `assignment_problem_links`, `assignment_submissions`, `assignment_attempts`, `assignment_grades`, `teacher_feedback`, and `grading_audit_events`.
- Enabled `ROW LEVEL SECURITY` and `FORCE ROW LEVEL SECURITY` on all 10 tables with `SECURITY DEFINER` helpers (`public.is_course_teacher`, `public.is_enrolled_student`).
- **Invitation Security:** Codes use a 10-character unambiguous alphabet (`CM-XXXXX-XXXXX`, 50 bits of entropy), are stored as SHA-256 hashes (`code_hash`), are rate-limited on redemption, and `class_invitations` is strictly inaccessible to students via RLS.
- **Grade Privacy & Auditability:** `assignment_grades` RLS permits student `SELECT` only when `student_id = auth.uid() AND status IN ('published', 'revision_requested')`. Every draft save, revision request, publication, and update appends an immutable row to `grading_audit_events`.

### 2. Reproducible Problem Pinning & Server-Enforced Submission Policy
- `AssignmentService` validates that every problem linked to an assignment is Admin-approved (`status = 'published'`) and pins its exact `problem_version_id` in `assignment_problem_links`.
- `evaluate_submission_eligibility` and `submit_student_assignment` enforce active course membership, `opens_at`/`due_at` deadlines (UTC), `allow_late_submissions`, `max_attempts`, `allow_ai_hints`/`hint_limit`, and revision resubmission (`allow_resubmission_on_revision`) on the **server** before delegating code execution to isolated Judge0 CE workers via `ExecutionService`.

### 3. Evidence-Based Teacher Dashboard & Class Analytics
- `TeacherAnalyticsService` computes real PostgreSQL aggregations scoped strictly to the teacher's authorized classes: enrollment counts, active assignments, upcoming deadlines, pending/graded submission counts, Judge0 attempt verdict distributions, ML `error_diagnoses` misconception frequencies, Skill Graph gap distributions, AI hint usage vs. independent transfer counts, and students needing support (`>= 2` non-accepted attempts with `0` accepted or high hint reliance). Never fabricates completion percentages or AI-generated estimates.

## Consequences
- Cross-teacher isolation (`Teacher B` receives `403` on `Teacher A`'s classes/assignments/submissions) and cross-student grade privacy are enforced at both the FastAPI service layer and PostgreSQL RLS.
- All Phase 1–6 modules (including Live Gemini Socratic mentoring) remain intact.
