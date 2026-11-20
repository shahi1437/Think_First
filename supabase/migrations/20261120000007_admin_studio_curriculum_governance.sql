-- =============================================================================
-- Migration 0007: Advanced Admin Studio, Curriculum Governance & Validation Engine
-- Authoritative schema for CodeMentor AI (Think_First) — Phase 8
-- =============================================================================

-- 1. Extend problem_versions with optional learner-track metadata for filtering/alignment
ALTER TABLE public.problem_versions
    ADD COLUMN IF NOT EXISTS track_slug text REFERENCES public.learning_tracks(slug) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_problem_versions_track
    ON public.problem_versions (track_slug, status, difficulty);

-- 2. Extend problem_reference_solutions with expected failure category for debugging validation
ALTER TABLE public.problem_reference_solutions
    ADD COLUMN IF NOT EXISTS expected_failure_category text;

-- 3. Allow 'archived' lifecycle action in content_reviews
ALTER TABLE public.content_reviews
    DROP CONSTRAINT IF EXISTS content_reviews_action_check;

ALTER TABLE public.content_reviews
    ADD CONSTRAINT content_reviews_action_check
    CHECK (action IN ('validated', 'submitted_for_review', 'approved', 'rejected', 'published', 'archived'));

-- 4. Allow rich governance statuses on lesson_versions & diagnostic_questions
ALTER TABLE public.lesson_versions
    DROP CONSTRAINT IF EXISTS lesson_versions_status_check;

ALTER TABLE public.lesson_versions
    ADD CONSTRAINT lesson_versions_status_check
    CHECK (status IN ('draft', 'validated', 'in_review', 'approved', 'published', 'archived'));

ALTER TABLE public.diagnostic_questions
    DROP CONSTRAINT IF EXISTS diagnostic_questions_status_check;

ALTER TABLE public.diagnostic_questions
    ADD CONSTRAINT diagnostic_questions_status_check
    CHECK (status IN ('draft', 'validated', 'in_review', 'approved', 'published', 'archived'));

-- 5. Private reference solution & validation summary on diagnostic_question_answers (strictly Admin-only RLS)
ALTER TABLE public.diagnostic_question_answers
    ADD COLUMN IF NOT EXISTS reference_solution text,
    ADD COLUMN IF NOT EXISTS validation_summary jsonb NOT NULL DEFAULT '{}'::jsonb;

-- 6. Curriculum validation log table (Admin-only audit of Judge0 curriculum validation runs)
CREATE TABLE IF NOT EXISTS public.curriculum_validations (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    target_type text NOT NULL CHECK (target_type IN ('problem_version', 'lesson_version', 'diagnostic_question')),
    target_id uuid NOT NULL,
    validator_id uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
    passed boolean NOT NULL,
    summary jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_curriculum_validations_target
    ON public.curriculum_validations (target_type, target_id, created_at DESC);

ALTER TABLE public.curriculum_validations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.curriculum_validations FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS curriculum_validations_admin_only ON public.curriculum_validations;
CREATE POLICY curriculum_validations_admin_only
    ON public.curriculum_validations FOR SELECT TO authenticated
    USING (public.has_role(auth.uid(), 'admin'));
