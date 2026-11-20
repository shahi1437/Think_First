-- Phase 9: Performance & Observability B-Tree Indexes
-- Idempotent index additions for hot dashboard, audit, grading, and analytics queries.

CREATE INDEX IF NOT EXISTS idx_learning_events_event_type_created
    ON public.learning_events (event_type, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_learning_events_student_verdict_created
    ON public.learning_events (student_id, verdict, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_audit_logs_target_type_created
    ON public.audit_logs (target_type, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_audit_logs_action_created
    ON public.audit_logs (action, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_assignment_submissions_course_status
    ON public.assignment_submissions (course_id, status);

CREATE INDEX IF NOT EXISTS idx_submissions_problem_created
    ON public.submissions (problem_id, created_at DESC);
